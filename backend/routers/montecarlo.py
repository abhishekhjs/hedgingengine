"""Monte Carlo simulation endpoint."""
from fastapi import APIRouter
import pandas as pd
import numpy as np
import math
from typing import Dict, Any
from src.db.connection import get_connection
from backend.schemas.models import MonteCarloRequest, MonteCarloResponse
from src.analytics.exposure_calc import get_latest_market_data, calculate_company_risk
from src.analytics.monte_carlo import run_monte_carlo_simulation

router = APIRouter(prefix="/api/montecarlo", tags=["Monte Carlo"])


def sanitize_value(val):
    """Replace NaN/Inf with None for JSON serialization."""
    if isinstance(val, (float, np.floating)):
        if math.isnan(val) or math.isinf(val):
            return None
    return val


def sanitize_dict(d):
    """Recursively sanitize a dict of numeric values."""
    if isinstance(d, dict):
        return {k: sanitize_dict(v) for k, v in d.items()}
    if isinstance(d, (float, np.floating)):
        return sanitize_value(d)
    if isinstance(d, np.integer):
        return int(d)
    return d


@router.post("/run", response_model=MonteCarloResponse)
def run_mc(req: MonteCarloRequest):
    conn = get_connection()
    try:
        exposure_df = pd.read_sql(
            "SELECT * FROM company_exposure WHERE company_name = ?",
            conn, params=(req.company_name,)
        )
        hedge_df = pd.read_sql(
            "SELECT * FROM hedges WHERE company_name = ?",
            conn, params=(req.company_name,)
        )
        financials_row = pd.read_sql(
            "SELECT * FROM company_financials WHERE company_name = ?",
            conn, params=(req.company_name,)
        )
        financials = financials_row.iloc[0].to_dict() if not financials_row.empty else {}

        market_data = get_latest_market_data(conn)
        risk_profile = calculate_company_risk(exposure_df, hedge_df, market_data)

        mc_results = run_monte_carlo_simulation(conn, risk_profile, financials, req.n_iterations)

        # Build histogram data from simulation arrays
        hist_data = {}
        for key in ["simulated_ev", "simulated_fcf", "simulated_cash"]:
            if key in mc_results:
                arr = np.array(mc_results[key], dtype=float)
                arr = arr[np.isfinite(arr)]
                if len(arr) > 0:
                    counts, bins = np.histogram(arr, bins=50)
                    hist_data[key] = {
                        "counts": counts.tolist(),
                        "bins": bins.tolist()
                    }

        # Extract correlation matrix (already a DataFrame from MC engine)
        corr_data = {}
        if "correlation_matrix" in mc_results:
            corr_df = mc_results["correlation_matrix"]
            if isinstance(corr_df, pd.DataFrame):
                corr_data = {
                    "columns": corr_df.columns.tolist(),
                    "data": corr_df.fillna(0).values.tolist()
                }

        return {
            "risk_metrics": sanitize_dict(mc_results.get("risk_metrics", {})),
            "base_ev": sanitize_value(mc_results.get("base_ev", 0.0)),
            "base_fcf": sanitize_value(mc_results.get("base_fcf", 0.0)),
            "base_cash": sanitize_value(mc_results.get("base_cash", 0.0)),
            "correlation_matrix": corr_data,
            "liquidity_shortfall_prob": sanitize_value(mc_results.get("liquidity_shortfall_prob", 0.0)),
            "histogram_data": hist_data
        }
    finally:
        conn.close()

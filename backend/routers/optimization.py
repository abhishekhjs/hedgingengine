from fastapi import APIRouter
from typing import Dict, Any, List
import pandas as pd
from src.db.connection import get_connection
from backend.schemas.models import OptimizationRequest, FrontierRequest
from src.analytics.exposure_calc import (
    get_latest_market_data,
    calculate_company_risk,
    compute_hedge_coverage_ratios,
    compute_proximity_scores
)
from src.analytics.monte_carlo import run_monte_carlo_simulation
from src.analytics.hedge_optimizer import (
    compute_hedge_priority_scores,
    compute_factor_attribution,
    compute_efficient_frontier
)

router = APIRouter(prefix="/api/optimization", tags=["Optimization"])

@router.post("/priority", response_model=List[Dict[str, Any]])
def get_priority(req: OptimizationRequest):
    conn = get_connection()
    try:
        exposure_df = pd.read_sql("SELECT * FROM company_exposure WHERE company_name = ?", conn, params=(req.company_name,))
        hedge_df = pd.read_sql("SELECT * FROM hedges WHERE company_name = ?", conn, params=(req.company_name,))
        financials_row = pd.read_sql("SELECT * FROM company_financials WHERE company_name = ?", conn, params=(req.company_name,))
        financials = financials_row.iloc[0].to_dict() if not financials_row.empty else {}
        
        market_data = get_latest_market_data(conn)
        risk_profile = calculate_company_risk(exposure_df, hedge_df, market_data)
        
        mc_results = run_monte_carlo_simulation(conn, risk_profile, financials, 1000)
        coverage_ratios = compute_hedge_coverage_ratios(risk_profile)
        proximity_scores = compute_proximity_scores(financials)
        
        df = compute_hedge_priority_scores(risk_profile, mc_results, coverage_ratios, proximity_scores)
        return df.to_dict(orient="records")
    finally:
        conn.close()

@router.post("/attribution", response_model=Dict[str, Any])
def get_attribution(req: OptimizationRequest):
    conn = get_connection()
    try:
        exposure_df = pd.read_sql("SELECT * FROM company_exposure WHERE company_name = ?", conn, params=(req.company_name,))
        hedge_df = pd.read_sql("SELECT * FROM hedges WHERE company_name = ?", conn, params=(req.company_name,))
        financials_row = pd.read_sql("SELECT * FROM company_financials WHERE company_name = ?", conn, params=(req.company_name,))
        financials = financials_row.iloc[0].to_dict() if not financials_row.empty else {}
        
        market_data = get_latest_market_data(conn)
        risk_profile = calculate_company_risk(exposure_df, hedge_df, market_data)
        
        attribution = compute_factor_attribution(conn, risk_profile, financials, 1000)
        return attribution
    finally:
        conn.close()

@router.post("/frontier", response_model=Dict[str, Any])
def get_frontier(req: FrontierRequest):
    conn = get_connection()
    try:
        exposure_df = pd.read_sql("SELECT * FROM company_exposure WHERE company_name = ?", conn, params=(req.company_name,))
        hedge_df = pd.read_sql("SELECT * FROM hedges WHERE company_name = ?", conn, params=(req.company_name,))
        financials_row = pd.read_sql("SELECT * FROM company_financials WHERE company_name = ?", conn, params=(req.company_name,))
        financials = financials_row.iloc[0].to_dict() if not financials_row.empty else {}
        
        market_data = get_latest_market_data(conn)
        risk_profile = calculate_company_risk(exposure_df, hedge_df, market_data)
        
        frontier_df = compute_efficient_frontier(conn, risk_profile, financials, req.steps)
        return {
            "index": frontier_df.index.tolist(),
            "columns": frontier_df.columns.tolist(),
            "data": frontier_df.values.tolist()
        }
    finally:
        conn.close()

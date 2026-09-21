from fastapi import APIRouter
from typing import Dict, Any
import pandas as pd
from src.db.connection import get_connection
from backend.schemas.models import TransmissionRequest
from src.analytics.exposure_calc import (
    get_latest_market_data,
    calculate_company_risk,
    calculate_financial_transmission,
    compute_proximity_scores
)

router = APIRouter(prefix="/api/transmission", tags=["Transmission"])

@router.post("/compute", response_model=Dict[str, Any])
def compute_transmission(req: TransmissionRequest):
    conn = get_connection()
    try:
        exposure_df = pd.read_sql("SELECT * FROM company_exposure WHERE company_name = ?", conn, params=(req.company_name,))
        hedge_df = pd.read_sql("SELECT * FROM hedges WHERE company_name = ?", conn, params=(req.company_name,))
        financials_row = pd.read_sql("SELECT * FROM company_financials WHERE company_name = ?", conn, params=(req.company_name,))
        financials = financials_row.iloc[0].to_dict() if not financials_row.empty else {}
        
        market_data = get_latest_market_data(conn)
        risk_profile = calculate_company_risk(exposure_df, hedge_df, market_data)
        
        transmission = calculate_financial_transmission(risk_profile, financials, req.sigma_multiplier)
        proximity_scores = compute_proximity_scores(financials)
        
        return {
            "transmission": transmission,
            "proximity_scores": proximity_scores
        }
    finally:
        conn.close()

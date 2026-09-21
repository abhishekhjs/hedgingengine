from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import pandas as pd
from src.db.connection import get_connection
from src.analytics.exposure_calc import get_latest_market_data
from backend.schemas.models import RiskMetricRow

router = APIRouter(prefix="/api/market", tags=["Market"])

@router.get("/risk-metrics", response_model=List[RiskMetricRow])
def get_risk_metrics():
    conn = get_connection()
    try:
        df = pd.read_sql("""
            SELECT m1.*
            FROM risk_metrics m1
            INNER JOIN (
                SELECT asset, MAX(date) as max_date
                FROM risk_metrics
                GROUP BY asset
            ) m2 ON m1.asset = m2.asset AND m1.date = m2.max_date
        """, conn)
        return df.to_dict(orient="records")
    finally:
        conn.close()

@router.get("/latest", response_model=Dict[str, Any])
def get_latest_market_data_endpoint():
    conn = get_connection()
    try:
        return get_latest_market_data(conn)
    finally:
        conn.close()

@router.get("/history/{asset}")
def get_market_history(asset: str):
    conn = get_connection()
    try:
        df = pd.read_sql(
            "SELECT date, value, vol_30d, vol_90d FROM risk_metrics WHERE asset = ? ORDER BY date DESC LIMIT 252",
            conn, params=(asset,)
        )
        return df.to_dict(orient="records")
    finally:
        conn.close()

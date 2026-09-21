from fastapi import APIRouter
from typing import List, Dict, Any
import pandas as pd
from src.db.connection import get_connection
from backend.schemas.models import CompanyExposure, HedgeInstrument, CompanyFinancials
from src.analytics.exposure_calc import get_latest_market_data, calculate_company_risk

router = APIRouter(prefix="/api/exposure", tags=["Exposure"])

@router.get("/companies", response_model=List[Dict[str, Any]])
def get_companies_exposure():
    conn = get_connection()
    try:
        df = pd.read_sql("SELECT * FROM company_exposure", conn)
        return df.to_dict(orient="records")
    finally:
        conn.close()

@router.post("/companies")
def upsert_companies_exposure(exposures: List[CompanyExposure]):
    conn = get_connection()
    try:
        df = pd.DataFrame([e.model_dump(exclude={"id"}) for e in exposures])
        df.to_sql("company_exposure", conn, if_exists="append", index=False)
        return {"status": "success"}
    finally:
        conn.close()

@router.get("/hedges", response_model=List[Dict[str, Any]])
def get_hedges():
    conn = get_connection()
    try:
        df = pd.read_sql("SELECT * FROM hedges", conn)
        return df.to_dict(orient="records")
    finally:
        conn.close()

@router.post("/hedges")
def upsert_hedges(hedges: List[HedgeInstrument]):
    conn = get_connection()
    try:
        df = pd.DataFrame([h.model_dump(exclude={"id"}) for h in hedges])
        df.to_sql("hedges", conn, if_exists="append", index=False)
        return {"status": "success"}
    finally:
        conn.close()

@router.get("/financials/{company_name}", response_model=Dict[str, Any])
def get_financials(company_name: str):
    conn = get_connection()
    try:
        df = pd.read_sql("SELECT * FROM company_financials WHERE company_name = ?", conn, params=(company_name,))
        return df.iloc[0].to_dict() if not df.empty else {}
    finally:
        conn.close()

@router.post("/financials")
def upsert_financials(financials: CompanyFinancials):
    conn = get_connection()
    try:
        df = pd.DataFrame([financials.model_dump(exclude={"id"})])
        df.to_sql("company_financials", conn, if_exists="append", index=False)
        return {"status": "success"}
    finally:
        conn.close()

@router.post("/risk-profile", response_model=Dict[str, Any])
def compute_risk_profile(payload: dict):
    company_name = payload.get("company_name")
    conn = get_connection()
    try:
        exposure_df = pd.read_sql("SELECT * FROM company_exposure WHERE company_name = ?", conn, params=(company_name,))
        hedge_df = pd.read_sql("SELECT * FROM hedges WHERE company_name = ?", conn, params=(company_name,))
        market_data = get_latest_market_data(conn)
        risk_profile = calculate_company_risk(exposure_df, hedge_df, market_data)
        return risk_profile
    finally:
        conn.close()

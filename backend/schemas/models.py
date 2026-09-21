"""Pydantic v2 models for API request/response serialization."""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any


# --- Database table models ---

class RiskMetricRow(BaseModel):
    date: str
    asset_class: Optional[str] = None
    asset: str
    value: Optional[float] = None
    return_1d: Optional[float] = None
    return_1m: Optional[float] = None
    return_3m: Optional[float] = None
    return_1y: Optional[float] = None
    vol_30d: Optional[float] = None
    vol_90d: Optional[float] = None
    high_52w: Optional[float] = None
    low_52w: Optional[float] = None
    drawdown_pct: Optional[float] = None
    z_score: Optional[float] = None
    percentile: Optional[float] = None


class CompanyExposure(BaseModel):
    id: Optional[int] = None
    company_name: str
    commodity: Optional[str] = None
    annual_quantity: Optional[float] = None
    currency: Optional[str] = None
    annual_imports: Optional[float] = None
    debt_amount: Optional[float] = None
    floating_rate_percentage: Optional[float] = None


class HedgeInstrument(BaseModel):
    id: Optional[int] = None
    company_name: str
    instrument: Optional[str] = None
    underlying: Optional[str] = None
    notional: Optional[float] = None
    strike: Optional[float] = None
    maturity: Optional[str] = None
    hedge_ratio: Optional[float] = None
    cost: Optional[float] = None


class CompanyFinancials(BaseModel):
    id: Optional[int] = None
    company_name: str
    base_revenue: Optional[float] = None
    base_cogs: Optional[float] = None
    base_opex: Optional[float] = None
    tax_rate: Optional[float] = None
    starting_cash: Optional[float] = None
    starting_debt: Optional[float] = None
    ev_ebitda_multiple: Optional[float] = None
    min_cash_buffer: Optional[float] = 0
    max_debt_ebitda_ratio: Optional[float] = 0


# --- Request/Response models ---

class TransmissionRequest(BaseModel):
    company_name: str
    sigma_multiplier: float = 1.0


class MonteCarloRequest(BaseModel):
    company_name: str
    n_iterations: int = 10000


class MonteCarloResponse(BaseModel):
    risk_metrics: Dict[str, Any]
    base_ev: Optional[float] = None
    base_fcf: Optional[float] = None
    base_cash: Optional[float] = None
    correlation_matrix: Dict[str, Any]
    liquidity_shortfall_prob: Optional[float] = None
    histogram_data: Dict[str, Any]


class OptimizationRequest(BaseModel):
    company_name: str


class FrontierRequest(BaseModel):
    company_name: str
    steps: int = 6


class IngestionStatus(BaseModel):
    status: Dict[str, str]

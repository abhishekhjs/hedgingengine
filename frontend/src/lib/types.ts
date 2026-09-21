/**
 * TypeScript interfaces matching the FastAPI Pydantic models
 * and the existing Python analytics engine output shapes.
 */

// --- Market Data ---

export interface RiskMetricRow {
  date: string;
  asset_class: string;
  asset: string;
  value: number | null;
  return_1d: number | null;
  return_1m: number | null;
  return_3m: number | null;
  return_1y: number | null;
  vol_30d: number | null;
  vol_90d: number | null;
  high_52w: number | null;
  low_52w: number | null;
  drawdown_pct: number | null;
  z_score: number | null;
  percentile: number | null;
}

export interface MarketDataPoint {
  price: number;
  vol: number;
}

export interface HistoryPoint {
  date: string;
  value: number;
  vol_30d: number | null;
  vol_90d: number | null;
}

// --- Company Data ---

export interface CompanyExposure {
  id?: number;
  company_name: string;
  commodity: string | null;
  annual_quantity: number | null;
  currency: string | null;
  annual_imports: number | null;
  debt_amount: number | null;
  floating_rate_percentage: number | null;
}

export interface HedgeInstrument {
  id?: number;
  company_name: string;
  instrument: string | null;
  underlying: string | null;
  notional: number | null;
  strike: number | null;
  maturity: string | null;
  hedge_ratio: number | null;
  cost: number | null;
}

export interface CompanyFinancials {
  id?: number;
  company_name: string;
  base_revenue: number | null;
  base_cogs: number | null;
  base_opex: number | null;
  tax_rate: number | null;
  starting_cash: number | null;
  starting_debt: number | null;
  ev_ebitda_multiple: number | null;
  min_cash_buffer: number | null;
  max_debt_ebitda_ratio: number | null;
}

// --- Risk Profile ---

export interface FactorMetrics {
  gross_exposure_jpy: number;
  hedged_jpy: number;
  net_exposure_jpy: number;
  impact_1sigma_jpy: number;
  vol: number;
}

export interface RiskProfile {
  commodity: Record<string, FactorMetrics>;
  fx: Record<string, FactorMetrics>;
  rates: Record<string, FactorMetrics>;
}

// --- Transmission ---

export interface TransmissionResult {
  transmission: {
    "Income Statement": Record<string, { Base: number; Shocked: number }>;
    "Balance Sheet & Value": Record<string, { Base: number; Shocked: number }>;
    "Shock Drivers": Record<string, number>;
  };
  proximity_scores: Record<string, {
    current: number;
    threshold: number;
    headroom_pct: number;
    proximity: number;
    breached: boolean;
    label: string;
  }>;
}

// --- Monte Carlo ---

export interface MonteCarloResponse {
  risk_metrics: Record<string, {
    var_95: number;
    var_99: number;
    cvar_95: number;
  }>;
  base_ev: number | null;
  base_fcf: number | null;
  base_cash: number | null;
  correlation_matrix: {
    columns: string[];
    data: number[][];
  };
  liquidity_shortfall_prob: number | null;
  histogram_data: Record<string, {
    counts: number[];
    bins: number[];
  }>;
}

// --- Optimization ---

export interface HedgePriorityRow {
  Factor: string;
  Category: string;
  "Gross Exposure (JPY B)": number;
  "CFaR Contrib (JPY B)": number;
  "Proximity Score": number;
  "Coverage %": number;
  "HedgePriority Score": number;
  Action: string;
}

export interface FactorAttribution {
  Commodity: number;
  FX: number;
  Rates: number;
  "Interaction / Diversification": number;
  "Total CFaR": number;
  base_fcf: number;
  cfar_full: number;
}

export interface FrontierResult {
  index: string[];
  columns: string[];
  data: number[][];
}

// --- Ingestion ---

export interface IngestionStatus {
  [source: string]: string;
}

export interface ConnectivityStatus {
  fred: boolean;
  yfinance: boolean;
  mof: boolean;
}

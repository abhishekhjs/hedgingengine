/**
 * API client for the FastAPI backend.
 * All requests go through this module for consistent error handling.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error");
    throw new ApiError(res.status, text);
  }

  return res.json();
}

// --- Market ---

export const market = {
  getRiskMetrics: () =>
    request<import("./types").RiskMetricRow[]>("/api/market/risk-metrics"),
  getLatest: () =>
    request<Record<string, import("./types").MarketDataPoint>>("/api/market/latest"),
  getHistory: (asset: string) =>
    request<import("./types").HistoryPoint[]>(`/api/market/history/${asset}`),
};

// --- Exposure ---

export const exposure = {
  getCompanies: () =>
    request<import("./types").CompanyExposure[]>("/api/exposure/companies"),
  upsertCompanies: (data: import("./types").CompanyExposure[]) =>
    request("/api/exposure/companies", { method: "POST", body: JSON.stringify(data) }),
  getHedges: () =>
    request<import("./types").HedgeInstrument[]>("/api/exposure/hedges"),
  upsertHedges: (data: import("./types").HedgeInstrument[]) =>
    request("/api/exposure/hedges", { method: "POST", body: JSON.stringify(data) }),
  getFinancials: (company: string) =>
    request<import("./types").CompanyFinancials>(`/api/exposure/financials/${encodeURIComponent(company)}`),
  upsertFinancials: (data: import("./types").CompanyFinancials) =>
    request("/api/exposure/financials", { method: "POST", body: JSON.stringify(data) }),
  getRiskProfile: (company: string) =>
    request<import("./types").RiskProfile>("/api/exposure/risk-profile", {
      method: "POST",
      body: JSON.stringify({ company_name: company }),
    }),
};

// --- Transmission ---

export const transmission = {
  compute: (company: string, sigma: number = 1.0) =>
    request<import("./types").TransmissionResult>("/api/transmission/compute", {
      method: "POST",
      body: JSON.stringify({ company_name: company, sigma_multiplier: sigma }),
    }),
};

// --- Monte Carlo ---

export const montecarlo = {
  run: (company: string, iterations: number = 10000) =>
    request<import("./types").MonteCarloResponse>("/api/montecarlo/run", {
      method: "POST",
      body: JSON.stringify({ company_name: company, n_iterations: iterations }),
    }),
};

// --- Optimization ---

export const optimization = {
  getPriority: (company: string) =>
    request<import("./types").HedgePriorityRow[]>("/api/optimization/priority", {
      method: "POST",
      body: JSON.stringify({ company_name: company }),
    }),
  getAttribution: (company: string) =>
    request<import("./types").FactorAttribution>("/api/optimization/attribution", {
      method: "POST",
      body: JSON.stringify({ company_name: company }),
    }),
  getFrontier: (company: string, steps: number = 6) =>
    request<import("./types").FrontierResult>("/api/optimization/frontier", {
      method: "POST",
      body: JSON.stringify({ company_name: company, steps }),
    }),
};

// --- Ingestion ---

export const ingestion = {
  run: () =>
    request<import("./types").IngestionStatus>("/api/ingestion/run", { method: "POST" }),
  checkConnectivity: () =>
    request<import("./types").ConnectivityStatus>("/api/ingestion/connectivity"),
};

// Unified API object for convenience imports: import { api } from "@/lib/api"
export const api = {
  market,
  exposure,
  transmission,
  montecarlo,
  optimization,
  ingestion,
};

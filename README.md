# 🏭 Japan Manufacturing Market Risk Monitor

A locally-runnable Python/Streamlit application that automatically ingests, stores, and analyzes market data relevant to Japanese manufacturing companies. Part of the foundational data layer for the Financial Resilience & Optionality Engine.

## 📊 What It Tracks

| Category | Instruments | Source |
|---|---|---|
| **Commodities** | WTI Crude, Brent Crude, Copper, Aluminium | FRED API, Yahoo Finance |
| **FX** | USD/JPY, EUR/JPY, AUD/JPY | Yahoo Finance |
| **Interest Rates** | JGB Yield Curve (2Y, 5Y, 10Y, 20Y, 30Y, 40Y) | Ministry of Finance Japan |

### Risk Metrics Computed

For every instrument: log returns (1d, 1m, 3m, 1y), annualized volatility (30d, 90d), 52-week high/low, drawdown, z-score (trailing 5-year), percentile rank (trailing 5-year). Plus JGB spread analysis (2Y-10Y, 10Y-30Y, 2Y-30Y).

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** (tested with 3.14)
- **Internet access** (for data source APIs)
- **FRED API key** (free) — [get one here](https://fred.stlouisfed.org/docs/api/api_key.html)

### Setup (< 10 minutes)

```bash
# 1. Clone the repository
git clone <repo-url>
cd engine

# 2. Add your FRED API key
#    Copy .env.example to .env and replace 'your_key_here' with your actual key
cp .env.example .env
# Edit .env and set: FRED_API_KEY=your_actual_key

# 3. Run the bootstrap script (creates venv, installs deps, backfills data, launches dashboard)
python setup.py
```

The setup script will:
1. ✅ Verify Python version
2. ✅ Create a virtual environment (`.venv/`)
3. ✅ Install all dependencies
4. ✅ Create `.env` from template (if missing)
5. ✅ Initialize the SQLite database
6. ✅ Check data source connectivity
7. ✅ Run the initial 5-year historical backfill
8. ✅ Launch the Streamlit dashboard in your browser

### Manual Setup (Alternative)

```bash
# Create and activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your FRED API key

# Run initial data ingestion
python run_ingestion.py

# Launch the dashboard
streamlit run app.py
```

---

## 🔄 Data Refresh

### Manual Refresh
Click the **🔄 Refresh Data** button in the dashboard UI. This triggers a full re-ingestion from all sources and recomputes all risk metrics.

### Scheduled Refresh
The ingestion pipeline runs as a standalone script for OS-level scheduling:

```bash
python run_ingestion.py
```

#### Linux/Mac (cron)
```bash
# Run daily at 7:00 AM (after Tokyo markets close)
0 7 * * * cd /path/to/engine && /path/to/engine/.venv/bin/python run_ingestion.py >> /var/log/market_monitor.log 2>&1
```

#### Windows (Task Scheduler)
1. Open Task Scheduler → Create Basic Task
2. Name: "Market Risk Monitor Daily Refresh"
3. Trigger: Daily at 07:00 AM
4. Action: Start a program
   - Program: `C:\path\to\engine\.venv\Scripts\python.exe`
   - Arguments: `C:\path\to\engine\run_ingestion.py`
   - Start in: `C:\path\to\engine`

---

## 🏗️ Architecture

```
┌─────────────┐  ┌──────────────┐  ┌───────────────┐
│ FRED API     │  │ yfinance     │  │ MOF CSV        │
│ (WTI, Brent) │  │ (Cu, Al, FX) │  │ (JGB curve)    │
└──────┬───────┘  └──────┬───────┘  └───────┬────────┘
       └─────────────────┼──────────────────┘
                          ↓
              INGESTION LAYER (src/ingestion/)
                          ↓
              VALIDATION & STORAGE (src/db/)
                          ↓
                    SQLite DATABASE
                    (data/market_data.db)
                          ↓
              RISK METRICS ENGINE (src/analytics/)
                          ↓
              STREAMLIT DASHBOARD (app.py)
```

### Project Structure
```
engine/
├── app.py                  # Streamlit dashboard entry point
├── run_ingestion.py        # Standalone ingestion script
├── setup.py                # Bootstrap script
├── requirements.txt
├── .env.example
├── src/
│   ├── config.py           # Configuration & constants
│   ├── db/
│   │   ├── schema.py       # Table definitions (6 tables)
│   │   └── connection.py   # SQLite connection & upsert
│   ├── ingestion/
│   │   ├── fred.py         # FRED API fetcher (oil)
│   │   ├── yfinance_fetcher.py  # Yahoo Finance (metals, FX)
│   │   ├── mof.py          # MOF CSV fetcher (JGBs)
│   │   └── runner.py       # Orchestrator
│   ├── analytics/
│   │   └── risk_metrics.py # All Section 5 calculations
│   └── dashboard/
│       └── components.py   # Reusable chart/table builders
├── tests/
│   ├── test_ingestion.py
│   ├── test_database.py
│   ├── test_risk_metrics.py
│   ├── test_fallback.py
│   └── test_data_quality.py
└── data/
    └── market_data.db      # SQLite database (gitignored)
```

---

## 📐 Risk Metrics Methodology

All metrics use **log returns** (natural logarithm).

| Metric | Formula | Window |
|---|---|---|
| Return (1d) | `ln(P_t / P_{t-1})` | 1 trading day |
| Return (1m) | `ln(P_t / P_{t-21})` | 21 trading days |
| Return (3m) | `ln(P_t / P_{t-63})` | 63 trading days |
| Return (1y) | `ln(P_t / P_{t-252})` | 252 trading days |
| Vol (30d) | `std(log_returns) × √252` | 21 trading days, annualized |
| Vol (90d) | `std(log_returns) × √252` | 63 trading days, annualized |
| 52w High/Low | max/min of price levels | 252 trading days |
| Drawdown | `(P - 52w_high) / 52w_high × 100` | Relative to 52w high |
| Z-Score | `(P - μ) / σ` on levels | 5-year trailing window |
| Percentile | `percentileofscore(kind='rank')` | 5-year trailing window |

### JGB Spreads
- **2Y-10Y Spread**: `yield_10Y - yield_2Y` (in basis points)
- **10Y-30Y Spread**: `yield_30Y - yield_10Y` (in basis points)
- **2Y-30Y Spread**: `yield_30Y - yield_2Y` (in basis points)

### Commodity Units
| Commodity | Unit | Source |
|---|---|---|
| WTI Crude | USD/barrel | FRED (`DCOILWTICO`) |
| Brent Crude | USD/barrel | FRED (`DCOILBRENTEU`) |
| Copper | USD/lb | Yahoo Finance (`HG=F`) |
| Aluminium | USD/metric ton | Yahoo Finance (`ALI=F`) |

---

## ⚠️ Known Limitations

### yfinance Caveat
`yfinance` is an **unofficial library** that scrapes Yahoo Finance endpoints. It has no official uptime or rate-limit guarantee and may break without notice. This is accepted for the MVP. If yfinance fails for Copper or Aluminium, the system automatically falls back to FRED's monthly series (`PCOPPUSDM`, `PALUMUSDM`) with degraded granularity, clearly tagged as `FRED_MONTHLY_FALLBACK` in the database.

### Futures Contract Rolls
Yahoo Finance futures tickers (`HG=F`, `ALI=F`) track the front-month contract and are stitched together without backward adjustment. This can create price discontinuities at contract roll dates, which may slightly affect return and volatility calculations around those dates.

### ALI=F Liquidity
COMEX Aluminium futures (`ALI=F`) have lower liquidity than LME aluminium. Data gaps may occur.

---

## 🔍 BOJ Manual Validation Note

The Bank of Japan's official daily FX page ([https://www.boj.or.jp/en/statistics/market/forex/fxdaily/](https://www.boj.or.jp/en/statistics/market/forex/fxdaily/)) can be used to manually spot-check the automated USD/JPY, EUR/JPY, and AUD/JPY figures.

This is a **deliberate manual step**, not an automated one, because:
- BOJ's public daily page only retains a rolling ~70 business day window
- BOJ's full-history "Time-Series Data Search" tool is an interactive interface, not a stable direct-download CSV endpoint suitable for automation

---

## 🧪 Running Tests

```bash
# Activate virtual environment first
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Run all tests
python -m pytest tests/ -v

# Run a specific test category
python -m pytest tests/test_risk_metrics.py -v
```

---

## 📝 Open Assumptions Log (Section 12)

The following decisions were made where the PRD left flexibility (`[FLEXIBLE]`):

1. **Volatility windows**: Use **trading days** (21 for 30d vol, 63 for 90d vol), not calendar days.
2. **52-week high/low**: Trailing **252 trading days**, not 365 calendar days.
3. **Percentile variant**: `scipy.stats.percentileofscore` with `kind='rank'`.
4. **Z-score std**: Sample standard deviation (`ddof=1`).
5. **JGB spreads**: Stored as synthetic assets in the `risk_metrics` table with `asset` = `SPREAD_2Y10Y`, `SPREAD_10Y30Y`, `SPREAD_2Y30Y`.
6. **Dashboard charts**: Click-to-expand (Streamlit expander) per instrument; yield curve is always visible.
7. **Market regime gauges**: Plotly gauge indicators with green/amber/red zones.
8. **FRED ingestion**: Via `fredapi` library (not raw `requests`).
9. **Bootstrap**: Python script (`setup.py`) for cross-platform (Windows + Linux/Mac) compatibility.
10. **MOF CSV parsing**: Shift-JIS encoding, hyphens as NA values, date format `YYYY/M/D`.
11. **Data staleness**: Simple calendar-day check (>3 days triggers warning). Normal weekend gaps (Friday→Monday = 3 days) do not trigger.

---

## 🚀 Built Features (MVP Complete)

- **Phase 1 (Market Risk Monitor)**: Automated ingestion and computation of trailing vol, z-scores, percentiles, and yield curves for Commodities, FX, and Rates.
- **Phase 2 (Company Exposure Mapping)**: Maps gross risks, hedges, and computes a 1-sigma shock to find net unhedged JPY exposure.
- **Phase 3 (Financial Transmission Modeling)**: Cascades unhedged risk shocks through a company's financial statements (EBITDA, FCF, Liquidity, Enterprise Value).
- **Phase 4 (Monte Carlo Simulation)**: Generates 10,000 correlated market scenarios using Cholesky decomposition on historical covariance.
- **Phase 5 (Comprehensive Risk Metrics)**: Standardized extraction of Cash-Flow-at-Risk (CFaR), Liquidity-at-Risk (LaR), and Enterprise-Value-at-Risk (EVaR).
- **Phase 6 (Hedge Optimization)**: Quantifies the "value of financial flexibility" by computing the delta between unhedged and hedged scenarios, and features an interactive sandbox to optimize target hedge ratios on the fly.

> **⚠️ Phase 3 Assumption Flag (FCF Simplification)**:
> In the Phase 3 Financial Transmission model, the Free Cash Flow (FCF) calculation is intentionally simplified for this MVP version. The calculation assumes that **Capital Expenditures (CapEx) exactly offset Depreciation & Amortization (D&A)**, and that **changes in Working Capital are zero**. Thus, FCF is modeled purely as EBITDA minus Interest Expense minus Taxes.

---

## 💰 Cost

This application runs at **\$0 marginal cost**. The only requirement is a free FRED API key. All other data sources (Yahoo Finance, MOF Japan) are free and require no API keys.

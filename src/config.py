"""Central configuration for the Japan Manufacturing Market Risk Monitor."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / '.env')

# Database
DATA_DIR = PROJECT_ROOT / 'data'
DB_PATH = DATA_DIR / 'market_data.db'

# FRED API
def get_fred_api_key() -> str:
    """Get FRED API key from environment, with actionable error if missing."""
    key = os.environ.get('FRED_API_KEY', '').strip()
    if not key or key == 'your_key_here':
        print(
            "\n" + "=" * 70 + "\n"
            "ERROR: FRED_API_KEY not found in .env\n\n"
            "To fix this:\n"
            "  1. Get a free API key at:\n"
            "     https://fred.stlouisfed.org/docs/api/api_key.html\n"
            "  2. Add it to your .env file:\n"
            "     FRED_API_KEY=your_actual_key_here\n"
            + "=" * 70 + "\n",
            file=sys.stderr
        )
        raise ValueError(
            "FRED_API_KEY not found in .env — get a free key at "
            "https://fred.stlouisfed.org/docs/api/api_key.html and add it to your .env file."
        )
    return key

# FRED series IDs
FRED_SERIES = {
    'WTI': 'DCOILWTICO',
    'BRENT': 'DCOILBRENTEU',
}

# FRED monthly fallback series (for Copper/Aluminium)
FRED_MONTHLY_FALLBACK = {
    'COPPER': 'PCOPPUSDM',
    'ALUMINIUM': 'PALUMUSDM',
}

# yfinance tickers
YFINANCE_COMMODITY_TICKERS = {
    'COPPER': {'ticker': 'HG=F', 'unit': 'USD/lb'},
    'ALUMINIUM': {'ticker': 'ALI=F', 'unit': 'USD/metric_ton'},
}

YFINANCE_FX_TICKERS = {
    'USDJPY': 'JPY=X',
    'EURJPY': 'EURJPY=X',
    'AUDJPY': 'AUDJPY=X',
}

# MOF JGB CSV
MOF_CSV_URL = 'https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/jgbcme.csv'
MOF_CSV_HISTORICAL_URL = 'https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv'

# All JGB tenors in the MOF CSV
JGB_ALL_TENORS = ['1Y', '2Y', '3Y', '4Y', '5Y', '6Y', '7Y', '8Y', '9Y', '10Y', '15Y', '20Y', '25Y', '30Y', '40Y']

# Tenors displayed on the dashboard
JGB_DASHBOARD_TENORS = ['2Y', '5Y', '10Y', '20Y', '30Y', '40Y']

# JGB spread definitions
JGB_SPREADS = {
    'SPREAD_2Y10Y': ('2Y', '10Y'),
    'SPREAD_10Y30Y': ('10Y', '30Y'),
    'SPREAD_2Y30Y': ('2Y', '30Y'),
}

# Risk metrics lookback constants (in trading days)
TRADING_DAYS_1M = 21
TRADING_DAYS_3M = 63
TRADING_DAYS_1Y = 252
TRADING_DAYS_5Y = 252 * 5  # 1260

# Annualization factor
ANNUALIZATION_FACTOR = 252 ** 0.5  # sqrt(252)

# Volatility windows (in trading days)
VOL_30D_WINDOW = 21  # ~30 calendar days = ~21 trading days
VOL_90D_WINDOW = 63  # ~90 calendar days = ~63 trading days

# Staleness threshold (calendar days) for data quality warnings
STALENESS_THRESHOLD_DAYS = 3

# Backfill depth
BACKFILL_YEARS = 5

# Commodity units
COMMODITY_UNITS = {
    'WTI': 'USD/barrel',
    'BRENT': 'USD/barrel',
    'COPPER': 'USD/lb',
    'ALUMINIUM': 'USD/metric_ton',
}

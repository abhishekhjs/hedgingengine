"""Shared test fixtures for the Japan Manufacturing Market Risk Monitor."""
import os
import sys
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

import pandas as pd
import numpy as np
import pytest

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary SQLite database with the full schema."""
    db_path = tmp_path / "test_market_data.db"
    
    # Patch the DB_PATH in config and connection modules
    with patch('src.config.DB_PATH', db_path), \
         patch('src.config.DATA_DIR', tmp_path), \
         patch('src.db.connection.DB_PATH', db_path), \
         patch('src.db.connection.DATA_DIR', tmp_path):
        from src.db.schema import initialize_db
        initialize_db()
        yield db_path


@pytest.fixture
def db_connection(temp_db):
    """Get a connection to the temporary database."""
    conn = sqlite3.connect(str(temp_db))
    conn.execute('PRAGMA journal_mode=WAL')
    yield conn
    conn.close()


@pytest.fixture
def sample_price_series():
    """A small, deterministic price series for testing risk metrics.
    
    Creates 300 trading days of synthetic data with known properties.
    """
    np.random.seed(42)
    n = 300
    dates = pd.bdate_range(start='2024-01-02', periods=n)
    
    # Generate a random walk starting at 100
    returns = np.random.normal(0.0005, 0.02, n)
    prices = 100 * np.exp(np.cumsum(returns))
    # Set the first price to exactly 100
    prices[0] = 100.0
    
    return pd.DataFrame({
        'date': dates.strftime('%Y-%m-%d'),
        'price': prices,
    })


@pytest.fixture
def sample_fred_response():
    """Mock FRED API response as a pandas Series (what fredapi returns)."""
    dates = pd.bdate_range(start='2024-01-02', periods=10)
    values = [72.50, 73.10, 72.80, np.nan, 73.50, 74.20, 73.80, 74.50, 75.00, 74.60]
    return pd.Series(values, index=dates, name='DCOILWTICO')


@pytest.fixture
def sample_mof_csv_text():
    """Sample MOF JGB CSV content for testing parsing."""
    return """Interest Rate (September 2024),,,,,,,,,,,,,,,(Unit : %)
Date,1Y,2Y,3Y,4Y,5Y,6Y,7Y,8Y,9Y,10Y,15Y,20Y,25Y,30Y,40Y
2024/9/2,0.427,0.392,0.403,0.432,0.470,0.530,0.590,0.670,0.760,0.900,1.380,1.670,-,1.960,2.190
2024/9/3,0.430,0.395,0.410,0.440,0.475,0.535,0.595,0.675,0.765,0.905,1.385,1.675,-,1.965,2.195
2024/9/4,0.425,0.390,0.400,0.430,0.465,0.525,0.585,0.665,0.755,0.895,1.375,1.665,-,1.955,2.185
,,,,,,,,,,,,,,,
"""


@pytest.fixture
def sample_yfinance_df():
    """Sample yfinance download response DataFrame."""
    dates = pd.bdate_range(start='2024-01-02', periods=5)
    return pd.DataFrame({
        'Open': [4.30, 4.32, 4.28, 4.35, 4.40],
        'High': [4.35, 4.38, 4.33, 4.42, 4.45],
        'Low': [4.28, 4.30, 4.25, 4.33, 4.38],
        'Close': [4.32, 4.35, 4.30, 4.40, 4.43],
        'Volume': [1000, 1200, 800, 1100, 950],
    }, index=dates)

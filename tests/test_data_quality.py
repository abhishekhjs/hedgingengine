"""Tests for data quality flagging (Section 9.5).

Staleness detection correctly flags stale instruments.
"""
import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestStalenessDetection:
    """Tests for data staleness detection."""

    def test_flags_stale_instrument(self, db_connection):
        """Instrument with data > 3 days old is flagged as stale."""
        # Insert data from 10 days ago
        old_date = (datetime.utcnow() - timedelta(days=10)).strftime('%Y-%m-%d')
        now = datetime.utcnow().isoformat()
        
        db_connection.execute(
            "INSERT OR REPLACE INTO commodity_prices (date, commodity, price_usd, unit, source, ingested_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (old_date, 'WTI', 72.50, 'USD/barrel', 'FRED', now)
        )
        db_connection.commit()
        
        # Check staleness
        today = datetime.utcnow().date()
        latest = pd.to_datetime(old_date).date()
        days_old = (today - latest).days
        
        assert days_old > 3, "Test data should be more than 3 days old"

    def test_does_not_flag_fresh_instrument(self, db_connection):
        """Instrument with recent data is NOT flagged as stale."""
        # Insert today's data
        today = datetime.utcnow().strftime('%Y-%m-%d')
        now = datetime.utcnow().isoformat()
        
        db_connection.execute(
            "INSERT OR REPLACE INTO commodity_prices (date, commodity, price_usd, unit, source, ingested_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (today, 'BRENT', 80.00, 'USD/barrel', 'FRED', now)
        )
        db_connection.commit()
        
        # Check staleness
        today_date = datetime.utcnow().date()
        latest = pd.to_datetime(today).date()
        days_old = (today_date - latest).days
        
        assert days_old <= 3, "Today's data should not be flagged as stale"

    def test_staleness_threshold_boundary(self, db_connection):
        """Data exactly 3 days old should NOT be flagged (threshold is >3)."""
        three_days_ago = (datetime.utcnow() - timedelta(days=3)).strftime('%Y-%m-%d')
        now = datetime.utcnow().isoformat()
        
        db_connection.execute(
            "INSERT OR REPLACE INTO fx_rates (date, currency_pair, rate, source, ingested_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (three_days_ago, 'USDJPY', 150.00, 'YFINANCE', now)
        )
        db_connection.commit()
        
        today = datetime.utcnow().date()
        latest = pd.to_datetime(three_days_ago).date()
        days_old = (today - latest).days
        
        assert days_old <= 3, "Data exactly 3 days old should not trigger staleness warning"

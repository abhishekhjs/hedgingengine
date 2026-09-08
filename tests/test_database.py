"""Tests for database layer (Section 9.2).

Upsert logic avoids duplicate rows.
Unique constraints are enforced.
Schema creation is idempotent.
"""
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestDatabaseSchema:
    """Tests for schema creation."""

    def test_schema_creation_creates_all_tables(self, db_connection):
        """Schema creation produces all 6 required tables."""
        cursor = db_connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in cursor.fetchall()}
        
        required = {
            'commodity_prices', 'fx_rates', 'jgb_yields',
            'risk_metrics', 'company_exposure', 'hedges'
        }
        assert required.issubset(tables)

    def test_schema_creation_is_idempotent(self, temp_db):
        """Running schema creation twice doesn't error."""
        from unittest.mock import patch
        with patch('src.config.DB_PATH', temp_db), \
             patch('src.db.connection.DB_PATH', temp_db):
            from src.db.schema import initialize_db
            # Should not raise
            initialize_db()
            initialize_db()

    def test_stub_tables_are_empty(self, db_connection):
        """Stub tables (company_exposure, hedges) exist but are empty."""
        for table in ['company_exposure', 'hedges']:
            count = db_connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            assert count == 0


class TestUpsertLogic:
    """Tests for upsert (INSERT OR REPLACE) behavior."""

    def test_upsert_avoids_duplicate_rows(self, db_connection):
        """Inserting the same (date, commodity) twice doesn't create duplicates."""
        now = datetime.utcnow().isoformat()
        
        # Insert first time
        db_connection.execute(
            "INSERT OR REPLACE INTO commodity_prices (date, commodity, price_usd, unit, source, ingested_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ('2024-01-02', 'WTI', 72.50, 'USD/barrel', 'FRED', now)
        )
        db_connection.commit()
        
        count1 = db_connection.execute(
            "SELECT COUNT(*) FROM commodity_prices WHERE date='2024-01-02' AND commodity='WTI'"
        ).fetchone()[0]
        assert count1 == 1
        
        # Insert again with updated price
        db_connection.execute(
            "INSERT OR REPLACE INTO commodity_prices (date, commodity, price_usd, unit, source, ingested_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ('2024-01-02', 'WTI', 73.00, 'USD/barrel', 'FRED', now)
        )
        db_connection.commit()
        
        count2 = db_connection.execute(
            "SELECT COUNT(*) FROM commodity_prices WHERE date='2024-01-02' AND commodity='WTI'"
        ).fetchone()[0]
        assert count2 == 1  # Still just 1 row
        
        # Price should be updated
        price = db_connection.execute(
            "SELECT price_usd FROM commodity_prices WHERE date='2024-01-02' AND commodity='WTI'"
        ).fetchone()[0]
        assert price == 73.00

    def test_unique_constraint_fx_rates(self, db_connection):
        """FX rates unique constraint on (date, currency_pair) works."""
        now = datetime.utcnow().isoformat()
        
        db_connection.execute(
            "INSERT OR REPLACE INTO fx_rates (date, currency_pair, rate, source, ingested_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ('2024-01-02', 'USDJPY', 148.50, 'YFINANCE', now)
        )
        db_connection.execute(
            "INSERT OR REPLACE INTO fx_rates (date, currency_pair, rate, source, ingested_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ('2024-01-02', 'USDJPY', 149.00, 'YFINANCE', now)
        )
        db_connection.commit()
        
        count = db_connection.execute(
            "SELECT COUNT(*) FROM fx_rates WHERE date='2024-01-02' AND currency_pair='USDJPY'"
        ).fetchone()[0]
        assert count == 1

    def test_unique_constraint_jgb_yields(self, db_connection):
        """JGB yields unique constraint on (date, tenor) works."""
        now = datetime.utcnow().isoformat()
        
        db_connection.execute(
            "INSERT OR REPLACE INTO jgb_yields (date, tenor, yield_pct, source, ingested_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ('2024-01-02', '10Y', 0.62, 'MOF', now)
        )
        db_connection.execute(
            "INSERT OR REPLACE INTO jgb_yields (date, tenor, yield_pct, source, ingested_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ('2024-01-02', '10Y', 0.65, 'MOF', now)
        )
        db_connection.commit()
        
        count = db_connection.execute(
            "SELECT COUNT(*) FROM jgb_yields WHERE date='2024-01-02' AND tenor='10Y'"
        ).fetchone()[0]
        assert count == 1

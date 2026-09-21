"""Database schema definition and initialization."""
import sqlite3
import logging

from src.db.connection import get_connection

logger = logging.getLogger(__name__)

# Schema version — bump this if tables change in future phases
SCHEMA_VERSION = 2

CREATE_TABLES_SQL = [
    # --- Raw market data tables ---
    """
    CREATE TABLE IF NOT EXISTS commodity_prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        commodity TEXT NOT NULL,
        price_usd REAL NOT NULL,
        unit TEXT NOT NULL,
        source TEXT NOT NULL,
        ingested_at TEXT NOT NULL,
        UNIQUE(date, commodity) ON CONFLICT REPLACE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS fx_rates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        currency_pair TEXT NOT NULL,
        rate REAL NOT NULL,
        source TEXT NOT NULL,
        ingested_at TEXT NOT NULL,
        UNIQUE(date, currency_pair) ON CONFLICT REPLACE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS jgb_yields (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        tenor TEXT NOT NULL,
        yield_pct REAL NOT NULL,
        source TEXT NOT NULL,
        ingested_at TEXT NOT NULL,
        UNIQUE(date, tenor) ON CONFLICT REPLACE
    )
    """,
    # --- Computed/derived table ---
    """
    CREATE TABLE IF NOT EXISTS risk_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        asset_class TEXT NOT NULL,
        asset TEXT NOT NULL,
        value REAL,
        return_1d REAL,
        return_1m REAL,
        return_3m REAL,
        return_1y REAL,
        vol_30d REAL,
        vol_90d REAL,
        high_52w REAL,
        low_52w REAL,
        drawdown_pct REAL,
        z_score REAL,
        percentile REAL,
        computed_at TEXT NOT NULL,
        UNIQUE(date, asset_class, asset) ON CONFLICT REPLACE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS company_exposure (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT NOT NULL,
        commodity TEXT,
        annual_quantity REAL,
        currency TEXT,
        annual_imports REAL,
        debt_amount REAL,
        floating_rate_percentage REAL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS hedges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT NOT NULL,
        instrument TEXT,
        underlying TEXT,
        notional REAL,
        strike REAL,
        maturity TEXT,
        hedge_ratio REAL,
        cost REAL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS company_financials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT NOT NULL UNIQUE,
        base_revenue REAL,
        base_cogs REAL,
        base_opex REAL,
        tax_rate REAL,
        starting_cash REAL,
        starting_debt REAL,
        ev_ebitda_multiple REAL,
        min_cash_buffer REAL DEFAULT 0,
        max_debt_ebitda_ratio REAL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS fx_rates_live (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        price REAL NOT NULL,
        prev_price REAL,
        timestamp TEXT NOT NULL,
        ingested_at TEXT NOT NULL
    )
    """,
]

# Indexes for query performance
CREATE_INDEXES_SQL = [
    'CREATE INDEX IF NOT EXISTS idx_commodity_prices_date ON commodity_prices(date)',
    'CREATE INDEX IF NOT EXISTS idx_commodity_prices_commodity ON commodity_prices(commodity)',
    'CREATE INDEX IF NOT EXISTS idx_fx_rates_date ON fx_rates(date)',
    'CREATE INDEX IF NOT EXISTS idx_fx_rates_pair ON fx_rates(currency_pair)',
    'CREATE INDEX IF NOT EXISTS idx_jgb_yields_date ON jgb_yields(date)',
    'CREATE INDEX IF NOT EXISTS idx_jgb_yields_tenor ON jgb_yields(tenor)',
    'CREATE INDEX IF NOT EXISTS idx_risk_metrics_date ON risk_metrics(date)',
    'CREATE INDEX IF NOT EXISTS idx_risk_metrics_asset ON risk_metrics(asset_class, asset)',
    'CREATE INDEX IF NOT EXISTS idx_fx_rates_live_symbol ON fx_rates_live(symbol, timestamp)',
]


def initialize_db() -> None:
    """Create all database tables and indexes if they don't exist.
    
    Safe to call multiple times — uses IF NOT EXISTS.
    """
    conn = get_connection()
    try:
        for sql in CREATE_TABLES_SQL:
            conn.execute(sql)
        for sql in CREATE_INDEXES_SQL:
            conn.execute(sql)
        conn.commit()
        logger.info(f"Database initialized successfully at {conn.execute('PRAGMA database_list').fetchone()[2]}")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    finally:
        conn.close()
    migrate_schema()


def migrate_schema() -> None:
    """Apply forward-compatible column migrations for existing databases.

    SQLite does not support DROP COLUMN or multi-column ADD, so we add each
    new column individually, ignoring errors when the column already exists.
    """
    MIGRATIONS = [
        # Schema v2: covenant constraint columns for Proximity_i computation
        "ALTER TABLE company_financials ADD COLUMN min_cash_buffer REAL DEFAULT 0",
        "ALTER TABLE company_financials ADD COLUMN max_debt_ebitda_ratio REAL DEFAULT 0",
    ]
    conn = get_connection()
    try:
        for sql in MIGRATIONS:
            try:
                conn.execute(sql)
            except Exception:
                pass  # Column already exists — safe to ignore
        conn.commit()
    finally:
        conn.close()


def reset_risk_metrics() -> None:
    """Drop and recreate the risk_metrics table.
    
    This table is fully recomputable from raw data.
    """
    conn = get_connection()
    try:
        conn.execute('DELETE FROM risk_metrics')
        conn.commit()
        logger.info("Cleared risk_metrics table for recomputation.")
    except Exception as e:
        logger.error(f"Failed to reset risk_metrics: {e}")
        raise
    finally:
        conn.close()

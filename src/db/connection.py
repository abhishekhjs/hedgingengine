"""SQLite connection management and data insertion utilities."""
import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager

import pandas as pd

from src.config import DB_PATH, DATA_DIR

logger = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    """Get a SQLite connection with WAL mode enabled.
    
    Creates the data directory if it doesn't exist.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def upsert_dataframe(df: pd.DataFrame, table_name: str, conn: sqlite3.Connection) -> int:
    """Insert DataFrame rows into a table using INSERT OR REPLACE.
    
    Args:
        df: DataFrame with columns matching the target table.
        table_name: Target database table name.
        conn: Active SQLite connection.
        
    Returns:
        Number of rows written.
    """
    if df.empty:
        logger.warning(f"Empty DataFrame passed for table '{table_name}', skipping.")
        return 0
    
    rows_before = conn.execute(f'SELECT COUNT(*) FROM {table_name}').fetchone()[0]
    
    # Use INSERT OR REPLACE to handle unique constraint conflicts
    cols = df.columns.tolist()
    placeholders = ', '.join(['?'] * len(cols))
    col_names = ', '.join(cols)
    sql = f'INSERT OR REPLACE INTO {table_name} ({col_names}) VALUES ({placeholders})'
    
    rows = df.values.tolist()
    conn.executemany(sql, rows)
    conn.commit()
    
    rows_after = conn.execute(f'SELECT COUNT(*) FROM {table_name}').fetchone()[0]
    net_new = rows_after - rows_before
    
    logger.info(f"Upserted {len(rows)} rows into '{table_name}' ({net_new} net new rows).")
    return len(rows)


def read_table(table_name: str, conn: sqlite3.Connection, where: str = None) -> pd.DataFrame:
    """Read a table (or subset) into a DataFrame.
    
    Args:
        table_name: Table to read from.
        conn: Active SQLite connection.
        where: Optional WHERE clause (without the WHERE keyword).
        
    Returns:
        DataFrame with query results.
    """
    sql = f'SELECT * FROM {table_name}'
    if where:
        sql += f' WHERE {where}'
    return pd.read_sql_query(sql, conn)

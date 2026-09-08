"""Risk metrics computation engine.

All metrics per PRD Section 5 (LOCKED):
- Returns: log returns (1d, 1m, 3m, 1y)
- Volatility: annualized std of log returns (30d, 90d windows)
- 52-week high/low and drawdown
- Z-score: (current - 5y mean) / 5y std on levels
- Percentile: rank within 5y distribution on levels (kind='rank')
- JGB spreads: 2Y-10Y, 10Y-30Y, 2Y-30Y

Assumptions (documented in README):
- Volatility windows: trading days (21d for 30d vol, 63d for 90d vol)
- 52-week high/low: trailing 252 trading days
- Percentile variant: scipy.stats.percentileofscore with kind='rank'
- Z-score std: sample std (ddof=1)
"""
import logging
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy.stats import percentileofscore

from src.config import (
    TRADING_DAYS_1M, TRADING_DAYS_3M, TRADING_DAYS_1Y, TRADING_DAYS_5Y,
    VOL_30D_WINDOW, VOL_90D_WINDOW,
    JGB_DASHBOARD_TENORS, JGB_ALL_TENORS, JGB_SPREADS,
)
from src.db.connection import get_connection, upsert_dataframe
from src.db.schema import reset_risk_metrics

logger = logging.getLogger(__name__)


def compute_metrics_for_series(
    dates: pd.Index,
    values: pd.Series,
    asset_class: str,
    asset: str,
) -> pd.DataFrame:
    """Compute all risk metrics for a date-sorted price/rate/yield series.
    
    Args:
        dates: DatetimeIndex or Index of date strings, sorted ascending.
        values: Corresponding price/rate/yield values, same length as dates.
        asset_class: One of 'COMMODITY', 'FX', 'RATE'.
        asset: Instrument identifier (e.g. 'COPPER', 'USDJPY', '10Y').
        
    Returns:
        DataFrame with one row per date, matching risk_metrics schema.
    """
    n = len(values)
    if n == 0:
        return pd.DataFrame()
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Ensure values is a clean float series with positional index
    values = values.reset_index(drop=True).astype(float)
    
    # Log returns
    log_ret = np.log(values / values.shift(1))
    
    # Period returns (log)
    return_1d = log_ret
    return_1m = np.log(values / values.shift(TRADING_DAYS_1M))
    return_3m = np.log(values / values.shift(TRADING_DAYS_3M))
    return_1y = np.log(values / values.shift(TRADING_DAYS_1Y))
    
    # Volatility: annualized std of trailing log returns
    vol_30d = log_ret.rolling(window=VOL_30D_WINDOW, min_periods=VOL_30D_WINDOW).std(ddof=1) * (252 ** 0.5)
    vol_90d = log_ret.rolling(window=VOL_90D_WINDOW, min_periods=VOL_90D_WINDOW).std(ddof=1) * (252 ** 0.5)
    
    # 52-week high/low (trailing 252 trading days)
    high_52w = values.rolling(window=TRADING_DAYS_1Y, min_periods=TRADING_DAYS_1Y).max()
    low_52w = values.rolling(window=TRADING_DAYS_1Y, min_periods=TRADING_DAYS_1Y).min()
    
    # Drawdown from 52w high (only where 52w high is available)
    drawdown_pct = (values - high_52w) / high_52w * 100
    
    # Z-score: (current - trailing_5y_mean) / trailing_5y_std on levels
    rolling_mean = values.rolling(window=TRADING_DAYS_5Y, min_periods=2).mean()
    rolling_std = values.rolling(window=TRADING_DAYS_5Y, min_periods=2).std(ddof=1)
    z_score = (values - rolling_mean) / rolling_std
    # Replace inf/-inf (from zero std) with NaN
    z_score = z_score.replace([np.inf, -np.inf], np.nan)
    
    # Percentile: rank of current value within trailing 5y window
    # This requires a loop since percentileofscore can't be vectorized
    pct_values = pd.Series(np.nan, index=values.index)
    for i in range(1, n):
        start_idx = max(0, i - TRADING_DAYS_5Y + 1)
        window = values.iloc[start_idx:i + 1].dropna()
        if len(window) >= 2:
            pct_values.iloc[i] = percentileofscore(window.values, values.iloc[i], kind='rank')
    
    # Convert dates to strings if needed
    if hasattr(dates, 'dt'):
        date_strings = dates.dt.strftime('%Y-%m-%d')
    elif isinstance(dates, pd.DatetimeIndex):
        date_strings = dates.strftime('%Y-%m-%d')
    else:
        date_strings = dates
    
    # Build result
    result = pd.DataFrame({
        'date': date_strings.values if hasattr(date_strings, 'values') else list(date_strings),
        'asset_class': asset_class,
        'asset': asset,
        'value': values.values,
        'return_1d': return_1d.values,
        'return_1m': return_1m.values,
        'return_3m': return_3m.values,
        'return_1y': return_1y.values,
        'vol_30d': vol_30d.values,
        'vol_90d': vol_90d.values,
        'high_52w': high_52w.values,
        'low_52w': low_52w.values,
        'drawdown_pct': drawdown_pct.values,
        'z_score': z_score.values,
        'percentile': pct_values.values,
        'computed_at': now,
    })
    
    # Replace NaN with None for SQLite compatibility
    result = result.where(result.notna(), None)
    
    return result


def compute_jgb_spreads(conn) -> pd.DataFrame:
    """Compute JGB spread metrics (2Y-10Y, 10Y-30Y, 2Y-30Y).
    
    Spreads are computed in basis points.
    Returns DataFrame matching risk_metrics schema with asset = 'SPREAD_2Y10Y' etc.
    """
    # Load JGB data
    jgb_df = pd.read_sql_query(
        "SELECT date, tenor, yield_pct FROM jgb_yields ORDER BY date",
        conn
    )
    
    if jgb_df.empty:
        return pd.DataFrame()
    
    # Pivot to wide format: date rows x tenor columns
    pivot = jgb_df.pivot_table(index='date', columns='tenor', values='yield_pct')
    pivot = pivot.sort_index()
    
    all_results = []
    
    for spread_name, (short_tenor, long_tenor) in JGB_SPREADS.items():
        if short_tenor not in pivot.columns or long_tenor not in pivot.columns:
            logger.warning(f"Missing tenor data for spread {spread_name}: need {short_tenor} and {long_tenor}")
            continue
        
        # Spread in basis points
        spread_series = (pivot[long_tenor] - pivot[short_tenor]) * 100
        spread_series = spread_series.dropna()
        
        if len(spread_series) == 0:
            continue
        
        dates = pd.Index(spread_series.index)
        values = spread_series.reset_index(drop=True)
        
        metrics = compute_metrics_for_series(dates, values, 'RATE', spread_name)
        all_results.append(metrics)
    
    if all_results:
        return pd.concat(all_results, ignore_index=True)
    return pd.DataFrame()


def compute_all_risk_metrics() -> None:
    """Compute risk metrics for all instruments and store in the database.
    
    Clears the risk_metrics table and recomputes from raw data.
    """
    logger.info("Starting risk metrics computation...")
    
    # Clear existing metrics
    reset_risk_metrics()
    
    conn = get_connection()
    all_metrics = []
    
    try:
        # --- Commodities ---
        commodity_df = pd.read_sql_query(
            "SELECT date, commodity, price_usd FROM commodity_prices ORDER BY date",
            conn
        )
        for commodity in commodity_df['commodity'].unique():
            subset = commodity_df[commodity_df['commodity'] == commodity].copy()
            subset = subset.sort_values('date').drop_duplicates(subset='date', keep='last')
            if len(subset) > 0:
                metrics = compute_metrics_for_series(
                    pd.Index(subset['date']),
                    subset['price_usd'].reset_index(drop=True),
                    'COMMODITY',
                    commodity
                )
                all_metrics.append(metrics)
                logger.info(f"  Computed metrics for {commodity}: {len(metrics)} rows")
        
        # --- FX ---
        fx_df = pd.read_sql_query(
            "SELECT date, currency_pair, rate FROM fx_rates ORDER BY date",
            conn
        )
        for pair in fx_df['currency_pair'].unique():
            subset = fx_df[fx_df['currency_pair'] == pair].copy()
            subset = subset.sort_values('date').drop_duplicates(subset='date', keep='last')
            if len(subset) > 0:
                metrics = compute_metrics_for_series(
                    pd.Index(subset['date']),
                    subset['rate'].reset_index(drop=True),
                    'FX',
                    pair
                )
                all_metrics.append(metrics)
                logger.info(f"  Computed metrics for {pair}: {len(metrics)} rows")
        
        # --- JGB Yields ---
        jgb_df = pd.read_sql_query(
            "SELECT date, tenor, yield_pct FROM jgb_yields ORDER BY date",
            conn
        )
        for tenor in jgb_df['tenor'].unique():
            subset = jgb_df[jgb_df['tenor'] == tenor].copy()
            subset = subset.sort_values('date').drop_duplicates(subset='date', keep='last')
            if len(subset) > 0:
                metrics = compute_metrics_for_series(
                    pd.Index(subset['date']),
                    subset['yield_pct'].reset_index(drop=True),
                    'RATE',
                    tenor
                )
                all_metrics.append(metrics)
                logger.info(f"  Computed metrics for JGB {tenor}: {len(metrics)} rows")
        
        # --- JGB Spreads ---
        spread_metrics = compute_jgb_spreads(conn)
        if not spread_metrics.empty:
            all_metrics.append(spread_metrics)
            logger.info(f"  Computed JGB spread metrics: {len(spread_metrics)} rows")
        
        # --- Write all metrics ---
        if all_metrics:
            combined = pd.concat(all_metrics, ignore_index=True)
            upsert_dataframe(combined, 'risk_metrics', conn)
            logger.info(f"Risk metrics computation complete: {len(combined)} total rows written.")
        else:
            logger.warning("No risk metrics computed — no raw data available.")
    
    except Exception as e:
        logger.error(f"Error computing risk metrics: {e}")
        raise
    finally:
        conn.close()

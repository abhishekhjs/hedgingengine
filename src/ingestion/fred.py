import logging
from datetime import datetime, timedelta
import pandas as pd
from fredapi import Fred
from src.config import (
    get_fred_api_key, FRED_SERIES, FRED_MONTHLY_FALLBACK,
    COMMODITY_UNITS, BACKFILL_YEARS
)

logger = logging.getLogger(__name__)

def fetch_fred_commodities() -> pd.DataFrame:
    try:
        api_key = get_fred_api_key()
        fred = Fred(api_key=api_key)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=BACKFILL_YEARS * 365.25)
        
        dfs = []
        for commodity, series_id in FRED_SERIES.items():
            try:
                logger.info(f"Fetching FRED series {series_id} for {commodity}")
                series = fred.get_series(series_id, observation_start=start_date)
                series = series.dropna()
                
                df = pd.DataFrame({'price_usd': series})
                df.index.name = 'date'
                df = df.reset_index()
                
                df['date'] = df['date'].dt.strftime('%Y-%m-%d')
                df['commodity'] = commodity
                df['unit'] = COMMODITY_UNITS.get(commodity, 'USD/barrel')
                df['source'] = 'FRED'
                df['ingested_at'] = datetime.utcnow().isoformat()
                
                logger.info(f"Fetched {len(df)} data points for {commodity}")
                dfs.append(df)
            except Exception as e:
                logger.error(f"Error fetching {commodity} ({series_id}): {e}")
        
        if dfs:
            return pd.concat(dfs, ignore_index=True)
        return pd.DataFrame(columns=['date', 'commodity', 'price_usd', 'unit', 'source', 'ingested_at'])
        
    except Exception as e:
        logger.error(f"Error initializing FRED API: {e}")
        return pd.DataFrame(columns=['date', 'commodity', 'price_usd', 'unit', 'source', 'ingested_at'])

def fetch_fred_monthly_fallback(commodity: str) -> pd.DataFrame:
    try:
        api_key = get_fred_api_key()
        fred = Fred(api_key=api_key)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=BACKFILL_YEARS * 365.25)
        
        series_id = FRED_MONTHLY_FALLBACK.get(commodity)
        if not series_id:
            logger.error(f"No fallback series found for {commodity}")
            return pd.DataFrame(columns=['date', 'commodity', 'price_usd', 'unit', 'source', 'ingested_at'])
            
        logger.info(f"Fetching fallback FRED series {series_id} for {commodity}")
        series = fred.get_series(series_id, observation_start=start_date)
        series = series.dropna()
        
        df = pd.DataFrame({'price_usd': series})
        df.index.name = 'date'
        df = df.reset_index()
        
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
        df['commodity'] = commodity
        df['unit'] = 'USD/lb' if commodity.upper() == 'COPPER' else 'USD/metric_ton'
        df['source'] = 'FRED_MONTHLY_FALLBACK'
        df['ingested_at'] = datetime.utcnow().isoformat()
        
        logger.info(f"Fetched {len(df)} fallback data points for {commodity}")
        return df
    except Exception as e:
        logger.error(f"Error in FRED fallback for {commodity}: {e}")
        return pd.DataFrame(columns=['date', 'commodity', 'price_usd', 'unit', 'source', 'ingested_at'])

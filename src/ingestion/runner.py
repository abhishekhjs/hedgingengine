import logging
import requests
from src.db.schema import initialize_db
from src.db.connection import get_connection, upsert_dataframe
from src.ingestion.fred import fetch_fred_commodities
from src.ingestion.yfinance_fetcher import fetch_yfinance_commodities, fetch_yfinance_fx
from src.ingestion.mof import fetch_mof_jgb_yields
import yfinance as yf
from src.config import get_fred_api_key, MOF_CSV_URL

logger = logging.getLogger(__name__)

def run_full_ingestion() -> dict:
    status = {}
    
    try:
        initialize_db()
    except Exception as e:
        logger.error(f"Error initializing DB: {e}")
        return {'db': f'error: {e}'}
        
    conn = get_connection()
    if conn is None:
        return {'db': 'error: connection failed'}
        
    try:
        fred_df = fetch_fred_commodities()
        if not fred_df.empty:
            upsert_dataframe(fred_df, 'commodity_prices', conn)
        status['fred'] = 'ok'
    except Exception as e:
        status['fred'] = f'error: {e}'
        
    try:
        yf_comm_df = fetch_yfinance_commodities()
        if not yf_comm_df.empty:
            upsert_dataframe(yf_comm_df, 'commodity_prices', conn)
        status['yfinance_commodities'] = 'ok'
    except Exception as e:
        status['yfinance_commodities'] = f'error: {e}'
        
    try:
        yf_fx_df = fetch_yfinance_fx()
        if not yf_fx_df.empty:
            upsert_dataframe(yf_fx_df, 'fx_rates', conn)
        status['yfinance_fx'] = 'ok'
    except Exception as e:
        status['yfinance_fx'] = f'error: {e}'
        
    try:
        mof_df = fetch_mof_jgb_yields()
        if not mof_df.empty:
            upsert_dataframe(mof_df, 'jgb_yields', conn)
        status['mof'] = 'ok'
    except Exception as e:
        status['mof'] = f'error: {e}'
        
    conn.close()
    
    try:
        from src.analytics.risk_metrics import compute_all_risk_metrics
        compute_all_risk_metrics()
        status['risk_metrics'] = 'ok'
    except Exception as e:
        status['risk_metrics'] = f'error: {e}'
        
    return status

def check_source_connectivity() -> dict:
    status = {'fred': False, 'yfinance': False, 'mof': False}
    
    try:
        from fredapi import Fred
        api_key = get_fred_api_key()
        fred = Fred(api_key=api_key)
        fred.get_series_info('DCOILWTICO')
        status['fred'] = True
    except Exception as e:
        logger.warning(f"FRED connectivity check failed: {e}")
        
    try:
        df = yf.download('SPY', period='1d', progress=False)
        if not df.empty:
            status['yfinance'] = True
    except Exception as e:
        logger.warning(f"yfinance connectivity check failed: {e}")
        
    try:
        response = requests.head(MOF_CSV_URL, timeout=10)
        if response.status_code == 200:
            status['mof'] = True
    except Exception as e:
        logger.warning(f"MOF connectivity check failed: {e}")
        
    return status

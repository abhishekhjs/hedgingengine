import logging
from datetime import datetime
import pandas as pd
import yfinance as yf
from src.config import YFINANCE_COMMODITY_TICKERS, YFINANCE_FX_TICKERS, COMMODITY_UNITS

logger = logging.getLogger(__name__)

def fetch_yfinance_commodities() -> pd.DataFrame:
    dfs = []
    
    for commodity, info in YFINANCE_COMMODITY_TICKERS.items():
        ticker_symbol = info['ticker']
        try:
            logger.info(f"Downloading yfinance commodity {commodity} ({ticker_symbol})")
            df = yf.download(ticker_symbol, period='5y', progress=False, auto_adjust=True, multi_level_index=False, ignore_tz=True)
            
            if df.empty:
                raise ValueError(f"Empty dataframe returned for {ticker_symbol}")
                
            if isinstance(df.columns, pd.MultiIndex):
                # Flatten multi-index columns if any
                df.columns = df.columns.get_level_values(0)
            
            # Use Close column
            if 'Close' not in df.columns:
                raise ValueError(f"No Close column for {ticker_symbol}")
                
            df = df[['Close']].copy()
            df = df.rename(columns={'Close': 'price_usd'})
            
            df.index.name = 'date'
            df = df.reset_index()
            
            if df['date'].dt.tz is not None:
                df['date'] = df['date'].dt.tz_localize(None)
            df['date'] = df['date'].dt.strftime('%Y-%m-%d')
            
            df['commodity'] = commodity
            df['unit'] = COMMODITY_UNITS.get(commodity, 'unknown')
            df['source'] = 'YFINANCE'
            df['ingested_at'] = datetime.utcnow().isoformat()
            
            dfs.append(df)
            
        except Exception as e:
            logger.warning(f"Failed to fetch {commodity} from yfinance: {e}. Attempting fallback...")
            from src.ingestion.fred import fetch_fred_monthly_fallback
            fallback_df = fetch_fred_monthly_fallback(commodity)
            if not fallback_df.empty:
                dfs.append(fallback_df)
                
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame(columns=['date', 'commodity', 'price_usd', 'unit', 'source', 'ingested_at'])

def fetch_yfinance_fx() -> pd.DataFrame:
    dfs = []
    
    for pair, ticker in YFINANCE_FX_TICKERS.items():
        try:
            logger.info(f"Downloading yfinance FX {pair} ({ticker})")
            df = yf.download(ticker, period='5y', progress=False, auto_adjust=True, multi_level_index=False, ignore_tz=True)
            
            if df.empty:
                logger.error(f"Empty dataframe returned for {ticker}")
                continue
                
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
                
            if 'Close' not in df.columns:
                logger.error(f"No Close column for {ticker}")
                continue
                
            df = df[['Close']].copy()
            df = df.rename(columns={'Close': 'rate'})
            
            df.index.name = 'date'
            df = df.reset_index()
            
            if df['date'].dt.tz is not None:
                df['date'] = df['date'].dt.tz_localize(None)
            df['date'] = df['date'].dt.strftime('%Y-%m-%d')
            
            df['currency_pair'] = pair
            df['source'] = 'YFINANCE'
            df['ingested_at'] = datetime.utcnow().isoformat()
            
            dfs.append(df)
            
        except Exception as e:
            logger.error(f"Failed to fetch FX {pair} from yfinance: {e}")
            
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame(columns=['date', 'currency_pair', 'rate', 'source', 'ingested_at'])

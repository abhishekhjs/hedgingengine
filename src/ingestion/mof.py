import logging
from datetime import datetime, timedelta
from io import StringIO
import pandas as pd
import requests
from src.config import MOF_CSV_URL, MOF_CSV_HISTORICAL_URL, JGB_ALL_TENORS, BACKFILL_YEARS

logger = logging.getLogger(__name__)

def fetch_mof_jgb_yields() -> pd.DataFrame:
    dfs = []
    
    # Calculate cutoff date for 5 years back
    cutoff_date = datetime.now() - timedelta(days=BACKFILL_YEARS * 365.25)
    
    for url, desc in [(MOF_CSV_HISTORICAL_URL, "Historical"), (MOF_CSV_URL, "Current")]:
        try:
            logger.info(f"Fetching MOF {desc} JGB yields from {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Decode raw bytes with shift_jis (MOF CSV uses this encoding)
            text = response.content.decode('shift_jis', errors='replace')
            df = pd.read_csv(StringIO(text), header=1, na_values=['-'])
            
            # Filter rows where Date matches a valid date pattern (e.g., length >= 8)
            df = df[df.iloc[:, 0].astype(str).str.contains(r'^\d{4}/\d{1,2}/\d{1,2}$', na=False)].copy()
            
            df['Date'] = pd.to_datetime(df.iloc[:, 0], format='%Y/%m/%d')
            df['date'] = df['Date'].dt.strftime('%Y-%m-%d')
            
            melted = df.melt(id_vars=['date', 'Date'], value_vars=[col for col in df.columns if col in JGB_ALL_TENORS])
            melted = melted.rename(columns={'variable': 'tenor', 'value': 'yield_pct'})
            melted = melted.dropna(subset=['yield_pct'])
            
            melted['source'] = 'MOF'
            melted['ingested_at'] = datetime.utcnow().isoformat()
            
            # Filter last 5 years
            melted = melted[melted['Date'] >= cutoff_date].copy()
            melted = melted.drop(columns=['Date'])
            
            logger.info(f"Fetched {len(melted)} records from MOF {desc} data")
            dfs.append(melted)
            
        except Exception as e:
            logger.error(f"Error fetching MOF {desc} data: {e}")
            
    if not dfs:
        return pd.DataFrame(columns=['date', 'tenor', 'yield_pct', 'source', 'ingested_at'])
        
    final_df = pd.concat(dfs, ignore_index=True)
    final_df = final_df.drop_duplicates(subset=['date', 'tenor'], keep='last')
    
    logger.info(f"Total MOF records after deduplication: {len(final_df)}")
    return final_df

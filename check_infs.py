import pandas as pd
import numpy as np
from src.db.connection import get_connection

with get_connection() as conn:
    df = pd.read_sql('SELECT * FROM risk_metrics', conn)
    
print(f'Total rows: {len(df)}')
print(f'inf count: {np.isinf(df.return_1d).sum()}')
print(f'NaN count: {df.return_1d.isna().sum()}')

ret_df = df.pivot(index='date', columns='asset', values='return_1d')
ret_df.replace([np.inf, -np.inf], np.nan, inplace=True)
ret_df = ret_df.fillna(0.0)
cov_matrix = ret_df.cov().values * 252

print(f"Covariance Matrix NaN count: {np.isnan(cov_matrix).sum()}")
print(f"Covariance Matrix inf count: {np.isinf(cov_matrix).sum()}")

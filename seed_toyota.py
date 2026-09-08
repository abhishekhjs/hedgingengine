import pandas as pd
from src.db.connection import get_connection

exposure = pd.DataFrame([
    {'company_name': 'Toyota (Case Study)', 'commodity': 'ALUMINIUM', 'annual_quantity': 500000, 'currency': 'USD', 'annual_imports': 2000000000, 'debt_amount': 50000000000, 'floating_rate_percentage': 0.35},
    {'company_name': 'Toyota (Case Study)', 'commodity': 'COPPER', 'annual_quantity': 250000, 'currency': 'EUR', 'annual_imports': 500000000, 'debt_amount': 10000000000, 'floating_rate_percentage': 0.15}
])

hedges = pd.DataFrame([
    {'company_name': 'Toyota (Case Study)', 'instrument': 'Forward', 'underlying': 'USDJPY', 'notional': 1000000000, 'strike': 140.0, 'maturity': '2027-12-31', 'hedge_ratio': 0.5, 'cost': 0},
    {'company_name': 'Toyota (Case Study)', 'instrument': 'Swap', 'underlying': 'ALUMINIUM', 'notional': 200000, 'strike': 2400.0, 'maturity': '2025-06-30', 'hedge_ratio': 0.4, 'cost': 500000}
])

with get_connection() as conn:
    conn.execute("DELETE FROM company_exposure WHERE company_name = 'Toyota (Case Study)'")
    conn.execute("DELETE FROM hedges WHERE company_name = 'Toyota (Case Study)'")
    exposure.to_sql('company_exposure', conn, if_exists='append', index=False)
    hedges.to_sql('hedges', conn, if_exists='append', index=False)
print('Seeded Toyota case study data.')

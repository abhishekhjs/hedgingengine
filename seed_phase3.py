import pandas as pd
from src.db.connection import get_connection
from src.db.schema import initialize_db

initialize_db()

financials = pd.DataFrame([{
    'company_name': 'Toyota (Case Study)',
    'base_revenue': 45000000000000,
    'base_cogs': 35000000000000,
    'base_opex': 5000000000000,
    'tax_rate': 0.30,
    'starting_cash': 9000000000000,
    'starting_debt': 30000000000000,
    'ev_ebitda_multiple': 8.5
}])

with get_connection() as conn:
    conn.execute("DELETE FROM company_financials WHERE company_name = 'Toyota (Case Study)'")
    financials.to_sql('company_financials', conn, if_exists='append', index=False)

print('Seeded Phase 3 financials.')

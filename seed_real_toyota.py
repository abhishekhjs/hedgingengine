"""Seed real FY2024 Toyota metrics into the database."""
import sqlite3
import pandas as pd
from pathlib import Path

# Connect to database
DB_PATH = Path('c:/Users/Abhishekh JS/Documents/engine/data/market_data.db')
conn = sqlite3.connect(str(DB_PATH))

company_name = 'Toyota (Real FY24)'

# 1. Company Exposure (Gross amounts)
exposure_data = [
    # Commodities (Volumes in tons/lbs) - estimated for 10M vehicles
    (company_name, 'COPPER', 500_000 * 2204.62, 'USD', 0, 0, 0),  # 500k metric tons to lbs
    (company_name, 'ALUMINIUM', 1_500_000, 'USD', 0, 0, 0),       # 1.5M metric tons
    
    # FX (USD and EUR Revenues that are unhedged/exposed)
    # Target net USD exposure is $45B. Let's say Gross is $90B and Hedge is $45B.
    (company_name, 'USDJPY', 0, 'USD', 90_000_000_000, 0, 0),
    # Target net EUR exposure is €10B. Let's say Gross is €20B and Hedge is €10B.
    (company_name, 'EURJPY', 0, 'EUR', 20_000_000_000, 0, 0),
    
    # Interest Rates (Floating Debt out of 36.5T total debt)
    # Let's say 30% is floating = ~11 Trillion JPY
    (company_name, 'Rates', 0, 'JPY', 0, 11_000_000_000_000, 1.0),
]

conn.executemany('''
    INSERT INTO company_exposure (company_name, commodity, annual_quantity, currency, annual_imports, debt_amount, floating_rate_percentage)
    VALUES (?, ?, ?, ?, ?, ?, ?)
''', exposure_data)

# 2. Hedges
hedge_data = [
    (company_name, 'Forward', 'USDJPY', 45_000_000_000, 145.0, '1Y', 0.50, 0),
    (company_name, 'Forward', 'EURJPY', 10_000_000_000, 155.0, '1Y', 0.50, 0),
    (company_name, 'Swap', 'Rates', 3_000_000_000_000, 1.0, '5Y', 1.0, 0), # 3T hedged
    (company_name, 'Forward', 'COPPER', 200_000 * 2204.62, 4.0, '1Y', 1.0, 0),
]

conn.executemany('''
    INSERT INTO hedges (company_name, instrument, underlying, notional, strike, maturity, hedge_ratio, cost)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
''', hedge_data)

# 3. Financials (FY2024 Actuals)
financials = [
    (
        company_name, 
        45_095_000_000_000,  # Revenue
        39_742_000_000_000,  # COGS + OpEx (Reverse-engineered to hit 5.35T Operating Income)
        0,                   # OpEx (merged into COGS for simplicity)
        0.30,                # Tax Rate
        9_412_000_000_000,   # Cash
        36_561_000_000_000,  # Total Debt
        7.0                  # EV Multiple (Est)
    )
]

conn.executemany('''
    INSERT INTO company_financials (company_name, base_revenue, base_cogs, base_opex, tax_rate, starting_cash, starting_debt, ev_ebitda_multiple)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
''', financials)

conn.commit()
conn.close()
print("Real Toyota FY24 data seeded!")

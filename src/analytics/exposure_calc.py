"""Phase 2 Calculation Engine for Unhedged Risk and Scenario Analysis."""
import pandas as pd
import numpy as np

def get_latest_market_data(conn) -> dict:
    """Fetch the most recent price and volatility for every asset."""
    query = """
        SELECT asset, value, vol_90d 
        FROM risk_metrics 
        WHERE (asset, date) IN (
            SELECT asset, MAX(date) 
            FROM risk_metrics 
            GROUP BY asset
        )
    """
    df = pd.read_sql(query, conn)
    market_data = {}
    for _, row in df.iterrows():
        market_data[row['asset']] = {
            'price': float(row['value']) if pd.notna(row['value']) else 0.0,
            'vol': float(row['vol_90d']) if pd.notna(row['vol_90d']) else 0.0
        }
    return market_data


def calculate_company_risk(exposure_df: pd.DataFrame, hedge_df: pd.DataFrame, market_data: dict) -> dict:
    """Calculate gross, hedged, net, and 1-sigma shocked risk profiles in JPY."""
    results = {
        'commodity': {},
        'fx': {},
        'rates': {}
    }
    
    # 1. Aggregate Base Exposures
    agg_commodities = {}
    agg_fx = {}
    total_floating_debt = 0.0
    
    for _, row in exposure_df.iterrows():
        # Commodities
        comm = row.get('commodity')
        qty = row.get('annual_quantity', 0.0)
        if pd.notna(comm) and comm and pd.notna(qty):
            agg_commodities[comm] = agg_commodities.get(comm, 0.0) + float(qty)
            
        # FX
        curr = row.get('currency')
        imp = row.get('annual_imports', 0.0)
        if pd.notna(curr) and curr and pd.notna(imp):
            pair = f"{curr}JPY"
            agg_fx[pair] = agg_fx.get(pair, 0.0) + float(imp)
            
        # Rates (Debt)
        debt = row.get('debt_amount', 0.0)
        flt_pct = row.get('floating_rate_percentage', 0.0)
        if pd.notna(debt) and pd.notna(flt_pct):
            total_floating_debt += (float(debt) * float(flt_pct))
            
    # 2. Aggregate Hedges
    hedge_totals = {}
    for _, row in hedge_df.iterrows():
        und = row.get('underlying')
        notional = row.get('notional', 0.0)
        hr = row.get('hedge_ratio', 1.0)
        if pd.notna(und) and und and pd.notna(notional) and pd.notna(hr):
            effective_hedge = float(notional) * float(hr)
            hedge_totals[und] = hedge_totals.get(und, 0.0) + effective_hedge

    # 3. Calculate Commodity Risk (Convert to JPY)
    # Note: Assuming commodity prices are in USD, so we multiply by USDJPY
    usd_jpy_rate = market_data.get('USDJPY', {}).get('price', 140.0)
    
    for comm, qty in agg_commodities.items():
        price = market_data.get(comm, {}).get('price', 0.0)
        vol = market_data.get(comm, {}).get('vol', 0.0)
        
        gross_jpy = qty * price * usd_jpy_rate
        hedged_qty = hedge_totals.get(comm, 0.0)
        hedged_jpy = hedged_qty * price * usd_jpy_rate
        net_qty = max(0.0, qty - hedged_qty)
        net_jpy = net_qty * price * usd_jpy_rate
        
        # 1-Sigma adverse shock (price goes UP)
        shocked_jpy = net_jpy * vol
        
        results['commodity'][comm] = {
            'gross_exposure_jpy': gross_jpy,
            'hedged_jpy': hedged_jpy,
            'net_exposure_jpy': net_jpy,
            'impact_1sigma_jpy': shocked_jpy,
            'vol': vol
        }

    # 4. Calculate FX Risk
    for pair, amount in agg_fx.items():
        rate = market_data.get(pair, {}).get('price', 0.0)
        vol = market_data.get(pair, {}).get('vol', 0.0)
        
        gross_jpy = amount * rate
        hedged_ccy = hedge_totals.get(pair, 0.0)
        hedged_jpy = hedged_ccy * rate
        net_ccy = max(0.0, amount - hedged_ccy)
        net_jpy = net_ccy * rate
        
        # 1-Sigma adverse shock (JPY appreciates / FX rate goes DOWN for foreign revenue, 
        # or FX goes UP if they are importing and spending FX. We assume 'annual_imports' means short FX).
        # A short exposure hurts when the pair goes UP.
        shocked_jpy = net_jpy * vol
        
        results['fx'][pair] = {
            'gross_exposure_jpy': gross_jpy,
            'hedged_jpy': hedged_jpy,
            'net_exposure_jpy': net_jpy,
            'impact_1sigma_jpy': shocked_jpy,
            'vol': vol
        }

    # 5. Calculate Interest Rate Risk (Using 10Y JGB as proxy)
    jgb_10y_yield = market_data.get('10Y', {}).get('price', 0.0) / 100.0  # Convert % to decimal
    jgb_10y_vol = market_data.get('10Y', {}).get('vol', 0.0)
    
    # Base annual interest expense
    gross_int_jpy = total_floating_debt * jgb_10y_yield
    hedged_debt = hedge_totals.get('Rates', 0.0) + hedge_totals.get('JGB', 0.0)
    
    net_debt = max(0.0, total_floating_debt - hedged_debt)
    net_int_jpy = net_debt * jgb_10y_yield
    
    # 1-Sigma shock to the yield (Yield goes UP -> expense goes UP)
    shocked_int_jpy = net_debt * (jgb_10y_yield * jgb_10y_vol)
    
    results['rates']['Floating Debt'] = {
        'gross_exposure_jpy': gross_int_jpy,
        'hedged_jpy': (total_floating_debt - net_debt) * jgb_10y_yield,
        'net_exposure_jpy': net_int_jpy,
        'impact_1sigma_jpy': shocked_int_jpy,
        'vol': jgb_10y_vol
    }

    return results

def calculate_financial_transmission(risk_profile: dict, financials: dict, sigma_multiplier: float = 1.0) -> dict:
    """
    Model the transmission of market shocks into financial statements.
    
    Args:
        risk_profile: Output from calculate_company_risk (contains JPY impacts).
        financials: Dictionary with baseline financials.
        sigma_multiplier: Stress severity — 1.0 = 1-sigma, 2.0 = 2-sigma, etc.
    
    Returns:
        Dictionary comparing 'Base' and 'Shocked' metrics.
    """
    # 1. Aggregate total shocks (scaled by sigma_multiplier)
    total_commodity_shock = sum(item['impact_1sigma_jpy'] for item in risk_profile['commodity'].values()) * sigma_multiplier
    total_fx_shock = sum(item['impact_1sigma_jpy'] for item in risk_profile['fx'].values()) * sigma_multiplier
    total_rate_shock = sum(item['impact_1sigma_jpy'] for item in risk_profile['rates'].values()) * sigma_multiplier
    
    # 2. Base metrics
    rev_base = float(financials.get('base_revenue', 0.0))
    cogs_base = float(financials.get('base_cogs', 0.0))
    opex_base = float(financials.get('base_opex', 0.0))
    tax_rate = float(financials.get('tax_rate', 0.30))
    cash_base = float(financials.get('starting_cash', 0.0))
    debt_base = float(financials.get('starting_debt', 0.0))
    ev_mult = float(financials.get('ev_ebitda_multiple', 8.0))
    
    # Extract baseline interest expense from the risk profile (assume it's the net_exposure_jpy)
    # The risk profile has floating debt interest expense under 'rates' -> 'Floating Debt'
    int_exp_base = risk_profile['rates']['Floating Debt']['net_exposure_jpy'] if 'Floating Debt' in risk_profile['rates'] else 0.0
    
    ebitda_base = rev_base - cogs_base - opex_base
    taxes_base = max(0.0, (ebitda_base - int_exp_base) * tax_rate)
    fcf_base = ebitda_base - int_exp_base - taxes_base
    ev_base = ebitda_base * ev_mult
    
    # 3. Shocked metrics
    # Assumption: adverse FX shock (e.g. stronger JPY) lowers export revenue
    rev_shock = rev_base - total_fx_shock
    
    # Assumption: adverse Commodity shock increases COGS
    cogs_shock = cogs_base + total_commodity_shock
    
    # Assumption: adverse Rate shock increases Interest Expense
    int_exp_shock = int_exp_base + total_rate_shock
    
    ebitda_shock = rev_shock - cogs_shock - opex_base
    taxes_shock = max(0.0, (ebitda_shock - int_exp_shock) * tax_rate)
    fcf_shock = ebitda_shock - int_exp_shock - taxes_shock
    
    cash_shock = cash_base + fcf_shock
    # If cash goes negative, we add to debt to plug the liquidity hole
    debt_shock = debt_base
    if cash_shock < 0:
        debt_shock += abs(cash_shock)
        cash_shock = 0.0
        
    ev_shock = ebitda_shock * ev_mult
    
    return {
        'Income Statement': {
            'Revenue': {'Base': rev_base, 'Shocked': rev_shock},
            'COGS': {'Base': -cogs_base, 'Shocked': -cogs_shock},
            'OpEx': {'Base': -opex_base, 'Shocked': -opex_base},
            'EBITDA': {'Base': ebitda_base, 'Shocked': ebitda_shock},
            'Interest Expense': {'Base': -int_exp_base, 'Shocked': -int_exp_shock},
            'Taxes': {'Base': -taxes_base, 'Shocked': -taxes_shock},
            'Net Income (FCF Proxy)': {'Base': fcf_base, 'Shocked': fcf_shock},
        },
        'Balance Sheet & Value': {
            'Ending Cash': {'Base': cash_base + fcf_base, 'Shocked': cash_shock},
            'Ending Debt': {'Base': debt_base, 'Shocked': debt_shock},
            'Enterprise Value': {'Base': ev_base, 'Shocked': ev_shock},
        },
        'Shock Drivers': {
            'Commodity Impact (Δ COGS)': -total_commodity_shock,
            'FX Impact (Δ Rev)': -total_fx_shock,
            'Rate Impact (Δ Int)': -total_rate_shock,
            'Total EBITDA Impact': ebitda_shock - ebitda_base,
            'Total EV Impact': ev_shock - ev_base,
        }
    }


def compute_hedge_coverage_ratios(risk_profile: dict) -> dict:
    """Return hedge coverage ratio (0–1) per factor from a computed risk profile.

    Returns:
        dict mapping factor name → {'coverage': float, 'gross_jpy': float, 'hedged_jpy': float}
    """
    coverage = {}
    for category in ['commodity', 'fx', 'rates']:
        for factor, metrics in risk_profile.get(category, {}).items():
            gross = metrics.get('gross_exposure_jpy', 0.0)
            hedged = metrics.get('hedged_jpy', 0.0)
            ratio = min(1.0, hedged / gross) if gross > 0 else 0.0
            coverage[factor] = {
                'coverage': ratio,
                'gross_jpy': gross,
                'hedged_jpy': hedged,
                'net_jpy': metrics.get('net_exposure_jpy', 0.0),
                'category': category,
            }
    return coverage


def compute_proximity_scores(financials: dict) -> dict:
    """Compute Proximity_i scores for each configured covenant constraint.

    Proximity_i = 1 / headroom_pct where headroom_pct = (current - minimum) / minimum.
    Higher proximity → closer to breach → higher urgency.

    Returns:
        dict mapping constraint name → {current, threshold, headroom_pct, proximity, breached}
    """
    scores = {}

    starting_cash = float(financials.get('starting_cash', 0.0))
    min_cash = float(financials.get('min_cash_buffer', 0.0))

    if min_cash > 0:
        if starting_cash <= min_cash:
            headroom_pct = 0.0
            proximity = 99.0  # effectively infinite / breached
            breached = True
        else:
            headroom_pct = (starting_cash - min_cash) / max(min_cash, 1.0)
            proximity = 1.0 / max(headroom_pct, 0.01)
            breached = False
        scores['Min Cash Buffer'] = {
            'current': starting_cash,
            'threshold': min_cash,
            'headroom_pct': headroom_pct * 100,
            'proximity': proximity,
            'breached': breached,
            'label': f"Cash ¥{starting_cash/1e9:.1f}B vs floor ¥{min_cash/1e9:.1f}B",
        }

    starting_debt = float(financials.get('starting_debt', 0.0))
    max_debt_ebitda = float(financials.get('max_debt_ebitda_ratio', 0.0))
    ebitda = (float(financials.get('base_revenue', 0.0))
              - float(financials.get('base_cogs', 0.0))
              - float(financials.get('base_opex', 0.0)))

    if max_debt_ebitda > 0 and ebitda > 0:
        current_ratio = starting_debt / ebitda
        if current_ratio >= max_debt_ebitda:
            headroom_pct = 0.0
            proximity = 99.0
            breached = True
        else:
            headroom = max_debt_ebitda - current_ratio
            headroom_pct = headroom / max(max_debt_ebitda, 0.01)
            proximity = 1.0 / max(headroom_pct, 0.01)
            breached = False
        scores['Debt/EBITDA Covenant'] = {
            'current': current_ratio,
            'threshold': max_debt_ebitda,
            'headroom_pct': headroom_pct * 100,
            'proximity': proximity,
            'breached': breached,
            'label': f"Net Debt/EBITDA {current_ratio:.2f}x vs max {max_debt_ebitda:.1f}x",
        }

    return scores


def compute_ev_sensitivities(risk_profile: dict, financials: dict) -> dict:
    """Compute ∂EV/∂factor — marginal EV impact per unit sigma of each risk factor.

    Returns:
        dict mapping factor name → EV impact (JPY) from 1-sigma adverse shock
    """
    ev_mult = float(financials.get('ev_ebitda_multiple', 8.0))
    tax_rate = float(financials.get('tax_rate', 0.30))
    sensitivities = {}

    # Commodity: 1-sigma adverse → COGS up → EBITDA down → EV down
    for factor, metrics in risk_profile.get('commodity', {}).items():
        impact_1s = metrics.get('impact_1sigma_jpy', 0.0)
        # EBITDA drops by the shock amount; EV = EBITDA × multiple (pre-tax simplification)
        dEV = -impact_1s * ev_mult
        sensitivities[factor] = {'dEV_per_sigma': dEV, 'category': 'Commodity', 'impact_1s_jpy': impact_1s}

    # FX: 1-sigma adverse → Revenue down → EBITDA down → EV down
    for factor, metrics in risk_profile.get('fx', {}).items():
        impact_1s = metrics.get('impact_1sigma_jpy', 0.0)
        dEV = -impact_1s * ev_mult
        sensitivities[factor] = {'dEV_per_sigma': dEV, 'category': 'FX', 'impact_1s_jpy': impact_1s}

    # Rates: 1-sigma adverse → Interest expense up → FCF down (but EBITDA unchanged)
    for factor, metrics in risk_profile.get('rates', {}).items():
        impact_1s = metrics.get('impact_1sigma_jpy', 0.0)
        # Rate shock hits below EBITDA, so EV (EBITDA × multiple) is unaffected
        # but FCF and firm value drop; we report net income impact as proxy
        dFCF = -impact_1s * (1 - tax_rate)
        sensitivities[factor] = {'dEV_per_sigma': dFCF, 'category': 'Rates', 'impact_1s_jpy': impact_1s}

    return sensitivities


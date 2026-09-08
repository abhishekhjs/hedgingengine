import pandas as pd
import numpy as np

def run_monte_carlo_simulation(conn, risk_profile, financials, n_iterations=10000):
    """
    Run a Monte Carlo simulation of financial transmission.
    """
    # 1. Fetch historical returns
    df = pd.read_sql("SELECT date, asset, return_1d FROM risk_metrics WHERE return_1d IS NOT NULL", conn)
    ret_df = df.pivot(index='date', columns='asset', values='return_1d')
    
    # Fill NAs and compute covariance
    # Explicitly cast to float, replace inf with nan, then fill nan with 0.0
    ret_df = ret_df.astype(float)
    ret_df = ret_df.replace([np.inf, -np.inf], np.nan)
    ret_df = ret_df.fillna(0.0)
    assets = ret_df.columns.tolist()
    
    cov_matrix = ret_df.cov().values * 252  # Annualized covariance
    corr_matrix = ret_df.corr()
    
    # Ensure positive semi-definite
    min_eig = np.min(np.linalg.eigvals(cov_matrix))
    if min_eig < 0:
        cov_matrix -= 10.0 * min_eig * np.eye(*cov_matrix.shape)
        
    L = np.linalg.cholesky(cov_matrix)
    
    # 2. Simulate N scenarios of 1-year returns
    Z = np.random.standard_normal((n_iterations, len(assets)))
    sim_returns = Z @ L.T  # Shape: (10000, num_assets)
    
    # Helper to get simulated return column
    def get_sim_ret(asset_name):
        if asset_name in assets:
            idx = assets.index(asset_name)
            return sim_returns[:, idx]
        return np.zeros(n_iterations)
        
    # 3. Apply simulated returns to Net Exposures
    
    # We will compute the change in cost/revenue for each scenario.
    # In Phase 2:
    # Commodity Impact = Net JPY * Vol (where Net JPY = net_qty * Price * USDJPY)
    # With MC, Simulated Price = Price * exp(sim_ret)
    # The impact (loss/gain) = Net JPY * (exp(sim_ret) - 1)
    # Wait! If price goes up by 10%, cost goes up by 10%, so impact on COGS is positive (bad).
    
    mc_cogs_impact = np.zeros(n_iterations)
    mc_rev_impact = np.zeros(n_iterations)
    mc_int_impact = np.zeros(n_iterations)
    
    # Commodities
    for comm, metrics in risk_profile.get('commodity', {}).items():
        net_jpy = metrics.get('net_exposure_jpy', 0.0)
        # Assuming asset is priced in USD, the simulated return of the commodity in JPY 
        # is approximately the sum of the log return of the commodity + log return of USDJPY.
        # But we can just use the commodity's simulated return for the commodity price,
        # and USDJPY simulated return for the FX rate.
        ret_c = get_sim_ret(comm)
        ret_fx = get_sim_ret('USDJPY')
        # Combined return = ret_c + ret_fx
        sim_multiplier = np.exp(ret_c + ret_fx) - 1.0
        # If multiplier > 0, price went up, COGS goes up
        mc_cogs_impact += net_jpy * sim_multiplier

    # FX (Imports)
    for pair, metrics in risk_profile.get('fx', {}).items():
        net_jpy = metrics.get('net_exposure_jpy', 0.0)
        ret_fx = get_sim_ret(pair)
        sim_multiplier = np.exp(ret_fx) - 1.0
        # Wait, if they import, they are short FX. If FX goes up, costs go up, so it hits COGS?
        # In Phase 3, we mapped FX Impact to Revenue (assuming exporter).
        # Let's map it to Revenue as we did in Phase 3. If FX goes down (JPY strengthens), revenue goes down.
        # So rev_impact = net_jpy * sim_multiplier (If sim_multiplier < 0, rev goes down).
        mc_rev_impact += net_jpy * sim_multiplier

    # Rates
    for rate_name, metrics in risk_profile.get('rates', {}).items():
        net_jpy = metrics.get('net_exposure_jpy', 0.0)
        # Yield is modeled via 10Y.
        ret_rate = get_sim_ret('10Y')
        sim_multiplier = np.exp(ret_rate) - 1.0
        # If rates go up, interest expense goes up
        mc_int_impact += net_jpy * sim_multiplier
        
    # 4. Financial Transmission (Vectorized)
    rev_base = float(financials.get('base_revenue', 0.0))
    cogs_base = float(financials.get('base_cogs', 0.0))
    opex_base = float(financials.get('base_opex', 0.0))
    tax_rate = float(financials.get('tax_rate', 0.30))
    cash_base = float(financials.get('starting_cash', 0.0))
    debt_base = float(financials.get('starting_debt', 0.0))
    ev_mult = float(financials.get('ev_ebitda_multiple', 8.0))
    
    int_exp_base = risk_profile.get('rates', {}).get('Floating Debt', {}).get('net_exposure_jpy', 0.0)
    
    # Base EBITDA
    ebitda_base = rev_base - cogs_base - opex_base
    
    # Simulated Line Items
    sim_rev = rev_base + mc_rev_impact
    sim_cogs = cogs_base + mc_cogs_impact
    sim_int_exp = int_exp_base + mc_int_impact
    
    sim_ebitda = sim_rev - sim_cogs - opex_base
    
    # FCF = EBITDA - Interest - Taxes
    sim_taxes = np.maximum(0.0, (sim_ebitda - sim_int_exp) * tax_rate)
    sim_fcf = sim_ebitda - sim_int_exp - sim_taxes
    
    sim_ev = sim_ebitda * ev_mult
    sim_cash = cash_base + sim_fcf
    
    # 5. Compute distribution metrics (Phase 5: EVaR, CFaR, LaR)
    def calc_risk_metrics(sim_array):
        var_95 = np.percentile(sim_array, 5)
        var_99 = np.percentile(sim_array, 1)
        tail = sim_array[sim_array <= var_95]
        cvar_95 = np.mean(tail) if len(tail) > 0 else var_95
        return var_95, var_99, cvar_95
        
    ev_var95, ev_var99, ev_cvar95 = calc_risk_metrics(sim_ev)
    fcf_var95, fcf_var99, fcf_cvar95 = calc_risk_metrics(sim_fcf)
    cash_var95, cash_var99, cash_cvar95 = calc_risk_metrics(sim_cash)
    
    liquidity_shortfall_prob = np.mean(sim_cash < 0) * 100.0
    
    results = {
        'correlation_matrix': corr_matrix,
        'simulated_ev': sim_ev,
        'simulated_fcf': sim_fcf,
        'simulated_cash': sim_cash,
        'base_metrics': {
            'EV': ebitda_base * ev_mult,
            'FCF': sim_fcf.mean() - np.mean(mc_rev_impact - mc_cogs_impact - mc_int_impact), # approximated base
            'Liquidity': cash_base + (sim_fcf.mean() - np.mean(mc_rev_impact - mc_cogs_impact - mc_int_impact))
        },
        # Calculate exact bases for cleaner UI
        'base_ev': ebitda_base * ev_mult,
        'base_fcf': ebitda_base - int_exp_base - np.maximum(0.0, (ebitda_base - int_exp_base) * tax_rate),
        'base_cash': cash_base + (ebitda_base - int_exp_base - np.maximum(0.0, (ebitda_base - int_exp_base) * tax_rate)),
        
        'risk_metrics': {
            'EV': {'var_95': ev_var95, 'var_99': ev_var99, 'cvar_95': ev_cvar95},
            'FCF': {'var_95': fcf_var95, 'var_99': fcf_var99, 'cvar_95': fcf_cvar95},
            'Liquidity': {'var_95': cash_var95, 'var_99': cash_var99, 'cvar_95': cash_cvar95},
        },
        'liquidity_shortfall_prob': liquidity_shortfall_prob
    }
    return results

import pandas as pd
import numpy as np

def generate_market_insight(latest_per_asset: pd.DataFrame) -> str:
    """Generate insight based on z-scores of market assets."""
    if latest_per_asset.empty:
        return "No market data available for analysis."
        
    highest_z_asset = latest_per_asset.loc[latest_per_asset['z_score'].abs().idxmax()]
    highest_z_val = highest_z_asset['z_score']
    asset_name = highest_z_asset['asset']
    
    if abs(highest_z_val) > 3.0:
        return f"CRITICAL MARKET ALERT: <strong>{asset_name}</strong> is experiencing extreme stress with a Z-score of <strong>{highest_z_val:.2f}σ</strong>. This indicates a severe 3-sigma deviation from historical norms, highly likely to trigger margin calls or break correlation models. Immediate attention required to ensure sufficient liquidity buffers."
    elif abs(highest_z_val) > 2.0:
        return f"Market Alert: <strong>{asset_name}</strong> is showing elevated stress (Z-score <strong>{highest_z_val:.2f}σ</strong>). Trading outside the 95% confidence interval, this anomaly suggests a potential structural shift in the underlying asset's regime. Monitor closely for contagion effects into associated corporate exposures."
    else:
        return f"Market conditions are relatively stable. The highest volatility driver is <strong>{asset_name}</strong> with a Z-score of <strong>{highest_z_val:.2f}σ</strong>, remaining within normal historical operating bands. No immediate systemic market shocks are detected."

def generate_exposure_insight(gross_total: float, net_total: float, cat_totals: dict) -> str:
    """Generate insight based on corporate exposures and hedge coverage."""
    if gross_total == 0:
        return "No corporate exposures found. The balance sheet is perfectly neutral to market risks."
        
    total_hedged = gross_total - net_total
    coverage_pct = (total_hedged / gross_total) * 100
    top_cat = max(cat_totals, key=cat_totals.get)
    
    insight = f"Our gross risk exposure across the enterprise stands at <strong>JPY {gross_total/1e9:,.1f} Billion</strong>. "
    
    if coverage_pct < 20:
        insight += f"We are alarmingly under-hedged, covering only <strong>{coverage_pct:.1f}%</strong> of this risk. This leaves a massive net exposure gap of <strong>JPY {net_total/1e9:,.1f} Billion</strong>, entirely vulnerable to market swings. "
    elif coverage_pct < 60:
        insight += f"We are partially hedged, actively protecting <strong>{coverage_pct:.1f}%</strong> of the risk. However, the remaining net exposure of <strong>JPY {net_total/1e9:,.1f} Billion</strong> still requires strategic oversight. "
    else:
        insight += f"Our hedging program is robust, covering <strong>{coverage_pct:.1f}%</strong> of our total risk, successfully reducing net exposure to a manageable <strong>JPY {net_total/1e9:,.1f} Billion</strong>. "
        
    insight += f"The primary driver of our vulnerability is the <strong>{top_cat}</strong> factor (grossing JPY {cat_totals.get(top_cat, 0)/1e9:,.1f}B). A shock to this segment would propagate most severely through our operating margins."
    return insight

def generate_transmission_insight(sensitivities: dict) -> str:
    """Generate insight on Enterprise Value sensitivities."""
    if not sensitivities:
        return "No significant sensitivities found. Enterprise Value is isolated from 1-sigma market shocks based on current parameters."
        
    sorted_sens = sorted(sensitivities.items(), key=lambda x: abs(x[1]["dEV_per_sigma"]))
    top_factor = sorted_sens[-1]
    impact_jpy = abs(top_factor[1]['dEV_per_sigma'])
    
    if impact_jpy > 50e9:
        severity = "catastrophic"
    elif impact_jpy > 10e9:
        severity = "severe"
    else:
        severity = "moderate"
        
    return f"Financial Transmission Alert: <strong>{top_factor[0]}</strong> poses the highest sensitivity to the company's valuation. A standard 1-sigma market shock to this specific factor alone creates a {severity} transmission effect, destroying exactly <strong>JPY {impact_jpy/1e9:,.1f} Billion</strong> in Enterprise Value. If this exposure crosses debt covenant thresholds, it will trigger accelerated loan recalls."

def generate_montecarlo_insight(cfar_95: float, base_fcf: float, evar_95: float) -> str:
    """Generate insight on Monte Carlo tail risk."""
    cfar_delta = cfar_95 - base_fcf
    
    insight = f"We executed a rigorous 10,000-iteration Monte Carlo simulation using current covariance matrices. "
    insight += f"At the 95% confidence level (Tail Risk), Free Cash Flow (FCF) collapses to <strong>JPY {cfar_95/1e9:,.1f} Billion</strong>, representing a severe liquidity drain of <strong>JPY {abs(cfar_delta)/1e9:,.1f}B</strong> against the baseline. "
    
    if cfar_95 < 0:
        insight += "CRITICAL WARNING: This CFaR outcome is negative, implying an absolute liquidity shortfall. The company would be insolvent under this 5% probability tail event without drawing emergency credit lines. "
        
    insight += f"Concurrently, the Enterprise Value at Risk (EVaR) plummets to <strong>JPY {evar_95/1e9:,.1f} Billion</strong>."
    return insight

def generate_optimization_insight(priorities_dict: list) -> str:
    """Generate insight for hedge optimization."""
    if not priorities_dict:
        return "No optimization priorities available. Current hedge portfolio is fully optimized or risk levels are negligible."
        
    top = priorities_dict[0]
    score = top['HedgePriority Score']
    factor = top['Factor']
    
    if score > 80:
        urgency = "immediate, critical action"
    elif score > 50:
        urgency = "prompt strategic review"
    else:
        urgency = "routine adjustment"
        
    return f"Strategic Optimization Matrix: Based on our proximity to covenant breaches and unhedged gaps, <strong>{factor}</strong> ({top['Category']}) emerges as the highest unhedged tail-risk priority (Score: <strong>{score:.3f}</strong>). The current coverage ratio of {top['Coverage %']:.0f}% is dangerously suboptimal. We strongly recommend {urgency}: <strong>{top['Action']}</strong> to maximize preserved Enterprise Value and restore the efficient frontier."

"""Phase 5 Analytics: Hedge Priority Scoring and Efficient Frontier.

This module implements the HedgePriority formula from the Phase 5/6 spec
(section 10.1.3) using real computed values from Phases 2-4.

    HedgePriority_i = CFaR_i x Proximity_i x (1 - ExistingHedgeCoverage_i)

The joint optimization (section 10.1.6) is deferred to Phase 6.
"""
import copy
import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def compute_hedge_priority_scores(
    risk_profile: dict,
    mc_results: dict,
    coverage_ratios: dict,
    proximity_scores: dict,
) -> pd.DataFrame:
    """Compute HedgePriority_i for each risk factor.

    HedgePriority_i = CFaR_i x Proximity_i x (1 - Coverage_i)

    Args:
        risk_profile:     Output of calculate_company_risk().
        mc_results:       Output of run_monte_carlo_simulation() -- provides CFaR.
        coverage_ratios:  Output of compute_hedge_coverage_ratios().
        proximity_scores: Output of compute_proximity_scores().

    Returns:
        DataFrame with columns: Factor, Category, Gross Exposure, CFaR Contrib,
        Proximity, Coverage, HedgePriority Score, Recommendation
    """
    # Build per-factor CFaR contribution via proportional attribution
    total_1s_impact = sum(
        v.get("impact_1sigma_jpy", 0.0)
        for cat in ["commodity", "fx", "rates"]
        for v in risk_profile.get(cat, {}).values()
    )
    cfar_portfolio = abs(
        mc_results["risk_metrics"]["FCF"]["var_95"] - mc_results["base_fcf"]
    )

    rows = []
    for category in ["commodity", "fx", "rates"]:
        for factor, metrics in risk_profile.get(category, {}).items():
            impact_1s = metrics.get("impact_1sigma_jpy", 0.0)
            if impact_1s <= 0:
                continue

            # Proportional CFaR contribution
            share = impact_1s / max(total_1s_impact, 1.0)
            cfar_i = cfar_portfolio * share

            # Coverage from Phase 2
            cov_data = coverage_ratios.get(factor, {})
            coverage_i = cov_data.get("coverage", 0.0)

            # Proximity: use max across configured constraints, or 1.0 if none configured
            proximity_i = max(
                (v["proximity"] for v in proximity_scores.values()),
                default=1.0,
            )
            proximity_i = min(proximity_i, 10.0)  # cap at 10 for display

            priority_score = cfar_i * proximity_i * (1.0 - coverage_i)

            if coverage_i < 0.30:
                rec = "Increase coverage urgently"
            elif coverage_i < 0.60:
                rec = "Consider increasing coverage"
            else:
                rec = "Adequate coverage"

            rows.append({
                "Factor": factor,
                "Category": category.capitalize(),
                "Gross Exposure (JPY B)": round(metrics.get("gross_exposure_jpy", 0.0) / 1e9, 2),
                "CFaR Contrib (JPY B)": round(cfar_i / 1e9, 2),
                "Proximity Score": round(proximity_i, 2),
                "Coverage %": round(coverage_i * 100, 1),
                "HedgePriority Score": round(priority_score / 1e9, 3),
                "Action": rec,
                "_priority_raw": priority_score,
                "_coverage_raw": coverage_i,
            })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows).sort_values("_priority_raw", ascending=False)
    df = df.drop(columns=["_priority_raw", "_coverage_raw"])
    df = df.reset_index(drop=True)
    df.index = df.index + 1
    df.index.name = "Rank"
    return df


def compute_factor_attribution(conn, risk_profile: dict, financials: dict, n_iterations: int = 5000) -> dict:
    """Attribute tail loss to each risk factor via ablation simulation.

    Runs 4 Monte Carlo simulations: full, no-commodity, no-FX, no-rates.
    Marginal contribution of each factor = how much tail loss disappears without it.

    Returns:
        dict with keys Commodity, FX, Rates, Interaction, Total CFaR, base_fcf, cfar_full.
    """
    from src.analytics.monte_carlo import run_monte_carlo_simulation

    def zero_category(profile, category):
        p = copy.deepcopy(profile)
        for factor in p.get(category, {}):
            p[category][factor]["net_exposure_jpy"] = 0.0
            p[category][factor]["impact_1sigma_jpy"] = 0.0
        return p

    np.random.seed(42)
    res_full = run_monte_carlo_simulation(conn, risk_profile, financials, n_iterations)
    cfar_full = res_full["risk_metrics"]["FCF"]["var_95"]
    base_fcf = res_full["base_fcf"]

    np.random.seed(42)
    res_no_comm = run_monte_carlo_simulation(conn, zero_category(risk_profile, "commodity"), financials, n_iterations)
    cfar_no_comm = res_no_comm["risk_metrics"]["FCF"]["var_95"]

    np.random.seed(42)
    res_no_fx = run_monte_carlo_simulation(conn, zero_category(risk_profile, "fx"), financials, n_iterations)
    cfar_no_fx = res_no_fx["risk_metrics"]["FCF"]["var_95"]

    np.random.seed(42)
    res_no_rates = run_monte_carlo_simulation(conn, zero_category(risk_profile, "rates"), financials, n_iterations)
    cfar_no_rates = res_no_rates["risk_metrics"]["FCF"]["var_95"]

    comm_contrib = max(0.0, cfar_no_comm - cfar_full)
    fx_contrib = max(0.0, cfar_no_fx - cfar_full)
    rates_contrib = max(0.0, cfar_no_rates - cfar_full)

    total_actual = base_fcf - cfar_full
    interaction = total_actual - (comm_contrib + fx_contrib + rates_contrib)

    return {
        "Commodity": comm_contrib,
        "FX": fx_contrib,
        "Rates": rates_contrib,
        "Interaction / Diversification": interaction,
        "Total CFaR": total_actual,
        "base_fcf": base_fcf,
        "cfar_full": cfar_full,
    }


def compute_efficient_frontier(conn, risk_profile: dict, financials: dict, steps: int = 6) -> pd.DataFrame:
    """Grid-search commodity vs FX coverage pairs and record 95% CFaR for each.

    Returns a wide pivot table (commodity coverage as index, FX coverage as columns)
    with CFaR values in JPY billions -- suitable for a heatmap.
    """
    from src.analytics.monte_carlo import run_monte_carlo_simulation
    from src.dashboard.optimization_ui import apply_hypothetical_hedges

    ratios = [round(i / (steps - 1), 2) for i in range(steps)]
    records = []

    for comm_r in ratios:
        for fx_r in ratios:
            opt_profile = apply_hypothetical_hedges(risk_profile, comm_r, fx_r, 0.5)
            np.random.seed(42)
            res = run_monte_carlo_simulation(conn, opt_profile, financials, n_iterations=2000)
            cfar = res["risk_metrics"]["FCF"]["var_95"] / 1e9
            records.append({
                "Commodity Coverage": f"{comm_r:.0%}",
                "FX Coverage": f"{fx_r:.0%}",
                "comm_r": comm_r,
                "fx_r": fx_r,
                "CFaR_95_B": round(cfar, 2),
            })

    df = pd.DataFrame(records)
    pivot = df.pivot(index="Commodity Coverage", columns="FX Coverage", values="CFaR_95_B")
    return pivot

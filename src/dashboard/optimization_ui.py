"""UI components for Phase 5: Hedge Optimization & Priority Scoring."""
import streamlit as st
import logging
import copy
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

from src.db.connection import get_connection
from src.dashboard.exposure_ui import load_company_names, load_exposure_data, load_hedge_data
from src.dashboard.transmission_ui import load_financials
from src.analytics.exposure_calc import (
    get_latest_market_data,
    calculate_company_risk,
    compute_hedge_coverage_ratios,
    compute_proximity_scores,
)
from src.analytics.monte_carlo import run_monte_carlo_simulation

logger = logging.getLogger(__name__)


def apply_hypothetical_hedges(risk_profile, comm_ratio, fx_ratio, rate_ratio):
    """Override the risk profile with hypothetical hedge ratios for scenario testing."""
    new_profile = copy.deepcopy(risk_profile)
    for comm, metrics in new_profile.get("commodity", {}).items():
        gross = metrics["gross_exposure_jpy"]
        metrics["hedged_jpy"] = gross * comm_ratio
        metrics["net_exposure_jpy"] = max(0.0, gross - metrics["hedged_jpy"])
    for pair, metrics in new_profile.get("fx", {}).items():
        gross = metrics["gross_exposure_jpy"]
        metrics["hedged_jpy"] = gross * fx_ratio
        metrics["net_exposure_jpy"] = max(0.0, gross - metrics["hedged_jpy"])
    for rate_item, metrics in new_profile.get("rates", {}).items():
        gross = metrics["gross_exposure_jpy"]
        metrics["hedged_jpy"] = gross * rate_ratio
        metrics["net_exposure_jpy"] = max(0.0, gross - metrics["hedged_jpy"])
    return new_profile


def render_optimization_tab():
    """Render the Phase 5 Hedge Optimization & Priority Scoring UI."""
    st.subheader("Hedge Optimization & Priority Scoring")
    st.caption(
        "Rank hedging priorities using HedgePriority_i = CFaR_i * Proximity_i * (1 - Coverage_i), "
        "then calibrate optimal factor coverage ratios."
    )

    existing_companies = load_company_names()
    company_name = st.selectbox(
        "Select Enterprise Profile",
        options=existing_companies,
        key="opt_company_select",
    )
    if not company_name:
        st.info("Please select a company to continue.")
        return

    financials = load_financials(company_name)
    if not financials:
        st.warning("No baseline financials found. Please configure them in the Financial Transmission tab.")
        return

    # Load and compute base data
    with st.spinner("Loading exposure and hedge data..."):
        try:
            with get_connection() as conn:
                market_data = get_latest_market_data(conn)
            exposure = load_exposure_data(company_name)
            hedges = load_hedge_data(company_name)
            actual_profile = calculate_company_risk(exposure, hedges, market_data)
            coverage_ratios = compute_hedge_coverage_ratios(actual_profile)
            proximity_scores = compute_proximity_scores(financials)
        except Exception as e:
            st.error(f"Could not load data: {e}")
            return

    # -----------------------------------------------------------------------
    # 1. HedgePriority Ranking Table
    # -----------------------------------------------------------------------
    st.markdown("#### HedgePriority Ranking")
    st.caption(
        "**Formula:** HedgePriority_i = CFaR_i * Proximity_i * (1 - Coverage_i) "
        "— ranked descending. Top-ranked factor should be hedged first."
    )

    if "opt_mc_results" not in st.session_state or st.session_state.get("opt_company") != company_name:
        st.session_state["opt_mc_results"] = None
        st.session_state["opt_company"] = company_name

    if st.button("Compute Hedge Priority Scores (runs 10k MC)", type="primary"):
        with st.spinner("Running Monte Carlo for CFaR inputs..."):
            try:
                with get_connection() as conn:
                    np.random.seed(42)
                    mc_res = run_monte_carlo_simulation(conn, actual_profile, financials, n_iterations=10000)
                st.session_state["opt_mc_results"] = mc_res
            except Exception as e:
                import traceback
                logger.error(traceback.format_exc())
                st.error(f"MC simulation failed: {e}")

    mc_results = st.session_state.get("opt_mc_results")

    if mc_results is not None:
        from src.analytics.hedge_optimizer import compute_hedge_priority_scores
        priority_df = compute_hedge_priority_scores(actual_profile, mc_results, coverage_ratios, proximity_scores)

        if not priority_df.empty:
            st.dataframe(priority_df, use_container_width=True)

            # Top recommendation banner
            top = priority_df.iloc[0]
            st.info(
                f"**Highest Priority:** **{top['Factor']}** ({top['Category']}) — "
                f"HedgePriority Score {top['HedgePriority Score']:.3f}. "
                f"Current coverage: {top['Coverage %']:.0f}%. {top['Action']}."
            )
        else:
            st.info("No factor exposures found. Enter exposures in the Company Exposure Mapping tab.")

    st.divider()

    # -----------------------------------------------------------------------
    # 2. Financial Flexibility Quantification
    # -----------------------------------------------------------------------
    st.markdown("#### Financial Flexibility Value")
    st.caption("How much EV does the current hedge overlay preserve versus an unhedged position?")

    with st.spinner("Simulating hedge scenarios..."):
        try:
            unhedged_profile = apply_hypothetical_hedges(actual_profile, 0.0, 0.0, 0.0)
            with get_connection() as conn:
                np.random.seed(42)
                res_unhedged = run_monte_carlo_simulation(conn, unhedged_profile, financials, n_iterations=10000)
                np.random.seed(42)
                res_actual = run_monte_carlo_simulation(conn, actual_profile, financials, n_iterations=10000)

            unhedged_evar = res_unhedged["risk_metrics"]["EV"]["var_95"]
            actual_evar = res_actual["risk_metrics"]["EV"]["var_95"]
            flexibility_value = actual_evar - unhedged_evar

            st.info(
                f"Active hedges preserve **JPY {flexibility_value/1e9:,.1f} Billion** in Enterprise Value "
                f"at the 95% tail-risk threshold vs. an unhedged position."
            )

            fc1, fc2 = st.columns(2)
            fc1.metric("Unhedged 95% EVaR", f"JPY {unhedged_evar/1e9:,.1f}B")
            fc2.metric(
                "Current Hedged 95% EVaR",
                f"JPY {actual_evar/1e9:,.1f}B",
                delta=f"+JPY {flexibility_value/1e9:,.1f}B protected",
            )
        except Exception as e:
            import traceback
            logger.error(traceback.format_exc())
            st.error(f"Could not compute flexibility value: {e}")
            res_actual = None

    st.divider()

    # -----------------------------------------------------------------------
    # 3. Interactive Strategy Calibration
    # -----------------------------------------------------------------------
    st.markdown("#### Strategy Calibration")
    st.caption("Adjust target coverage ratios to compare optimized strategy against current overlay.")

    col_controls, col_chart = st.columns([1, 2])

    try:
        with col_controls:
            st.markdown("##### Target Hedge Ratios")
            comm_pct = st.slider("Commodities Coverage", 0, 100, 50, 5, format="%d%%")
            fx_pct = st.slider("Foreign Exchange Coverage", 0, 100, 50, 5, format="%d%%")
            rate_pct = st.slider("Interest Rate Coverage", 0, 100, 50, 5, format="%d%%")
            comm_target, fx_target, rate_target = comm_pct / 100, fx_pct / 100, rate_pct / 100

        with col_chart:
            opt_profile = apply_hypothetical_hedges(actual_profile, comm_target, fx_target, rate_target)
            with get_connection() as conn:
                np.random.seed(42)
                res_opt = run_monte_carlo_simulation(conn, opt_profile, financials, n_iterations=10000)

            opt_evar = res_opt["risk_metrics"]["EV"]["var_95"]
            opt_cfar = res_opt["risk_metrics"]["FCF"]["var_95"]

            scenarios = ["Unhedged Baseline", "Current Overlay", "Optimized Strategy"]
            evar_values = [unhedged_evar, actual_evar, opt_evar]
            opt_color = "#4318FF" if opt_evar >= actual_evar else "#EE5D50"

            fig = go.Figure(go.Bar(
                x=scenarios,
                y=[v / 1e9 for v in evar_values],
                text=[f"JPY {v/1e9:.1f}B" for v in evar_values],
                textposition="auto",
                marker=dict(
                    color=["#EE5D50", "#A3AED0", opt_color],
                    line=dict(color="#FFFFFF", width=1.5),
                ),
            ))
            fig.update_layout(
                title=dict(text="95% Enterprise Value-at-Risk by Strategy",
                           font=dict(size=14, color="#2B3674")),
                yaxis_title="95% EVaR (JPY B)",
                showlegend=False,
                height=340,
                margin=dict(l=30, r=20, t=40, b=30),
                paper_bgcolor="#FFFFFF",
                plot_bgcolor="#FFFFFF",
            )
            st.plotly_chart(fig, use_container_width=True)

        # Optimized summary metrics
        st.markdown("##### Optimized Strategy Tail Risk")
        oc1, oc2, oc3 = st.columns(3)
        oc1.metric(
            "Optimized 95% EVaR",
            f"JPY {opt_evar/1e9:,.1f}B",
            delta=f"JPY {(opt_evar - actual_evar)/1e9:,.1f}B vs Current",
        )
        oc2.metric(
            "Optimized 95% CFaR",
            f"JPY {opt_cfar/1e9:,.1f}B",
            delta=f"JPY {(opt_cfar - res_actual['risk_metrics']['FCF']['var_95'])/1e9:,.1f}B vs Current",
        )
        prob_shortfall = res_opt["liquidity_shortfall_prob"]
        if prob_shortfall > 0:
            oc3.error(f"Liquidity Shortfall Risk: {prob_shortfall:.1f}%")
        else:
            oc3.success("Liquidity: 100% Protected")

    except Exception as e:
        import traceback
        logger.error(f"Calibration error: {traceback.format_exc()}")
        st.error(f"Could not run calibration: {e}")

    # -----------------------------------------------------------------------
    # 4. Efficient Frontier Heatmap
    # -----------------------------------------------------------------------
    st.divider()
    st.markdown("#### Efficient Frontier — Commodity vs FX Coverage")
    st.caption(
        "Each cell shows 95% CFaR (JPY B) at a given commodity/FX coverage combination "
        "(rate coverage held at 50%). Darker = less tail risk."
    )

    if st.button("Compute Efficient Frontier Grid (~45s)", help="Runs 36 Monte Carlo simulations"):
        with st.spinner("Running frontier grid (36 scenarios x 2,000 iterations)..."):
            try:
                from src.analytics.hedge_optimizer import compute_efficient_frontier
                pivot = compute_efficient_frontier(conn=None, risk_profile=actual_profile,
                                                  financials=financials, steps=6)
                # Re-run with proper conn
                with get_connection() as conn:
                    pass
                from src.analytics.hedge_optimizer import compute_efficient_frontier as cef

                records = []
                ratios = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
                for comm_r in ratios:
                    for fx_r in ratios:
                        opt_p = apply_hypothetical_hedges(actual_profile, comm_r, fx_r, 0.5)
                        with get_connection() as conn:
                            np.random.seed(42)
                            res = run_monte_carlo_simulation(conn, opt_p, financials, n_iterations=2000)
                        cfar = res["risk_metrics"]["FCF"]["var_95"] / 1e9
                        records.append({
                            "Commodity": f"{comm_r:.0%}",
                            "FX": f"{fx_r:.0%}",
                            "CFaR_95_B": round(cfar, 2),
                        })

                df_frontier = pd.DataFrame(records)
                pivot = df_frontier.pivot(index="Commodity", columns="FX", values="CFaR_95_B")
                st.session_state["opt_frontier"] = pivot

            except Exception as e:
                import traceback
                logger.error(traceback.format_exc())
                st.error(f"Could not compute frontier: {e}")

    frontier = st.session_state.get("opt_frontier")
    if frontier is not None:
        fig_frontier = px.imshow(
            frontier,
            text_auto=True,
            aspect="auto",
            color_continuous_scale=[[0, "#4318FF"], [0.5, "#F4F7FE"], [1, "#EE5D50"]],
            labels=dict(x="FX Coverage", y="Commodity Coverage", color="CFaR (JPY B)"),
        )
        fig_frontier.update_layout(
            height=380,
            margin=dict(l=20, r=20, t=30, b=20),
            paper_bgcolor="#FFFFFF",
        )
        st.plotly_chart(fig_frontier, use_container_width=True)
        st.caption("Blue = lower CFaR (less tail risk). Red = higher CFaR (more tail risk).")

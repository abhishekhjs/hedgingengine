"""UI components for Phase 4: Monte Carlo Simulation & Correlation."""
import streamlit as st
import logging
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import pandas as pd

from src.db.connection import get_connection
from src.dashboard.exposure_ui import load_company_names
from src.dashboard.transmission_ui import load_financials

logger = logging.getLogger(__name__)


def render_monte_carlo_tab():
    """Render the Phase 4 Monte Carlo UI."""
    st.subheader("Monte Carlo & Correlation Analysis")
    st.caption("Stochastic 10,000-scenario simulation driven by historical Cholesky-correlated log returns.")

    # 1. Company Selection
    existing_companies = load_company_names()
    company_name = st.selectbox(
        "Select Enterprise Profile",
        options=existing_companies,
        key="mc_company_select",
    )
    if not company_name:
        st.info("Please select a company to continue.")
        return

    financials = load_financials(company_name)
    if not financials:
        st.warning("No baseline financials found. Please configure them in the Financial Transmission tab first.")
        return

    st.markdown("---")

    if "mc_company" not in st.session_state or st.session_state["mc_company"] != company_name:
        st.session_state["mc_results"] = None
        st.session_state["mc_attr"] = None
        st.session_state["mc_company"] = company_name

    col_run, col_attr = st.columns([1, 1])
    with col_run:
        run_sim = st.button("Run Monte Carlo (10,000 iterations)", type="primary", use_container_width=True)
    with col_attr:
        run_attr = st.button("Run Factor Attribution (ablation, ~30s)", use_container_width=True)

    if run_sim:
        with st.spinner("Executing 10,000 correlated market draws..."):
            from src.dashboard.exposure_ui import load_exposure_data, load_hedge_data
            from src.analytics.exposure_calc import get_latest_market_data, calculate_company_risk
            from src.analytics.monte_carlo import run_monte_carlo_simulation

            try:
                with get_connection() as conn:
                    market_data = get_latest_market_data(conn)
                    exposure = load_exposure_data(company_name)
                    hedges = load_hedge_data(company_name)
                    risk_profile = calculate_company_risk(exposure, hedges, market_data)
                    results = run_monte_carlo_simulation(conn, risk_profile, financials, n_iterations=10000)
                st.session_state["mc_results"] = results
                st.session_state["mc_risk_profile"] = risk_profile
            except Exception as e:
                import traceback
                logger.error(f"Monte Carlo error:\n{traceback.format_exc()}")
                st.error(f"Could not run simulation: {e}")

    if run_attr and st.session_state.get("mc_results") is not None:
        with st.spinner("Running factor ablation simulations (4 x 5,000 scenarios)..."):
            try:
                from src.analytics.hedge_optimizer import compute_factor_attribution
                risk_profile = st.session_state.get("mc_risk_profile")
                if risk_profile is None:
                    st.warning("Run the main simulation first.")
                else:
                    with get_connection() as conn:
                        attr = compute_factor_attribution(conn, risk_profile, financials, n_iterations=5000)
                    st.session_state["mc_attr"] = attr
            except Exception as e:
                import traceback
                logger.error(f"Attribution error:\n{traceback.format_exc()}")
                st.error(f"Could not compute attribution: {e}")

    if st.session_state.get("mc_results") is None:
        return

    try:
        results = st.session_state["mc_results"]

        # -----------------------------------------------------------------------
        # CFaR Headline Cards
        # -----------------------------------------------------------------------
        st.markdown("#### Tail-Risk Summary")
        base_fcf = results["base_fcf"]
        cfar_95 = results["risk_metrics"]["FCF"]["var_95"]
        cfar_delta = cfar_95 - base_fcf
        evar_95 = results["risk_metrics"]["EV"]["var_95"]
        lar_95 = results["risk_metrics"]["Liquidity"]["var_95"]

        h1, h2, h3, h4 = st.columns(4)
        h1.metric(
            "Base FCF",
            f"JPY {base_fcf/1e9:,.1f}B",
        )
        h2.metric(
            "95% CFaR (Cash-Flow-at-Risk)",
            f"JPY {cfar_95/1e9:,.1f}B",
            delta=f"JPY {cfar_delta/1e9:,.1f}B vs base",
            delta_color="inverse",
            help="5th percentile of simulated FCF across 10,000 scenarios.",
        )
        h3.metric(
            "95% EVaR (Enterprise Value-at-Risk)",
            f"JPY {evar_95/1e9:,.1f}B",
        )
        h4.metric(
            "95% LaR (Liquidity-at-Risk)",
            f"JPY {lar_95/1e9:,.1f}B",
        )

        prob_shortfall = results.get("liquidity_shortfall_prob", 0)
        if prob_shortfall > 0:
            st.error(f"Liquidity Shortfall Warning: {prob_shortfall:.1f}% of 10,000 scenarios end with negative cash.")
        else:
            st.success("Liquidity Solvency: 100% of 10,000 scenarios maintain positive cash.")

        from src.dashboard.components import render_insight
        insight_msg = f"Monte Carlo Insight: We ran 10,000 market shock scenarios. In the worst 5% of cases (95% confidence level), Free Cash Flow drops to <strong>JPY {cfar_95/1e9:,.1f} Billion</strong> (a decline of JPY {abs(cfar_delta)/1e9:,.1f}B). Enterprise Value at Risk is calculated at <strong>JPY {evar_95/1e9:,.1f} Billion</strong>."
        render_insight(insight_msg)

        st.markdown("---")

        # -----------------------------------------------------------------------
        # Executive Risk Table
        # -----------------------------------------------------------------------
        st.markdown("#### Full Risk Metric Table")
        risk_data = []
        for metric_name, key_prefix in [
            ("Enterprise Value (EVaR)", "EV"),
            ("Free Cash Flow (CFaR)", "FCF"),
            ("Ending Liquidity (LaR)", "Liquidity"),
        ]:
            base_val = results["base_ev"] if key_prefix == "EV" else (results["base_fcf"] if key_prefix == "FCF" else results["base_cash"])
            m = results["risk_metrics"][key_prefix]
            risk_data.append({
                "Risk Dimension": metric_name,
                "Base Case (JPY B)": f"{base_val/1e9:,.1f}",
                "95% VaR (JPY B)": f"{m['var_95']/1e9:,.1f}",
                "Delta vs Base (JPY B)": f"{(m['var_95']-base_val)/1e9:,.1f}",
                "99% VaR (JPY B)": f"{m['var_99']/1e9:,.1f}",
                "95% CVaR / ES (JPY B)": f"{m['cvar_95']/1e9:,.1f}",
            })
        st.dataframe(pd.DataFrame(risk_data), use_container_width=True, hide_index=True)

        st.markdown("---")

        # -----------------------------------------------------------------------
        # Factor Attribution Bar
        # -----------------------------------------------------------------------
        attr = st.session_state.get("mc_attr")
        if attr:
            st.markdown("#### Factor Attribution of CFaR")
            st.caption("Marginal contribution of each risk factor to the 95% tail loss (ablation method).")

            attr_factors = ["Commodity", "FX", "Rates"]
            attr_values = [attr.get(f, 0.0) / 1e9 for f in attr_factors]
            attr_colors = ["#ea2261", "#533afd", "#665efd"]

            fig_attr = go.Figure(go.Bar(
                x=attr_factors,
                y=attr_values,
                marker=dict(color=attr_colors, line=dict(color="#ffffff", width=1.5)),
                text=[f"¥{v:,.2f}B" for v in attr_values],
                textposition="outside",
            ))
            fig_attr.update_layout(
                yaxis_title="Marginal CFaR Contribution (JPY B)",
                height=300,
                margin=dict(l=20, r=20, t=30, b=30),
                paper_bgcolor="#ffffff",
                plot_bgcolor="#ffffff",
                showlegend=False,
            )
            st.plotly_chart(fig_attr, use_container_width=True)
            st.markdown("---")

        # -----------------------------------------------------------------------
        # Probability Distribution + Correlation Matrix
        # -----------------------------------------------------------------------
        col_hist, col_corr = st.columns([3, 2])

        with col_hist:
            st.markdown("#### Probability Distribution")
            dist_choice = st.selectbox(
                "Select Metric to Visualize",
                ["Free Cash Flow", "Enterprise Value", "Ending Liquidity"],
                key="dist_choice_selectbox",
            )
            if dist_choice == "Enterprise Value":
                sim_data = results["simulated_ev"]
                base_val = results["base_ev"]
                var95_val = results["risk_metrics"]["EV"]["var_95"]
                color = "#533afd"
            elif dist_choice == "Free Cash Flow":
                sim_data = results["simulated_fcf"]
                base_val = results["base_fcf"]
                var95_val = results["risk_metrics"]["FCF"]["var_95"]
                color = "#059669"
            else:
                sim_data = results["simulated_cash"]
                base_val = results["base_cash"]
                var95_val = results["risk_metrics"]["Liquidity"]["var_95"]
                color = "#665efd"

            fig_hist = go.Figure()
            fig_hist.add_trace(go.Histogram(
                x=sim_data,
                nbinsx=80,
                name=dist_choice,
                marker=dict(color=color, opacity=0.82, line=dict(color="#ffffff", width=0.5)),
            ))
            fig_hist.add_vline(x=base_val, line_width=2.5, line_dash="dash",
                               line_color="#059669", annotation_text="Base", annotation_position="top")
            fig_hist.add_vline(x=var95_val, line_width=2.5, line_dash="dash",
                               line_color="#ea2261", annotation_text="95% VaR", annotation_position="top")
            fig_hist.update_layout(
                xaxis_title=f"{dist_choice} (JPY)",
                yaxis_title="Frequency",
                showlegend=False,
                bargap=0.04,
                height=360,
                margin=dict(l=30, r=20, t=30, b=30),
                paper_bgcolor="#ffffff",
                plot_bgcolor="#ffffff",
            )
            st.plotly_chart(fig_hist, use_container_width=True)

        with col_corr:
            st.markdown("#### Historical Correlation Matrix")
            st.caption("5-year trailing daily log return co-movements.")
            corr = results["correlation_matrix"]
            relevant_cols = [c for c in corr.columns if c in ["COPPER", "ALUMINIUM", "WTI", "BRENT", "USDJPY", "EURJPY", "10Y"]]
            corr_filtered = corr.loc[relevant_cols, relevant_cols] if relevant_cols else corr
            fig_corr = px.imshow(
                corr_filtered.round(2),
                text_auto=True,
                aspect="auto",
                color_continuous_scale=[[0, "#ea2261"], [0.5, "#f6f9fc"], [1, "#533afd"]],
                zmin=-1, zmax=1,
            )
            fig_corr.update_layout(
                height=360,
                margin=dict(l=20, r=20, t=30, b=20),
                paper_bgcolor="#ffffff",
                plot_bgcolor="#ffffff",
            )
            st.plotly_chart(fig_corr, use_container_width=True)

        # -----------------------------------------------------------------------
        # FCF Fan Chart (12-quarter forward projection)
        # -----------------------------------------------------------------------
        st.markdown("---")
        st.markdown("#### FCF Forward Scenario Fan (12-Quarter Projection)")
        st.caption("Percentile bands constructed by scaling 1Y simulated FCF across quarterly steps with Brownian scaling.")

        n_quarters = 12
        q_labels = [f"Q{i+1}" for i in range(n_quarters)]
        sim_fcf = results["simulated_fcf"]
        # Scale annual FCF to quarterly with sqrt-time scaling
        fan_data = {}
        for p in [5, 25, 50, 75, 95]:
            pval = np.percentile(sim_fcf, p)
            scale = np.sqrt(np.arange(1, n_quarters + 1) / 4)
            fan_data[p] = (base_fcf / 4) + (pval - base_fcf) / 4 * scale

        fig_fan = go.Figure()
        # Shaded bands
        fig_fan.add_trace(go.Scatter(
            x=q_labels + q_labels[::-1],
            y=list(fan_data[95] / 1e9) + list(fan_data[5][::-1] / 1e9),
            fill="toself", fillcolor="rgba(83,58,253,0.07)", line=dict(color="rgba(0,0,0,0)"),
            name="P5-P95 Range", hoverinfo="skip",
        ))
        fig_fan.add_trace(go.Scatter(
            x=q_labels + q_labels[::-1],
            y=list(fan_data[75] / 1e9) + list(fan_data[25][::-1] / 1e9),
            fill="toself", fillcolor="rgba(83,58,253,0.14)", line=dict(color="rgba(0,0,0,0)"),
            name="P25-P75 Range", hoverinfo="skip",
        ))
        # Median line
        fig_fan.add_trace(go.Scatter(
            x=q_labels, y=fan_data[50] / 1e9,
            line=dict(color="#533afd", width=2.5),
            name="Median (P50)",
        ))
        # Base line
        base_line = [base_fcf / 4e9] * n_quarters
        fig_fan.add_trace(go.Scatter(
            x=q_labels, y=base_line,
            line=dict(color="#059669", width=1.5, dash="dash"),
            name="Base FCF/Q",
        ))
        fig_fan.update_layout(
            yaxis_title="FCF (JPY B)",
            height=320,
            margin=dict(l=30, r=20, t=30, b=30),
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_fan, use_container_width=True)

    except Exception as render_e:
        import traceback
        logger.error(f"MC render error:\n{traceback.format_exc()}")
        st.error(f"Error rendering charts: {render_e}")

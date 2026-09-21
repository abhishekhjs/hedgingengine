"""Stress Testing UI — Custom market shock scenario builder."""
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go

from src.db.connection import get_connection
from src.analytics.exposure_calc import (
    get_latest_market_data,
    calculate_company_risk,
    compute_ev_sensitivities,
)
from src.analytics.monte_carlo import run_monte_carlo_simulation
from src.analytics.stress_test import apply_stress_scenario, build_shock_table, compute_shocked_price
from src.dashboard.exposure_ui import load_company_names, load_exposure_data, load_hedge_data
from src.dashboard.transmission_ui import load_financials
from src.dashboard.components import render_insight


def render_stress_test_tab():
    st.subheader("Custom Stress Scenario Builder")
    st.caption("Manually override market prices to simulate tail scenarios and measure impact on CFaR, EVaR, and Net Income.")

    # --- Company selector ---
    companies = load_company_names()
    if not companies:
        st.info("No company profiles found. Add data in the Exposure Mapping tab first.")
        return

    company = st.selectbox("Enterprise Profile", companies, key="stress_company")

    with get_connection() as conn:
        market_data = get_latest_market_data(conn)

    if not market_data:
        st.warning("No market data found. Run the Refresh Feed first.")
        return

    exposure = load_exposure_data(company)
    hedges = load_hedge_data(company)
    financials = load_financials(company)

    if not financials:
        st.warning("No financials configured for this company. Set them in the Financial Transmission tab.")
        return

    st.markdown("---")
    st.markdown("#### Shock Input Grid")
    st.caption("Set Shock Type to **pct** (percentage change) or **absolute** (target price). Shocked Price updates automatically.")

    shock_df = build_shock_table(market_data)

    edited = st.data_editor(
        shock_df,
        column_config={
            "Asset": st.column_config.TextColumn("Asset", disabled=True),
            "Current Price": st.column_config.NumberColumn("Current Price", disabled=True, format="%.4f"),
            "Shock Type": st.column_config.SelectboxColumn("Shock Type", options=["pct", "absolute"]),
            "Shock Value (%)": st.column_config.NumberColumn("Shock Value / Target", format="%.2f"),
            "Shocked Price": st.column_config.NumberColumn("Shocked Price", disabled=True, format="%.4f"),
        },
        use_container_width=True,
        hide_index=True,
        key="stress_editor",
    )

    # Recompute Shocked Price column live
    edited["Shocked Price"] = edited.apply(compute_shocked_price, axis=1)

    if st.button("Run Stress Scenario", type="primary", use_container_width=True):
        shocks = []
        for _, row in edited.iterrows():
            if row["Shock Value (%)"] != 0.0:
                shocks.append({
                    "asset": row["Asset"],
                    "shock_type": row["Shock Type"],
                    "shock_value": row["Shock Value (%)"],
                })

        if not shocks:
            st.info("No shocks defined. Change at least one Shock Value to run the scenario.")
            return

        with st.spinner("Computing Base Case & Stressed outputs..."):
            # Base case
            base_risk = calculate_company_risk(exposure, hedges, market_data)
            with get_connection() as conn:
                base_mc = run_monte_carlo_simulation(conn, base_risk, financials, n_iterations=5000)
            base_cfar = base_mc["risk_metrics"]["FCF"]["var_95"]
            base_evar = base_mc["risk_metrics"]["EV"]["var_95"]
            base_fcf = base_mc["base_fcf"]

            # Stressed
            shocked_market = apply_stress_scenario(market_data, shocks)
            stressed_risk = calculate_company_risk(exposure, hedges, shocked_market)
            with get_connection() as conn:
                stressed_mc = run_monte_carlo_simulation(conn, stressed_risk, financials, n_iterations=5000)
            stressed_cfar = stressed_mc["risk_metrics"]["FCF"]["var_95"]
            stressed_evar = stressed_mc["risk_metrics"]["EV"]["var_95"]
            stressed_fcf = stressed_mc["base_fcf"]

        # --- Results ---
        st.markdown("---")
        st.markdown("#### Scenario Results: Base vs. Stressed")

        cfar_delta = stressed_cfar - base_cfar
        evar_delta = stressed_evar - base_evar
        fcf_delta = stressed_fcf - base_fcf

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Base CFaR (95%)", f"¥{base_cfar/1e9:.1f}B")
        c2.metric("Stressed CFaR (95%)", f"¥{stressed_cfar/1e9:.1f}B",
                  delta=f"{cfar_delta/1e9:+.1f}B", delta_color="inverse")
        c3.metric("Base EVaR (95%)", f"¥{base_evar/1e9:.1f}B")
        c4.metric("Stressed EVaR (95%)", f"¥{stressed_evar/1e9:.1f}B",
                  delta=f"{evar_delta/1e9:+.1f}B", delta_color="inverse")
        c5.metric("Base FCF", f"¥{base_fcf/1e9:.1f}B")
        c6.metric("Stressed FCF", f"¥{stressed_fcf/1e9:.1f}B",
                  delta=f"{fcf_delta/1e9:+.1f}B", delta_color="inverse")

        # Insight
        pct_cfar_change = ((stressed_cfar - base_cfar) / abs(base_cfar)) * 100 if base_cfar != 0 else 0
        direction = "worsened" if stressed_cfar < base_cfar else "improved"
        render_insight(
            f"Under this stress scenario, the 95% Cash Flow at Risk <strong>{direction} by "
            f"{abs(pct_cfar_change):.1f}%</strong> (from ¥{base_cfar/1e9:.1f}B to "
            f"¥{stressed_cfar/1e9:.1f}B). Enterprise Value at Risk shifted by "
            f"<strong>¥{evar_delta/1e9:+.1f}B</strong>."
        )

        # Distribution overlay chart
        st.markdown("#### CFaR Distribution: Base vs. Stressed")
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=base_mc["simulated_fcf"], nbinsx=60,
            name="Base Case", marker_color="rgba(30, 64, 175, 0.65)", opacity=0.75
        ))
        fig.add_trace(go.Histogram(
            x=stressed_mc["simulated_fcf"], nbinsx=60,
            name="Stressed", marker_color="rgba(246, 70, 93, 0.6)", opacity=0.75
        ))
        fig.add_vline(x=base_cfar, line_dash="dash", line_color="#1e40af",
                      annotation_text=f"Base CFaR ¥{base_cfar/1e9:.1f}B", annotation_font_color="#1e40af")
        fig.add_vline(x=stressed_cfar, line_dash="dash", line_color="#f6465d",
                      annotation_text=f"Stressed CFaR ¥{stressed_cfar/1e9:.1f}B", annotation_font_color="#f6465d")
        fig.update_layout(
            barmode="overlay",
            height=380,
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
            font=dict(color="#181a20", family="Inter, sans-serif"),
            xaxis=dict(showgrid=True, gridcolor="#eaecef", tickfont=dict(color="#707a8a")),
            yaxis=dict(showgrid=True, gridcolor="#eaecef", tickfont=dict(color="#707a8a")),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="#181a20")),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Applied shocks summary
        st.markdown("#### Applied Shocks")
        shocked_rows = edited[edited["Shock Value (%)"] != 0].copy()
        st.dataframe(shocked_rows[["Asset", "Current Price", "Shock Type", "Shock Value (%)", "Shocked Price"]],
                     use_container_width=True, hide_index=True)

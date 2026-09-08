"""UI components for Phase 3: Financial Transmission Modeling."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import logging

from src.db.connection import get_connection
from src.dashboard.exposure_ui import load_company_names

logger = logging.getLogger(__name__)

SIGMA_SCENARIOS = {
    "Base (0-sigma)": 0.0,
    "Moderate (1-sigma)": 1.0,
    "Severe (2-sigma)": 2.0,
    "Extreme (3-sigma)": 3.0,
}


def load_financials(company_name: str) -> dict:
    """Load baseline financials for a company."""
    with get_connection() as conn:
        df = pd.read_sql(
            "SELECT * FROM company_financials WHERE company_name = ?",
            conn,
            params=(company_name,),
        )
    if df.empty:
        return {}
    return df.iloc[0].to_dict()


def save_financials(company_name: str, financials: dict):
    """Save baseline financials to DB."""
    df = pd.DataFrame([financials])
    df["company_name"] = company_name
    with get_connection() as conn:
        conn.execute("DELETE FROM company_financials WHERE company_name = ?", (company_name,))
        df.to_sql("company_financials", conn, if_exists="append", index=False)


def render_transmission_tab():
    """Render the Phase 3 Financial Transmission UI."""
    st.subheader("Financial Transmission Modeling")
    st.caption(
        "Cascade market factor shocks into Income Statement, Balance Sheet, and Enterprise Value "
        "across four stress scenarios."
    )

    # 1. Company Selection
    existing_companies = load_company_names()
    company_name = st.selectbox(
        "Select Enterprise Profile",
        options=existing_companies,
        key="transmission_company_select",
    )
    if not company_name:
        st.info("Please select a company to continue.")
        return

    st.markdown("---")

    # 2. Baseline Financials Form
    current_financials = load_financials(company_name)

    with st.expander(
        f"Baseline Financial & Covenant Parameters ({company_name})",
        expanded=not current_financials,
    ):
        with st.form("financials_form"):
            st.markdown("##### Income Statement Inputs")
            col1, col2, col3 = st.columns(3)
            with col1:
                rev = st.number_input("Base Revenue (JPY)", value=float(current_financials.get("base_revenue", 0.0)), step=1e9, format="%.0f")
                cogs = st.number_input("Base COGS (JPY)", value=float(current_financials.get("base_cogs", 0.0)), step=1e9, format="%.0f")
                opex = st.number_input("Base OpEx (JPY)", value=float(current_financials.get("base_opex", 0.0)), step=1e9, format="%.0f")
            with col2:
                cash = st.number_input("Starting Cash (JPY)", value=float(current_financials.get("starting_cash", 0.0)), step=1e9, format="%.0f")
                debt = st.number_input("Starting Debt (JPY)", value=float(current_financials.get("starting_debt", 0.0)), step=1e9, format="%.0f")
            with col3:
                tax = st.number_input("Corporate Tax Rate (%)", value=float(current_financials.get("tax_rate", 0.30) * 100)) / 100
                mult = st.number_input("EV / EBITDA Multiple (x)", value=float(current_financials.get("ev_ebitda_multiple", 8.0)), step=0.5)

            st.markdown("##### Covenant Constraint Inputs")
            cov1, cov2 = st.columns(2)
            with cov1:
                min_cash = st.number_input(
                    "Minimum Cash Buffer (JPY)",
                    value=float(current_financials.get("min_cash_buffer", 0.0)),
                    step=1e9,
                    format="%.0f",
                    help="Breach if ending cash falls below this level. Used for Proximity_i computation.",
                )
            with cov2:
                max_debt_ebitda = st.number_input(
                    "Max Debt/EBITDA Covenant (x)",
                    value=float(current_financials.get("max_debt_ebitda_ratio", 0.0)),
                    step=0.25,
                    help="Breach if Debt/EBITDA exceeds this ratio. Used for Proximity_i computation.",
                )

            if st.form_submit_button("Save Financial Parameters", type="primary"):
                new_fin = {
                    "base_revenue": rev, "base_cogs": cogs, "base_opex": opex,
                    "tax_rate": tax, "starting_cash": cash, "starting_debt": debt,
                    "ev_ebitda_multiple": mult,
                    "min_cash_buffer": min_cash,
                    "max_debt_ebitda_ratio": max_debt_ebitda,
                }
                save_financials(company_name, new_fin)
                current_financials = new_fin
                st.success("Financial parameters saved.")
                st.rerun()

    if not current_financials:
        st.warning("Please configure and save baseline financials above to activate transmission modeling.")
        return

    st.info("Transmission Assumption: FCF assumes CapEx offsets D&A with net-zero working capital change.")

    # 3. Load risk profile
    from src.dashboard.exposure_ui import load_exposure_data, load_hedge_data
    from src.analytics.exposure_calc import (
        get_latest_market_data,
        calculate_company_risk,
        calculate_financial_transmission,
        compute_ev_sensitivities,
        compute_proximity_scores,
    )

    try:
        with get_connection() as conn:
            market_data = get_latest_market_data(conn)

        exposure = load_exposure_data(company_name)
        hedges = load_hedge_data(company_name)
        risk_profile = calculate_company_risk(exposure, hedges, market_data)

        # -----------------------------------------------------------------------
        # 4. Multi-Scenario Stress Panel
        # -----------------------------------------------------------------------
        st.markdown("#### Multi-Scenario Stress Analysis")
        st.caption("Simultaneous adverse shift across all factor markets at each severity level.")

        scenario_tabs = st.tabs(list(SIGMA_SCENARIOS.keys()))

        for tab, (scenario_name, sigma) in zip(scenario_tabs, SIGMA_SCENARIOS.items()):
            with tab:
                t = calculate_financial_transmission(risk_profile, current_financials, sigma_multiplier=sigma)

                col_is, col_bs = st.columns(2)
                with col_is:
                    st.markdown("##### Pro-Forma Income Statement")
                    is_rows = []
                    for item, vals in t["Income Statement"].items():
                        delta = vals["Shocked"] - vals["Base"]
                        is_rows.append({
                            "Line Item": item,
                            "Base Case (JPY B)": f"{vals['Base']/1e9:,.1f}",
                            "Shocked (JPY B)": f"{vals['Shocked']/1e9:,.1f}",
                            "Delta (JPY B)": f"{'+' if delta >= 0 else ''}{delta/1e9:,.1f}",
                        })
                    st.dataframe(pd.DataFrame(is_rows), use_container_width=True, hide_index=True)

                with col_bs:
                    st.markdown("##### Balance Sheet & Valuation")
                    bs_rows = []
                    for item, vals in t["Balance Sheet & Value"].items():
                        delta = vals["Shocked"] - vals["Base"]
                        bs_rows.append({
                            "Metric": item,
                            "Base Case (JPY B)": f"{vals['Base']/1e9:,.1f}",
                            "Shocked (JPY B)": f"{vals['Shocked']/1e9:,.1f}",
                            "Delta (JPY B)": f"{'+' if delta >= 0 else ''}{delta/1e9:,.1f}",
                        })
                    st.dataframe(pd.DataFrame(bs_rows), use_container_width=True, hide_index=True)

                # Covenant check
                if sigma > 0:
                    ebitda_shocked = t["Income Statement"]["EBITDA"]["Shocked"]
                    debt_shocked = t["Balance Sheet & Value"]["Ending Debt"]["Shocked"]
                    cash_shocked = t["Balance Sheet & Value"]["Ending Cash"]["Shocked"]
                    max_debt_ebitda = float(current_financials.get("max_debt_ebitda_ratio", 0.0))
                    min_cash = float(current_financials.get("min_cash_buffer", 0.0))

                    covenants_ok = True
                    if max_debt_ebitda > 0 and ebitda_shocked > 0:
                        actual_ratio = debt_shocked / ebitda_shocked
                        if actual_ratio > max_debt_ebitda:
                            st.error(f"COVENANT BREACH: Debt/EBITDA = {actual_ratio:.2f}x exceeds covenant of {max_debt_ebitda:.1f}x under {scenario_name}.")
                            covenants_ok = False
                    if min_cash > 0 and cash_shocked < min_cash:
                        st.error(f"COVENANT BREACH: Ending cash JPY {cash_shocked/1e9:.1f}B falls below minimum buffer JPY {min_cash/1e9:.1f}B under {scenario_name}.")
                        covenants_ok = False
                    if covenants_ok:
                        st.success(f"All covenant constraints satisfied under {scenario_name}.")

        # -----------------------------------------------------------------------
        # 5. EV Tornado Chart (dEV/dFactor)
        # -----------------------------------------------------------------------
        st.divider()
        st.markdown("#### Enterprise Value Sensitivity — Tornado Chart")
        st.caption(
            "1-sigma adverse move in each factor independently. "
            "Wider bar = greater EV destruction per unit of shock."
        )

        sensitivities = compute_ev_sensitivities(risk_profile, current_financials)
        if sensitivities:
            sorted_sens = sorted(sensitivities.items(), key=lambda x: abs(x[1]["dEV_per_sigma"]))
            factors = [s[0] for s in sorted_sens]
            impacts = [s[1]["dEV_per_sigma"] / 1e9 for s in sorted_sens]
            categories = [s[1]["category"] for s in sorted_sens]
            cat_color = {"Commodity": "#EE5D50", "FX": "#4318FF", "Rates": "#FFB547"}
            colors = [cat_color.get(c, "#A3AED0") for c in categories]

            fig_tornado = go.Figure(go.Bar(
                x=impacts,
                y=factors,
                orientation="h",
                marker=dict(color=colors, line=dict(color="#FFFFFF", width=1)),
                text=[f"JPY {v:,.1f}B" for v in impacts],
                textposition="outside",
                hovertemplate="%{y}: JPY %{x:,.1f}B EV impact<extra></extra>",
            ))
            fig_tornado.update_layout(
                height=max(280, len(factors) * 42),
                margin=dict(l=20, r=80, t=20, b=30),
                paper_bgcolor="#FFFFFF",
                plot_bgcolor="#FFFFFF",
                xaxis_title="EV Impact per 1-sigma shock (JPY B)",
                xaxis=dict(zeroline=True, zerolinecolor="#E5E7EB", zerolinewidth=2),
            )
            # Legend annotation
            for i, (cat, color) in enumerate(cat_color.items()):
                fig_tornado.add_annotation(
                    x=1.0, y=1.0 - i * 0.12,
                    xref="paper", yref="paper",
                    text=f"<span style='color:{color}'>■</span> {cat}",
                    showarrow=False, font=dict(size=11), xanchor="right",
                )
            st.plotly_chart(fig_tornado, use_container_width=True)

        # -----------------------------------------------------------------------
        # 6. Proximity-to-Constraint Panel
        # -----------------------------------------------------------------------
        st.divider()
        st.markdown("#### Proximity to Covenant Constraints")
        st.caption(
            "Proximity_i = 1 / headroom_pct. Higher score = closer to breach under base-case conditions. "
            "Feeds directly into Phase 5 HedgePriority formula."
        )

        proximity_scores = compute_proximity_scores(current_financials)
        if not proximity_scores:
            st.info("No covenant constraints configured. Enter Minimum Cash Buffer or Max Debt/EBITDA above.")
        else:
            for constraint, pdata in proximity_scores.items():
                breached = pdata["breached"]
                color = "#EE5D50" if breached else ("#FFB547" if pdata["proximity"] > 3 else "#01B574")
                status = "BREACHED" if breached else f"Proximity {pdata['proximity']:.2f}"
                headroom = f"{pdata['headroom_pct']:.1f}% headroom"

                st.markdown(
                    f"""
                    <div style="border:1px solid #E5E7EB;border-radius:10px;padding:14px 18px;margin-bottom:10px;">
                      <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                          <div style="font-weight:700;font-size:14px;color:#111827;">{constraint}</div>
                          <div style="font-size:12px;color:#6B7280;margin-top:2px;">{pdata['label']}</div>
                        </div>
                        <div style="text-align:right;">
                          <div style="font-size:18px;font-weight:800;color:{color};">{status}</div>
                          <div style="font-size:11px;color:#9CA3AF;">{headroom}</div>
                        </div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # -----------------------------------------------------------------------
        # 7. EV Waterfall (1-sigma default)
        # -----------------------------------------------------------------------
        st.divider()
        st.markdown("#### EV Transmission Bridge (1-sigma Stress)")

        transmission_1s = calculate_financial_transmission(risk_profile, current_financials, sigma_multiplier=1.0)
        drivers = transmission_1s["Shock Drivers"]
        ev_base = transmission_1s["Balance Sheet & Value"]["Enterprise Value"]["Base"]
        ev_shock = transmission_1s["Balance Sheet & Value"]["Enterprise Value"]["Shocked"]

        fig = go.Figure(go.Waterfall(
            name="EV Transmission",
            orientation="v",
            measure=["absolute", "relative", "relative", "relative", "total"],
            x=["Base EV", "FX Effect", "Commodity Effect", "Rate Effect", "Shocked EV"],
            textposition="outside",
            text=[
                f"JPY {ev_base/1e9:,.1f}B",
                f"JPY {drivers.get('FX Impact (Δ Rev)', 0)/1e9:,.1f}B",
                f"JPY {drivers.get('Commodity Impact (Δ COGS)', 0)/1e9:,.1f}B",
                f"JPY {drivers.get('Rate Impact (Δ Int)', 0)/1e9:,.1f}B",
                f"JPY {ev_shock/1e9:,.1f}B",
            ],
            y=[
                ev_base,
                drivers.get("FX Impact (Δ Rev)", 0),
                drivers.get("Commodity Impact (Δ COGS)", 0),
                drivers.get("Rate Impact (Δ Int)", 0),
                ev_shock,
            ],
            increasing={"marker": {"color": "#01B574"}},
            decreasing={"marker": {"color": "#EE5D50"}},
            totals={"marker": {"color": "#4318FF"}},
            connector={"line": {"color": "#E9EDF7", "width": 2}},
        ))
        fig.update_layout(
            height=360,
            margin=dict(l=30, r=20, t=40, b=30),
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#FFFFFF",
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        import traceback
        logger.error(f"Error computing transmission:\n{traceback.format_exc()}")
        st.error(f"Could not compute transmission: {e}")

"""UI components for Phase 2: Company Exposure Mapping."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import logging

from src.db.connection import get_connection

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Toyota Motor case-study seed data
# ---------------------------------------------------------------------------
TOYOTA_EXPOSURES = [
    {"commodity": "COPPER",    "annual_quantity": 500000,   "currency": "USD", "annual_imports": 8000000000,  "debt_amount": 15000000000000, "floating_rate_percentage": 0.40},
    {"commodity": "ALUMINIUM", "annual_quantity": 800000,   "currency": "EUR", "annual_imports": 4000000000,  "debt_amount": 0,              "floating_rate_percentage": 0.0},
    {"commodity": "WTI",       "annual_quantity": 20000000, "currency": "",    "annual_imports": 0,            "debt_amount": 0,              "floating_rate_percentage": 0.0},
]
TOYOTA_HEDGES = [
    {"instrument": "Forward",    "underlying": "COPPER",    "notional": 300000,      "strike": 9200,  "maturity": "2026-03-31", "hedge_ratio": 0.60, "cost": 2500000000},
    {"instrument": "Forward",    "underlying": "USDJPY",    "notional": 4800000000,  "strike": 148.0, "maturity": "2026-03-31", "hedge_ratio": 0.60, "cost": 1800000000},
    {"instrument": "Swap",       "underlying": "Rates",     "notional": 6000000000000,"strike": 0.0,  "maturity": "2028-03-31", "hedge_ratio": 0.40, "cost": 800000000},
]
TOYOTA_FINANCIALS = {
    "base_revenue":       43000000000000,
    "base_cogs":          35000000000000,
    "base_opex":           3000000000000,
    "tax_rate":                     0.28,
    "starting_cash":       5000000000000,
    "starting_debt":      15000000000000,
    "ev_ebitda_multiple":          8.0,
    "min_cash_buffer":     2000000000000,
    "max_debt_ebitda_ratio":        3.5,
}


def load_company_names() -> list[str]:
    """Get a list of all unique companies currently in the database."""
    with get_connection() as conn:
        df1 = pd.read_sql("SELECT DISTINCT company_name FROM company_exposure", conn)
        df2 = pd.read_sql("SELECT DISTINCT company_name FROM hedges", conn)
    companies = set(df1["company_name"].tolist() + df2["company_name"].tolist())
    if not companies:
        companies.add("Toyota Motor (Case Study)")
    return sorted(list(companies))


def load_exposure_data(company_name: str) -> pd.DataFrame:
    """Load the exposure mapping for a specific company."""
    with get_connection() as conn:
        df = pd.read_sql(
            "SELECT * FROM company_exposure WHERE company_name = ?",
            conn,
            params=(company_name,),
        )
    if df.empty:
        return pd.DataFrame(columns=[
            "commodity", "annual_quantity", "currency", "annual_imports",
            "debt_amount", "floating_rate_percentage",
        ])
    return df.drop(columns=["id", "company_name"], errors="ignore")


def load_hedge_data(company_name: str) -> pd.DataFrame:
    """Load the hedges for a specific company."""
    with get_connection() as conn:
        df = pd.read_sql(
            "SELECT * FROM hedges WHERE company_name = ?",
            conn,
            params=(company_name,),
        )
    if df.empty:
        return pd.DataFrame(columns=[
            "instrument", "underlying", "notional", "strike",
            "maturity", "hedge_ratio", "cost",
        ])
    return df.drop(columns=["id", "company_name"], errors="ignore")


def save_company_data(company_name: str, exposure_df: pd.DataFrame, hedge_df: pd.DataFrame):
    """Save both exposure and hedge data for a company, replacing old data."""
    exposure_df = exposure_df.copy()
    hedge_df = hedge_df.copy()
    if not exposure_df.empty:
        exposure_df["company_name"] = company_name
    if not hedge_df.empty:
        hedge_df["company_name"] = company_name
    with get_connection() as conn:
        conn.execute("DELETE FROM company_exposure WHERE company_name = ?", (company_name,))
        conn.execute("DELETE FROM hedges WHERE company_name = ?", (company_name,))
        if not exposure_df.empty:
            exposure_df.to_sql("company_exposure", conn, if_exists="append", index=False)
        if not hedge_df.empty:
            hedge_df.to_sql("hedges", conn, if_exists="append", index=False)


def seed_toyota():
    """Insert Toyota case-study data into the database."""
    from src.dashboard.transmission_ui import save_financials
    import pandas as pd

    exp_df = pd.DataFrame(TOYOTA_EXPOSURES)
    hdg_df = pd.DataFrame(TOYOTA_HEDGES)
    save_company_data("Toyota Motor (Case Study)", exp_df, hdg_df)
    save_financials("Toyota Motor (Case Study)", TOYOTA_FINANCIALS)


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def _rag_color(coverage: float) -> str:
    if coverage >= 0.60:
        return "#01B574"
    elif coverage >= 0.30:
        return "#FFB547"
    return "#EE5D50"


def render_exposure_mapping_tab():
    """Render the Phase 2 UI for mapping company exposures and hedges."""
    st.subheader("Company Exposure Mapping")
    st.caption("Define gross commodity, currency, and rate exposures, along with active hedge overlays.")

    # --- Company Selection ---
    col1, col_seed = st.columns([3, 1])
    with col1:
        existing_companies = load_company_names()
        selected_company = st.selectbox(
            "Select Enterprise Profile",
            options=existing_companies + ["+ Add New Company..."],
        )
        if selected_company == "+ Add New Company...":
            company_name = st.text_input("Enter new company name:", value="").strip()
        else:
            company_name = selected_company

    with col_seed:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("Load Toyota Case Study", use_container_width=True):
            try:
                seed_toyota()
                st.success("Toyota Motor (Case Study) loaded.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to seed data: {e}")

    if not company_name:
        st.info("Please select or enter a company name to continue.")
        return

    st.markdown("---")

    # Load current data
    current_exposure = load_exposure_data(company_name)
    current_hedges = load_hedge_data(company_name)

    # --- Editable DataFrames ---
    col_exp, col_hdg = st.columns(2)
    with col_exp:
        st.markdown("#### Gross Operating Exposures")
        st.caption("Raw materials, FX trade volumes, and debt amounts.")
        edited_exposure = st.data_editor(
            current_exposure,
            num_rows="dynamic",
            use_container_width=True,
            key=f"exposure_editor_{company_name}",
        )
    with col_hdg:
        st.markdown("#### Mapped Financial Hedges")
        st.caption("Forwards, swaps, and options offsetting operating risk.")
        edited_hedges = st.data_editor(
            current_hedges,
            num_rows="dynamic",
            use_container_width=True,
            key=f"hedge_editor_{company_name}",
        )

    if st.button("Save Exposure Mapping", type="primary"):
        try:
            save_company_data(company_name, edited_exposure, edited_hedges)
            st.success(f"Exposure and hedge profile updated for {company_name}.")
            current_exposure = edited_exposure
            current_hedges = edited_hedges
        except Exception as e:
            logger.error(f"Error saving company mapping: {e}")
            st.error(f"Failed to save data: {e}")

    st.divider()

    # -----------------------------------------------------------------------
    # Analytics & Scenario Stress Test
    # -----------------------------------------------------------------------
    st.subheader(f"Risk Analytics Overview: {company_name}")
    st.caption("Localized JPY translation, hedge coverage, and 1-sigma adverse market stress assessment.")

    try:
        from src.analytics.exposure_calc import (
            get_latest_market_data,
            calculate_company_risk,
            compute_hedge_coverage_ratios,
        )

        with get_connection() as conn:
            market_data = get_latest_market_data(conn)

        if not market_data:
            st.warning("No market data found. Run the ingestion pipeline first.")
            return

        risk_profile = calculate_company_risk(current_exposure, current_hedges, market_data)
        coverage_ratios = compute_hedge_coverage_ratios(risk_profile)

        gross_total = 0
        net_total = 0
        shock_total = 0
        cat_totals = {"Commodity": 0.0, "FX": 0.0, "Rate": 0.0}

        rows = []
        for cat, items in risk_profile.items():
            cat_label = {"commodity": "Commodity", "fx": "FX", "rates": "Rate"}[cat]
            for asset, metrics in items.items():
                if metrics["gross_exposure_jpy"] > 0:
                    gross_total += metrics["gross_exposure_jpy"]
                    net_total += metrics["net_exposure_jpy"]
                    shock_total += metrics["impact_1sigma_jpy"]
                    cat_totals[cat_label] += metrics["gross_exposure_jpy"]
                    rows.append({
                        "Category": cat_label,
                        "Exposure": asset,
                        "Gross (JPY)": f"JPY {metrics['gross_exposure_jpy']:,.0f}",
                        "Hedged (JPY)": f"JPY {metrics['hedged_jpy']:,.0f}",
                        "Net (JPY)": f"JPY {metrics['net_exposure_jpy']:,.0f}",
                        "1s Shock Impact (JPY)": f"JPY {metrics['impact_1sigma_jpy']:,.0f}",
                    })

        # Summary metrics row
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Gross Risk", f"JPY {gross_total / 1e9:,.1f} B")
        c2.metric("Total Net Unhedged", f"JPY {net_total / 1e9:,.1f} B",
                  delta=f"-JPY {(gross_total - net_total)/1e9:,.1f} B hedged",
                  delta_color="normal")
        c3.metric("1-Sigma Shock Impact", f"JPY {shock_total / 1e9:,.2f} B", delta_color="inverse")

        st.markdown("---")

        col_donut, col_cov = st.columns([1, 2])

        # --- Exposure Donut ---
        with col_donut:
            st.markdown("#### Gross Risk by Category")
            donut_labels = [k for k, v in cat_totals.items() if v > 0]
            donut_values = [v for v in cat_totals.values() if v > 0]
            if donut_labels:
                fig_donut = go.Figure(go.Pie(
                    labels=donut_labels,
                    values=donut_values,
                    hole=0.55,
                    marker=dict(colors=["#4318FF", "#01B574", "#FFB547"],
                                line=dict(color="#FFFFFF", width=2)),
                    textinfo="label+percent",
                    hovertemplate="%{label}<br>JPY %{value:,.0f}<extra></extra>",
                ))
                fig_donut.update_layout(
                    height=260,
                    margin=dict(l=10, r=10, t=20, b=10),
                    paper_bgcolor="#FFFFFF",
                    showlegend=False,
                )
                st.plotly_chart(fig_donut, use_container_width=True)

        # --- Hedge Coverage Bars ---
        with col_cov:
            st.markdown("#### Hedge Coverage by Factor")
            st.caption("Red < 30%  |  Amber 30–60%  |  Green > 60%")
            for factor, cov_data in coverage_ratios.items():
                cov = cov_data["coverage"]
                gross = cov_data["gross_jpy"]
                if gross <= 0:
                    continue
                color = _rag_color(cov)
                pct = cov * 100
                st.markdown(
                    f"""
                    <div style="margin-bottom:10px;">
                      <div style="display:flex;justify-content:space-between;font-size:12px;color:#374151;margin-bottom:3px;">
                        <span style="font-weight:600;">{factor}</span>
                        <span style="color:{color};font-weight:700;">{pct:.0f}%</span>
                      </div>
                      <div style="background:#F3F5F9;border-radius:6px;height:10px;overflow:hidden;">
                        <div style="background:{color};width:{min(pct,100):.0f}%;height:100%;border-radius:6px;transition:width 0.4s;"></div>
                      </div>
                      <div style="font-size:11px;color:#9CA3AF;margin-top:2px;">
                        JPY {cov_data["hedged_jpy"]/1e9:.1f}B hedged of JPY {gross/1e9:.1f}B gross
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # --- Exposure Waterfall ---
        if rows:
            st.markdown("#### Exposure Bridge: Gross to Net")
            hedged_delta = gross_total - net_total
            fig = go.Figure(go.Waterfall(
                name="Risk Bridge",
                orientation="v",
                measure=["relative", "relative", "total"],
                x=["Gross Risk", "Hedges Applied", "Net Unhedged Risk"],
                textposition="outside",
                text=[
                    f"JPY {gross_total/1e9:,.1f}B",
                    f"-JPY {hedged_delta/1e9:,.1f}B",
                    f"JPY {net_total/1e9:,.1f}B",
                ],
                y=[gross_total, -hedged_delta, net_total],
                increasing={"marker": {"color": "#EE5D50"}},
                decreasing={"marker": {"color": "#01B574"}},
                totals={"marker": {"color": "#4318FF"}},
                connector={"line": {"color": "#E9EDF7", "width": 2}},
            ))
            fig.update_layout(
                height=340,
                margin=dict(l=30, r=20, t=40, b=30),
                paper_bgcolor="#FFFFFF",
                plot_bgcolor="#FFFFFF",
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("#### Factor-Level Breakdown")
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    except Exception as e:
        logger.error(f"Error computing analytics: {e}")
        st.error(f"Could not compute analytics: {e}")

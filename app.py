"""Japan Manufacturing Market Risk Monitor — Streamlit Dashboard.

SaaS Dashboard UI Kit inspired by Base design system.
Clean, modern enterprise risk monitoring for FX, Commodities,
JGB Yield Curve, Exposure Mapping, Transmission, and Monte Carlo.
"""
import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path for imports
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.io as pio
import plotly.graph_objects as go
import plotly.express as px

# ---------------------------------------------------------------------------
# 1. Page Config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="IFSA Risk Resilience Engine", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# 2. Mercury Plotly Theme
# ---------------------------------------------------------------------------
mercury_palette = ["#4318FF", "#01B574", "#FFB547", "#EA3A99", "#3965FF", "#7551FF"]

mercury_template = go.layout.Template()
mercury_template.layout.paper_bgcolor = "#FFFFFF"
mercury_template.layout.plot_bgcolor = "#FFFFFF"
mercury_template.layout.font = dict(family="Plus Jakarta Sans, Inter, sans-serif", color="#111827", size=12)
mercury_template.layout.colorway = mercury_palette
mercury_template.layout.xaxis = dict(
    showgrid=True,
    gridcolor="#F3F5F9",
    zeroline=False,
    linecolor="#E5E7EB",
    tickfont=dict(color="#9CA3AF", size=11)
)
mercury_template.layout.yaxis = dict(
    showgrid=True,
    gridcolor="#F3F5F9",
    zeroline=False,
    linecolor="#E5E7EB",
    tickfont=dict(color="#9CA3AF", size=11)
)

pio.templates["mercury"] = mercury_template
pio.templates.default = "mercury"

# ---------------------------------------------------------------------------
# 3. Mercury Custom CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    /* Ambient background gradient matching Mercury dashboard */
    .stApp {
        background: radial-gradient(circle at 95% 95%, rgba(222, 230, 255, 0.55) 0%, rgba(246, 248, 254, 0.8) 45%, #F9FAFC 100%) !important;
        background-attachment: fixed !important;
    }

    /* Main container padding */
    .main .block-container {
        padding-top: 1.25rem !important;
        padding-bottom: 3rem !important;
        padding-left: 2.25rem !important;
        padding-right: 2.25rem !important;
        max-width: 1440px !important;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #ECEFF5 !important;
        box-shadow: 2px 0 16px rgba(0, 0, 0, 0.02) !important;
        width: 250px !important;
    }
    section[data-testid="stSidebar"] .block-container {
        padding-top: 1.25rem !important;
        padding-left: 1.1rem !important;
        padding-right: 1.1rem !important;
    }

    /* Mercury Brand Switcher */
    .mercury-sidebar-brand {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 4px 6px 14px 6px;
        margin-bottom: 12px;
        border-bottom: 1px solid #F1F4F9;
    }
    .mercury-brand-logo {
        width: 34px;
        height: 34px;
        border-radius: 9px;
        background: linear-gradient(135deg, #4318FF 0%, #6366F1 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #FFFFFF;
        box-shadow: 0 4px 10px rgba(67, 24, 255, 0.25);
    }
    .mercury-brand-name {
        font-size: 14.5px;
        font-weight: 700;
        color: #111827;
        letter-spacing: -0.2px;
        line-height: 1.2;
    }
    .mercury-brand-sub {
        font-size: 11px;
        font-weight: 500;
        color: #9CA3AF;
    }
    .mercury-brand-caret {
        color: #9CA3AF;
        font-size: 12px;
        margin-left: auto;
    }

    /* Sidebar Section Divider */
    .mercury-nav-heading {
        font-size: 11px;
        font-weight: 700;
        color: #9CA3AF;
        letter-spacing: 0.6px;
        text-transform: uppercase;
        margin-top: 18px;
        margin-bottom: 8px;
        padding-left: 8px;
    }

    /* Custom Radio Navigation as Mercury Sidebar Menu */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] > div {
        gap: 3px !important;
    }
    section[data-testid="stSidebar"] [data-testid="stRadioOption"] {
        display: flex !important;
        align-items: center !important;
        padding: 8px 12px !important;
        border-radius: 10px !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
        margin-bottom: 2px !important;
        width: 100% !important;
    }
    section[data-testid="stSidebar"] [data-testid="stRadioOption"] div:has(+ div[data-testid="stMarkdownContainer"]) {
        display: none !important;
    }
    section[data-testid="stSidebar"] [data-testid="stRadioOption"] p {
        font-size: 13.5px !important;
        font-weight: 500 !important;
        color: #4B5563 !important;
        margin: 0 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover {
        background-color: #F6F8FC !important;
    }
    section[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover p {
        color: #111827 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] {
        background-color: #EEF2FF !important;
    }
    section[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] p {
        color: #4318FF !important;
        font-weight: 700 !important;
    }

    /* Container Card styling for st.container(border=True) */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        background: #FFFFFF !important;
        border: 1px solid #ECEFF5 !important;
        border-radius: 18px !important;
        padding: 20px 22px 14px 22px !important;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.03) !important;
    }

    /* Top Search Bar & Header */
    .mercury-top-nav {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 22px;
        gap: 16px;
    }
    .mercury-search-box {
        display: flex;
        align-items: center;
        gap: 10px;
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 7px 14px;
        width: 380px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .mercury-search-placeholder {
        color: #9CA3AF;
        font-size: 13px;
        font-weight: 500;
        flex: 1;
    }
    .mercury-search-kbd {
        background: #F3F4F6;
        color: #6B7280;
        border-radius: 6px;
        padding: 2px 6px;
        font-size: 11px;
        font-weight: 600;
        border: 1px solid #E5E7EB;
    }
    .mercury-top-right {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-left: auto;
    }
    .mercury-pill-button {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 9999px;
        padding: 6px 14px;
        font-size: 13px;
        font-weight: 600;
        color: #374151;
        cursor: pointer;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02);
    }
    .mercury-icon-btn {
        width: 34px;
        height: 34px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #6B7280;
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        cursor: pointer;
    }
    .mercury-avatar {
        width: 34px;
        height: 34px;
        border-radius: 50%;
        background: linear-gradient(135deg, #FFB547 0%, #EA3A99 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #FFFFFF;
        font-weight: 700;
        font-size: 13px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }

    /* Action Buttons Row */
    .mercury-actions-bar {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 22px;
        flex-wrap: wrap;
    }
    .mercury-btn-primary {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #4318FF;
        color: #FFFFFF;
        padding: 7px 18px;
        border-radius: 9999px;
        font-size: 13px;
        font-weight: 600;
        box-shadow: 0 4px 12px rgba(67, 24, 255, 0.25);
        border: none;
        cursor: pointer;
        text-decoration: none;
    }
    .mercury-btn-secondary {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #FFFFFF;
        color: #374151;
        padding: 6px 14px;
        border-radius: 9999px;
        font-size: 13px;
        font-weight: 500;
        border: 1px solid #E5E7EB;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
        cursor: pointer;
    }
    .mercury-btn-customize {
        margin-left: auto;
        color: #6B7280;
        font-size: 13px;
        font-weight: 500;
        display: inline-flex;
        align-items: center;
        gap: 4px;
        cursor: pointer;
    }

    /* Mercury Card */
    .mercury-card {
        background: #FFFFFF;
        border: 1px solid #ECEFF5;
        border-radius: 18px;
        padding: 22px 24px;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.03);
        margin-bottom: 20px;
    }

    /* Balance Hero Card Details */
    .mercury-balance-title-row {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-bottom: 6px;
    }
    .mercury-balance-title {
        font-size: 13.5px;
        font-weight: 600;
        color: #4B5563;
    }
    .mercury-balance-amount {
        font-size: 32px;
        font-weight: 800;
        color: #111827;
        letter-spacing: -0.8px;
        line-height: 1.1;
        margin-bottom: 6px;
    }
    .mercury-cents {
        font-size: 18px;
        font-weight: 600;
        color: #6B7280;
        vertical-align: super;
    }
    .mercury-period-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 12.5px;
        font-weight: 500;
        color: #4B5563;
        cursor: pointer;
    }
    .mercury-flow-badges {
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 13px;
        font-weight: 600;
    }
    .mercury-flow-up {
        color: #059669;
    }
    .mercury-flow-down {
        color: #DC2626;
    }

    /* Card Controls (Chart / Table toggle icons) */
    .mercury-card-controls {
        display: flex;
        align-items: center;
        background: #F8FAFC;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 2px;
        gap: 2px;
    }
    .mercury-toggle-icon {
        width: 26px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 6px;
        font-size: 12px;
        color: #6B7280;
        cursor: pointer;
    }
    .mercury-toggle-icon.active {
        background: #FFFFFF;
        color: #111827;
        box-shadow: 0 1px 2px rgba(0,0,0,0.06);
    }

    /* Accounts Card Details */
    .mercury-accounts-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 16px;
    }
    .mercury-accounts-title {
        font-size: 15px;
        font-weight: 700;
        color: #111827;
        margin: 0;
    }
    .mercury-accounts-icons {
        display: flex;
        gap: 8px;
        color: #6B7280;
        font-size: 14px;
        cursor: pointer;
    }
    .mercury-account-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 11px 0;
        border-bottom: 1px solid #F3F4F6;
    }
    .mercury-account-item:last-child {
        border-bottom: none;
    }
    .mercury-acc-label {
        font-size: 13.5px;
        font-weight: 600;
        color: #1F2937;
    }
    .mercury-acc-mask {
        color: #9CA3AF;
        font-weight: 500;
        margin-left: 4px;
    }
    .mercury-acc-balance {
        font-size: 13.5px;
        font-weight: 700;
        color: #111827;
        letter-spacing: -0.2px;
    }

    /* General tables and widgets */
    .stDataFrame {
        border-radius: 14px !important;
        overflow: hidden !important;
        border: 1px solid #ECEFF5 !important;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.02) !important;
        background: #FFFFFF !important;
    }
    div[data-testid="stExpander"] {
        border-radius: 14px !important;
        border: 1px solid #ECEFF5 !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02) !important;
        background: #FFFFFF !important;
        margin-bottom: 10px !important;
    }
    div[data-testid="stExpander"] summary {
        font-weight: 600 !important;
        color: #111827 !important;
    }

    /* Metric Cards */
    div[data-testid="stMetric"] {
        background: #FFFFFF !important;
        border: 1px solid #ECEFF5 !important;
        padding: 16px 20px !important;
        border-radius: 16px !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.02) !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #6B7280 !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
    }
    div[data-testid="stMetricValue"] {
        color: #111827 !important;
        font-size: 24px !important;
        font-weight: 800 !important;
        letter-spacing: -0.5px !important;
    }

    /* Buttons */
    .stButton button {
        background: #4318FF !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 9999px !important;
        padding: 8px 20px !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        box-shadow: 0 4px 12px rgba(67, 24, 255, 0.25) !important;
        transition: all 0.15s ease !important;
    }
    .stButton button:hover {
        background: #3965FF !important;
        box-shadow: 0 6px 16px rgba(67, 24, 255, 0.35) !important;
        transform: translateY(-1px);
    }
</style>
""", unsafe_allow_html=True)

from src.db.schema import initialize_db
from src.db.connection import get_connection
from src.dashboard.components import (
    render_data_quality_warnings,
    build_summary_table,
    plot_trailing_chart,
    plot_yield_curve,
    render_market_regime,
)
from src.config import JGB_DASHBOARD_TENORS, JGB_SPREADS
from src.dashboard.exposure_ui import render_exposure_mapping_tab
from src.dashboard.transmission_ui import render_transmission_tab
from src.dashboard.monte_carlo_ui import render_monte_carlo_tab
from src.dashboard.optimization_ui import render_optimization_tab


def plot_mercury_balance_chart(dates=None, values=None) -> go.Figure:
    """Create a sleek, smooth spline chart matching the Mercury Balance hero chart."""
    if dates is None or values is None or len(dates) == 0:
        dates = pd.date_range(start="2024-07-25", periods=32, freq="D")
        t = np.linspace(0, 1, 32)
        y = (
            12.42 
            + 0.45 * np.exp(-((t - 0.22) ** 2) / 0.005)
            - 0.18 * np.exp(-((t - 0.40) ** 2) / 0.008)
            + 0.06 * np.sin(t * 18)
            + 0.24 * (t ** 1.6)
        )
        values = y * 1_000_000

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates,
        y=values,
        mode="lines",
        name="Mercury Balance",
        line=dict(color="#4318FF", width=2.8, shape="spline", smoothing=1.3),
        fill="tozeroy",
        fillcolor="rgba(67, 24, 255, 0.035)",
        hovertemplate="<b>%{x|%b %d, %Y}</b><br>Balance: $%{y:,.2f}<extra></extra>"
    ))

    fig.update_layout(
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showline=False,
            tickmode="array",
            tickvals=[
                pd.Timestamp("2024-07-26"),
                pd.Timestamp("2024-08-04"),
                pd.Timestamp("2024-08-13"),
                pd.Timestamp("2024-08-22")
            ],
            ticktext=["Jul 26", "Aug 4", "Aug 13", "Aug 22"],
            tickfont=dict(color="#9CA3AF", size=11.5, family="Plus Jakarta Sans, sans-serif"),
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showline=False,
            showticklabels=False,
            range=[12.25e6, 12.95e6],
        ),
        height=220,
        margin=dict(l=0, r=0, t=10, b=25),
        hovermode="x unified",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    return fig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper: load all risk metrics
# ---------------------------------------------------------------------------
@st.cache_data(ttl=60)
def load_risk_metrics():
    """Load all risk metrics from the database."""
    try:
        conn = get_connection()
        df = pd.read_sql_query("SELECT * FROM risk_metrics ORDER BY date", conn)
        conn.close()
        return df
    except Exception as e:
        logger.error(f"Error loading risk metrics: {e}")
        return pd.DataFrame()


def get_last_refreshed():
    """Get the latest ingested_at timestamp across all raw tables."""
    try:
        conn = get_connection()
        timestamps = []
        for table in ["commodity_prices", "fx_rates", "jgb_yields"]:
            try:
                result = conn.execute(
                    f"SELECT MAX(ingested_at) FROM {table}"
                ).fetchone()
                if result and result[0]:
                    timestamps.append(result[0])
            except Exception:
                pass
        conn.close()
        if timestamps:
            return max(timestamps)
    except Exception:
        pass
    return "Never"


# ---------------------------------------------------------------------------
# Initialize database on startup
# ---------------------------------------------------------------------------
initialize_db()

# ---------------------------------------------------------------------------
# Mercury Layout & Navigation
# ---------------------------------------------------------------------------
last_refresh = get_last_refreshed()

# ---------------------------------------------------------------------------
# Sidebar Navigation (Mercury Style)
# ---------------------------------------------------------------------------
with st.sidebar:
    # Organization / Workspace Brand Header
    st.markdown("""
    <div class="mercury-sidebar-brand">
        <div>
            <div class="mercury-brand-name">Risk Resilience Engine</div>
            <div class="mercury-brand-sub">IFSA</div>
        </div>
        <div class="mercury-brand-caret">▾</div>
    </div>
    """, unsafe_allow_html=True)

    # Primary Navigation (Matching the reference photo)
    nav_selection = st.radio(
        label="Navigation",
        options=[
            "Market Risk Monitor",
            "Company Exposure Mapping",
            "Financial Transmission",
            "Monte Carlo & Correlation",
            "Hedge Optimization"
        ],
        index=0,
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown(f"""
    <div style="padding: 0 4px;">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
            <div style="width: 8px; height: 8px; border-radius: 50%; background: #01B574; box-shadow: 0 0 0 3px rgba(1, 181, 116, 0.2);"></div>
            <span style="font-size: 12px; font-weight: 600; color: #374151;">Live Market Feed</span>
        </div>
        <div style="font-size: 11px; color: #9CA3AF; margin-bottom: 12px;">Synced: {str(last_refresh)[:19]}</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Refresh Feed", use_container_width=True):
        with st.spinner("Refreshing live market data..."):
            from src.ingestion.runner import run_full_ingestion
            run_full_ingestion()
            load_risk_metrics.clear()
        st.rerun()



# ---------------------------------------------------------------------------
# Main Content Views
# ---------------------------------------------------------------------------
metrics_df = load_risk_metrics()

if nav_selection == "Market Risk Monitor":
    st.markdown("### Market Risk Monitor")
    st.caption("Foreign Exchange, Commodities, and Japanese Government Bonds analytics.")

    try:
        conn = get_connection()
        render_data_quality_warnings(conn)
        conn.close()
    except Exception:
        pass

    if metrics_df.empty:
        st.info("No market data available yet. Click 'Live Sync' above to run ingestion.")
        st.stop()

    st.subheader("Foreign Exchange")
    st.caption("Key trade currencies tracking USD/JPY, EUR/JPY, and AUD/JPY spot volatility.")
    fx_instruments = ["USDJPY", "EURJPY", "AUDJPY"]
    fx_table = build_summary_table(metrics_df, fx_instruments, value_col_label="Rate", decimals=2)
    st.dataframe(fx_table, use_container_width=True, hide_index=True)

    for pair in fx_instruments:
        with st.expander(f"{pair} — Trailing 1Y Performance", expanded=True):
            fig = plot_trailing_chart(metrics_df, pair, y_label="Rate", trailing_days=252)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("Commodities")
    st.caption("Industrial inputs and energy benchmark prices (WTI, Brent, Copper, Aluminium).")
    commodity_instruments = ["WTI", "BRENT", "COPPER", "ALUMINIUM"]
    commodity_table = build_summary_table(metrics_df, commodity_instruments, value_col_label="Price (USD)", decimals=2)
    st.dataframe(commodity_table, use_container_width=True, hide_index=True)

    for commodity in commodity_instruments:
        with st.expander(f"{commodity} — Trailing 1Y Performance", expanded=True):
            fig = plot_trailing_chart(metrics_df, commodity, y_label="Price (USD)", trailing_days=252)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("JGB Yield Curve")
    st.caption("Japanese Government Bond benchmark term structure and slope metrics.")
    try:
        conn = get_connection()
        yield_curve_fig = plot_yield_curve(conn)
        conn.close()
        st.plotly_chart(yield_curve_fig, use_container_width=True)
    except Exception as e:
        st.error(f"Could not render yield curve: {e}")

    jgb_table = build_summary_table(metrics_df, JGB_DASHBOARD_TENORS, value_col_label="Yield (%)", decimals=3, is_rate=True)
    st.dataframe(jgb_table, use_container_width=True, hide_index=True)

    spread_names = list(JGB_SPREADS.keys())
    spread_table = build_summary_table(metrics_df, spread_names, value_col_label="Spread (bps)", decimals=1, is_rate=True)
    if not spread_table.empty:
        st.markdown("#### Benchmark Yield Curve Spreads")
        st.dataframe(spread_table, use_container_width=True, hide_index=True)

    for tenor in JGB_DASHBOARD_TENORS:
        with st.expander(f"JGB {tenor} — Trailing 1Y Performance", expanded=True):
            fig = plot_trailing_chart(metrics_df, tenor, y_label="Yield (%)", trailing_days=252)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()
    render_market_regime(metrics_df)

elif nav_selection == "Company Exposure Mapping":
    render_exposure_mapping_tab()

elif nav_selection == "Financial Transmission":
    render_transmission_tab()

elif nav_selection == "Monte Carlo & Correlation":
    render_monte_carlo_tab()

elif nav_selection == "Hedge Optimization":
    render_optimization_tab()



# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.divider()
st.caption(
    "IFSA Risk Resilience Engine v2.0 • "
    "Data sources: FRED, Yahoo Finance, Ministry of Finance Japan. "
    "Designed with Mercury SaaS System."
)

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
import os
import sqlite3
import pandas as pd

# Monkey-patch pandas Styler.applymap to fix Streamlit crash with pandas >= 2.1
try:
    from pandas.io.formats.style import Styler
    Styler.applymap = Styler.map
except Exception:
    pass

import numpy as np
import plotly.io as pio
import plotly.graph_objects as go
import plotly.express as px

# ---------------------------------------------------------------------------
# 1. Page Config
# ---------------------------------------------------------------------------
# 1. Page Config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="IFSA Market Risk Engine", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# 2. Plotly Theme (Light Mode with Darkish Blue Accent)
# ---------------------------------------------------------------------------
# Palette: Darkish Blue, Trading Up Green, Trading Down Red, Info Blue, Accent Turquoise, Muted
binance_palette = ["#1e40af", "#0ecb81", "#f6465d", "#3b82f6", "#2dbdb6", "#707a8a"]

binance_template = go.layout.Template()
binance_template.layout.paper_bgcolor = "#ffffff"
binance_template.layout.plot_bgcolor = "#ffffff"
binance_template.layout.font = dict(family="Inter, -apple-system, system-ui, sans-serif", color="#181a20", size=12)
binance_template.layout.colorway = binance_palette
binance_template.layout.xaxis = dict(
    showgrid=True,
    gridcolor="#eaecef",
    zeroline=False,
    linecolor="#eaecef",
    tickfont=dict(color="#707a8a", size=11, family="Inter, sans-serif")
)
binance_template.layout.yaxis = dict(
    showgrid=True,
    gridcolor="#eaecef",
    zeroline=False,
    linecolor="#eaecef",
    tickfont=dict(color="#707a8a", size=11, family="Inter, sans-serif")
)

pio.templates["binance"] = binance_template
pio.templates.default = "binance"

# ---------------------------------------------------------------------------
# 3. Binance Design System Custom CSS (Light Mode with same accents)
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"], .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        font-feature-settings: "ss01" 1 !important;
        color: #181a20 !important;
        -webkit-font-smoothing: antialiased !important;
    }

    /* Binance Canvas Light (#ffffff) */
    .stApp {
        background-color: #ffffff !important;
        background-image: none !important;
    }

    /* Streamlit Top Header Bar Light Theme */
    header[data-testid="stHeader"], [data-testid="stHeader"], header {
        background-color: #ffffff !important;
        background: #ffffff !important;
        border-bottom: 1px solid #eaecef !important;
    }
    div[data-testid="stDecoration"] {
        background-image: linear-gradient(90deg, #1e40af, #3b82f6) !important;
    }
    header[data-testid="stHeader"] *, [data-testid="stHeader"] button, [data-testid="stHeader"] svg {
        color: #181a20 !important;
        fill: #181a20 !important;
    }

    /* Tighter main container */
    .main .block-container {
        padding-top: 0.75rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1.25rem !important;
        padding-right: 1.25rem !important;
        max-width: 1600px !important;
    }

    /* Binance Typography (Light Theme) */
    h1 { font-size: 32px !important; font-weight: 700 !important; letter-spacing: -0.6px !important; color: #181a20 !important; margin-bottom: 6px !important; }
    h2 { font-size: 24px !important; font-weight: 600 !important; letter-spacing: -0.4px !important; color: #181a20 !important; margin-top: 18px !important; margin-bottom: 6px !important; }
    h3 { font-size: 19px !important; font-weight: 600 !important; letter-spacing: -0.2px !important; color: #181a20 !important; margin-top: 14px !important; margin-bottom: 4px !important; }
    h4, h5, h6 { font-size: 16px !important; font-weight: 600 !important; color: #181a20 !important; margin-top: 8px !important; margin-bottom: 4px !important; }
    p, span, label { font-weight: 400; font-size: 14px; line-height: 1.4; color: #181a20; }
    .stCaption, [data-testid="stCaptionContainer"] p, [data-testid="stCaptionContainer"] span {
        color: #707a8a !important; font-size: 13px !important;
        font-weight: 400 !important; line-height: 1.4 !important;
    }

    /* Sidebar Light (#fafafa) */
    section[data-testid="stSidebar"] {
        background-color: #fafafa !important;
        border-right: 1px solid #eaecef !important;
        box-shadow: none !important;
        width: 230px !important;
    }
    section[data-testid="stSidebar"] .block-container {
        padding-top: 0.9rem !important;
        padding-left: 0.85rem !important;
        padding-right: 0.85rem !important;
    }

    /* Sidebar brand with Darkish Blue Icon */
    .stripi-sidebar-brand {
        display: flex; align-items: center; gap: 10px;
        padding: 2px 4px 10px 4px; margin-bottom: 10px;
        border-bottom: 1px solid #eaecef;
    }
    .stripi-brand-icon {
        width: 28px; height: 28px; border-radius: 6px;
        background: #1e40af; display: flex; align-items: center;
        justify-content: center; color: #ffffff; font-weight: 700;
        font-size: 14px; box-shadow: 0 2px 6px rgba(30, 64, 175, 0.3);
    }
    .stripi-brand-name { font-size: 13.5px; font-weight: 600; color: #181a20; letter-spacing: -0.2px; line-height: 1.2; }
    .stripi-brand-sub { font-size: 10px; font-weight: 500; color: #707a8a; text-transform: uppercase; letter-spacing: 0.5px; }

    /* Sidebar nav */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] > div { gap: 2px !important; }
    section[data-testid="stSidebar"] [data-testid="stRadioOption"] {
        display: flex !important; align-items: center !important;
        padding: 7px 10px !important; border-radius: 6px !important;
        cursor: pointer !important; transition: all 0.12s ease !important;
        margin-bottom: 2px !important; width: 100% !important;
    }
    section[data-testid="stSidebar"] [data-testid="stRadioOption"] div:has(+ div[data-testid="stMarkdownContainer"]) { display: none !important; }
    section[data-testid="stSidebar"] [data-testid="stRadioOption"] p {
        font-size: 13px !important; font-weight: 400 !important;
        color: #475569 !important; margin: 0 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover { background-color: #f1f5f9 !important; }
    section[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover p { color: #181a20 !important; }
    section[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] {
        background-color: #ffffff !important; border: 1px solid #e2e8f0 !important;
        border-left: 3px solid #1e40af !important;
    }
    section[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] p {
        color: #1e40af !important; font-weight: 600 !important;
    }

    /* Flash animations for live ticks */
    @keyframes flash-green {
        0%   { background-color: rgba(14, 203, 129, 0.25); }
        100% { background-color: transparent; }
    }
    @keyframes flash-red {
        0%   { background-color: rgba(246, 70, 93, 0.20); }
        100% { background-color: transparent; }
    }
    .tick-up   { animation: flash-green 1.2s ease-out; }
    .tick-down { animation: flash-red   1.2s ease-out; }

    /* Binance Metric Cards */
    div[data-testid="stMetric"] {
        background: #ffffff !important; border: 1px solid #eaecef !important;
        padding: 16px 20px !important; border-radius: 8px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03) !important;
        display: flex !important; flex-direction: column !important;
        align-items: flex-start !important; gap: 4px !important;
    }
    div[data-testid="stMetric"] > div {
        display: flex !important; flex-direction: column !important;
        align-items: flex-start !important; width: 100% !important;
        gap: 4px !important;
    }
    div[data-testid="stMetricLabel"], div[data-testid="stMetricLabel"] * {
        color: #707a8a !important; font-size: 12px !important;
        font-weight: 600 !important; text-transform: uppercase !important; 
        letter-spacing: 0.5px !important; margin: 0 !important;
        display: block !important;
    }
    div[data-testid="stMetricValue"], div[data-testid="stMetricValue"] * {
        color: #181a20 !important; font-size: 24px !important;
        font-weight: 700 !important; letter-spacing: -0.5px !important;
        font-feature-settings: "tnum" 1 !important; margin: 0 !important;
        line-height: 1.2 !important; display: block !important;
    }
    div[data-testid="stMetricDelta"], div[data-testid="stMetricDelta"] * {
        font-size: 13px !important; font-weight: 600 !important;
        margin: 0 !important; display: flex !important;
        align-items: center !important;
    }
    div[data-testid="stExpander"] summary, div[data-testid="stExpander"] summary p {
        font-weight: 600 !important; font-size: 14.5px !important; color: #181a20 !important;
    }

    /* Darkish Blue Primary CTAs (#1e40af) */
    .stButton button,
    button[kind="primary"],
    button[kind="secondary"],
    button[data-testid*="stBaseButton"] {
        background: #1e40af !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 8px 18px !important;
        box-shadow: 0 2px 6px rgba(30, 64, 175, 0.25) !important;
        transition: all 0.12s ease !important;
        min-height: unset !important;
        height: auto !important;
    }

    .stButton button *,
    button[kind="primary"] *,
    button[kind="secondary"] *,
    button[data-testid*="stBaseButton"] * {
        background: transparent !important;
        padding: 0 !important;
        margin: 0 !important;
        box-shadow: none !important;
        border: none !important;
        color: #ffffff !important;
        font-weight: 600 !important;
    }

    .stButton button, .stButton button *,
    button[kind="primary"], button[kind="primary"] *,
    button[kind="secondary"], button[kind="secondary"] *,
    button[data-testid*="stBaseButton"], button[data-testid*="stBaseButton"] * {
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 13.5px !important;
        line-height: 1.25 !important;
    }

    .stButton button:hover {
        background: #172554 !important;
        transform: translateY(-0.5px);
    }

    button:disabled {
        background: #eaecef !important;
        color: #707a8a !important;
        opacity: 0.7 !important;
    }

    /* DataFrames, DataEditors & Tables (Light Theme) */
    .stDataFrame, [data-testid="stDataFrame"], [data-testid="stDataEditor"], [data-testid="stTable"] { 
        border-radius: 8px !important; border: 1px solid #eaecef !important;
        background-color: #ffffff !important;
        box-shadow: none !important;
        font-feature-settings: "tnum" 1 !important; font-size: 13px !important;
        color: #181a20 !important;
    }
    .stDataFrame iframe, [data-testid="stDataFrame"] > div, [data-testid="stDataEditor"] > div {
        background-color: #ffffff !important;
        color: #181a20 !important;
    }
    table {
        background-color: #ffffff !important;
        color: #181a20 !important;
        border-collapse: collapse !important;
    }
    th {
        background-color: #fafafa !important;
        color: #707a8a !important;
        border-bottom: 1px solid #eaecef !important;
    }
    td {
        background-color: #ffffff !important;
        color: #181a20 !important;
        border-bottom: 1px solid #eaecef !important;
    }

    /* Container cards */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        background: #ffffff !important; border: 1px solid #eaecef !important;
        border-radius: 8px !important; padding: 14px 16px 10px 16px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03) !important;
    }

    div[data-testid="stExpander"] {
        border-radius: 8px !important; border: 1px solid #eaecef !important;
        box-shadow: none !important;
        background: #ffffff !important; margin-bottom: 6px !important;
    }
    div[data-testid="stExpander"] summary { font-weight: 600 !important; font-size: 14px !important; color: #181a20 !important; }

    /* Inputs, Selectboxes & Dropdown Popovers */
    div[data-baseweb="input"], div[data-baseweb="select"] > div { 
        border: 1px solid #eaecef !important; border-radius: 6px !important; 
        background-color: #ffffff !important; color: #181a20 !important; 
    }
    div[data-baseweb="input"]:focus-within, div[data-baseweb="select"]:focus-within { border-color: #1e40af !important; box-shadow: 0 0 0 1px #1e40af !important; }
    input { color: #181a20 !important; font-size: 13.5px !important; font-feature-settings: "tnum" 1 !important; }

    div[data-baseweb="popover"], div[data-baseweb="menu"], ul[role="listbox"] {
        background-color: #ffffff !important;
        border: 1px solid #eaecef !important;
        color: #181a20 !important;
    }
    li[role="option"] {
        background-color: #ffffff !important;
        color: #181a20 !important;
    }
    li[role="option"]:hover, li[aria-selected="true"] {
        background-color: #fafafa !important;
        color: #181a20 !important;
    }
    div[data-baseweb="select"] span {
        color: #181a20 !important;
    }

    /* Darkish Blue Pill tag */
    .stripi-pill-tag {
        display: inline-flex; align-items: center;
        background-color: rgba(30, 64, 175, 0.1); color: #1e40af; font-size: 10px;
        font-weight: 600; letter-spacing: 0.5px; text-transform: uppercase;
        border-radius: 9999px; padding: 3px 9px; line-height: 1.2;
        border: 1px solid rgba(30, 64, 175, 0.25);
    }

    /* Live FX tick display */
    .live-tick-card {
        background: #ffffff; border: 1px solid #eaecef; border-radius: 8px;
        padding: 12px 14px; display: flex; flex-direction: column; 
        justify-content: flex-start; align-items: flex-start; gap: 4px;
        margin-bottom: 8px; font-feature-settings: "tnum" 1;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .live-tick-pair { font-size: 11.5px; font-weight: 600; color: #707a8a; text-transform: uppercase; letter-spacing: 0.5px; }
    .live-tick-row { display: flex; align-items: baseline; gap: 6px; width: 100%; }
    .live-tick-price { font-size: 19px; font-weight: 700; color: #181a20; letter-spacing: -0.3px; line-height: 1.1; }
    .live-tick-arrow-up   { color: #0ecb81; font-size: 12px; font-weight: 700; display:flex; align-items:baseline; }
    .live-tick-arrow-down { color: #f6465d; font-size: 12px; font-weight: 700; display:flex; align-items:baseline; }
</style>
""", unsafe_allow_html=True)



from src.db.schema import initialize_db
from src.db.connection import get_connection
from src.dashboard.components import (
    render_data_quality_warnings,
    build_summary_table,
    style_summary_table,
    plot_trailing_chart,
    plot_yield_curve,
    render_market_regime,
)
from src.config import JGB_DASHBOARD_TENORS, JGB_SPREADS, LIVE_FX_REFRESH_MS
from src.dashboard.exposure_ui import render_exposure_mapping_tab
from src.dashboard.transmission_ui import render_transmission_tab
from src.dashboard.monte_carlo_ui import render_monte_carlo_tab
from src.dashboard.optimization_ui import render_optimization_tab
from src.dashboard.stress_test_ui import render_stress_test_tab


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
# ---------------------------------------------------------------------------
# Sidebar Navigation (Stripi Style)
# ---------------------------------------------------------------------------
with st.sidebar:
    # Organization / Workspace Brand Header
    st.markdown("""
    <div class="stripi-sidebar-brand">
        <div>
            <div class="stripi-brand-name">Risk Resilience & Hedge Optimising</div>
            <div class="stripi-brand-sub">IFSA NITT</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Primary Navigation
    nav_selection = st.radio(
        label="Navigation",
        options=[
            "Market Risk Monitor",
            "Company Exposure Mapping",
            "Financial Transmission",
            "Monte Carlo & Correlation",
            "Hedge Optimization",
            "Stress Testing",
        ],
        index=0,
        label_visibility="collapsed"
    )

    st.markdown("---")

    # --- Live FX Stream Panel ---
    import subprocess, sys
    stream_running = st.session_state.get("stream_pid") is not None
    try:
        if stream_running:
            proc = st.session_state.get("stream_proc")
            if proc and proc.poll() is not None:
                stream_running = False
                st.session_state.pop("stream_proc", None)
                st.session_state.pop("stream_pid", None)
    except Exception:
        pass

    status_dot = "🟢" if stream_running else "🔴"
    status_txt = "Live FX Stream Active" if stream_running else "FX Stream Offline"
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
        <span style="font-size:11px;">{status_dot}</span>
        <span style="font-size:11px;font-weight:600;color:#0d253d;">{status_txt}</span>
    </div>
    <div style="font-size:10px;color:#64748d;margin-bottom:8px;font-feature-settings:'tnum' 1;">Synced: {str(last_refresh)[:19]}</div>
    """, unsafe_allow_html=True)

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        if not stream_running:
            if st.button("▶ Start Stream", use_container_width=True):
                proc = subprocess.Popen(
                    [sys.executable, "-m", "src.ingestion.finnhub_stream"],
                    cwd=str(Path(__file__).parent)
                )
                st.session_state["stream_proc"] = proc
                st.session_state["stream_pid"] = proc.pid
                st.rerun()
        else:
            st.button("▶ Stream On", use_container_width=True, disabled=True)
    with col_s2:
        if stream_running:
            if st.button("■ Stop", use_container_width=True):
                proc = st.session_state.get("stream_proc")
                if proc:
                    proc.terminate()
                st.session_state.pop("stream_proc", None)
                st.session_state.pop("stream_pid", None)
                st.rerun()
        else:
            st.button("■ Stop", use_container_width=True, disabled=True)

    # Live FX tick display
    try:
        with get_connection() as _lconn:
            _live_df = pd.read_sql(
                "SELECT symbol, price, prev_price FROM fx_rates_live "
                "WHERE id IN (SELECT MAX(id) FROM fx_rates_live GROUP BY symbol)",
                _lconn
            )
        if not _live_df.empty:
            for _, row in _live_df.iterrows():
                is_up = row["price"] >= (row["prev_price"] or row["price"])
                arrow = "▲" if is_up else "▼"
                arrow_class = "live-tick-arrow-up" if is_up else "live-tick-arrow-down"
                pct = ((row["price"] - (row["prev_price"] or row["price"])) / (row["prev_price"] or row["price"])) * 100
                st.markdown(f"""
                <div class="live-tick-card">
                    <span class="live-tick-pair">{row['symbol']}</span>
                    <div class="live-tick-row">
                        <span class="live-tick-price">{row['price']:.4f}</span>
                        <span class="{arrow_class}">{arrow} {abs(pct):.3f}%</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    except Exception:
        pass

    if st.button("Refresh Feed", use_container_width=True):
        with st.spinner("Refreshing live market data..."):
            from src.ingestion.runner import run_full_ingestion
            run_full_ingestion()
            load_risk_metrics.clear()
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("#### Export & Reporting")
    
    from src.dashboard.exposure_ui import load_company_names
    existing_companies_for_report = load_company_names()
    report_company = st.selectbox(
        "Select Enterprise Profile for Report",
        options=existing_companies_for_report,
        key="report_company_select"
    )
    
    if st.button("Master Risk Check-up", type="primary", use_container_width=True, help="Runs all simulations and exports a PDF"):
        import datetime
        from src.reporting.generator import generate_master_report
        
        with st.status(f"Generating Master Risk Report for {report_company}...", expanded=True) as status:
            try:
                def progress_cb(msg):
                    status.update(label=msg, state="running")
                
                pdf_bytes = generate_master_report(company_name=report_company, progress_callback=progress_cb)
                
                status.update(label="PDF Report generated successfully!", state="complete", expanded=False)
                
                st.download_button(
                    label="Download PDF Report",
                    data=pdf_bytes,
                    file_name=f"Master_Risk_Report_{datetime.datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
            except Exception as e:
                status.update(label=f"Generation failed: {e}", state="error")
                st.error(f"Error generating report: {e}")




# ---------------------------------------------------------------------------
# Compact dense header bar
# ---------------------------------------------------------------------------
st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            padding:10px 0 10px 0;border-bottom:1px solid #eaecef;margin-bottom:16px;">
    <div style="display:flex;align-items:center;gap:10px;">
        <span style="font-size:17px;font-weight:700;letter-spacing:-0.4px;color:#181a20;">
            Manufacturing Risk Monitor
        </span>
        <span style="font-size:12px;color:#707a8a;font-weight:400;">
            FX · Commodities · JGB · Transmission · Monte Carlo
        </span>
    </div>
    <div style="font-size:11px;color:#707a8a;font-weight:500;font-feature-settings:'tnum' 1;">
        <span style="color:#1e40af;font-weight:700;">●</span>&nbsp;Synced: {str(last_refresh)[:19]}
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Main Content Views
# ---------------------------------------------------------------------------
metrics_df = load_risk_metrics()

if nav_selection == "Market Risk Monitor":
    # Auto-refresh every 5s when stream is live
    if st.session_state.get("stream_pid"):
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=LIVE_FX_REFRESH_MS, key="live_refresh")

    try:
        conn = get_connection()
        render_data_quality_warnings(conn)
        conn.close()
    except Exception:
        pass

    if metrics_df.empty:
        st.info("No market data available yet. Click 'Refresh Feed' in the sidebar to run ingestion.")
        st.stop()

    st.subheader("Foreign Exchange")
    st.caption("Key trade currencies tracking USD/JPY, EUR/JPY, and AUD/JPY spot volatility.")
    fx_instruments = ["USDJPY", "EURJPY", "AUDJPY"]
    fx_table = build_summary_table(metrics_df, fx_instruments, value_col_label="Rate", decimals=2)
    st.dataframe(style_summary_table(fx_table), use_container_width=True, hide_index=True)

    for pair in fx_instruments:
        with st.expander(f"{pair} — Trailing 1M Performance", expanded=True):
            fig = plot_trailing_chart(metrics_df, pair, y_label="Rate", trailing_days=21, auto_color=True)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("Commodities")
    st.caption("Industrial inputs and energy benchmark prices (WTI, Brent, Copper, Aluminium).")
    commodity_instruments = ["WTI", "BRENT", "COPPER", "ALUMINIUM"]
    commodity_table = build_summary_table(metrics_df, commodity_instruments, value_col_label="Price (USD)", decimals=2)
    st.dataframe(style_summary_table(commodity_table), use_container_width=True, hide_index=True)

    for commodity in commodity_instruments:
        with st.expander(f"{commodity} — Trailing 1Y Performance", expanded=True):
            fig = plot_trailing_chart(metrics_df, commodity, y_label="Price (USD)", trailing_days=252, auto_color=True)
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
    st.dataframe(style_summary_table(jgb_table), use_container_width=True, hide_index=True)

    spread_names = list(JGB_SPREADS.keys())
    spread_table = build_summary_table(metrics_df, spread_names, value_col_label="Spread (bps)", decimals=1, is_rate=True)
    if not spread_table.empty:
        st.markdown("#### Benchmark Yield Curve Spreads")
        st.dataframe(style_summary_table(spread_table), use_container_width=True, hide_index=True)

    for tenor in JGB_DASHBOARD_TENORS:
        with st.expander(f"JGB {tenor} — Trailing 1Y Performance", expanded=True):
            fig = plot_trailing_chart(metrics_df, tenor, y_label="Yield (%)", trailing_days=252, auto_color=True)
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

elif nav_selection == "Stress Testing":
    render_stress_test_tab()



# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.divider()
st.caption(
    "IFSA Market Risk Infrastructure v2.0 • "
    "Data sources: FRED, Yahoo Finance, Ministry of Finance Japan."
)


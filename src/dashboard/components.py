"""Reusable Streamlit/Plotly dashboard components.

SaaS Dashboard UI Kit inspired components for the
Japan Manufacturing Market Risk Monitor dashboard.
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from src.config import JGB_DASHBOARD_TENORS, JGB_SPREADS, STALENESS_THRESHOLD_DAYS


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def render_insight(text: str):
    """Render a Binance Light-styled dynamic text insight card."""
    st.markdown(f"""
    <div style="margin-top: 14px; margin-bottom: 14px; padding: 14px 18px; border-radius: 8px; 
                background-color: #fafafa; border: 1px solid #eaecef; border-left: 4px solid #1e40af; 
                color: #181a20; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
        <div style="line-height: 1.5; font-size: 13.5px; font-weight: 400; color: #181a20;">
            {text}
        </div>
    </div>
    """, unsafe_allow_html=True)


def _fmt_change(val, is_rate=False):
    """Format a change value with sign and units."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    if is_rate:
        bps = val * 100
        sign = "+" if bps > 0 else ""
        return f"{sign}{bps:.1f} bps"
    else:
        pct = val * 100
        sign = "+" if pct > 0 else ""
        return f"{sign}{pct:.2f}%"


def _safe_float(val, decimals=4):
    """Safely format a float or return '—'."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    return f"{val:.{decimals}f}"


# ---------------------------------------------------------------------------
# Data quality warning banner
# ---------------------------------------------------------------------------

def render_data_quality_warnings(conn):
    """Show warning banner if any instrument has stale or fallback data."""
    from datetime import datetime, timedelta

    warnings = []
    today = datetime.utcnow().date()

    tables_and_keys = [
        ("commodity_prices", "commodity", "date"),
        ("fx_rates", "currency_pair", "date"),
        ("jgb_yields", "tenor", "date"),
    ]

    for table, key_col, date_col in tables_and_keys:
        try:
            query = f"""
                SELECT {key_col}, MAX({date_col}) as latest_date
                FROM {table}
                GROUP BY {key_col}
            """
            df = pd.read_sql_query(query, conn)
            for _, row in df.iterrows():
                try:
                    d = datetime.strptime(str(row["latest_date"])[:10], "%Y-%m-%d").date()
                    if (today - d).days > STALENESS_THRESHOLD_DAYS:
                        warnings.append(
                            f"[{row[key_col]}] Data stale: last update was {row['latest_date']}"
                        )
                except Exception:
                    pass
        except Exception:
            pass

    try:
        fallback_query = "SELECT DISTINCT commodity FROM commodity_prices WHERE source = 'FRED_MONTHLY'"
        fallback_df = pd.read_sql_query(fallback_query, conn)
        for _, row in fallback_df.iterrows():
            warnings.append(
                f"[{row['commodity']}] Using monthly FRED fallback data (yfinance daily unavailable)"
            )
    except Exception:
        pass

    if warnings:
        count = len(warnings)
        label = f"⚠️ {count} Data Alert{'s' if count > 1 else ''}"
        
        # Push the popover button to the right corner
        _, col_btn = st.columns([0.8, 0.2])
        with col_btn:
            with st.popover(label, use_container_width=True):
                for w in warnings:
                    st.warning(w)


# ---------------------------------------------------------------------------
# Summary table builder
# ---------------------------------------------------------------------------

def build_summary_table(metrics_df: pd.DataFrame, instruments: list,
                        value_col_label: str = "Current Value",
                        decimals: int = 2, is_rate: bool = False) -> pd.DataFrame:
    """Build a clean summary table for a set of instruments."""
    rows = []
    for inst in instruments:
        subset = metrics_df[metrics_df["asset"] == inst].sort_values("date")
        if subset.empty:
            rows.append({
                "Instrument": inst,
                value_col_label: "—",
                "Dir": "—",
                "1D Change": "—",
                "1M Change": "—",
                "Vol (30D)": "—",
                "Z-Score": "—",
                "52W Range": "—",
            })
            continue

        latest = subset.iloc[-1]
        r1d = latest.get("return_1d")
        r1m = latest.get("return_1m")
        high_52w = latest.get("high_52w")
        low_52w = latest.get("low_52w")

        # Directional arrow based on 1D change
        if r1d is not None and not np.isnan(float(r1d)):
            arrow = "▲" if float(r1d) >= 0 else "▼"
        else:
            arrow = "—"

        range_str = "—"
        if high_52w and low_52w:
            range_str = f"{_safe_float(low_52w, decimals)} – {_safe_float(high_52w, decimals)}"

        rows.append({
            "Instrument": inst,
            value_col_label: _safe_float(latest.get("value"), decimals),
            "Dir": arrow,
            "1D Change": _fmt_change(r1d, is_rate=is_rate),
            "1M Change": _fmt_change(r1m, is_rate=is_rate),
            "Vol (30D)": _safe_float(latest.get("vol_30d"), 2) if latest.get("vol_30d") else "—",
            "Z-Score": _safe_float(latest.get("z_score"), 2),
            "52W Range": range_str,
        })

    return pd.DataFrame(rows)


def style_summary_table(df: pd.DataFrame):
    """Style summary table cells for Binance Light Theme (#ffffff surface, light headers, same accents)."""
    if df.empty:
        return df

    styler = df.style.set_properties(**{
        'background-color': '#ffffff',
        'color': '#181a20',
        'border-color': '#eaecef'
    }).set_table_styles([
        {'selector': 'th', 'props': [('background-color', '#fafafa'), ('color', '#707a8a'), ('font-weight', '600'), ('border-bottom', '1px solid #eaecef')]},
        {'selector': 'td', 'props': [('border-bottom', '1px solid #eaecef'), ('background-color', '#ffffff'), ('color', '#181a20')]}
    ])

    def style_change_cell(val):
        val_str = str(val).strip()
        if val_str.startswith("+"):
            return "color: #0ecb81; font-weight: 600; background-color: rgba(14, 203, 129, 0.12);"
        elif val_str.startswith("-"):
            return "color: #f6465d; font-weight: 600; background-color: rgba(246, 70, 93, 0.12);"
        return "background-color: #ffffff; color: #181a20;"

    def style_dir_cell(val):
        val_str = str(val).strip()
        if "▲" in val_str:
            return "color: #0ecb81; font-weight: 700; background-color: #ffffff;"
        elif "▼" in val_str:
            return "color: #f6465d; font-weight: 700; background-color: #ffffff;"
        return "background-color: #ffffff; color: #181a20;"

    map_func = getattr(styler, "map", getattr(styler, "applymap", None))
    if map_func:
        cols_to_style = [col for col in ["1D Change", "1M Change"] if col in df.columns]
        if cols_to_style:
            styler = map_func(style_change_cell, subset=cols_to_style)
        if "Dir" in df.columns:
            styler = map_func(style_dir_cell, subset=["Dir"])

    return styler


# ---------------------------------------------------------------------------
# Trailing price/yield chart (Binance Light aesthetic)
# ---------------------------------------------------------------------------

def plot_trailing_chart(metrics_df: pd.DataFrame, asset: str,
                        y_label: str = "Value",
                        trailing_days: int = 252,
                        auto_color: bool = False) -> go.Figure:
    """Create a sleek, smooth Plotly line chart with Binance light canvas."""
    subset = metrics_df[metrics_df["asset"] == asset].sort_values("date")
    if len(subset) > trailing_days:
        subset = subset.tail(trailing_days)

    line_color = "#1e40af"
    fill_color = "rgba(30, 64, 175, 0.08)"

    if auto_color and not subset.empty:
        first_val = subset.iloc[0]["value"]
        last_val = subset.iloc[-1]["value"]
        if last_val >= first_val:
            line_color = "#0ecb81"  # Binance Trading Up Green
            fill_color = "rgba(14, 203, 129, 0.08)"
        else:
            line_color = "#f6465d"  # Binance Trading Down Red
            fill_color = "rgba(246, 70, 93, 0.08)"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pd.to_datetime(subset["date"]),
        y=subset["value"],
        mode="lines",
        name=asset,
        line=dict(color=line_color, width=2.5, shape="spline"),
        fill="tozeroy",
        fillcolor=fill_color,
        hovertemplate="<b>%{x|%b %d, %Y}</b><br>" + y_label + ": %{y:,.2f}<extra></extra>"
    ))

    if trailing_days >= 252:
        title_text = f"{asset} Historical Performance (Trailing {trailing_days // 252}Y)"
    elif trailing_days <= 30:
        title_text = f"{asset} Trailing 1 Month Performance"
    else:
        title_text = f"{asset} Historical Performance ({trailing_days} Days)"

    fig.update_layout(
        title=dict(
            text=title_text,
            font=dict(size=14, color="#181a20", family="Inter, -apple-system, sans-serif")
        ),
        xaxis=dict(
            showgrid=True, gridcolor="#eaecef", zeroline=False, linecolor="#eaecef",
            tickfont=dict(color="#707a8a", size=11, family="Inter, sans-serif")
        ),
        yaxis=dict(
            title=dict(text=y_label, font=dict(color="#707a8a", size=12)),
            showgrid=True, gridcolor="#eaecef", zeroline=False, linecolor="#eaecef",
            tickfont=dict(color="#707a8a", size=11, family="Inter, sans-serif")
        ),
        height=320,
        margin=dict(l=30, r=20, t=40, b=20),
        hovermode="x unified",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff"
    )
    return fig


# ---------------------------------------------------------------------------
# JGB yield curve chart (Binance Light aesthetic)
# ---------------------------------------------------------------------------

def plot_yield_curve(conn) -> go.Figure:
    """Plot the current JGB yield curve with Binance light canvas."""
    query = """
        SELECT tenor, yield_pct, date
        FROM jgb_yields
        WHERE date = (SELECT MAX(date) FROM jgb_yields)
        ORDER BY
            CASE tenor
                WHEN '1Y' THEN 1
                WHEN '2Y' THEN 2
                WHEN '3Y' THEN 3
                WHEN '4Y' THEN 4
                WHEN '5Y' THEN 5
                WHEN '6Y' THEN 6
                WHEN '7Y' THEN 7
                WHEN '8Y' THEN 8
                WHEN '9Y' THEN 9
                WHEN '10Y' THEN 10
                WHEN '15Y' THEN 15
                WHEN '20Y' THEN 20
                WHEN '25Y' THEN 25
                WHEN '30Y' THEN 30
                WHEN '40Y' THEN 40
            END
    """
    df = pd.read_sql_query(query, conn)

    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No JGB data available", showarrow=False, font=dict(color="#707a8a"))
        return fig

    dashboard_df = df[df["tenor"].isin(JGB_DASHBOARD_TENORS)]
    curve_date = df["date"].iloc[0]

    tenor_order = {t: i for i, t in enumerate(JGB_DASHBOARD_TENORS)}
    dashboard_df = dashboard_df.copy()
    dashboard_df["sort_key"] = dashboard_df["tenor"].map(tenor_order)
    dashboard_df = dashboard_df.sort_values("sort_key")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dashboard_df["tenor"],
        y=dashboard_df["yield_pct"],
        mode="lines+markers",
        name="Yield Curve",
        line=dict(width=2.5, color="#1e40af", shape="spline"),
        marker=dict(size=8, color="#1e40af", line=dict(color="#ffffff", width=2)),
        fill="tozeroy",
        fillcolor="rgba(30, 64, 175, 0.08)",
        hovertemplate="<b>%{x} Tenor</b><br>Yield: %{y:.3f}%<extra></extra>"
    ))

    fig.update_layout(
        title=dict(
            text=f"Benchmark JGB Yield Curve ({curve_date})",
            font=dict(size=14, color="#181a20", family="Inter, -apple-system, sans-serif")
        ),
        xaxis=dict(
            title=dict(text="Tenor", font=dict(color="#707a8a", size=12)),
            showgrid=True, gridcolor="#eaecef", zeroline=False, linecolor="#eaecef",
            tickfont=dict(color="#707a8a", size=11)
        ),
        yaxis=dict(
            title=dict(text="Yield (%)", font=dict(color="#707a8a", size=12)),
            showgrid=True, gridcolor="#eaecef", zeroline=False, linecolor="#eaecef",
            tickfont=dict(color="#707a8a", size=11)
        ),
        height=360,
        margin=dict(l=30, r=20, t=50, b=30),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff"
    )
    return fig


# ---------------------------------------------------------------------------
# Market Regime gauges (Binance light theme)
# ---------------------------------------------------------------------------

def render_market_regime(metrics_df: pd.DataFrame):
    """Render the Market Regime section with Binance light indicators."""
    st.subheader("Market Regime Indicators")
    st.caption(
        "Average absolute z-score across tracked instruments (trailing 5Y window). "
        "Measures aggregate tail-risk tension across asset classes."
    )

    if metrics_df.empty:
        st.info("No risk metrics available yet. Run a data refresh first.")
        return

    latest_per_asset = (
        metrics_df.sort_values("date")
        .groupby(["asset_class", "asset"])
        .last()
        .reset_index()
    )

    categories = {
        "FX Volatility Stress": {
            "class": "FX",
            "instruments": ["USDJPY", "EURJPY", "AUDJPY"],
            "color": "#1e40af",
        },
        "Commodity Price Pressure": {
            "class": "COMMODITY",
            "instruments": ["WTI", "BRENT", "COPPER", "ALUMINIUM"],
            "color": "#f6465d",
        },
        "Rates & Curve Pressure": {
            "class": "RATE",
            "instruments": JGB_DASHBOARD_TENORS,
            "color": "#0ecb81",
        },
    }

    cols = st.columns(3)
    for i, (label, info) in enumerate(categories.items()):
        with cols[i]:
            cat_data = latest_per_asset[
                (latest_per_asset["asset_class"] == info["class"])
                & (latest_per_asset["asset"].isin(info["instruments"]))
            ]
            z_scores = cat_data["z_score"].dropna()

            avg_abs_z = float(z_scores.abs().mean()) if len(z_scores) > 0 else 0.0

            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=avg_abs_z,
                title={"text": label, "font": {"size": 13, "color": "#181a20", "family": "Inter, sans-serif"}},
                number={"suffix": "σ", "valueformat": ".2f", "font": {"size": 26, "color": "#181a20", "family": "Inter, sans-serif"}},
                gauge={
                    "axis": {"range": [0, 3], "tickwidth": 1, "tickcolor": "#707a8a"},
                    "bar": {"color": info["color"], "thickness": 0.28},
                    "bgcolor": "#ffffff",
                    "borderwidth": 0,
                    "steps": [
                        {"range": [0, 1], "color": "#fafafa"},
                        {"range": [1, 2], "color": "#f1f5f9"},
                        {"range": [2, 3], "color": "#fde8ef"},
                    ],
                    "threshold": {
                        "line": {"color": "#f6465d", "width": 2.5},
                        "thickness": 0.8,
                        "value": 2.5,
                    },
                },
            ))
            fig.update_layout(
                height=220, 
                margin=dict(l=20, r=20, t=40, b=10),
                paper_bgcolor="#ffffff",
                plot_bgcolor="#ffffff"
            )
            st.plotly_chart(fig, use_container_width=True)
            
    # Compute insight
    highest_z_asset = latest_per_asset.loc[latest_per_asset['z_score'].abs().idxmax()]
    highest_z_val = highest_z_asset['z_score']
    
    if abs(highest_z_val) > 2.0:
        insight_msg = f"Market Alert: <strong>{highest_z_asset['asset']}</strong> is experiencing extreme stress with a Z-score of <strong>{highest_z_val:.2f}σ</strong>, indicating significant deviation from historical norms."
    elif abs(highest_z_val) > 1.0:
        insight_msg = f"Elevated Volatility: <strong>{highest_z_asset['asset']}</strong> is the primary risk driver (Z-score <strong>{highest_z_val:.2f}σ</strong>), trading outside normal historical bands."
    else:
        insight_msg = f"Normal Conditions: All asset classes are currently trading within standard historical bands (max stress: {highest_z_asset['asset']} at {highest_z_val:.2f}σ)."
        
    render_insight(insight_msg)

# ---------------------------------------------------------------------------
# Stripi Balance Hero Chart
# ---------------------------------------------------------------------------

def plot_mercury_balance_chart(dates=None, values=None) -> go.Figure:
    """Create a sleek, smooth spline chart matching the Stripi balance trajectory."""
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
        name="Balance Trajectory",
        line=dict(color="#533afd", width=2.5, shape="spline", smoothing=1.3),
        fill="tozeroy",
        fillcolor="rgba(83, 58, 253, 0.04)",
        hovertemplate="<b>%{x|%b %d, %Y}</b><br>Value: ¥%{y:,.2f}<extra></extra>"
    ))

    fig.update_layout(
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showline=False,
            tickmode="auto",
            nticks=5,
            tickformat="%b %d",
            tickfont=dict(color="#64748d", size=11, family="Inter, -apple-system, sans-serif"),
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showline=False,
            showticklabels=False,
        ),
        height=220,
        margin=dict(l=5, r=5, t=10, b=25),
        hovermode="x unified",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    return fig

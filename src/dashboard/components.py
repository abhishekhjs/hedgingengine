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
                instrument = row[key_col]
                latest = pd.to_datetime(row["latest_date"]).date()
                days_old = (today - latest).days

                if days_old > STALENESS_THRESHOLD_DAYS:
                    warnings.append(
                        f"[{instrument}] Latest data is {days_old} days old (last: {row['latest_date']})"
                    )
        except Exception:
            pass

    try:
        fallback_df = pd.read_sql_query(
            "SELECT DISTINCT commodity FROM commodity_prices WHERE source = 'FRED_MONTHLY_FALLBACK'",
            conn,
        )
        for _, row in fallback_df.iterrows():
            warnings.append(
                f"[{row['commodity']}] Using monthly FRED fallback data (yfinance daily unavailable)"
            )
    except Exception:
        pass

    if warnings:
        count = len(warnings)
        label = f"Data Feed Notice ({count} alert{'s' if count > 1 else ''})"
        with st.expander(label, expanded=False):
            st.warning("\n\n".join(warnings))


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
                "1D Change": "—",
                "1M Change": "—",
                "Vol (30D)": "—",
                "Z-Score": "—",
                "Percentile": "—",
            })
            continue

        latest = subset.iloc[-1]
        r1d = latest.get("return_1d")
        r1m = latest.get("return_1m")

        rows.append({
            "Instrument": inst,
            value_col_label: _safe_float(latest.get("value"), decimals),
            "1D Change": _fmt_change(r1d, is_rate=is_rate),
            "1M Change": _fmt_change(r1m, is_rate=is_rate),
            "Vol (30D)": _safe_float(latest.get("vol_30d"), 2) if latest.get("vol_30d") else "—",
            "Z-Score": _safe_float(latest.get("z_score"), 2),
            "Percentile": _safe_float(latest.get("percentile"), 1),
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Trailing price/yield chart (Base SaaS curved spline aesthetic)
# ---------------------------------------------------------------------------

def plot_trailing_chart(metrics_df: pd.DataFrame, asset: str,
                        y_label: str = "Value",
                        trailing_days: int = 252) -> go.Figure:
    """Create a sleek, smooth Plotly line chart matching the Base UI kit."""
    subset = metrics_df[metrics_df["asset"] == asset].sort_values("date")
    if len(subset) > trailing_days:
        subset = subset.tail(trailing_days)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pd.to_datetime(subset["date"]),
        y=subset["value"],
        mode="lines",
        name=asset,
        line=dict(color="#4318FF", width=3, shape="spline"),
        fill="tozeroy",
        fillcolor="rgba(67, 24, 255, 0.05)",
        hovertemplate="<b>%{x|%b %d, %Y}</b><br>" + y_label + ": %{y:,.2f}<extra></extra>"
    ))

    fig.update_layout(
        title=dict(
            text=f"{asset} Historical Performance (Trailing {trailing_days // 252}Y)" if trailing_days >= 252 else f"{asset} Historical",
            font=dict(size=14, color="#2B3674", family="sans-serif")
        ),
        xaxis_title=None,
        yaxis_title=y_label,
        height=320,
        margin=dict(l=30, r=20, t=40, b=20),
        hovermode="x unified",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF"
    )
    return fig


# ---------------------------------------------------------------------------
# JGB yield curve chart (Base SaaS aesthetic)
# ---------------------------------------------------------------------------

def plot_yield_curve(conn) -> go.Figure:
    """Plot the current JGB yield curve with smooth interpolation."""
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
        fig.add_annotation(text="No JGB data available", showarrow=False)
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
        line=dict(width=3, color="#4318FF", shape="spline"),
        marker=dict(size=9, color="#4318FF", line=dict(color="#FFFFFF", width=2)),
        fill="tozeroy",
        fillcolor="rgba(67, 24, 255, 0.05)",
        hovertemplate="<b>%{x} Tenor</b><br>Yield: %{y:.3f}%<extra></extra>"
    ))

    fig.update_layout(
        title=dict(
            text=f"Benchmark JGB Yield Curve ({curve_date})",
            font=dict(size=14, color="#2B3674", family="sans-serif")
        ),
        xaxis_title="Tenor",
        yaxis_title="Yield (%)",
        height=360,
        margin=dict(l=30, r=20, t=50, b=30),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF"
    )
    return fig


# ---------------------------------------------------------------------------
# Market Regime gauges (Base SaaS modern radial gauges)
# ---------------------------------------------------------------------------

def render_market_regime(metrics_df: pd.DataFrame):
    """Render the Market Regime section with clean, modern radial gauges."""
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
            "color": "#4318FF",
        },
        "Commodity Price Pressure": {
            "class": "COMMODITY",
            "instruments": ["WTI", "BRENT", "COPPER", "ALUMINIUM"],
            "color": "#FFB547",
        },
        "Rates & Curve Pressure": {
            "class": "RATE",
            "instruments": JGB_DASHBOARD_TENORS,
            "color": "#01B574",
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
                title={"text": label, "font": {"size": 14, "color": "#2B3674", "family": "sans-serif"}},
                number={"suffix": "σ", "valueformat": ".2f", "font": {"size": 28, "color": "#2B3674", "family": "sans-serif"}},
                gauge={
                    "axis": {"range": [0, 3], "tickwidth": 1, "tickcolor": "#A3AED0"},
                    "bar": {"color": info["color"], "thickness": 0.3},
                    "bgcolor": "#F4F7FE",
                    "borderwidth": 0,
                    "steps": [
                        {"range": [0, 1], "color": "#F4F7FE"},
                        {"range": [1, 2], "color": "#EDF2F7"},
                        {"range": [2, 3], "color": "#FEEFE7"},
                    ],
                    "threshold": {
                        "line": {"color": "#EE5D50", "width": 3},
                        "thickness": 0.8,
                        "value": 2.5,
                    },
                },
            ))
            fig.update_layout(
                height=220, 
                margin=dict(l=20, r=20, t=40, b=10),
                paper_bgcolor="#FFFFFF",
                plot_bgcolor="#FFFFFF"
            )
            st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Mercury Balance Hero Chart
# ---------------------------------------------------------------------------

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
        line=dict(color="#4318FF", width=2.5, shape="spline", smoothing=1.3),
        fill="tozeroy",
        fillcolor="rgba(67, 24, 255, 0.04)",
        hovertemplate="<b>%{x|%b %d, %Y}</b><br>Balance: $%{y:,.2f}<extra></extra>"
    ))

    fig.update_layout(
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showline=False,
            tickmode="auto",
            nticks=5,
            tickformat="%b %d",
            tickfont=dict(color="#9CA3AF", size=11, family="sans-serif"),
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

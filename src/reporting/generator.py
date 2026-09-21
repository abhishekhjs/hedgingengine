import os
import io
import base64
import tempfile
import datetime
from pathlib import Path
import pandas as pd
import numpy as np

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

import plotly.io as pio
import plotly.graph_objects as go

from src.db.connection import get_connection
from src.analytics.exposure_calc import (
    get_latest_market_data,
    calculate_company_risk,
    compute_hedge_coverage_ratios,
    calculate_financial_transmission,
    compute_ev_sensitivities,
    compute_proximity_scores
)
from src.dashboard.exposure_ui import load_exposure_data, load_hedge_data
from src.dashboard.transmission_ui import load_financials
from src.analytics.monte_carlo import run_monte_carlo_simulation
from src.analytics.hedge_optimizer import (
    compute_hedge_priority_scores,
    compute_efficient_frontier
)
from src.dashboard.components import plot_yield_curve, plot_trailing_chart
from src.reporting.insights import (
    generate_market_insight,
    generate_exposure_insight,
    generate_transmission_insight,
    generate_montecarlo_insight,
    generate_optimization_insight
)

# Set up Jinja2 environment
TEMPLATES_DIR = Path(__file__).parent / "templates"
env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))

def fig_to_base64(fig: go.Figure) -> str:
    """Convert a Plotly figure to a base64 encoded PNG string using kaleido."""
    try:
        img_bytes = pio.to_image(fig, format="png", width=800, height=450, scale=2)
        return base64.b64encode(img_bytes).decode("utf-8")
    except Exception as e:
        print(f"Error converting figure to image: {e}")
        return ""

def generate_pdf_from_html(html_content: str) -> bytes:
    """Generate a PDF from HTML using Playwright synchronously."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_content, wait_until="networkidle")
        pdf_bytes = page.pdf(format="A4", print_background=True, margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
        browser.close()
        return pdf_bytes

def generate_master_report(company_name: str, progress_callback=None) -> bytes:
    """
    Orchestrate the entire analytics pipeline and generate a comprehensive PDF report.
    progress_callback: A function that takes a string to update Streamlit UI.
    """
    conn = get_connection()
    try:
        if progress_callback: progress_callback("1/5: Analyzing Market Data & Trailing Regimes...")
        
        # 1. Market Data
        market_data = get_latest_market_data(conn)
        metrics_df = pd.read_sql("SELECT * FROM risk_metrics", conn)
        
        latest_per_asset = metrics_df.sort_values("date").groupby(["asset_class", "asset"]).last().reset_index()
        insight_market = generate_market_insight(latest_per_asset)
        
        fig_yield = plot_yield_curve(conn)
        b64_yield = fig_to_base64(fig_yield)
        
        highest_z_asset_name = None
        if not latest_per_asset.empty:
            highest_z_asset = latest_per_asset.loc[latest_per_asset['z_score'].abs().idxmax()]
            highest_z_asset_name = highest_z_asset['asset']
            fig_trailing = plot_trailing_chart(metrics_df, highest_z_asset_name, y_label="Price/Rate", trailing_days=252)
            b64_trailing = fig_to_base64(fig_trailing)
        else:
            b64_trailing = ""

        if progress_callback: progress_callback("2/5: Reconciling Corporate Exposure & Active Hedges...")
        
        # 2. Corporate Exposure
        exposure = load_exposure_data(company_name)
        hedges = load_hedge_data(company_name)
        risk_profile = calculate_company_risk(exposure, hedges, market_data)
        
        gross_total = 0
        net_total = 0
        cat_totals = {"Commodity": 0.0, "FX": 0.0, "Rate": 0.0}
        
        for cat, items in risk_profile.items():
            cat_label = {"commodity": "Commodity", "fx": "FX", "rates": "Rate"}[cat]
            for asset, metrics in items.items():
                if metrics["gross_exposure_jpy"] > 0:
                    gross_total += metrics["gross_exposure_jpy"]
                    net_total += metrics["net_exposure_jpy"]
                    cat_totals[cat_label] += metrics["gross_exposure_jpy"]
                    
        total_hedged = gross_total - net_total
        insight_exposure = generate_exposure_insight(gross_total, net_total, cat_totals)

        if progress_callback: progress_callback("3/5: Calculating Financial Transmission & Sensitivities...")

        # 3. Transmission
        financials = load_financials(company_name)
        if not financials:
            raise ValueError("Financials not configured for this company.")
            
        sensitivities = compute_ev_sensitivities(risk_profile, financials)
        insight_transmission = generate_transmission_insight(sensitivities)
        
        b64_tornado = ""
        if sensitivities:
            sorted_sens = sorted(sensitivities.items(), key=lambda x: abs(x[1]["dEV_per_sigma"]))
            factors = [s[0] for s in sorted_sens]
            impacts = [s[1]["dEV_per_sigma"] / 1e9 for s in sorted_sens]
            categories = [s[1]["category"] for s in sorted_sens]
            cat_color = {"Commodity": "#ea2261", "FX": "#533afd", "Rates": "#665efd"}
            colors = [cat_color.get(c, "#64748d") for c in categories]

            fig_tornado = go.Figure(go.Bar(
                x=impacts, y=factors, orientation="h",
                marker=dict(color=colors, line=dict(color="#ffffff", width=1)),
                text=[f"¥{v:,.1f}B" for v in impacts], textposition="outside",
            ))
            fig_tornado.update_layout(height=400, margin=dict(l=20, r=80, t=20, b=30), paper_bgcolor="#ffffff", plot_bgcolor="#ffffff")
            b64_tornado = fig_to_base64(fig_tornado)
            
        if progress_callback: progress_callback("4/5: Running 10,000 Monte Carlo Iterations...")

        # 4. Monte Carlo
        np.random.seed(42)
        mc_results = run_monte_carlo_simulation(conn, risk_profile, financials, n_iterations=10000)
        cfar_95 = mc_results["risk_metrics"]["FCF"]["var_95"]
        evar_95 = mc_results["risk_metrics"]["EV"]["var_95"]
        base_fcf = mc_results["base_fcf"]
        
        insight_montecarlo = generate_montecarlo_insight(cfar_95, base_fcf, evar_95)
        
        # CFaR Histogram
        fcf_vals = mc_results["simulated_fcf"]
        fig_cfar = go.Figure(go.Histogram(x=fcf_vals, nbinsx=50, marker_color="#665efd", opacity=0.75))
        fig_cfar.add_vline(x=cfar_95, line_width=3, line_dash="dash", line_color="#ea2261", annotation_text=f"95% CFaR: ¥{cfar_95/1e9:.1f}B")
        fig_cfar.update_layout(height=400, paper_bgcolor="#ffffff", plot_bgcolor="#ffffff")
        b64_cfar = fig_to_base64(fig_cfar)

        if progress_callback: progress_callback("5/5: Constructing Efficient Frontier & Optimization Matrix...")

        # 5. Optimization
        coverage = compute_hedge_coverage_ratios(risk_profile)
        prox = compute_proximity_scores(financials)
        priority_df = compute_hedge_priority_scores(risk_profile, mc_results, coverage, prox)
        priorities_dict = priority_df.to_dict('records') if not priority_df.empty else []
        insight_optimization = generate_optimization_insight(priorities_dict)
        
        b64_frontier = ""
        # Efficient frontier heatmap
        if not priority_df.empty:
            frontier_df = compute_efficient_frontier(conn, risk_profile, financials, steps=5)
            # frontier_df is a pivot table with columns="FX Coverage", index="Commodity Coverage", values="CFaR_95_B"
            # Create a heatmap
            fig_frontier = go.Figure(data=go.Heatmap(
                z=frontier_df.values,
                x=frontier_df.columns.tolist(),
                y=frontier_df.index.tolist(),
                colorscale="Viridis",
                colorbar=dict(title="CFaR 95% (Billion JPY)")
            ))
            fig_frontier.update_layout(
                title="Efficient Frontier (CFaR Optimization vs. Hedge Ratio)",
                xaxis_title="FX Coverage",
                yaxis_title="Commodity Coverage",
                height=400, paper_bgcolor="#ffffff", plot_bgcolor="#ffffff"
            )
            b64_frontier = fig_to_base64(fig_frontier)

        if progress_callback: progress_callback("Compiling PDF Report with Jinja2...")

        # Render HTML
        template = env.get_template("report.html")
        html_out = template.render(
            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            exec_summary=f"This Master Risk Check-up report synthesizes current market volatility against {company_name}'s underlying exposures. The total Enterprise Value at 95% risk (EVaR) stands at JPY {evar_95/1e9:,.1f}B.",
            total_gross=gross_total,
            total_hedged=total_hedged,
            net_exposure=net_total,
            cfar_95=cfar_95,
            
            insight_market=insight_market,
            fig_yield_curve=b64_yield,
            fig_trailing=b64_trailing,
            highest_z_asset_name=highest_z_asset_name,
            
            insight_exposure=insight_exposure,
            hedges=hedges.to_dict('records') if not hedges.empty else [],
            
            insight_transmission=insight_transmission,
            fig_tornado=b64_tornado,
            
            insight_montecarlo=insight_montecarlo,
            fig_cfar=b64_cfar,
            
            insight_optimization=insight_optimization,
            priorities=priorities_dict,
            fig_frontier=b64_frontier
        )

        pdf_bytes = generate_pdf_from_html(html_out)
        
        if progress_callback: progress_callback("Done!")
        
        return pdf_bytes

    finally:
        conn.close()

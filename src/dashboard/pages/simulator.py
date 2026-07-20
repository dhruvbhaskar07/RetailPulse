"""What-if simulator dashboard page — promo lift and price change scenario modelling."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.dashboard.components.ui import (
    kpi_hero, metric_card, section_header, chart_container,
    paginated_table, role_export_section, empty_state, alert_card,
)

from src.dashboard.config import (
    FORECAST_PROJECTION_DAYS,
    PRICE_ELASTICITY_FACTOR,
    ROLLING_AVG_WINDOW,
)

PAGE_ICON = "🧪"

def render():
    role = st.session_state.get("user", {}).get("role", "viewer")
    from src.dashboard.utils import apply_filters, get_store_name
    ds = apply_filters(st.session_state.get("data_cache", {}).get("daily_sales"))

    if ds is None or ds.empty:
        empty_state("🧪", "No data for simulation",
                    "Run the ETL pipeline to generate sales data.")
        return

    st.markdown(
        f'<p style="color:#94a3b8;font-size:0.85rem;margin-bottom:1rem;">'
        f'Adjust the sliders to simulate promotional campaigns and price changes. '
        f'Results update in real-time across the {FORECAST_PROJECTION_DAYS}-day projection window.</p>',
        unsafe_allow_html=True,
    )

    # ── Selection ─────────────────────────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        so = sorted(ds["store_id"].unique())
        sel_store = st.selectbox("Store", so, key="sim_store", format_func=get_store_name)
    with c2:
        po = sorted(ds[ds["store_id"] == sel_store]["product_id"].unique())
        sel_prod = st.selectbox("Product", po, key="sim_prod")

    ts = ds[(ds["store_id"] == sel_store) & (ds["product_id"] == sel_prod)].sort_values("date")
    if len(ts) == 0:
        empty_state("🧪", "No data for this selection",
                    "Try a different store or product combination.")
        return

    # ── Scenario Controls ─────────────────────────────────────────
    section_header("Scenario Parameters", "Adjust inputs to model promotional impact", icon="🎛️")
    c1, c2 = st.columns(2)
    with c1:
        promo = st.slider("Promotional Lift (%)", -50, 100, 20,
                          help="Expected demand increase from a promotional event")
    with c2:
        price = st.slider("Price Change (%)", -30, 30, 0,
                          help="Negative = discount, Positive = price increase. "
                               f"Uses price elasticity factor of {PRICE_ELASTICITY_FACTOR}x")

    # ── Calculation ───────────────────────────────────────────────
    base = ts.tail(ROLLING_AVG_WINDOW)["total_quantity"].mean()
    mult = 1.0
    if promo != 0:
        mult *= (1 + promo / 100)
    if price != 0:
        mult *= (1 - PRICE_ELASTICITY_FACTOR * price / 100)
    scen = base * mult
    delta_pct = (scen - base) / base * 100 if base > 0 else 0

    # ── Impact KPIs ───────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_hero(f"{base:.1f}", "Base Demand", delta=f"{ROLLING_AVG_WINDOW}-day avg", delta_dir="flat", cls="violet")
    with c2:
        dir_val = "up" if scen > base else "down"
        kpi_hero(f"{scen:.1f}", "Scenario Demand",
                 delta=f"{delta_pct:+.1f}% vs base", delta_dir=dir_val,
                 cls="teal" if scen > base else "danger")
    days = FORECAST_PROJECTION_DAYS
    base_rev  = base * days
    scen_rev  = scen * days
    impact    = scen_rev - base_rev
    with c3:
        kpi_hero(f"${impact:+,.0f}", f"{days}-Day Revenue Impact",
                 delta="Projected net change", delta_dir="up" if impact > 0 else "down",
                 cls="gold" if impact > 0 else "danger")
    with c4:
        kpi_hero(f"{delta_pct:+.1f}%", "Demand Change",
                 delta="vs baseline", delta_dir="up" if delta_pct > 0 else "down",
                 cls="teal" if delta_pct > 0 else "danger")

    # ── Alert ─────────────────────────────────────────────────────
    if impact > 0:
        alert_card(f"Scenario projects ${impact:,.0f} additional revenue over {days} days",
                   f"Promotional lift of {promo}% combined with {price:+}% price change "
                   f"results in {delta_pct:+.1f}% demand increase.", variant="ok", icon="📈")
    else:
        alert_card(f"Scenario projects ${abs(impact):,.0f} revenue loss over {days} days",
                   f"Consider adjusting the price change — current elasticity penalty is reducing demand.",
                   variant="warn", icon="⚠️")

    # ── Projection Chart ──────────────────────────────────────────
    section_header(f"{days}-Day Demand Projection", "Base vs Scenario comparison", icon="📊")
    days_x = list(range(1, days + 1))
    bp = [base] * days
    sp = [scen] * days

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=days_x, y=bp, mode="lines", name="Base Demand",
        line=dict(color="#818cf8", width=2.5),
        fill="tozeroy", fillcolor="rgba(129,140,248,0.06)",
        hovertemplate="Day %{x}<br>Base: %{y:.1f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=days_x, y=sp, mode="lines", name="Scenario",
        line=dict(color="#f472b6", width=2.5, dash="dash"),
        fill="tozeroy", fillcolor="rgba(244,114,182,0.06)",
        hovertemplate="Day %{x}<br>Scenario: %{y:.1f}<extra></extra>",
    ))
    fig.update_layout(xaxis_title="Day", yaxis_title="Demand (Units)")
    chart_container(fig, height=360)

    st.markdown("---")
    wdf = pd.DataFrame({"Day": days_x, "Base_Demand": bp, "Scenario_Demand": sp})
    role_export_section([(wdf, "whatif_scenario.csv", "Scenario CSV")], role)

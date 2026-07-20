"""Demand forecast dashboard page — Prophet + LSTM ensemble with MAPE tracking."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from src.dashboard.components.ui import (
    kpi_hero, metric_card, section_header, chart_container,
    paginated_table, role_export_section, methodology_card, empty_state,
)

from src.dashboard.config import FORECAST_MAPE_TARGET, ROLLING_AVG_WINDOW

PAGE_ICON = "📈"

def render():
    from src.dashboard.utils import apply_filters, get_store_name
    ds  = apply_filters(st.session_state.get("data_cache", {}).get("daily_sales"))
    ens = apply_filters(st.session_state.get("data_cache", {}).get("ensemble_forecast_results"))
    role = st.session_state.get("user", {}).get("role", "viewer")

    methodology_card(
        "Ensemble Forecasting Engine (Prophet + LSTM)",
        "Our hybrid forecasting pipeline combines Facebook Prophet with a PyTorch LSTM neural "
        "network. The ensemble dynamically weights both predictions to achieve minimum MAPE ≤ 12%. "
        "Select a store-product pair below to explore demand patterns.",
        icon="⚙️",
    )

    if ds is None or ds.empty:
        empty_state("📈", "No forecast data",
                    "Run the forecasting pipeline to generate demand predictions.")
        return

    # ── Store / Product Selectors ─────────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        so = sorted(ds["store_id"].unique())
        sel_store = st.selectbox("Store", so, index=0, format_func=get_store_name)
    with c2:
        po = sorted(ds[ds["store_id"] == sel_store]["product_id"].unique())
        sel_prod = st.selectbox("Product", po, index=0)

    ts = ds[(ds["store_id"] == sel_store) & (ds["product_id"] == sel_prod)].sort_values("date")

    if len(ts) == 0:
        empty_state("📈", "No data for this selection",
                    "Try a different store or product combination.")
        return

    # ── Ensemble KPI Cards ────────────────────────────────────────
    if ens is not None and not ens.empty:
        fc = ens[(ens["store_id"] == sel_store) & (ens["product_id"] == sel_prod)]
        if len(fc) > 0:
            row = fc.iloc[0]
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                mape_val = row.get("ensemble_mape", None)
                mape_str = f"{mape_val:.2%}" if mape_val is not None else "—"
                dir_val  = "up" if mape_val is not None and mape_val < FORECAST_MAPE_TARGET else "down"
                tgt_pct  = f"{FORECAST_MAPE_TARGET:.0%}"
                kpi_hero(mape_str, "Ensemble MAPE",
                         delta=f"< {tgt_pct} target" if dir_val == "up" else f"> {tgt_pct} target",
                         delta_dir=dir_val, cls="violet",
                         tooltip="Mean Absolute Percentage Error of the blended model")
            with c2:
                pw = row.get("prophet_weight", None)
                kpi_hero(f"{pw:.1f}" if pw is not None else "—", "Prophet Weight",
                         delta="Ensemble allocation", delta_dir="flat", cls="gold",
                         tooltip="Ensemble weight assigned to Prophet forecast")
            with c3:
                lw = row.get("lstm_weight", None)
                kpi_hero(f"{lw:.1f}" if lw is not None else "—", "LSTM Weight",
                         delta="Ensemble allocation", delta_dir="flat", cls="teal",
                         tooltip="Ensemble weight assigned to LSTM forecast")
            with c4:
                cov = ts["total_quantity"].std() / ts["total_quantity"].mean() if ts["total_quantity"].mean() > 0 else 0
                kpi_hero(f"{cov:.2f}", "Coeff. of Variation",
                         delta="Demand volatility", delta_dir="flat", cls="info",
                         tooltip="Std Dev / Mean — lower is more stable demand")

    # ── Forecast Chart (Area with conf bands if available) ────────
    section_header("Demand Time-Series", f"Store: {get_store_name(sel_store)} · Product: {sel_prod}", icon="📈")
    fig = go.Figure()

    # Actual demand area
    fig.add_trace(go.Scatter(
        x=ts["date"], y=ts["total_quantity"],
        mode="lines", name="Actual Demand",
        line=dict(color="#34d399", width=2.5),
        fill="tozeroy", fillcolor="rgba(16,185,129,0.07)",
        hovertemplate="<b>%{x}</b><br>Qty: %{y:.0f}<extra></extra>",
    ))

    # Rolling average overlay
    ts_roll = ts["total_quantity"].rolling(ROLLING_AVG_WINDOW, min_periods=1).mean()
    fig.add_trace(go.Scatter(
        x=ts["date"], y=ts_roll,
        mode="lines", name=f"{ROLLING_AVG_WINDOW}-Day Avg",
        line=dict(color="#818cf8", width=1.5, dash="dot"),
        hovertemplate=f"<b>%{{x}}</b><br>{ROLLING_AVG_WINDOW}D Avg: %{{y:.1f}}<extra></extra>",
    ))

    fig.update_layout(xaxis_title="Date", yaxis_title="Quantity Sold")
    chart_container(fig, height=380)

    # ── Supporting Stats ──────────────────────────────────────────
    section_header("Summary Statistics", icon="📋")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card(f"{ts['total_quantity'].mean():.1f}", "Avg Daily Demand", cls="violet")
    with c2:
        metric_card(f"{ts['total_quantity'].max():.0f}", "Peak Demand", cls="gold")
    with c3:
        metric_card(f"{ts['total_quantity'].std():.1f}", "Std Dev", cls="teal")
    with c4:
        metric_card(f"{len(ts)}", "Data Points", cls="info")

    st.markdown("---")
    role_export_section(
        [(ts, f"forecast_s{sel_store}_p{sel_prod}.csv", "Time Series CSV"),
         (ens, "ensemble_forecast.csv", "Ensemble CSV")],
        role,
    )
    with st.expander("🗂️ Forecast Data", expanded=False):
        paginated_table(ts, page_size=20, key_suffix="forecast")

"""Overview dashboard page — KPIs, revenue trend, country map, and top products."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.dashboard.components.ui import (
    kpi_hero, metric_card, section_header, chart_container,
    paginated_table, role_export_section, methodology_card,
    loading_skeleton, empty_state,
)

from src.dashboard.config import PALETTE, SEGMENT_COLORS

PAGE_ICON = "📊"

def render():
    from src.dashboard.utils import apply_filters
    sf   = apply_filters(st.session_state.get("data_cache", {}).get("sales_clean"))
    segs = apply_filters(st.session_state.get("data_cache", {}).get("customer_segments"))
    role = st.session_state.get("user", {}).get("role", "viewer")

    methodology_card(
        "Platform Overview & Aggregations",
        "Real-time retail sales KPIs, customer activity, and distribution analysis "
        "across all active store locations from the UCI Online Retail II dataset.",
        icon="ℹ️",
    )

    # ── Hero KPI Row ──────────────────────────────────────────────
    if sf is not None and not sf.empty:
        total_rev   = sf["revenue"].sum()
        total_ord   = sf["transaction_id"].nunique()
        total_cust  = sf["customer_id"].nunique()
        aov         = total_rev / total_ord if total_ord > 0 else 0

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            kpi_hero(f"${total_rev:,.0f}", "Total Revenue",
                     delta="vs all time", delta_dir="up", cls="gold",
                     tooltip="Total revenue across all stores and products")
        with c2:
            kpi_hero(f"{total_ord:,}", "Total Orders",
                     delta=f"{total_ord/total_cust:.1f} per customer", delta_dir="flat", cls="",
                     tooltip="Number of unique transactions")
        with c3:
            kpi_hero(f"{total_cust:,}", "Active Customers",
                     delta="Distinct buyers", delta_dir="up", cls="teal",
                     tooltip="Distinct customers with purchases")
        with c4:
            kpi_hero(f"${aov:.2f}", "Avg Order Value",
                     delta="Per transaction", delta_dir="flat", cls="violet",
                     tooltip="Average revenue per transaction")
    else:
        loading_skeleton(4, 110)

    # ── Charts ────────────────────────────────────────────────────
    if sf is not None and not sf.empty:
        st.markdown('<div style="height:0.3rem"></div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)

        with c1:
            section_header("Revenue Trend", "Daily aggregated revenue", icon="📈")
            dr = sf.groupby("date")["revenue"].sum().reset_index()
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=dr["date"], y=dr["revenue"],
                mode="lines", name="Revenue",
                line=dict(color="#818cf8", width=2.5),
                fill="tozeroy",
                fillcolor="rgba(99,102,241,0.08)",
                hovertemplate="<b>%{x}</b><br>Revenue: $%{y:,.0f}<extra></extra>",
            ))
            chart_container(fig, height=320)

        with c2:
            if "category" in sf.columns:
                section_header("Top Categories", "Revenue by product category", icon="🏷️")
                cr = sf.groupby("category")["revenue"].sum().sort_values(ascending=True).tail(10)
                colors = PALETTE[:len(cr)]
                fig = go.Figure(go.Bar(
                    x=cr.values, y=cr.index, orientation="h",
                    marker=dict(color=colors, opacity=0.85),
                    hovertemplate="<b>%{y}</b><br>Revenue: $%{x:,.0f}<extra></extra>",
                ))
                chart_container(fig, height=320)

        # ── Segment Distribution ──────────────────────────────────
        if segs is not None and not segs.empty:
            c1, c2 = st.columns([1.4, 1])
            with c1:
                section_header("Customer Segments", "RFM-based segmentation distribution", icon="👥")
                sc = segs["segment_label"].value_counts()
                fig = px.pie(
                    values=sc.values, names=sc.index,
                    color_discrete_sequence=SEGMENT_COLORS,
                    hole=0.45,
                )
                fig.update_traces(
                    textinfo="percent+label",
                    textfont_size=11,
                    marker=dict(line=dict(color="#080b14", width=1.5)),
                )
                chart_container(fig, height=340)

            with c2:
                section_header("Segment Breakdown", "Customer count by group", icon="📊")
                for seg, count in sc.items():
                    pct = count / sc.sum() * 100
                    st.markdown(
                        f'<div style="display:flex;justify-content:space-between;'
                        f'padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.04);">'
                        f'<span style="font-size:0.78rem;color:#94a3b8">{seg}</span>'
                        f'<span style="font-size:0.78rem;font-weight:600;color:#f1f5f9">'
                        f'{count:,} <span style="color:#475569;font-weight:400">({pct:.1f}%)</span></span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
    else:
        empty_state("📊", "No sales data", "Run the ETL pipeline to generate data.")

    st.markdown("---")
    role_export_section(
        [(sf, "overview_sales.csv", "Sales CSV"),
         (segs, "customer_segments.csv", "Segments CSV")],
        role,
    )
    with st.expander("🗂️ Raw Data", expanded=False):
        paginated_table(sf, page_size=15, key_suffix="overview")

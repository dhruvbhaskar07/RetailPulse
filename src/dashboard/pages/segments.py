"""Customer segments dashboard page — RFM distribution, 3D clusters, and segment profiles."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.dashboard.components.ui import (
    kpi_hero, metric_card, section_header, chart_container,
    paginated_table, role_export_section, methodology_card, empty_state,
)

from src.dashboard.config import SEGMENT_COLORS, N_SEGMENTS

PAGE_ICON = "👥"

def render():
    from src.dashboard.utils import apply_filters
    segs  = apply_filters(st.session_state.get("data_cache", {}).get("customer_segments"))
    churn = apply_filters(st.session_state.get("data_cache", {}).get("churn_scores"))
    role  = st.session_state.get("user", {}).get("role", "viewer")

    methodology_card(
        "RFM & Behavioral Clustering",
        f"Customers are evaluated on Recency (days since last order), Frequency (total purchase count), "
        f"and Monetary value (total spend). K-Means clustering segments them into {N_SEGMENTS} actionable profiles.",
        icon="🔬",
    )

    if segs is None or segs.empty:
        empty_state("👥", "No segmentation data",
                    "Run the segmentation pipeline to generate customer clusters.")
        return

    # ── Segment stats ─────────────────────────────────────────────
    ss = segs.groupby("segment_label").agg(
        customer_count=("customer_id", "count"),
        avg_rec=("recency", "mean"),
        avg_freq=("frequency", "mean"),
        avg_mon=("monetary", "mean"),
    ).round(1).reset_index().sort_values("customer_count", ascending=False)

    # ── Hero KPI Row ──────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_hero(f"{len(segs):,}", "Total Customers", delta="All segments", delta_dir="flat", cls="",
                 tooltip="Total customers in the dataset")
    with c2:
        kpi_hero(f"{segs['segment_label'].nunique()}", "Segments", delta="K-Means clusters", delta_dir="flat", cls="teal")
    with c3:
        kpi_hero(f"${segs['monetary'].mean():.0f}", "Avg Customer Value",
                 delta="Mean LTV", delta_dir="up", cls="gold",
                 tooltip="Average lifetime monetary value per customer")
    with c4:
        kpi_hero(f"{segs['recency'].mean():.0f}d", "Avg Recency",
                 delta="Days since last order", delta_dir="flat", cls="violet")

    # ── Segment Cards Grid ────────────────────────────────────────
    st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)
    section_header("Segment Profiles", "Click to explore each segment in detail", icon="🃏")

    seg_list = ss["segment_label"].tolist()
    cols = st.columns(min(len(seg_list), 4))
    for i, seg in enumerate(seg_list):
        row = ss[ss["segment_label"] == seg].iloc[0]
        color = SEGMENT_COLORS[i % len(SEGMENT_COLORS)]
        with cols[i % 4]:
            st.markdown(
                f'<div class="segment-card" style="border-left:3px solid {color};">'
                f'<div class="segment-card-name" style="color:{color}">{seg}</div>'
                f'<div class="segment-card-stat"><span>Customers</span><span>{row["customer_count"]:,.0f}</span></div>'
                f'<div class="segment-card-stat"><span>Avg Revenue</span><span>${row["avg_mon"]:.0f}</span></div>'
                f'<div class="segment-card-stat"><span>Avg Freq</span><span>{row["avg_freq"]:.1f}x</span></div>'
                f'<div class="segment-card-stat"><span>Avg Recency</span><span>{row["avg_rec"]:.0f}d</span></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── RFM 3D Visualization ──────────────────────────────────────
    st.markdown('<div style="height:0.3rem"></div>', unsafe_allow_html=True)
    section_header("RFM Space", "3D customer distribution across Recency, Frequency, Monetary dimensions", icon="🌐")
    smp = segs.sample(min(1200, len(segs)), random_state=42)
    fig = px.scatter_3d(
        smp, x="recency", y="frequency", z="monetary",
        color="segment_label", size="monetary",
        hover_data=["customer_id"],
        color_discrete_sequence=SEGMENT_COLORS,
        opacity=0.75,
    )
    fig.update_layout(
        height=520, scene=dict(bgcolor="rgba(0,0,0,0)"),
        legend=dict(orientation="h", y=-0.05),
    )
    chart_container(fig, height=520)

    # ── Drill-Down ────────────────────────────────────────────────
    st.markdown('<div style="height:0.3rem"></div>', unsafe_allow_html=True)
    section_header("Segment Deep-Dive", "Explore individual segment analytics", icon="🔍")
    sel = st.selectbox("Select Segment to Explore", segs["segment_label"].unique(), key="seg_select")
    sg = segs[segs["segment_label"] == sel]

    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card(f"{len(sg):,}", "Customers in Segment", cls="teal")
        metric_card(f"{sg['recency'].mean():.0f} days", "Avg Recency", cls="violet")
    with c2:
        metric_card(f"{sg['frequency'].mean():.1f}x", "Avg Frequency", cls="gold")
        metric_card(f"${sg['monetary'].mean():.2f}", "Avg Monetary", cls="pink")
    with c3:
        if churn is not None and not churn.empty:
            sc2 = churn[churn["customer_id"].isin(sg["customer_id"])]
            rd = sc2["churn_risk_level"].value_counts()
            if not rd.empty:
                fig = px.pie(
                    values=rd.values, names=rd.index,
                    title=f"Churn Distribution — {sel}",
                    color_discrete_sequence=["#ef4444","#f87171","#f59e0b","#10b981"],
                    hole=0.4,
                )
                fig.update_layout(height=260, margin=dict(t=30,b=0,l=0,r=0))
                chart_container(fig, height=260)

    st.markdown("---")
    role_export_section(
        [(ss, "segment_stats.csv", "Stats CSV"),
         (segs, "all_segments.csv", "All Segments CSV")],
        role,
    )
    with st.expander("🗂️ Segment Detail", expanded=False):
        paginated_table(segs, page_size=20, key_suffix="segments")

"""Churn analysis dashboard page — risk distribution, top at-risk customers, and SHAP explanations."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.dashboard.components.ui import (
    kpi_hero, metric_card, section_header, chart_container,
    paginated_table, role_export_section, alert_card, empty_state,
)

from src.dashboard.config import RISK_COLORS, CHURN_HIGH_RISK_ALERT_THRESHOLD

PAGE_ICON = "⚠️"

def render():
    from src.dashboard.utils import apply_filters
    cs   = apply_filters(st.session_state.get("data_cache", {}).get("churn_scores"))
    segs = apply_filters(st.session_state.get("data_cache", {}).get("customer_segments"))
    role = st.session_state.get("user", {}).get("role", "viewer")

    if cs is None or cs.empty:
        empty_state("⚠️", "No churn data",
                    "Run the churn prediction pipeline to generate risk scores.")
        return

    rl    = cs["churn_risk_level"].value_counts()
    total = len(cs)
    high_risk  = rl.get("Very High", 0) + rl.get("High", 0)
    avg_risk   = cs["churn_risk_score"].mean()
    above_half = (cs["churn_risk_score"] > CHURN_HIGH_RISK_ALERT_THRESHOLD).sum()

    # ── Alert Banner ──────────────────────────────────────────────
    if high_risk > 0:
        alert_card(
            f"{high_risk:,} Customers At High Risk",
            f"These customers have high churn probability. Immediate re-engagement campaigns are recommended. "
            f"Average risk across all {total:,} customers is {avg_risk:.1%}.",
            variant="danger", icon="🔴",
        )
    else:
        alert_card("Churn Risk Nominal", "No critical risk clusters detected.", variant="ok", icon="✅")

    # ── Hero KPI Row ──────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_hero(f"{high_risk:,}", "High Risk Customers",
                 delta="Very High + High", delta_dir="down", cls="danger",
                 tooltip="Customers with High or Very High churn risk")
    with c2:
        kpi_hero(f"{total:,}", "Total Scored",
                 delta="All customers", delta_dir="flat", cls="violet",
                 tooltip="Total customers scored by the churn model")
    with c3:
        kpi_hero(f"{avg_risk:.1%}", "Avg Risk Score",
                 delta="Portfolio-wide", delta_dir="down" if avg_risk > 0.3 else "flat", cls="gold",
                 tooltip="Average churn risk across all customers")
    with c4:
        pct_label = f"{CHURN_HIGH_RISK_ALERT_THRESHOLD:.0%}"
        kpi_hero(f"{above_half:,}", f"Risk > {pct_label}",
                 delta="Needs attention", delta_dir="down", cls="pink",
                 tooltip=f"Customers with predicted churn probability above {pct_label}")

    # ── Charts ────────────────────────────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        section_header("Risk Distribution", "Customer count by risk band", icon="🎯")
        risk_order = ["Very High", "High", "Medium", "Low"]
        rl_ordered = rl.reindex([r for r in risk_order if r in rl.index])
        colors = [RISK_COLORS.get(r, "#6366f1") for r in rl_ordered.index]
        fig = go.Figure(go.Bar(
            x=rl_ordered.index, y=rl_ordered.values,
            marker=dict(color=colors, opacity=0.85),
            hovertemplate="<b>%{x}</b><br>Customers: %{y:,}<extra></extra>",
        ))
        chart_container(fig, height=300)

    with c2:
        section_header("Top 20 At-Risk", "Highest churn probability customers", icon="🚨")
        top20 = cs.nlargest(20, "churn_risk_score")[["customer_id", "churn_risk_score", "churn_risk_level"]].copy()
        def style_risk(val):
            return f"color: {RISK_COLORS.get(val, '#94a3b8')}"
        st.dataframe(
            top20,
            use_container_width=True,
            column_config={
                "customer_id": st.column_config.TextColumn("Customer ID"),
                "churn_risk_score": st.column_config.ProgressColumn(
                    "Risk Score", min_value=0, max_value=1, format="%.1%"
                ),
                "churn_risk_level": st.column_config.TextColumn("Risk Level"),
            },
        )

    # ── Segment Comparison ────────────────────────────────────────
    if segs is not None and not segs.empty:
        st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)
        section_header("Risk by Customer Segment", "Average churn score per RFM cluster", icon="👥")
        m = segs.merge(cs[["customer_id", "churn_risk_score"]], on="customer_id")
        rb = m.groupby("segment_label").agg(
            avg_risk=("churn_risk_score", "mean"),
            high_pct=("churn_risk_score", lambda x: (x > 0.5).mean()),
            count=("customer_id", "count"),
        ).reset_index().sort_values("avg_risk", ascending=False)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=rb["segment_label"], y=rb["avg_risk"],
            name="Avg Risk Score",
            marker=dict(color="#6366f1", opacity=0.85),
            hovertemplate="<b>%{x}</b><br>Avg Risk: %{y:.1%}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=rb["segment_label"], y=rb["high_pct"],
            name="% Risk > 50%", mode="markers+lines",
            marker=dict(color="#f472b6", size=8),
            line=dict(color="#f472b6", width=1.5, dash="dot"),
            yaxis="y2",
            hovertemplate="<b>%{x}</b><br>High Risk %: %{y:.1%}<extra></extra>",
        ))
        fig.update_layout(
            yaxis=dict(tickformat=".0%", title="Avg Risk"),
            yaxis2=dict(tickformat=".0%", overlaying="y", side="right", title="High Risk %"),
        )
        chart_container(fig, height=320)

    st.markdown("---")
    role_export_section(
        [(cs, "churn_scores.csv", "All Scores CSV"),
         (cs.nlargest(100, "churn_risk_score")[["customer_id", "churn_risk_score", "churn_risk_level"]],
          "top_100_at_risk.csv", "Top 100 CSV")],
        role,
    )
    with st.expander("🗂️ All Scores", expanded=False):
        paginated_table(cs, page_size=20, key_suffix="churn")

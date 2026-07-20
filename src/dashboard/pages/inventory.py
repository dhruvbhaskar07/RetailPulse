"""Inventory dashboard page — stockout risk, days of supply, and reorder recommendations."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.dashboard.components.ui import (
    kpi_hero, metric_card, section_header, chart_container,
    paginated_table, role_export_section, alert_card, empty_state,
)

from src.dashboard.config import INVENTORY_DAYS_WARNING

PAGE_ICON = "📦"

def render():
    from src.dashboard.utils import apply_filters, get_store_name
    inv  = apply_filters(st.session_state.get("data_cache", {}).get("inventory_recommendations"))
    role = st.session_state.get("user", {}).get("role", "viewer")

    if inv is None or inv.empty:
        empty_state("📦", "No inventory data",
                    "Run the inventory optimization pipeline to generate recommendations.")
        return

    stockout_risk = int(inv["is_stockout_risk"].sum()) if "is_stockout_risk" in inv.columns else 0
    below_reorder = int(inv["is_below_reorder"].sum()) if "is_below_reorder" in inv.columns else 0
    total_skus    = len(inv)

    # ── Alert Banner ──────────────────────────────────────────────
    if stockout_risk > 0:
        alert_card(
            f"⚡ {stockout_risk} SKUs at Immediate Stockout Risk",
            f"{below_reorder} SKUs are also below reorder point. "
            f"Recommended order quantity: {inv['recommended_order_qty'].sum():,.0f} units.",
            variant="danger", icon="🔴",
        )
    elif below_reorder > 0:
        alert_card(
            f"⚠️ {below_reorder} SKUs Below Reorder Point",
            "No immediate stockouts, but replenishment orders should be placed soon.",
            variant="warn", icon="🟡",
        )
    else:
        alert_card("✅ Inventory Levels Healthy", "All SKUs above safety stock thresholds.",
                   variant="ok", icon="🟢")

    # ── Hero KPI Row ──────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_hero(f"{total_skus:,}", "Total SKUs", delta="Under management", delta_dir="flat", cls="")
    with c2:
        kpi_hero(f"{below_reorder:,}", "Below Reorder", delta="Needs ordering", delta_dir="down", cls="warm",
                 tooltip="SKUs with stock below reorder point")
    with c3:
        kpi_hero(f"{stockout_risk:,}", "Stockout Risk", delta="Critical", delta_dir="down", cls="danger",
                 tooltip="SKUs at immediate stockout risk")
    with c4:
        kpi_hero(f"{inv['recommended_order_qty'].sum():,}", "Rec. Order Units",
                 delta="Total across SKUs", delta_dir="up", cls="teal",
                 tooltip="Total recommended order quantity")

    # ── Filters ───────────────────────────────────────────────────
    st.markdown('<div style="height:0.3rem"></div>', unsafe_allow_html=True)
    fc1, fc2 = st.columns(2)
    with fc1:
        sf2 = st.selectbox(
            "Filter by Store",
            ["All"] + sorted(inv["store_id"].unique().tolist()),
            format_func=lambda x: "All Stores" if x == "All" else get_store_name(x),
        )
    with fc2:
        mu = st.slider("Minimum Urgency Score", 0.0, float(inv["urgency_score"].max() or 200.0), 0.0,
                       help="Show only items with urgency above this threshold")

    fi = inv.copy()
    if sf2 != "All":
        fi = fi[fi["store_id"] == sf2]
    fi = fi[fi["urgency_score"] >= mu]

    # ── Urgent Reorders Table ─────────────────────────────────────
    section_header("Most Urgent Reorders", f"Top items requiring attention ({len(fi):,} SKUs filtered)", icon="🚨")
    cols_show = [c for c in ["store_id","product_id","stock_level","avg_daily_demand",
                              "safety_stock","reorder_point_calculated",
                              "recommended_order_qty","days_of_supply","urgency_score"]
                 if c in fi.columns]
    top_urgent = fi.nlargest(20, "urgency_score")[cols_show]
    st.dataframe(
        top_urgent, use_container_width=True,
        column_config={
            "urgency_score": st.column_config.ProgressColumn(
                "Urgency", min_value=0, max_value=float(inv["urgency_score"].max() or 1), format="%.1f"
            ),
            "days_of_supply": st.column_config.NumberColumn("Days Supply", format="%.1f"),
            "recommended_order_qty": st.column_config.NumberColumn("Rec. Qty", format="%d"),
        },
    )

    # ── Charts ────────────────────────────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        section_header("Days of Supply", "Distribution across filtered SKUs", icon="📊")
        fig = go.Figure(go.Histogram(
            x=fi["days_of_supply"], nbinsx=30,
            marker=dict(color="#6366f1", opacity=0.8),
            hovertemplate="Days: %{x:.0f}<br>Count: %{y}<extra></extra>",
        ))
        fig.add_vline(x=INVENTORY_DAYS_WARNING, line_dash="dash", line_color="#ef4444",
                      annotation_text=f"{INVENTORY_DAYS_WARNING}-day critical", annotation_font_color="#f87171")
        chart_container(fig, height=300)

    with c2:
        section_header("Stock vs Demand", "Bubble size = recommended order qty", icon="🔵")
        fig = px.scatter(
            fi, x="avg_daily_demand", y="stock_level",
            color="urgency_score", size="recommended_order_qty",
            color_continuous_scale=["#10b981", "#f59e0b", "#ef4444"],
            labels={"avg_daily_demand": "Avg Daily Demand", "stock_level": "Current Stock"},
            hover_data=["product_id", "days_of_supply"],
        )
        chart_container(fig, height=300)

    st.markdown("---")
    role_export_section(
        [(fi.nlargest(100, "urgency_score"), "urgent_items.csv", "Top 100 Urgent CSV"),
         (inv, "full_inventory.csv", "Full Inventory CSV")],
        role,
    )
    with st.expander("🗂️ All Inventory", expanded=False):
        paginated_table(inv, page_size=20, key_suffix="inventory")

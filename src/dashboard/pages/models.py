"""Model performance dashboard page — metrics, feature importance, and retrain controls."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.dashboard.components.ui import (
    kpi_hero, metric_card, section_header, chart_container,
    paginated_table, role_export_section, empty_state, alert_card,
)

from src.dashboard.config import (
    FORECAST_MAPE_TARGET,
    TARGET_AUC_ROC,
    SEGMENT_COLORS,
    PALETTE,
)

PAGE_ICON = "🤖"

def render():
    from src.dashboard.utils import apply_filters
    ens  = apply_filters(st.session_state.get("data_cache", {}).get("ensemble_forecast_results"))
    ci   = st.session_state.get("data_cache", {}).get("churn_importance")
    inv  = apply_filters(st.session_state.get("data_cache", {}).get("inventory_recommendations"))
    segs = apply_filters(st.session_state.get("data_cache", {}).get("customer_segments"))
    sf   = apply_filters(st.session_state.get("data_cache", {}).get("sales_clean"))
    role = st.session_state.get("user", {}).get("role", "viewer")

    mape_pct_str = f"{FORECAST_MAPE_TARGET:.0%}"

    # ── System Health Banner ──────────────────────────────────────
    issues = []
    if ens is None or ens.empty:
        issues.append("Forecasting")
    elif "ensemble_mape" in ens.columns and ens["ensemble_mape"].mean() > FORECAST_MAPE_TARGET:
        issues.append(f"Forecasting MAPE > {mape_pct_str}")
    if ci is None or (hasattr(ci, "empty") and ci.empty):
        issues.append("Churn Importance")

    if issues:
        alert_card(
            f"Model Health: {len(issues)} Issue(s) Detected",
            f"Degraded or missing data in: {', '.join(issues)}. Run the affected pipelines.",
            variant="warn", icon="⚠️",
        )
    else:
        alert_card(
            "All Models Operational",
            "Forecasting, churn, segmentation, and inventory models are producing results.",
            variant="ok", icon="✅",
        )

    # ── Dataset KPIs ──────────────────────────────────────────────
    if sf is not None:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            kpi_hero(f"{len(sf):,}", "Transactions",
                     delta="UCI Online Retail II", delta_dir="flat", cls="violet")
        with c2:
            stores = sf["store_id"].nunique() if "store_id" in sf.columns else 0
            kpi_hero(f"{stores}", "Stores",
                     delta="Countries as stores", delta_dir="flat", cls="gold")
        with c3:
            custs = sf["customer_id"].nunique() if "customer_id" in sf.columns else 0
            kpi_hero(f"{custs:,}", "Customers",
                     delta="Unique buyers", delta_dir="flat", cls="teal")
        with c4:
            prods = sf["product_id"].nunique() if "product_id" in sf.columns else 0
            kpi_hero(f"{prods:,}", "Products",
                     delta="Unique SKUs", delta_dir="flat", cls="pink")

        # Data source badges
        st.markdown(
            f'<div style="display:flex;gap:8px;flex-wrap:wrap;margin:0.5rem 0 1rem;">'
            f'<span class="badge badge-primary">📦 Online Retail II (UCI)</span>'
            f'<span class="badge badge-success">🎯 MAPE Target ≤ {mape_pct_str}</span>'
            f'<span class="badge badge-warn">🎯 AUC Target ≥ {TARGET_AUC_ROC:.2f}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Pill Tabs ─────────────────────────────────────────────────
    t1, t2, t3, t4 = st.tabs(["📈  Forecasting", "⚠️  Churn", "👥  Segmentation", "📦  Inventory"])

    # ── Tab 1: Forecasting ────────────────────────────────────────
    with t1:
        if ens is not None and not ens.empty:
            mape_col = next((c for c in ["ensemble_mape", "mape"] if c in ens.columns), None)
            c1, c2, c3 = st.columns(3)
            with c1:
                avg_mape = ens[mape_col].mean() if mape_col else None
                kpi_hero(f"{avg_mape:.2%}" if avg_mape is not None else "—", "Avg MAPE",
                         delta=f"< {mape_pct_str} target" if avg_mape and avg_mape < FORECAST_MAPE_TARGET else f"> {mape_pct_str} target",
                         delta_dir="up" if avg_mape and avg_mape < FORECAST_MAPE_TARGET else "down",
                         cls="teal" if avg_mape and avg_mape < FORECAST_MAPE_TARGET else "danger")
            with c2:
                if mape_col:
                    passing = int((ens[mape_col] < FORECAST_MAPE_TARGET).sum())
                    total_m = len(ens)
                    kpi_hero(f"{passing}/{total_m}", f"Models < {mape_pct_str} MAPE",
                             delta=f"{passing/total_m:.0%} pass rate",
                             delta_dir="up", cls="gold")
                else:
                    kpi_hero(f"{len(ens):,}", "Total Models", cls="gold")
            with c3:
                if "prophet_weight" in ens.columns:
                    kpi_hero(f"{ens['prophet_weight'].mean():.1f}", "Avg Prophet Weight",
                             delta="Ensemble allocation", delta_dir="flat", cls="violet")
                else:
                    kpi_hero(f"{len(ens):,}", "Evaluations", cls="violet")

            if mape_col:
                c1, c2 = st.columns(2)
                with c1:
                    section_header("MAPE Distribution", "Performance across store-product pairs", icon="📊")
                    fig = go.Figure(go.Histogram(
                        x=ens[mape_col], nbinsx=25,
                        marker=dict(color="#6366f1", opacity=0.85),
                        hovertemplate="MAPE: %{x:.1%}<br>Count: %{y}<extra></extra>",
                    ))
                    fig.add_vline(x=FORECAST_MAPE_TARGET, line_dash="dash", line_color="#ef4444",
                                  annotation_text=f"{mape_pct_str} target", annotation_font_color="#f87171")
                    chart_container(fig, height=280)
                with c2:
                    if "prophet_mape" in ens.columns and "lstm_mape" in ens.columns:
                        section_header("Prophet vs LSTM", "Scatter comparison of model errors", icon="🤖")
                        fig = px.scatter(
                            ens, x="prophet_mape", y="lstm_mape",
                            hover_data=["store_id", "product_id"],
                            color_discrete_sequence=["#818cf8"],
                            labels={"prophet_mape": "Prophet MAPE", "lstm_mape": "LSTM MAPE"},
                            opacity=0.7,
                        )
                        fig.add_shape(type="line", x0=0, y0=0, x1=1, y1=1,
                                      line=dict(dash="dash", color="#475569"))
                        chart_container(fig, height=280)

            dc = [c for c in ["store_id","product_id","model","ensemble_mape",
                               "prophet_mape","lstm_mape","prophet_weight","lstm_weight"]
                  if c in ens.columns]
            with st.expander("🗂️ Full Forecasting Table", expanded=False):
                paginated_table(ens[dc].sort_values("ensemble_mape") if mape_col else ens[dc],
                                page_size=15, key_suffix="model_fc")
        else:
            empty_state("📈", "No forecasting results", "Run the forecasting pipeline.")

    # ── Tab 2: Churn ──────────────────────────────────────────────
    with t2:
        if ci is not None and not (hasattr(ci, "empty") and ci.empty):
            section_header("Feature Importance", "Top drivers of customer churn risk", icon="🔑")
            fig = px.bar(
                ci.head(15), x="importance", y="feature", orientation="h",
                color="importance", color_continuous_scale=["#475569", "#6366f1"],
            )
            fig.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=False)
            chart_container(fig, height=420)
            with st.expander("🗂️ All Features", expanded=False):
                paginated_table(ci, page_size=15, key_suffix="model_churn")
        else:
            empty_state("⚠️", "No churn importance data", "Run the churn pipeline.")

    # ── Tab 3: Segmentation ───────────────────────────────────────
    with t3:
        if segs is not None and not segs.empty:
            sz = segs["segment_label"].value_counts()
            c1, c2 = st.columns(2)
            with c1:
                section_header("Segment Distribution", icon="🥧")
                fig = px.pie(
                    values=sz.values, names=sz.index, hole=0.4,
                    color_discrete_sequence=SEGMENT_COLORS,
                )
                fig.update_traces(textinfo="percent+label")
                chart_container(fig, height=320)
            with c2:
                section_header("Segment Stats Table", icon="📋")
                ss_tab = segs.groupby("segment_label").agg(
                    Count=("customer_id","count"),
                    Avg_Recency=("recency","mean"),
                    Avg_Frequency=("frequency","mean"),
                    Avg_Monetary=("monetary","mean"),
                ).round(1).sort_values("Count", ascending=False).reset_index()
                st.dataframe(ss_tab, use_container_width=True)
            with st.expander("🗂️ Segment Detail", expanded=False):
                paginated_table(segs, page_size=15, key_suffix="model_seg")
        else:
            empty_state("👥", "No segmentation data", "Run the segmentation pipeline.")

    # ── Tab 4: Inventory ──────────────────────────────────────────
    with t4:
        if inv is not None and not inv.empty:
            c1, c2, c3 = st.columns(3)
            with c1:
                kpi_hero(f"{int(inv['is_stockout_risk'].sum()):,}", "Stockout SKUs",
                         delta="Critical", delta_dir="down", cls="danger")
            with c2:
                kpi_hero(f"{int(inv['is_below_reorder'].sum()):,}", "Below Reorder",
                         delta="Needs ordering", delta_dir="down", cls="warm")
            with c3:
                kpi_hero(f"{inv['days_of_supply'].mean():.1f}", "Avg Days Supply",
                         delta="Inventory runway", delta_dir="flat", cls="teal")

            if "category" in inv.columns:
                section_header("Days Supply by Category", icon="📊")
                cs2 = inv.groupby("category")["days_of_supply"].mean().reset_index().sort_values("days_of_supply")
                fig = go.Figure(go.Bar(
                    x=cs2["days_of_supply"], y=cs2["category"], orientation="h",
                    marker=dict(color="#6366f1", opacity=0.85),
                ))
                chart_container(fig, height=320)
            with st.expander("🗂️ Inventory Data", expanded=False):
                paginated_table(inv, page_size=15, key_suffix="model_inv")
        else:
            empty_state("📦", "No inventory data", "Run the inventory optimization pipeline.")

    st.markdown("---")
    role_export_section(
        [(ens, "ensemble_perf.csv", "Forecasting CSV"),
         (ci, "churn_importance.csv", "Churn CSV")],
        role,
    )

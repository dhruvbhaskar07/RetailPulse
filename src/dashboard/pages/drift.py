"""Data drift dashboard page — Evidently AI drift reports and summary statistics."""

import json
from pathlib import Path
import streamlit as st
import pandas as pd
from src.dashboard.components.ui import (
    kpi_hero, metric_card, section_header, chart_container,
    role_export_section, alert_card, empty_state,
)

from src.dashboard.config import DRIFT_SHARE_HIGH_THRESHOLD, DRIFT_SOURCES

PAGE_ICON = "📡"

def render():
    role = st.session_state.get("user", {}).get("role", "viewer")

    dp = Path(__file__).parent.parent.parent.parent / "reports" / "drift" / "drift_summary.json"
    if not dp.exists():
        empty_state("📡", "No drift data",
                    "Run the drift detection pipeline to generate reports.")
        return

    with open(dp, encoding="utf-8") as f:
        ds_drift = json.load(f)

    sd = ds_drift.get("sales_drift", {})
    cd = ds_drift.get("customer_drift", {})
    sd_drift = sd.get("dataset_drift", False)
    cd_drift = cd.get("dataset_drift", False)
    ts_val   = str(ds_drift.get("timestamp", "Unknown"))[:19]

    # ── System Health Banner ──────────────────────────────────────
    if sd_drift or cd_drift:
        alert_card(
            "Data Drift Detected — Model Retraining Recommended",
            f"Drift detected in {'Sales' if sd_drift else ''}{' & ' if sd_drift and cd_drift else ''}{'Customer' if cd_drift else ''} data. "
            f"Last checked: {ts_val}. Consider retraining affected models to maintain accuracy.",
            variant="danger", icon="🔴",
        )
    else:
        alert_card(
            "✅ All Systems Nominal — No Significant Drift",
            f"Sales and customer data distributions remain within acceptable thresholds. "
            f"Last checked: {ts_val}.",
            variant="ok", icon="🟢",
        )

    # ── KPI Row ───────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    with c1:
        sd_share = sd.get("drift_share", 0)
        dir_val  = "down" if sd_share > DRIFT_SHARE_HIGH_THRESHOLD else "flat"
        kpi_hero(f"{sd_share:.1%}", "Sales Drift Share",
                 delta="⚠️ High" if sd_share > DRIFT_SHARE_HIGH_THRESHOLD else "✓ Within threshold",
                 delta_dir=dir_val, cls="danger" if sd_share > DRIFT_SHARE_HIGH_THRESHOLD else "teal")
    with c2:
        cd_share = cd.get("drift_share", 0)
        dir_val  = "down" if cd_share > DRIFT_SHARE_HIGH_THRESHOLD else "flat"
        kpi_hero(f"{cd_share:.1%}", "Customer Drift Share",
                 delta="⚠️ High" if cd_share > DRIFT_SHARE_HIGH_THRESHOLD else "✓ Within threshold",
                 delta_dir=dir_val, cls="danger" if cd_share > DRIFT_SHARE_HIGH_THRESHOLD else "teal")
    with c3:
        kpi_hero(f"{len(DRIFT_SOURCES)} Checked", "Data Sources",
                 delta=ts_val, delta_dir="flat", cls="violet")

    # ── Drift Reports ─────────────────────────────────────────────
    st.markdown('<div style="height:0.3rem"></div>', unsafe_allow_html=True)
    section_header("Evidently AI Drift Reports", "Interactive HTML reports for each data source", icon="📋")
    reports_dir = Path(__file__).parent.parent.parent.parent / "reports" / "drift"
    for title, fn, icon in DRIFT_SOURCES:
        rp = reports_dir / fn
        with st.expander(f"{icon} {title}", expanded=False):
            if rp.exists():
                st.components.v1.html(open(rp, encoding="utf-8").read(), height=550, scrolling=True)
            else:
                st.info(f"Report not generated yet. Run the drift detection pipeline.")

    st.markdown("---")
    drift_data = pd.DataFrame([
        {"source": "Sales",    "drift_share": sd.get("drift_share", 0), "drifted": sd_drift},
        {"source": "Customer", "drift_share": cd.get("drift_share", 0), "drifted": cd_drift},
    ])
    role_export_section([(drift_data, "drift_summary.csv", "Drift Summary CSV")], role)

"""UI components for the Streamlit dashboard — cards, headers, tables, and skeleton states."""

import streamlit as st
import pandas as pd
from pathlib import Path

from src.dashboard.config import PALETTE
PC = PALETTE

# ══════════════════════════════
# CSS LOADER
# ══════════════════════════════
def load_css():
    css_path = Path(__file__).parent.parent / "assets" / "styles.css"
    if css_path.exists():
        css = css_path.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    # Inject Lucide icons CDN
    st.markdown(
        '<script src="https://unpkg.com/lucide@latest/dist/umd/lucide.min.js"></script>',
        unsafe_allow_html=True,
    )

# ══════════════════════════════
# SPLASH SCREEN
# ══════════════════════════════
def render_splash():
    st.markdown(
        '''<div class="splash-screen">
        <div class="splash-ring"></div>
        <div class="splash-inner">
        <div class="splash-logo">RP</div>
        <h1 class="splash-title">RetailPulse</h1>
        <p class="splash-sub">AI-Powered Retail Intelligence</p>
        </div></div>''',
        unsafe_allow_html=True,
    )

# ══════════════════════════════
# PAGE HEADER
# ══════════════════════════════
def page_header(title: str, subtitle: str = "", icon: str = "📊", badge: str = "Live"):
    badge_html = f'<span class="rp-live-dot">{badge}</span>' if badge else ""
    st.markdown(
        f'''<div class="rp-page-header">
<div class="rp-page-header-left">
<div class="rp-page-header-icon">{icon}</div>
<div>
<div class="rp-page-title">{title}</div>
{f'<div class="rp-page-subtitle">{subtitle}</div>' if subtitle else ""}
</div>
</div>
<div class="rp-page-header-right">{badge_html}</div>
</div>''',
        unsafe_allow_html=True,
    )

# ══════════════════════════════
# SECTION HEADER
# ══════════════════════════════
def section_header(title: str, subtitle: str = "", icon=None):
    icon_html = f'<span style="font-size:1rem">{icon}</span>' if icon and len(str(icon)) <= 4 else ""
    st.markdown(
        f'''<div class="rp-section-header">
{icon_html}
<div>
<h3>{title}</h3>
{f'<p>{subtitle}</p>' if subtitle else ""}
</div>
</div>''',
        unsafe_allow_html=True,
    )

# ══════════════════════════════
# KPI HERO CARD
# ══════════════════════════════
def kpi_hero(value, label: str, delta: str = "", delta_dir: str = "flat", cls: str = "", tooltip: str = ""):
    tip = f'title="{tooltip}"' if tooltip else ""
    delta_html = ""
    if delta:
        arrow = "↑" if delta_dir == "up" else ("↓" if delta_dir == "down" else "→")
        delta_html = f'<div class="kpi-hero-delta {delta_dir}">{arrow} {delta}</div>'
    st.markdown(
        f'<div class="kpi-hero {cls}" {tip}>'
        f'<div class="kpi-hero-value">{value}</div>'
        f'<div class="kpi-hero-label">{label}</div>'
        f'{delta_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

# ══════════════════════════════
# METRIC CARD (supporting, smaller)
# ══════════════════════════════
def metric_card(value, label: str, cls: str = "", tooltip: str = ""):
    tip = f'title="{tooltip}"' if tooltip else ""
    st.markdown(
        f'<div class="metric-card {cls}" {tip}>'
        f'<div class="metric-value">{value}</div>'
        f'<div class="metric-label">{label}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ══════════════════════════════
# BADGE
# ══════════════════════════════
def badge(text: str, variant: str = "primary"):
    st.markdown(f'<span class="badge badge-{variant}">{text}</span>', unsafe_allow_html=True)

# ══════════════════════════════
# ALERT CARD
# ══════════════════════════════
def alert_card(title: str, message: str, variant: str = "warn", icon: str = "⚠️"):
    st.markdown(
        f'<div class="alert-card {variant}">'
        f'<div class="alert-card-icon">{icon}</div>'
        f'<div><h3>{title}</h3><p>{message}</p></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

def error_box(message: str):
    alert_card("Issue Detected", message, variant="danger", icon="🔴")

def info_box(title: str, message: str):
    alert_card(title, message, variant="ok", icon="✅")

# ══════════════════════════════
# CHART CONTAINER
# ══════════════════════════════
def chart_container(fig, height: int = 340, title: str = ""):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94a3b8", family="Inter", size=11),
        colorway=PC,
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.04)",
            zerolinecolor="rgba(255,255,255,0.06)",
            tickfont=dict(size=10),
        ),
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.04)",
            zerolinecolor="rgba(255,255,255,0.06)",
            tickfont=dict(size=10),
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(255,255,255,0.06)",
            borderwidth=1,
            font=dict(size=10),
        ),
        height=height,
        margin=dict(l=0, r=0, t=28, b=0),
        title=dict(font=dict(size=13, color="#94a3b8")),
        hoverlabel=dict(
            bgcolor="#161c2e",
            bordercolor="rgba(99,102,241,0.4)",
            font=dict(size=11, color="#f1f5f9"),
        ),
    )
    if title:
        st.markdown(f'<div class="chart-card-title">📈 {title}</div>', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════
# METHODOLOGY CARD
# ══════════════════════════════
def methodology_card(title: str, description: str, icon: str = "💡"):
    st.markdown(
        f'<div class="info-card">'
        f'<h4>{icon} {title}</h4>'
        f'<p>{description}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ══════════════════════════════
# SKELETON LOADER
# ══════════════════════════════
def loading_skeleton(count: int = 4, height: int = 90):
    for _ in range(count):
        st.markdown(
            f'<div class="skeleton-card" style="height:{height}px;margin-bottom:0.5rem"></div>',
            unsafe_allow_html=True,
        )

# ══════════════════════════════
# EMPTY STATE
# ══════════════════════════════
def empty_state(icon: str = "📭", title: str = "No data available",
                message: str = "There is no data to display.", action_label=None, action_fn=None):
    emoji = icon if len(icon) <= 4 else "📭"
    st.markdown(
        f'<div class="empty-state">'
        f'<div class="empty-state-icon">{emoji}</div>'
        f'<h3>{title}</h3>'
        f'<p>{message}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if action_label and action_fn:
        if st.button(action_label, key=f"empty_{title}"):
            action_fn()

# ══════════════════════════════
# CSV & EXCEL DOWNLOAD
# ══════════════════════════════
def csv_download(df, filename: str, label: str = "Download CSV"):
    if df is not None and not df.empty:
        st.download_button(label=label, data=df.to_csv(index=False), file_name=filename, mime="text/csv", use_container_width=True)

def xlsx_download(df, filename: str, label: str = "Download Excel"):
    if df is not None and not df.empty:
        import io
        try:
            import xlsxwriter
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name="Sheet1")
            st.download_button(label=label, data=output.getvalue(), file_name=filename,
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True)
        except ImportError:
            csv_download(df, filename.replace(".xlsx", ".csv"), label.replace("Excel", "CSV"))

def role_export_section(dfs, role: str):
    if role not in ("admin", "analyst"):
        return
    with st.expander("📥 Export Data", expanded=False):
        cols = st.columns(len(dfs))
        for col, (df_item, filename, label) in zip(cols, dfs):
            with col:
                csv_download(df_item, filename, label)

# ══════════════════════════════
# PAGINATED TABLE
# ══════════════════════════════
def paginated_table(df, page_size: int = 20, key_suffix: str = "", column_config=None):
    from src.dashboard.utils import paginate_dataframe
    sliced = paginate_dataframe(df, page_size, key_suffix)
    if sliced is not None and not sliced.empty:
        st.dataframe(sliced, use_container_width=True, column_config=column_config)

# ══════════════════════════════
# RENDER WITH STATE GUARD
# ══════════════════════════════
def render_page_with_state(data_key: str, render_fn, loading_height=90, empty_message="No data available"):
    data = st.session_state.get("data_cache", {}).get(data_key)
    if data is None:
        loading_skeleton(count=4, height=loading_height)
        return
    if isinstance(data, pd.DataFrame) and data.empty:
        empty_state(title="No data", message=empty_message)
        return
    render_fn(data)

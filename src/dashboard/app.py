"""RetailPulse Streamlit dashboard — main app with login, navigation, and global filters."""

import sys
from pathlib import Path
import time
import streamlit as st

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.dashboard.components.ui import load_css, render_splash, page_header
from src.dashboard.utils import (
    authenticate, get_data, invalidate_cache,
    load_preferences, save_preferences, get_store_name,
)
from src.dashboard.pages import PAGE_RENDERERS
from src.dashboard.config import (
    NAV_ITEMS, PAGE_SUBTITLES, PAGE_ICONS,
    ROLE_COLORS, DEFAULT_DATE_RANGE_DAYS, DEFAULT_STORE_COUNT,
)

st.set_page_config(
    page_title="RetailPulse",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)
load_css()

# ── Splash Screen (first load only) ─────────────────────────────
if not st.session_state.get("splash_done"):
    render_splash()
    st.session_state["splash_done"] = True
    time.sleep(0.7)
    st.rerun()

# ═══════════════════════════════════════════════════════════════
# LOGIN PAGE
# ═══════════════════════════════════════════════════════════════
if "user" not in st.session_state:
    _, c2, _ = st.columns([1, 1.8, 1])
    with c2:
        st.markdown(
            '''<div class="lc">
              <div class="lh">
                <div style="width:56px;height:56px;border-radius:12px;
                     background:linear-gradient(135deg,#6366f1,#10b981);
                     display:flex;align-items:center;justify-content:center;
                     color:#fff;font-weight:800;font-size:1.5rem;margin:0 auto 1rem;
                     box-shadow:0 0 40px rgba(99,102,241,0.3)">RP</div>
                <h1>RetailPulse</h1>
                <p>AI-Powered Retail Intelligence Platform</p>
              </div>
            </div>''',
            unsafe_allow_html=True,
        )
        with st.form("login_form"):
            u   = st.text_input("Username", placeholder="Enter your username")
            p   = st.text_input("Password", type="password", placeholder="Enter your password")
            sub = st.form_submit_button("Sign In →", type="primary", use_container_width=True)
            if sub:
                user = authenticate(u, p)
                if user:
                    st.session_state["user"] = {
                        "username": u,
                        "role":     user["role"],
                        "name":     user["name"],
                    }
                    st.rerun()
                else:
                    st.error("❌  Invalid credentials — check username and password")

        # Show demo credentials only if DEFAULT_USERS (no custom users.json)
        from src.dashboard.config import USERS_FILE, DEFAULT_USERS
        if not USERS_FILE.exists():
            demo_lines = " &nbsp;·&nbsp; ".join(
                f'<code>{u} / {d["password"]}</code>'
                for u, d in DEFAULT_USERS.items()
            )
            st.markdown(
                f'<div class="ld"><b>Demo Accounts</b> &nbsp;{demo_lines}</div>',
                unsafe_allow_html=True,
            )
    st.stop()

# ═══════════════════════════════════════════════════════════════
# SESSION & PREFERENCES
# ═══════════════════════════════════════════════════════════════
if "prefs" not in st.session_state:
    st.session_state["prefs"] = load_preferences()
prefs    = st.session_state["prefs"]
role     = st.session_state["user"]["role"]
name     = st.session_state["user"]["name"]
initials = "".join([part[0] for part in name.split()[:2]]).upper()

# Drift notification badge (reads from report file, not hardcoded)
notif_badge = ""
try:
    _drift_path = Path(__file__).parent.parent.parent / "reports" / "drift" / "drift_summary.json"
    if _drift_path.exists():
        import json as _json
        from src.dashboard.config import DRIFT_SHARE_HIGH_THRESHOLD
        _ds = _json.loads(_drift_path.read_text(encoding="utf-8"))
        _sd = _ds.get("sales_drift",    {}).get("dataset_drift", False)
        _cd = _ds.get("customer_drift", {}).get("dataset_drift", False)
        if _sd or _cd:
            notif_badge = (
                '<span style="background:#ef4444;color:#fff;border-radius:8px;'
                'padding:1px 6px;font-size:.55rem;margin-left:5px;font-weight:700">!</span>'
            )
except Exception:
    pass

# ═══════════════════════════════════════════════════════════════
# SIDEBAR — Config-driven navigation
# ═══════════════════════════════════════════════════════════════
if "page" not in st.session_state:
    st.session_state["page"] = NAV_ITEMS[0][0]   # first nav item

with st.sidebar:
    # Brand logo
    st.markdown(
        '<div class="rp-sidebar-logo">'
        '<div class="rp-sidebar-logo-icon">RP</div>'
        '<div>'
        '<div class="rp-sidebar-logo-name">RetailPulse</div>'
        '<div class="rp-sidebar-logo-sub">Analytics Platform</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    # Nav items — fully driven by config.NAV_ITEMS
    current_group = None
    for key, emoji, label, group in NAV_ITEMS:
        if group != current_group:
            st.markdown(
                f'<div class="rp-nav-section">{group}</div>',
                unsafe_allow_html=True,
            )
            current_group = group

        badge_html = notif_badge if key == "Drift" else ""
        display    = f"{emoji}  {label}"

        clicked = st.button(
            display,
            key=f"nav_{key}",
            use_container_width=True,
        )
        if clicked:
            st.session_state["page"] = key
            st.rerun()

    st.markdown('<div class="rp-nav-divider"></div>', unsafe_allow_html=True)

    # User block — role color pulled from config
    role_style = ROLE_COLORS.get(role, ROLE_COLORS.get("viewer", ""))
    st.markdown(
        f'''<div class="rp-sidebar-user">
          <div class="rp-sidebar-avatar">{initials}</div>
          <div>
            <div class="rp-sidebar-name">{name}</div>
            <span class="rp-sidebar-role"
                  style="{role_style};padding:1px 7px;border-radius:10px;">{role}</span>
          </div>
        </div>''',
        unsafe_allow_html=True,
    )

    st.markdown('<div style="height:0.4rem"></div>', unsafe_allow_html=True)
    if st.button("🚪 Sign Out", key="logout_btn", use_container_width=True):
        for k in ["user", "data_cache", "cache_ttl", "filters", "prefs", "splash_done"]:
            st.session_state.pop(k, None)
        st.rerun()

# ═══════════════════════════════════════════════════════════════
# MAIN AREA — Page Header
# ═══════════════════════════════════════════════════════════════
page = st.session_state["page"]

page_header(
    title    = PAGE_SUBTITLES.get(page, page).split(" — ")[0] if page == "Churn" else page,
    subtitle = PAGE_SUBTITLES.get(page, ""),
    icon     = PAGE_ICONS.get(page, "📊"),
    badge    = "Live",
)

# Controls row
ctrl1, ctrl2, ctrl3 = st.columns([1, 1, 4])
with ctrl1:
    if st.button("↺ Refresh", key="refresh_btn", use_container_width=True):
        invalidate_cache()
        st.rerun()
with ctrl2:
    auto_refresh = st.toggle(
        "Auto-refresh",
        value=prefs.get("auto_refresh", False),
        key="auto_refresh_toggle",
    )
    prefs["auto_refresh"] = auto_refresh
    save_preferences(prefs)
with ctrl3:
    st.write("")

# ═══════════════════════════════════════════════════════════════
# GLOBAL FILTER TOOLBAR
# All defaults come from config — no hardcoded numbers
# ═══════════════════════════════════════════════════════════════
if "filters" not in st.session_state:
    st.session_state["filters"] = {}

sales = get_data("sales_clean")

# Calculate coverage summary first to display it outside
if sales is not None and not sales.empty:
    from src.dashboard.utils import apply_filters
    filtered_sales = apply_filters(sales)
    n_filtered     = len(filtered_sales)
    n_total        = len(sales)
    pct            = (n_filtered / n_total * 100) if n_total > 0 else 0
    
    # Render premium Expander for configuring filters
    with st.expander("🔍 Configure Global Filters (applied across all pages)", expanded=False):
        fc0, fc1, fc2, fc3, fc4 = st.columns([1.2, 1.8, 1.8, 1.8, 0.8])
        
        with fc0:
            import pandas as pd
            min_d = sales["date"].min().date()
            max_d = sales["date"].max().date()
            default_start = max_d - pd.Timedelta(days=DEFAULT_DATE_RANGE_DAYS)
            date_range = st.date_input(
                "Date Range",
                value=(default_start, max_d),
                min_value=min_d,
                max_value=max_d,
                key="global_date_range",
            )
            st.session_state["filters"]["date_range"] = date_range

        with fc1:
            store_options   = sorted(sales["store_id"].unique())
            default_stores  = store_options[:DEFAULT_STORE_COUNT] if len(store_options) >= DEFAULT_STORE_COUNT else store_options
            selected_stores = st.multiselect(
                "Stores",
                options=store_options,
                default=default_stores,
                key="global_stores",
                format_func=get_store_name,
            )
            st.session_state["filters"]["stores"] = selected_stores

        with fc2:
            cat_options    = sorted(sales["category"].dropna().unique()) if "category" in sales.columns else []
            selected_cats  = st.multiselect(
                "Categories",
                options=cat_options,
                default=[],
                key="global_categories",
                placeholder="All Categories",
            )
            st.session_state["filters"]["categories"] = selected_cats

        with fc3:
            prod_options      = sorted(sales["product_id"].unique())
            selected_products = st.multiselect(
                "Products",
                options=prod_options,
                default=[],
                key="global_products",
                placeholder="All Products",
            )
            st.session_state["filters"]["products"] = selected_products

        with fc4:
            st.markdown('<div style="height:1.5rem"></div>', unsafe_allow_html=True)
            if st.button("✕ Reset", key="reset_filters_btn", use_container_width=True):
                for k in ["global_date_range", "global_stores", "global_categories", "global_products"]:
                    st.session_state.pop(k, None)
                st.session_state["filters"] = {}
                st.rerun()

    # Always visible coverage summary badge below the expander
    st.markdown(
        f'<div class="rp-filter-coverage" style="margin-top: -0.5rem; margin-bottom: 1.5rem;">'
        f'<span>📊 Active View: <strong style="color:#34d399">{n_filtered:,}</strong>'
        f' / {n_total:,} transactions</span>'
        f'<span class="rp-filter-badge">{pct:.1f}% data slice · synced across all pages</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
else:
    with st.spinner("⏳ Loading dataset — this may take a moment on first load…"):
        pass
    st.info("⚙️ No sales data loaded — click Refresh or run the ETL pipeline.")

# ═══════════════════════════════════════════════════════════════
# PAGE RENDERER
# ═══════════════════════════════════════════════════════════════
render_fn = PAGE_RENDERERS.get(page)
if render_fn:
    render_fn()
else:
    st.info("🚧 Page under construction.")

# Footer
st.markdown(
    f'<div style="text-align:center;padding:1.5rem 0 0.5rem;'
    f'font-size:0.65rem;color:#475569;border-top:1px solid rgba(255,255,255,0.05);margin-top:2rem;">'
    f'RetailPulse v3.0 &nbsp;·&nbsp; AI-Powered Analytics &nbsp;·&nbsp; '
    f'<span style="color:#6366f1">{name}</span> &nbsp;·&nbsp; '
    f'<span style="background:rgba(124,58,237,.15);color:#C4B5FD;padding:1px 8px;'
    f'border-radius:10px;font-size:.6rem;font-weight:600;border:1px solid rgba(124,58,237,.2)">'
    f'{role}</span></div>',
    unsafe_allow_html=True,
)

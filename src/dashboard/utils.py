"""
Dashboard Utilities
====================
All configurable values are imported from config.py — nothing hardcoded here.
"""
import hashlib
import json
import logging
import time
from datetime import datetime
from functools import wraps
from pathlib import Path

import pandas as pd
import streamlit as st

from src.dashboard.config import (
    CACHE_TTL_SECONDS,
    DEFAULT_PREFS,
    DEFAULT_STORE_COUNT,
    DEFAULT_DATE_RANGE_DAYS,
    ROLE_PERMISSIONS,
    IMPORT_ALLOWED_ROLES,
    DEFAULT_USERS,
    USERS_FILE,
    CHURN_RISK_THRESHOLDS,
    STOCKOUT_DAYS_CRITICAL,
    URGENCY_SCORE_MAX,
)

logger = logging.getLogger(__name__)


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler()],
    )


# ══════════════════════════════
# PASSWORD UTILITIES
# ══════════════════════════════
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ══════════════════════════════
# USER MANAGEMENT
# Load from data/users.json if available, else use DEFAULT_USERS from config
# ══════════════════════════════
def _load_users() -> dict:
    """
    Load users from USERS_FILE (data/users.json) if it exists,
    otherwise fall back to DEFAULT_USERS from config.py.
    Returns dict: { username: { "password_hash": str, "role": str, "name": str } }
    """
    if USERS_FILE.exists():
        try:
            raw = json.loads(USERS_FILE.read_text(encoding="utf-8"))
            # Support both pre-hashed and plain passwords in the JSON file
            users = {}
            for uname, udata in raw.items():
                if "password_hash" in udata:
                    users[uname] = udata  # already hashed
                elif "password" in udata:
                    users[uname] = {
                        "password_hash": hash_password(udata["password"]),
                        "role": udata.get("role", "viewer"),
                        "name": udata.get("name", uname.capitalize()),
                    }
            return users
        except Exception as exc:
            logger.warning("Failed to load users.json: %s — using defaults", exc)

    # Build from DEFAULT_USERS (plain passwords → hash at startup)
    return {
        uname: {
            "password_hash": hash_password(udata["password"]),
            "role": udata["role"],
            "name": udata["name"],
        }
        for uname, udata in DEFAULT_USERS.items()
    }


# Loaded once at import time
_USERS: dict = _load_users()


def authenticate(username: str, password: str) -> dict | None:
    """Return user dict { role, name } if credentials match, else None."""
    user = _USERS.get(username)
    if user and hash_password(password) == user["password_hash"]:
        return {"role": user["role"], "name": user["name"]}
    return None


def check_permission(permission: str) -> bool:
    if "user" not in st.session_state:
        return False
    role = st.session_state["user"].get("role", "viewer")
    return permission in ROLE_PERMISSIONS.get(role, [])


def can_import() -> bool:
    """Returns True if the logged-in user is allowed to import data."""
    return st.session_state.get("user", {}).get("role") in IMPORT_ALLOWED_ROLES


# ══════════════════════════════
# ERROR BOUNDARY
# ══════════════════════════════
def with_error_boundary(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            logger.exception("UI data load failed: %s", exc)
            return None
    return wrapper


# ══════════════════════════════
# USER PREFERENCES
# ══════════════════════════════
def _prefs_path() -> Path:
    return Path(__file__).parent.parent.parent / "data" / "user_prefs.json"


def load_preferences() -> dict:
    try:
        path = _prefs_path()
        if path.exists():
            return {**DEFAULT_PREFS, **json.loads(path.read_text(encoding="utf-8"))}
    except Exception as exc:
        logger.warning("Failed to load preferences: %s", exc)
    return DEFAULT_PREFS.copy()


def save_preferences(prefs: dict):
    try:
        path = _prefs_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(prefs, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("Failed to save preferences: %s", exc)


# ══════════════════════════════
# SESSION STATE INIT
# ══════════════════════════════
if "data_cache" not in st.session_state:
    st.session_state["data_cache"] = {}
if "cache_ttl" not in st.session_state:
    st.session_state["cache_ttl"] = {}


# ══════════════════════════════
# DATA CACHE
# ══════════════════════════════
@with_error_boundary
def get_data(key: str, ttl: int = CACHE_TTL_SECONDS) -> pd.DataFrame | None:
    cache   = st.session_state.setdefault("data_cache", {})
    ttl_map = st.session_state.setdefault("cache_ttl", {})
    now     = time.time()
    if key in cache and key in ttl_map and (now - ttl_map[key]) < ttl:
        return cache[key]
    from src.utils.data_loader import load_all_data
    all_data = load_all_data() or {}
    for k, v in all_data.items():
        cache[k]   = v
        ttl_map[k] = now
    return cache.get(key)


def invalidate_cache(key: str | None = None):
    cache   = st.session_state.get("data_cache", {})
    ttl_map = st.session_state.get("cache_ttl", {})
    if key is None:
        cache.clear()
        ttl_map.clear()
    else:
        cache.pop(key, None)
        ttl_map.pop(key, None)


# ══════════════════════════════
# PAGINATION
# ══════════════════════════════
def paginate_dataframe(df: pd.DataFrame, page_size: int = 20, key_suffix: str = ""):
    if df is None or df.empty:
        st.info("No data to display.")
        return df
    total    = len(df)
    pages    = max(1, (total + page_size - 1) // page_size)
    page_key = f"_page_{key_suffix}" if key_suffix else "_page"
    if page_key not in st.session_state:
        st.session_state[page_key] = 1
    page = st.session_state[page_key]
    page = max(1, min(page, pages))
    start = (page - 1) * page_size
    end   = min(start + page_size, total)
    c1, c2, c3 = st.columns([1, 3, 1])
    with c1:
        if st.button("◀ Prev", key=f"prev_{key_suffix}", disabled=(page <= 1)):
            st.session_state[page_key] = max(1, page - 1)
            st.rerun()
    with c2:
        st.markdown(
            f'<div style="text-align:center;font-size:.8rem;color:var(--text-muted);padding:.25rem 0">'
            f'Page <strong>{page}</strong> of <strong>{pages}</strong> · {total:,} rows</div>',
            unsafe_allow_html=True,
        )
    with c3:
        if st.button("Next ▶", key=f"next_{key_suffix}", disabled=(page >= pages)):
            st.session_state[page_key] = min(pages, page + 1)
            st.rerun()
    return df.iloc[start:end]


# ══════════════════════════════
# GLOBAL FILTERS
# ══════════════════════════════
def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    filters    = st.session_state.get("filters", {})
    if not filters:
        return df
    filtered   = df.copy()

    # Date filter
    if "date" in filtered.columns and "date_range" in filters:
        dr = filters["date_range"]
        if isinstance(dr, (list, tuple)) and len(dr) == 2:
            start_d, end_d = dr
            filtered = filtered[
                (filtered["date"].dt.date >= start_d) &
                (filtered["date"].dt.date <= end_d)
            ]

    # Store filter
    if "store_id" in filtered.columns and filters.get("stores"):
        filtered = filtered[filtered["store_id"].isin(filters["stores"])]

    # Product filter
    if "product_id" in filtered.columns and filters.get("products"):
        filtered = filtered[filtered["product_id"].isin(filters["products"])]

    # Category filter
    if "category" in filtered.columns and filters.get("categories"):
        filtered = filtered[filtered["category"].isin(filters["categories"])]

    # Customer cross-filter (for customer-level tables)
    if "customer_id" in filtered.columns and "store_id" not in filtered.columns:
        sales = st.session_state.get("data_cache", {}).get("sales_clean")
        if sales is not None:
            sf = sales.copy()
            if filters.get("stores"):
                sf = sf[sf["store_id"].isin(filters["stores"])]
            if filters.get("products"):
                sf = sf[sf["product_id"].isin(filters["products"])]
            if "date_range" in filters:
                dr = filters["date_range"]
                if isinstance(dr, (list, tuple)) and len(dr) == 2:
                    sf = sf[(sf["date"].dt.date >= dr[0]) & (sf["date"].dt.date <= dr[1])]
            allowed = sf["customer_id"].unique()
            filtered = filtered[filtered["customer_id"].isin(allowed)]

    return filtered


# ══════════════════════════════
# STORE NAME RESOLVER
# Fully dynamic — reads names from actual data, no hardcoded store names
# ══════════════════════════════
def get_store_name(store_id) -> str:
    cache = st.session_state.get("data_cache", {})
    # Priority: inventory → sales
    for ds_key in ("inventory_recommendations", "sales_clean"):
        ds = cache.get(ds_key)
        if ds is not None and "store_id" in ds.columns:
            for col in ("region", "country", "store_name", "store_type", "location"):
                if col in ds.columns:
                    match = ds[ds["store_id"] == store_id]
                    if not match.empty and pd.notna(match[col].iloc[0]):
                        return f"Store #{store_id} ({match[col].iloc[0]})"
    return f"Store #{store_id}"


# ══════════════════════════════
# CHURN RISK LEVEL (dynamic thresholds from config)
# ══════════════════════════════
def score_to_risk_level(score: float) -> str:
    """Convert a churn score [0-1] to a risk label using config thresholds."""
    for level, threshold in sorted(CHURN_RISK_THRESHOLDS.items(), key=lambda x: -x[1]):
        if score >= threshold:
            return level
    return "Low"


# ══════════════════════════════
# INVENTORY URGENCY (dynamic from config)
# ══════════════════════════════
def compute_urgency(days_of_supply: pd.Series) -> pd.Series:
    """Compute urgency score 0–URGENCY_SCORE_MAX from days_of_supply."""
    max_dos = days_of_supply.max()
    if max_dos == 0:
        return pd.Series(0, index=days_of_supply.index)
    return ((max_dos - days_of_supply) / max_dos * URGENCY_SCORE_MAX).clip(0, URGENCY_SCORE_MAX)


def is_stockout_risk(days_of_supply: pd.Series) -> pd.Series:
    """Returns boolean Series: True where days_of_supply < STOCKOUT_DAYS_CRITICAL."""
    return days_of_supply < STOCKOUT_DAYS_CRITICAL

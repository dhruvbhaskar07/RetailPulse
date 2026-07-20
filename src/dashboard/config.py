"""
RetailPulse Dashboard Configuration
=====================================
Single source of truth for ALL configurable values in the dashboard.
No hardcoded values should exist in any other dashboard file —
everything that could change should live here.
"""
from pathlib import Path
import json, os

# ── Project roots ──────────────────────────────────────────────
ROOT          = Path(__file__).parent.parent   # retailpulse/
DATA_DIR      = ROOT / "data"
REPORTS_DIR   = ROOT / "reports"
PROCESSED_DIR = DATA_DIR / "processed"

# ── Pull shared model targets from src/config.py ──────────────
try:
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    from src.config import (
        TARGET_MAPE,
        TARGET_AUC_ROC,
        N_SEGMENTS,
        SEGMENT_LABELS,
        CHURN_THRESHOLD_DAYS,
        INVENTORY_CONFIG,
        RANDOM_SEED,
    )
except ImportError:
    TARGET_MAPE             = 0.12
    TARGET_AUC_ROC          = 0.88
    N_SEGMENTS              = 7
    SEGMENT_LABELS          = {}
    CHURN_THRESHOLD_DAYS    = 90
    INVENTORY_CONFIG        = {"lead_time_days": 7, "service_level": 0.95}
    RANDOM_SEED             = 42

# ═══════════════════════════════════════════════════════════════
# AUTHENTICATION & ROLES
# ═══════════════════════════════════════════════════════════════
# Users are loaded from data/users.json if it exists,
# otherwise the DEFAULT_USERS below are used.
# Structure: { username: { "password_hash": "...", "role": "...", "name": "..." } }
USERS_FILE = DATA_DIR / "users.json"

DEFAULT_USERS = {
    "admin": {
        "password": "admin123",      # plain — will be hashed at runtime
        "role":     "admin",
        "name":     "Admin User",
    },
    "analyst": {
        "password": "analyst123",
        "role":     "analyst",
        "name":     "Analyst User",
    },
    "viewer": {
        "password": "viewer123",
        "role":     "viewer",
        "name":     "Viewer User",
    },
}

ROLE_PERMISSIONS = {
    "admin":   ["view", "export", "retrain", "import"],
    "analyst": ["view", "export", "import"],
    "viewer":  ["view"],
}

ROLE_COLORS = {
    "admin":   "background:rgba(248,113,113,.15);color:#FCA5A5;border:1px solid rgba(248,113,113,.25)",
    "analyst": "background:rgba(124,58,237,.15);color:#C4B5FD;border:1px solid rgba(124,58,237,.25)",
    "viewer":  "background:rgba(255,255,255,.06);color:#94a3b8;border:1px solid rgba(255,255,255,.08)",
}

# Roles that can import data
IMPORT_ALLOWED_ROLES = {"admin", "analyst"}

# ═══════════════════════════════════════════════════════════════
# CACHE & SESSION
# ═══════════════════════════════════════════════════════════════
CACHE_TTL_SECONDS   = int(os.getenv("RP_CACHE_TTL",  "300"))   # 5 min default
AUTO_REFRESH_MIN    = int(os.getenv("RP_REFRESH_MIN", "5"))

# ═══════════════════════════════════════════════════════════════
# FILTER DEFAULTS
# ═══════════════════════════════════════════════════════════════
DEFAULT_DATE_RANGE_DAYS = int(os.getenv("RP_DATE_DAYS", "90"))
DEFAULT_STORE_COUNT     = int(os.getenv("RP_STORES",    "5"))   # how many stores selected by default
MAX_IMPORT_ROWS         = int(os.getenv("RP_MAX_ROWS",  "5000000"))

# ═══════════════════════════════════════════════════════════════
# CHURN THRESHOLDS
# ═══════════════════════════════════════════════════════════════
CHURN_RISK_THRESHOLDS = {
    "Very High": float(os.getenv("RP_CHURN_VERY_HIGH", "0.75")),
    "High":      float(os.getenv("RP_CHURN_HIGH",      "0.50")),
    "Medium":    float(os.getenv("RP_CHURN_MEDIUM",    "0.25")),
    "Low":       0.0,
}
CHURN_HIGH_RISK_ALERT_THRESHOLD = float(os.getenv("RP_CHURN_ALERT", "0.5"))

# ═══════════════════════════════════════════════════════════════
# INVENTORY THRESHOLDS
# ═══════════════════════════════════════════════════════════════
STOCKOUT_DAYS_CRITICAL  = int(os.getenv("RP_STOCKOUT_DAYS",   "3"))
URGENCY_SCORE_MAX       = float(os.getenv("RP_URGENCY_MAX",   "200.0"))
INVENTORY_DAYS_WARNING  = int(os.getenv("RP_INV_WARNING",     "7"))

# ═══════════════════════════════════════════════════════════════
# FORECAST MODEL TARGETS
# ═══════════════════════════════════════════════════════════════
FORECAST_MAPE_TARGET    = TARGET_MAPE        # from src/config.py
ROLLING_AVG_WINDOW      = int(os.getenv("RP_ROLLING_WIN", "7"))
FORECAST_PROJECTION_DAYS = int(os.getenv("RP_PROJ_DAYS", "30"))
PRICE_ELASTICITY_FACTOR = float(os.getenv("RP_ELASTICITY", "1.5"))

# ═══════════════════════════════════════════════════════════════
# DATA QUALITY THRESHOLDS (Import page)
# ═══════════════════════════════════════════════════════════════
MISSING_DATA_HIGH_PCT   = float(os.getenv("RP_MISS_HIGH",  "10.0"))
MISSING_DATA_WARN_PCT   = float(os.getenv("RP_MISS_WARN",   "5.0"))
MAX_MISSING_PCT_IMPORT  = float(os.getenv("RP_MISS_MAX",   "50.0"))

# ═══════════════════════════════════════════════════════════════
# CHART COLORS (all charts use this — no hex values elsewhere)
# ═══════════════════════════════════════════════════════════════
PALETTE = [
    "#6366f1",   # indigo    (primary)
    "#10b981",   # emerald   (accent)
    "#f472b6",   # pink
    "#f59e0b",   # amber     (warm)
    "#818cf8",   # indigo-light
    "#38bdf8",   # sky blue  (info)
    "#a78bfa",   # violet
    "#34d399",   # emerald-light
    "#fbbf24",   # yellow
    "#f87171",   # red-light (danger)
]
RISK_COLORS = {
    "Very High": "#ef4444",
    "High":      "#f87171",
    "Medium":    "#f59e0b",
    "Low":       "#10b981",
}
SEGMENT_COLORS = [
    "#6366f1", "#10b981", "#f472b6", "#f59e0b",
    "#818cf8", "#f87171", "#34d399",
]

# ═══════════════════════════════════════════════════════════════
# NAVIGATION
# ═══════════════════════════════════════════════════════════════
# (key, emoji, label, group)  — edit here to add/remove nav items
NAV_ITEMS = [
    ("Overview",  "📊", "Overview",    "Analytics"),
    ("Forecast",  "📈", "Forecast",    "Analytics"),
    ("Segments",  "👥", "Segments",    "Analytics"),
    ("Churn",     "⚠️",  "Churn Risk",  "Analytics"),
    ("Inventory", "📦", "Inventory",   "Analytics"),
    ("Simulator", "🧪", "Simulator",   "AI Tools"),
    ("Drift",     "📡", "Drift",       "AI Tools"),
    ("Models",    "🤖", "Models",      "AI Tools"),
    ("Import",    "⬆️",  "Import Data", "Data"),
]

PAGE_SUBTITLES = {
    "Overview":  "High-level KPIs and revenue trends",
    "Forecast":  "Demand forecasting with Prophet + LSTM",
    "Segments":  "RFM-based customer segmentation",
    "Churn":     "Identify customers at risk of churning",
    "Inventory": "Stock optimization & reorder management",
    "Simulator": "Simulate campaigns and price changes",
    "Drift":     "Data drift & model degradation tracking",
    "Models":    "Model performance & accuracy metrics",
    "Import":    "Upload CSV, Excel, JSON or Parquet datasets",
}

PAGE_ICONS = {k: emoji for k, emoji, _, _ in NAV_ITEMS}

# ═══════════════════════════════════════════════════════════════
# USER PREFERENCES DEFAULTS
# ═══════════════════════════════════════════════════════════════
DEFAULT_PREFS = {
    "auto_refresh":          False,
    "refresh_interval_min":  AUTO_REFRESH_MIN,
    "theme":                 "dark",
    "default_date_range_days": DEFAULT_DATE_RANGE_DAYS,
}

# ═══════════════════════════════════════════════════════════════
# DRIFT DETECTION
# ═══════════════════════════════════════════════════════════════
DRIFT_SHARE_HIGH_THRESHOLD = float(os.getenv("RP_DRIFT_HIGH", "0.30"))
DRIFT_SOURCES = [
    ("Sales Data Drift",       "sales_data_drift.html",       "📦"),
    ("Customer Feature Drift", "customer_features_drift.html","👥"),
    ("Target Drift",           "target_drift.html",           "🎯"),
]

# ═══════════════════════════════════════════════════════════════
# IMPORT PAGE — DATASET SCHEMA TEMPLATES
# ═══════════════════════════════════════════════════════════════
# Each entry: schema_col → list of fuzzy match aliases from user files
COLUMN_ALIASES = {
    "date":              ["date", "invoice_date", "order_date", "purchase_date", "transaction_date", "dt"],
    "revenue":           ["revenue", "amount", "total", "price", "sales", "gross_sales", "net_sales", "value"],
    "transaction_id":    ["transaction_id", "invoice_no", "invoice", "order_id", "txn_id", "id"],
    "customer_id":       ["customer_id", "cust_id", "client_id", "user_id", "customer", "customerid"],
    "product_id":        ["product_id", "stock_code", "sku", "item_id", "product", "prod_id", "productid"],
    "store_id":          ["store_id", "shop_id", "country", "location", "store", "branch", "outlet_id"],
    "quantity":          ["quantity", "qty", "units", "count", "volume"],
    "category":          ["category", "product_category", "department", "type", "class", "group"],
    "total_quantity":    ["total_quantity", "qty", "quantity", "units", "total_qty", "demand"],
    "segment_label":     ["segment_label", "segment", "cluster", "group", "label", "tier"],
    "recency":           ["recency", "days_since_last", "last_order_days", "r_score"],
    "frequency":         ["frequency", "order_count", "purchase_count", "f_score", "num_orders"],
    "monetary":          ["monetary", "total_spend", "ltv", "lifetime_value", "m_score", "total_revenue"],
    "churn_risk_score":  ["churn_risk_score", "churn_score", "churn_prob", "probability", "risk_score", "score"],
    "churn_risk_level":  ["churn_risk_level", "churn_level", "risk_level", "risk_band", "risk_tier"],
    "stock_level":       ["stock_level", "stock", "inventory", "on_hand", "quantity_on_hand", "qty_on_hand"],
    "avg_daily_demand":  ["avg_daily_demand", "daily_demand", "demand", "avg_demand"],
    "urgency_score":     ["urgency_score", "urgency", "priority", "priority_score"],
    "days_of_supply":    ["days_of_supply", "dos", "days_stock", "coverage_days"],
    "recommended_order_qty": ["recommended_order_qty", "reorder_qty", "order_qty", "suggested_qty"],
    "reorder_point_calculated": ["reorder_point_calculated", "reorder_point", "rop", "reorder_level"],
    "safety_stock":      ["safety_stock", "buffer_stock", "min_stock"],
}

SCHEMA_TEMPLATES = {
    "Sales / Transactions": {
        "required": ["date", "revenue"],
        "optional": ["transaction_id", "customer_id", "product_id", "store_id", "quantity", "category"],
        "description": "Transaction-level sales data. Powers Overview, Forecast, and Simulator pages.",
        "cache_key": "sales_clean",
        "icon": "💰",
    },
    "Daily Sales Aggregated": {
        "required": ["date", "store_id", "product_id", "total_quantity"],
        "optional": ["revenue", "category"],
        "description": "Pre-aggregated daily demand per store-product pair. Powers the Forecast page.",
        "cache_key": "daily_sales",
        "icon": "📈",
    },
    "Customer Segments (RFM)": {
        "required": ["customer_id", "segment_label"],
        "optional": ["recency", "frequency", "monetary"],
        "description": f"RFM-based segmentation data. Powers Segments page. Expected: {N_SEGMENTS} clusters.",
        "cache_key": "customer_segments",
        "icon": "👥",
    },
    "Churn Scores": {
        "required": ["customer_id", "churn_risk_score"],
        "optional": ["churn_risk_level"],
        "description": (
            f"Predicted churn probability per customer (0–1 scale). "
            f"Risk bands: Very High ≥ {CHURN_RISK_THRESHOLDS['Very High']}, "
            f"High ≥ {CHURN_RISK_THRESHOLDS['High']}, "
            f"Medium ≥ {CHURN_RISK_THRESHOLDS['Medium']}. Powers Churn page."
        ),
        "cache_key": "churn_scores",
        "icon": "⚠️",
    },
    "Inventory / Stock": {
        "required": ["product_id", "stock_level"],
        "optional": [
            "store_id", "avg_daily_demand", "reorder_point_calculated",
            "recommended_order_qty", "urgency_score", "days_of_supply",
            "safety_stock", "is_stockout_risk", "is_below_reorder",
        ],
        "description": (
            f"Inventory levels and reorder recommendations. "
            f"Stockout risk = days_of_supply < {STOCKOUT_DAYS_CRITICAL}. Powers Inventory page."
        ),
        "cache_key": "inventory_recommendations",
        "icon": "📦",
    },
    "Custom (Raw Explore)": {
        "required": [],
        "optional": [],
        "description": "Any dataset for ad-hoc exploration. Stored as 'custom_raw'.",
        "cache_key": "custom_raw",
        "icon": "🔬",
    },
}

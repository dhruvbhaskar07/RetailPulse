from pathlib import Path
import os

ROOT = Path(__file__).parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
MLRUNS_DIR = ROOT / "mlruns"
REPORTS_DIR = ROOT / "reports"
MODELS_DIR = ROOT / "models"
NOTEBOOKS_DIR = ROOT / "notebooks"

for p in [DATA_RAW, DATA_PROCESSED, MLRUNS_DIR, REPORTS_DIR, MODELS_DIR]:
    p.mkdir(parents=True, exist_ok=True)

N_CUSTOMERS = 5000
N_PRODUCTS = 200
N_STORES = 50
START_DATE = "2022-01-01"
END_DATE = "2024-12-31"

TARGET_MAPE = 0.12
TARGET_AUC_ROC = 0.88
TARGET_STOCKOUT_REDUCTION = 0.30
TARGET_REVENUE_INCREASE = 0.15

N_SEGMENTS = 7
RFM_QUANTILES = 5

RANDOM_SEED = 42

MLFLOW_TRACKING_URI = f"file://{MLRUNS_DIR.resolve()}"

PROPHET_SEASONALITIES = {
    "yearly": True,
    "weekly": True,
    "daily": False,
}

LSTM_CONFIG = {
    "hidden_size": 128,
    "num_layers": 2,
    "dropout": 0.2,
    "sequence_length": 30,
    "batch_size": 64,
    "learning_rate": 1e-3,
    "epochs": 50,
    "patience": 10,
}

XGBOOST_CONFIG = {
    "n_estimators": 500,
    "max_depth": 6,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": RANDOM_SEED,
    "n_jobs": -1,
}

INVENTORY_CONFIG = {
    "service_level": 0.95,
    "lead_time_days": 7,
    "review_period_days": 7,
    "holding_cost_rate": 0.25,
    "stockout_cost_multiplier": 5.0,
}

SEGMENT_LABELS = {
    0: "Champions",
    1: "Loyal Customers",
    2: "Potential Loyalists",
    3: "New Customers",
    4: "Promising",
    5: "Need Attention",
    6: "At Risk",
}

CHURN_THRESHOLD_DAYS = 90
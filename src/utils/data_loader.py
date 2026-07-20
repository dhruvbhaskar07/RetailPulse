"""Thread-safe cached data loader for the Streamlit dashboard.

Loads processed parquet/CSV files and serialised model pickles
into a global in-memory cache with TTL invalidation.
"""

import pandas as pd
import numpy as np
import joblib
import warnings
from pathlib import Path
import threading
warnings.filterwarnings("ignore")

BASE_PATH = Path(__file__).parent.parent.parent
DATA_PROCESSED = BASE_PATH / "data" / "processed"

_cache = {}
_cache_lock = threading.Lock()

DATA_FILES = {
    "sales_clean": "sales_clean.parquet",
    "daily_sales": "daily_sales_ts.parquet",
    "customer_features": "customer_features.parquet",
    "customer_segments": "customer_segments.parquet",
    "churn_scores": "churn_scores.parquet",
    "inventory_recommendations": "inventory_recommendations.parquet",
    "forecast_results": "forecast_results.csv",
    "ensemble_forecast_results": "ensemble_forecast_results.csv",
    "churn_importance": "churn_importance.csv",
}

MODEL_FILES = {
    "churn_model": "models/churn_model.pkl",
    "segmentation_model": "models/kmeans_segmentation.pkl",
}

def _load_single_file(key: str, filename: str):
    path = DATA_PROCESSED / filename
    if not path.exists():
        return None
    try:
        if filename.endswith(".parquet"):
            return pd.read_parquet(path)
        return pd.read_csv(path)
    except Exception as e:
        print(f"  {key}: Error - {e}")
        return None

def load_all_data():
    global _cache
    with _cache_lock:
        if _cache:
            return _cache

        print("Loading processed data...")
        for key, filename in DATA_FILES.items():
            val = _load_single_file(key, filename)
            if val is not None:
                _cache[key] = val
                print(f"  {key}: {len(val):,} rows")
            else:
                print(f"  {key}: File not found")

        for key, filename in MODEL_FILES.items():
            path = DATA_PROCESSED / filename
            if path.exists():
                try:
                    _cache[key] = joblib.load(path)
                    print(f"  {key}: loaded")
                except Exception as e:
                    print(f"  {key}: Error - {e}")
            else:
                print(f"  {key}: File not found")

        print("Data loading complete!")
        return _cache

def get_data(key: str):
    with _cache_lock:
        if not _cache:
            _cache.update(load_all_data() or {})
        return _cache.get(key)

def invalidate_cache(key: str = None):
    with _cache_lock:
        if key is None:
            _cache.clear()
        else:
            _cache.pop(key, None)

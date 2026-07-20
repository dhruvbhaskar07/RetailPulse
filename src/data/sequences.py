"""Sequence data preparation for LSTM forecasting"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import warnings
warnings.filterwarnings("ignore")

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.config import DATA_PROCESSED, LSTM_CONFIG


def test_stationarity(series: pd.Series, series_name: str = "series", output_dir: Path = None):
    """Test stationarity using ADF test and KPSS test. Returns dict of results."""
    from statsmodels.tsa.stattools import adfuller, kpss
    from statsmodels.tsa.seasonal import seasonal_decompose
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    results = {}

    # ADF Test
    adf_stat, adf_pval, _, _, adf_crit, _ = adfuller(series.dropna(), maxlag=None, autolag="AIC")
    results["adf_statistic"] = float(adf_stat)
    results["adf_pvalue"] = float(adf_pval)
    results["adf_is_stationary"] = bool(adf_pval < 0.05)
    for key, val in adf_crit.items():
        results[f"adf_critical_{key}"] = float(val)

    # KPSS Test
    kpss_stat, kpss_pval, _, kpss_crit = kpss(series.dropna(), regression="c", nlags="auto")
    results["kpss_statistic"] = float(kpss_stat)
    results["kpss_pvalue"] = float(kpss_pval)
    results["kpss_is_stationary"] = bool(kpss_pval >= 0.05)
    for key, val in kpss_crit.items():
        results[f"kpss_critical_{key}"] = float(val)

    print(f"  Stationarity tests for '{series_name}':")
    print(f"    ADF: stat={adf_stat:.4f}, pval={adf_pval:.6f}, stationary={results['adf_is_stationary']}")
    print(f"    KPSS: stat={kpss_stat:.4f}, pval={kpss_pval:.6f}, stationary={results['kpss_is_stationary']}")

    # Seasonal decompose (if enough data)
    if len(series.dropna()) >= 60:
        fig, axes = plt.subplots(4, 1, figsize=(14, 10))
        decomp = seasonal_decompose(series.dropna().values, model="additive", period=7)
        axes[0].plot(decomp.observed, color="#1f77b4")
        axes[0].set_title(f"Observed — {series_name}")
        axes[1].plot(decomp.trend, color="#ff7f0e")
        axes[1].set_title("Trend")
        axes[2].plot(decomp.seasonal, color="#2ca02c")
        axes[2].set_title("Seasonal (7-day)")
        axes[3].plot(decomp.resid, color="#d62728")
        axes[3].set_title("Residual")
        plt.tight_layout()

        if output_dir:
            out = Path(output_dir)
            out.mkdir(parents=True, exist_ok=True)
            safe_name = series_name.replace("/", "_").replace(" ", "_")[:40]
            fig.savefig(out / f"decompose_{safe_name}.png", dpi=120)
        plt.close(fig)

    return results


def make_stationary(series: pd.Series, max_diffs: int = 2):
    """Apply differencing until series is stationary. Returns (transformed, n_diffs)."""
    transformed = series.copy()
    n_diffs = 0
    for _ in range(max_diffs):
        adf_pval = adfuller(transformed.dropna(), maxlag=None, autolag="AIC")[1]
        if adf_pval < 0.05:
            break
        transformed = transformed.diff()
        n_diffs += 1
    return transformed, n_diffs


def run_stationarity_checks(daily_sales: pd.DataFrame, output_dir: Path = None):
    """Run stationarity checks on all store-product combos and save report."""
    print("\nRunning stationarity tests...")
    all_results = []
    count = 0

    for (store_id, product_id), group in daily_sales.groupby(["store_id", "product_id"]):
        group = group.sort_values("date")
        series = group["total_quantity"]
        name = f"store{store_id}_prod{product_id}"

        if len(series.dropna()) < 30:
            continue

        res = test_stationarity(series, series_name=name, output_dir=output_dir)
        res["store_id"] = int(store_id)
        res["product_id"] = int(product_id)
        res["n_observations"] = len(series)
        all_results.append(res)
        count += 1

        if count >= 50:
            break

    summary = pd.DataFrame(all_results)
    pct_stationary = summary["adf_is_stationary"].mean() * 100
    print(f"\nStationarity Summary ({len(summary)} combos):")
    print(f"  ADF stationary: {pct_stationary:.1f}%")
    print(f"  KPSS stationary: {summary['kpss_is_stationary'].mean()*100:.1f}%")

    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        summary.to_csv(out / "stationarity_report.csv", index=False)
        print(f"  Report saved to {out / 'stationarity_report.csv'}")

    return summary


def create_sequences(
    data: pd.DataFrame,
    sequence_length: int = 30,
    horizon: int = 30,
    target_col: str = "total_quantity",
    feature_cols: list = None,
) -> tuple:
    """
    Create sliding window sequences for LSTM training.
    
    Args:
        data: DataFrame with columns [date, store_id, product_id, target_col, ...]
        sequence_length: Number of past time steps to use as input
        horizon: Number of future time steps to predict
        target_col: Target column name
        feature_cols: Additional feature columns to include
    
    Returns:
        X: (n_samples, sequence_length, n_features)
        y: (n_samples, horizon)
        dates: (n_samples,) - target dates for each sample
    """
    if feature_cols is None:
        feature_cols = []
    
    # Sort by date
    data = data.sort_values("date").reset_index(drop=True)
    
    n_samples = len(data) - sequence_length - horizon + 1
    if n_samples <= 0:
        return None, None, None
    
    # Prepare features
    all_cols = [target_col] + feature_cols
    feature_data = data[all_cols].values
    
    X = np.zeros((n_samples, sequence_length, len(all_cols)))
    y = np.zeros((n_samples, horizon))
    target_dates = []
    
    for i in range(n_samples):
        # Input sequence
        X[i] = feature_data[i:i + sequence_length]
        
        # Target sequence
        y[i] = data[target_col].values[i + sequence_length:i + sequence_length + horizon]
        
        # Target date (first prediction date)
        target_dates.append(data["date"].iloc[i + sequence_length])
    
    return X, y, np.array(target_dates)


def create_sequences_per_store_product(
    daily_sales: pd.DataFrame,
    sequence_length: int = 30,
    horizon: int = 30,
    target_col: str = "total_quantity",
    feature_cols: list = None,
    min_history: int = 60,
) -> dict:
    """
    Create sequences for each store-product combination.
    
    Returns dict with keys: X, y, dates, store_ids, product_ids
    """
    if feature_cols is None:
        feature_cols = []
    
    all_X = []
    all_y = []
    all_dates = []
    all_store_ids = []
    all_product_ids = []
    
    # Add temporal features if not present
    daily_sales = daily_sales.copy()
    if "day_of_week" not in daily_sales.columns:
        daily_sales["day_of_week"] = daily_sales["date"].dt.dayofweek
    if "is_weekend" not in daily_sales.columns:
        daily_sales["is_weekend"] = daily_sales["day_of_week"].isin([5, 6]).astype(int)
    if "month" not in daily_sales.columns:
        daily_sales["month"] = daily_sales["date"].dt.month
    
    # Default feature cols if not provided
    if len(feature_cols) == 0:
        feature_cols = ["day_of_week", "is_weekend", "month"]
    
    for (store_id, product_id), group in daily_sales.groupby(["store_id", "product_id"]):
        group = group.sort_values("date").reset_index(drop=True)
        
        if len(group) < min_history:
            continue
        
        # Create sequences for this combo
        X, y, dates = create_sequences(
            group,
            sequence_length=sequence_length,
            horizon=horizon,
            target_col=target_col,
            feature_cols=feature_cols,
        )
        
        if X is not None and len(X) > 0:
            all_X.append(X)
            all_y.append(y)
            all_dates.append(dates)
            all_store_ids.extend([store_id] * len(X))
            all_product_ids.extend([product_id] * len(X))
    
    if len(all_X) == 0:
        return None
    
    return {
        "X": np.vstack(all_X),
        "y": np.vstack(all_y),
        "dates": np.concatenate(all_dates),
        "store_ids": np.array(all_store_ids),
        "product_ids": np.array(all_product_ids),
    }


def prepare_lstm_data(
    daily_sales: pd.DataFrame,
    sequence_length: int = 30,
    horizon: int = 30,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    target_col: str = "total_quantity",
) -> tuple:
    """
    Prepare train/val/test splits for LSTM.
    
    Returns:
        (X_train, y_train), (X_val, y_val), (X_test, y_test), scaler_info
    """
    # Feature columns (excluding target)
    feature_cols = ["day_of_week", "is_weekend", "month"]
    
    sequences = create_sequences_per_store_product(
        daily_sales,
        sequence_length=sequence_length,
        horizon=horizon,
        target_col=target_col,
        feature_cols=feature_cols,
    )
    
    if sequences is None:
        raise ValueError("No valid sequences created")
    
    X = sequences["X"]
    y = sequences["y"]
    
    n_samples = len(X)
    
    # Temporal split (chronological)
    train_end = int(n_samples * train_ratio)
    val_end = int(n_samples * (train_ratio + val_ratio))
    
    X_train, y_train = X[:train_end], y[:train_end]
    X_val, y_val = X[train_end:val_end], y[train_end:val_end]
    X_test, y_test = X[val_end:], y[val_end:]
    
    # Scaler info for inverse transform
    scaler_info = {
        "target_col": target_col,
        "feature_cols": feature_cols,
        "sequence_length": sequence_length,
        "horizon": horizon,
    }
    
    print(f"LSTM Data Shapes:")
    print(f"  Train: X={X_train.shape}, y={y_train.shape}")
    print(f"  Val:   X={X_val.shape}, y={y_val.shape}")
    print(f"  Test:  X={X_test.shape}, y={y_test.shape}")
    
    return (X_train, y_train), (X_val, y_val), (X_test, y_test), scaler_info


def normalize_sequences(X: np.ndarray, y: np.ndarray, method: str = "standard") -> tuple:
    """
    Normalize sequences for LSTM training.
    
    Returns:
        X_norm, y_norm, scaler_params
    """
    # Flatten for computing stats
    X_flat = X.reshape(-1, X.shape[-1])
    y_flat = y.reshape(-1, 1)
    
    if method == "standard":
        X_mean = X_flat.mean(axis=0)
        X_std = X_flat.std(axis=0) + 1e-8
        y_mean = y_flat.mean()
        y_std = y_flat.std() + 1e-8
        
        X_norm = (X - X_mean) / X_std
        y_norm = (y - y_mean) / y_std
        
    elif method == "minmax":
        X_min = X_flat.min(axis=0)
        X_max = X_flat.max(axis=0)
        y_min = y_flat.min()
        y_max = y_flat.max()
        
        X_norm = (X - X_min) / (X_max - X_min + 1e-8)
        y_norm = (y - y_min) / (y_max - y_min + 1e-8)
        
        X_mean, X_std = X_min, X_max - X_min
        y_mean, y_std = y_min, y_max - y_min
    
    scaler_params = {
        "method": method,
        "X_mean": X_mean,
        "X_std": X_std,
        "y_mean": y_mean,
        "y_std": y_std,
    }
    
    return X_norm, y_norm, scaler_params


def denormalize_predictions(y_norm: np.ndarray, scaler_params: dict) -> np.ndarray:
    """Denormalize predictions back to original scale"""
    method = scaler_params["method"]
    y_mean = scaler_params["y_mean"]
    y_std = scaler_params["y_std"]
    
    if method == "standard":
        return y_norm * y_std + y_mean
    elif method == "minmax":
        return y_norm * y_std + y_mean
    return y_norm


if __name__ == "__main__":
    # Test with synthetic data
    from src.config import DATA_PROCESSED
    
    daily_sales = pd.read_parquet(DATA_PROCESSED / "daily_sales_ts.parquet")
    print(f"Daily sales shape: {daily_sales.shape}")
    
    # Prepare data
    (X_train, y_train), (X_val, y_val), (X_test, y_test), scaler_info = prepare_lstm_data(daily_sales)
    
    # Normalize
    X_train_norm, y_train_norm, scaler_params = normalize_sequences(X_train, y_train)
    X_val_norm, y_val_norm, _ = normalize_sequences(X_val, y_val)
    X_test_norm, y_test_norm, _ = normalize_sequences(X_test, y_test)
    
    print(f"Normalized shapes - Train: {X_train_norm.shape}, Val: {X_val_norm.shape}, Test: {X_test_norm.shape}")
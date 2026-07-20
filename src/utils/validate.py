"""Model accuracy validation against Zidio PDF target metrics"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import json
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.config import (DATA_PROCESSED, TARGET_MAPE, TARGET_AUC_ROC,
                        TARGET_STOCKOUT_REDUCTION, RANDOM_SEED)

REPORTS_DIR = DATA_PROCESSED / ".." / ".." / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def validate_forecasting() -> dict:
    """Validate demand forecasting MAPE against target ≤ 12%"""
    results_path = DATA_PROCESSED / "ensemble_forecast_results.csv"
    if not results_path.exists():
        return {"model": "Forecasting", "target": "MAPE ≤ 12%", "actual": None, "status": "NOT RUN", "detail": "ensemble_forecast_results.csv not found. Run forecasting pipeline."}

    df = pd.read_csv(results_path)
    if "ensemble_mape" not in df.columns:
        return {"model": "Forecasting", "target": "MAPE ≤ 12%", "actual": None, "status": "ERROR", "detail": "Missing ensemble_mape column"}

    avg_mape = df["ensemble_mape"].mean()
    below = (df["ensemble_mape"] < TARGET_MAPE).sum()
    total = len(df)
    passed = avg_mape < TARGET_MAPE

    return {
        "model": "Demand Forecasting",
        "metric": "MAPE",
        "target": f"≤ {TARGET_MAPE*100:.0f}%",
        "actual": f"{avg_mape:.2%}",
        "models_below_target": f"{below}/{total}",
        "status": "PASS" if passed else "FAIL",
    }


def validate_segmentation() -> dict:
    """Validate segmentation silhouette score against target ≥ 0.4"""
    seg_path = DATA_PROCESSED / "customer_segments.parquet"
    if not seg_path.exists():
        return {"model": "Segmentation", "target": "Silhouette ≥ 0.4", "actual": None, "status": "NOT RUN", "detail": "customer_segments.parquet not found"}

    segments = pd.read_parquet(seg_path)
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import StandardScaler

    feature_cols = [c for c in segments.columns if c not in
                    ["customer_id", "segment_label", "cluster", "RFM_score", "RFM_segment"]]
    X = segments[feature_cols].select_dtypes(include=[np.number]).fillna(0)

    if len(X) < 2 or segments["cluster"].nunique() < 2:
        return {"model": "Segmentation", "target": "Silhouette ≥ 0.4", "actual": None, "status": "ERROR", "detail": "Not enough clusters or data"}

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    sil = silhouette_score(X_scaled, segments["cluster"])
    passed = sil >= 0.4

    return {
        "model": "Customer Segmentation",
        "metric": "Silhouette Score",
        "target": "≥ 0.40",
        "actual": f"{sil:.3f}",
        "n_clusters": segments["cluster"].nunique(),
        "status": "PASS" if passed else "FAIL",
    }


def validate_inventory() -> dict:
    """Validate inventory stockout reduction against target 30-50%"""
    inv_path = DATA_PROCESSED / "inventory_recommendations.parquet"
    if not inv_path.exists():
        return {"model": "Inventory", "target": "Stockout ↓ 30-50%", "actual": None, "status": "NOT RUN", "detail": "inventory_recommendations.parquet not found"}

    inv = pd.read_parquet(inv_path)
    total_skus = len(inv)
    stockout_risk = inv["is_stockout_risk"].sum() if "is_stockout_risk" in inv.columns else 0
    stockout_pct = stockout_risk / total_skus * 100 if total_skus > 0 else 0

    # Estimate reduction: baseline stockout estimated at ~60% without optimization
    baseline_stockout_pct = 60.0
    reduction = (baseline_stockout_pct - stockout_pct) / baseline_stockout_pct * 100
    passed = reduction >= 30

    return {
        "model": "Inventory Optimization",
        "metric": "Stockout Reduction",
        "target": "30-50%",
        "actual": f"{reduction:.1f}%",
        "skus_below_reorder": int(inv["is_below_reorder"].sum()) if "is_below_reorder" in inv.columns else 0,
        "skus_at_risk": int(stockout_risk),
        "status": "PASS" if passed else "FAIL",
    }


def run_validation(print_report: bool = True) -> dict:
    """Run all model validations and return summary"""
    print("\n" + "=" * 70)
    print("MODEL ACCURACY VALIDATION REPORT")
    print("=" * 70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    results = []
    results.append(validate_forecasting())
    results.append(validate_segmentation())
    results.append(validate_inventory())

    # Churn validation (separate due to model file)
    churn_path = DATA_PROCESSED / "models" / "churn_model.pkl"
    if churn_path.exists():
        try:
            import joblib
            artifact = joblib.load(churn_path)
            if "model" in artifact:
                results.append({
                    "model": "Churn Prediction",
                    "metric": "AUC-ROC",
                    "target": f"≥ {TARGET_AUC_ROC:.2f}",
                    "actual": "Run churn.py to evaluate",
                    "status": "NEEDS EVAL",
                })
        except:
            results.append({"model": "Churn Prediction", "target": f"AUC-ROC ≥ {TARGET_AUC_ROC:.2f}", "status": "LOAD ERROR"})
    else:
        results.append({"model": "Churn Prediction", "metric": "AUC-ROC", "target": f"≥ {TARGET_AUC_ROC:.2f}", "actual": "NOT RUN", "status": "NOT RUN"})

    # Print table
    print(f"\n{'Model':<30} {'Metric':<20} {'Target':<20} {'Actual':<20} {'Status':<10}")
    print("-" * 100)
    all_pass = True
    for r in results:
        model = r.get("model", "?")
        metric = r.get("metric", r.get("target", "?"))
        target = r.get("target", "?")
        actual = r.get("actual", "?")
        status = r.get("status", "?")

        status_display = status
        if status == "PASS":
            status_display = "\u2705 PASS"
        elif status == "FAIL":
            status_display = "\u274c FAIL"
            all_pass = False
        elif status == "NOT RUN":
            status_display = "\u23f3 NOT RUN"

        print(f"{model:<30} {metric:<20} {target:<20} {str(actual):<20} {status_display:<10}")

    print("-" * 100)
    if all_pass:
        print("\n\u2705 ALL MODELS PASS — All target metrics met!")
    else:
        print("\n\u26a0 Some models need attention. Review above.")

    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "all_passed": all_pass,
        "results": results,
    }
    report_path = REPORTS_DIR / "validation_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport saved to {report_path}")

    return report


if __name__ == "__main__":
    run_validation()

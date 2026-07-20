"""Prefect Flows for Daily Retraining and Drift Detection"""
from prefect import flow, task, get_run_logger
from prefect.task_runners import SequentialTaskRunner
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import mlflow
import subprocess

sys.path.append(str(Path(__file__).parent.parent))
from src.config import DATA_PROCESSED, MLRUNS_DIR, RANDOM_SEED
from src.models.forecasting import run_forecasting_pipeline
from src.models.churn import run_churn_pipeline
from src.models.segmentation import run_segmentation
from src.models.inventory import run_inventory_pipeline
from src.utils.drift import run_drift_detection_pipeline, check_drift_threshold
from src.utils.mlflow_utils import promote_if_better, get_production_model


# ============================================================
# TASKS
# ============================================================

@task(retries=2, retry_delay_seconds=60)
def load_incremental_data(last_run_date: str = None) -> pd.DataFrame:
    """Load new sales data since last run"""
    logger = get_run_logger()
    
    # In production, this would query the data warehouse
    # For now, we'll simulate by checking for new data
    logger.info("Loading incremental sales data...")
    
    # Placeholder - in real implementation, query DB for new data
    # SELECT * FROM sales WHERE date > last_run_date
    
    return pd.DataFrame()  # Return new data


@task
def retrain_forecasting_models():
    """Retrain Prophet + LSTM ensemble models"""
    logger = get_run_logger()
    logger.info("Starting forecasting model retraining...")
    
    # Run the forecasting pipeline
    results = run_forecasting_pipeline()
    
    if len(results) > 0:
        avg_mape = results['ensemble_mape'].mean()
        logger.info(f"Retrained {len(results)} models. Avg MAPE: {avg_mape:.4f}")
        
        # Check if any model beats production
        for _, row in results.iterrows():
            # Would compare with production model here
            pass
    
    return results


@task
def retrain_churn_model():
    """Retrain XGBoost churn model"""
    logger = get_run_logger()
    logger.info("Starting churn model retraining...")
    
    results = run_churn_pipeline()
    
    logger.info("Churn model retraining complete")
    return results


@task
def retrain_segmentation():
    """Retrain customer segmentation"""
    logger = get_run_logger()
    logger.info("Starting segmentation retraining...")
    
    results = run_segmentation()
    
    logger.info("Segmentation retraining complete")
    return results


@task
def retrain_inventory():
    """Retrain inventory optimization"""
    logger = get_run_logger()
    logger.info("Starting inventory optimization...")
    
    results = run_inventory_pipeline()
    
    logger.info("Inventory optimization complete")
    return results


@task
def run_drift_checks():
    """Run Evidently AI drift detection"""
    logger = get_run_logger()
    logger.info("Running drift detection...")
    
    drift_results = run_drift_detection_pipeline()
    
    # Check if any drift exceeds threshold
    alerts = []
    for key, result in drift_results.items():
        if key != "timestamp" and isinstance(result, dict):
            if check_drift_threshold(result, threshold=0.3):
                alerts.append(f"Drift detected in {key}: {result.get('drift_share', 0):.2%}")
    
    if alerts:
        logger.warning(f"DRIFT ALERTS: {alerts}")
    else:
        logger.info("No significant drift detected")
    
    return {"drift_results": drift_results, "alerts": alerts}


@task
def promote_champion_models():
    """Compare challenger models with production and promote if better"""
    logger = get_run_logger()
    logger.info("Checking for model promotions...")
    
    # This would load test data and compare
    # For now, placeholder
    promotions = []
    
    # Example logic:
    # forecast_results = load_latest_forecast_results()
    # for combo in forecast_results:
    #     promoted = promote_if_better("forecasting", combo["version"], X_test, y_test)
    #     if promoted:
    #         promotions.append(f"Forecasting {combo['store_id']}_{combo['product_id']}")
    
    logger.info(f"Promotions completed: {promotions}")
    return promotions


@task
def update_feature_store():
    """Update feature store with latest computed features"""
    logger = get_run_logger()
    logger.info("Updating feature store...")
    
    # In production, this would write to Feast/feature store
    logger.info("Feature store updated")
    return True


@task
def send_notification(message: str, level: str = "info"):
    """Send notification (Slack, email, etc.)"""
    logger = get_run_logger()
    if level == "warning":
        logger.warning(message)
    elif level == "error":
        logger.error(message)
    else:
        logger.info(message)
    
    # In production: send to Slack webhook, email, etc.
    # requests.post(slack_webhook, json={"text": message})


# ============================================================
# FLOWS
# ============================================================

@flow(name="daily-retraining", task_runner=SequentialTaskRunner())
def daily_retraining_flow():
    """
    Daily retraining flow - runs at 2:00 AM UTC
    
    Steps:
    1. Load incremental data
    2. Run drift detection
    3. Retrain forecasting models (if drift or scheduled)
    4. Retrain churn model (weekly on Monday)
    5. Retrain segmentation (monthly on 1st)
    6. Retrain inventory (daily)
    5. Promote champion models
    6. Update feature store
    7. Send notifications
    """
    logger = get_run_logger()
    logger.info("Starting daily retraining flow")
    
    # 1. Load new data
    new_data = load_incremental_data()
    
    # 2. Drift detection (always run)
    drift_results = run_drift_checks()
    
    # 3. Determine what needs retraining
    needs_forecast_retrain = len(drift_results.get("alerts", [])) > 0 or True  # Daily for now
    needs_churn_retrain = pd.Timestamp.now().dayofweek == 0  # Monday
    needs_segment_retrain = pd.Timestamp.now().day == 1  # 1st of month
    
    results = {}
    
    # 4. Retrain forecasting (daily if drift, else weekly)
    if needs_forecast_retrain:
        results["forecasting"] = retrain_forecasting_models()
    else:
        logger.info("Skipping forecasting retraining")
    
    # 5. Retrain churn (weekly)
    if needs_churn_retrain:
        results["churn"] = retrain_churn_model()
    else:
        logger.info("Skipping churn retraining (not Monday)")
    
    # 6. Retrain segmentation (monthly)
    if needs_segment_retrain:
        results["segmentation"] = retrain_segmentation()
    else:
        logger.info("Skipping segmentation retraining (not 1st of month)")
    
    # 7. Inventory (daily)
    results["inventory"] = retrain_inventory()
    
    # 8. Promote champions
    promotions = promote_champion_models()
    
    # 9. Update feature store
    update_feature_store()
    
    # 10. Notify
    summary = f"""
    Daily Retraining Complete:
    - Forecasting: {'Retrained' if needs_forecast_retrain else 'Skipped'}
    - Churn: {'Retrained' if needs_churn_retrain else 'Skipped'}
    - Segmentation: {'Retrained' if needs_segment_retrain else 'Skipped'}
    - Inventory: Retrained
    - Promotions: {promotions}
    - Drift Alerts: {len(drift_results.get('alerts', []))}
    """
    send_notification(summary)
    
    logger.info("Daily retraining flow completed")
    return results


@flow(name="drift-monitoring", task_runner=SequentialTaskRunner())
def drift_monitoring_flow():
    """
    Drift monitoring flow - runs hourly
    
    Lightweight drift checks on key features
    """
    logger = get_run_logger()
    logger.info("Running drift monitoring")
    
    drift_results = run_drift_checks()
    
    if drift_results.get("alerts"):
        send_notification(
            f"Drift Alert: {drift_results['alerts']}", 
            level="warning"
        )
    
    return drift_results


@flow(name="weekly-full-retrain", task_runner=SequentialTaskRunner())
def weekly_full_retrain_flow():
    """
    Weekly full retraining - runs Sunday night
    
    Full retraining of all models with expanded data
    """
    logger = get_run_logger()
    logger.info("Starting weekly full retraining")
    
    # Full retraining with all available data
    results = {
        "forecasting": retrain_forecasting_models(),
        "churn": retrain_churn_model(),
        "segmentation": retrain_segmentation(),
        "inventory": retrain_inventory(),
    }
    
    # Promote champions
    promote_champion_models()
    
    # Update feature store
    update_feature_store()
    
    send_notification("Weekly full retraining completed", "info")
    
    return results


@flow(name="manual-retrain", task_runner=SequentialTaskRunner())
def manual_retrain_flow(
    models: list = ["forecasting", "churn", "segmentation", "inventory"],
    force_promotion: bool = False
):
    """
    Manual retraining trigger for on-demand retraining
    
    Args:
        models: List of models to retrain
        force_promotion: Skip comparison, promote directly
    """
    logger = get_run_logger()
    logger.info(f"Manual retraining triggered for: {models}")
    
    results = {}
    
    if "forecasting" in models:
        results["forecasting"] = retrain_forecasting_models()
    if "churn" in models:
        results["churn"] = retrain_churn_model()
    if "segmentation" in models:
        results["segmentation"] = retrain_segmentation()
    if "inventory" in models:
        results["inventory"] = retrain_inventory()
    
    if force_promotion:
        promote_champion_models()
    
    send_notification(f"Manual retraining completed for {models}", "info")
    
    return results


# ============================================================
# DEPLOYMENT HELPERS
# ============================================================

def create_deployments():
    """Create Prefect deployments for all flows"""
    
    # Daily retraining at 2:00 AM UTC
    daily_deployment = Deployment.build_from_flow(
        flow=daily_retraining_flow,
        name="daily-retraining",
        schedule=CronSchedule(cron="0 2 * * *", timezone="UTC"),
        work_queue_name="ml-training",
        tags=["daily", "retraining", "production"]
    )
    
    # Drift monitoring hourly
    drift_deployment = Deployment.build_from_flow(
        flow=drift_monitoring_flow,
        name="drift-monitoring",
        schedule=CronSchedule(cron="0 * * * *", timezone="UTC"),
        work_queue_name="ml-monitoring",
        tags=["hourly", "drift", "monitoring"]
    )
    
    # Weekly full retrain Sunday 3:00 AM UTC
    weekly_deployment = Deployment.build_from_flow(
        flow=weekly_full_retrain_flow,
        name="weekly-full-retrain",
        schedule=CronSchedule(cron="0 3 * * 0", timezone="UTC"),
        work_queue_name="ml-training",
        tags=["weekly", "retraining", "full"]
    )
    
    return [daily_deployment, drift_deployment, weekly_deployment]


def apply_deployments():
    """Apply all deployments to Prefect server"""
    deployments = create_deployments()
    for dep in deployments:
        dep.apply()
        print(f"Applied deployment: {dep.name}")


if __name__ == "__main__":
    # For testing
    import pandas as pd
    
    # Test daily flow
    print("Testing daily retraining flow...")
    # result = daily_retraining_flow()
    
    # Create deployments
    # apply_deployments()
    
    print("Prefect flows defined. Use 'prefect deploy' to create deployments.")
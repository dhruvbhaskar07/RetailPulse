"""MLflow Utilities for Model Registry, Versioning, and Promotion"""
import mlflow
import mlflow.sklearn
import mlflow.xgboost
import mlflow.pytorch
import mlflow.pyfunc
from mlflow.tracking import MlflowClient
from mlflow.entities import ViewType
from pathlib import Path
import sys
import json
import warnings
warnings.filterwarnings("ignore")

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.config import MLRUNS_DIR

# Use SQLite for MLflow on Windows
mlflow_db = MLRUNS_DIR / "mlflow.db"
mlflow.set_tracking_uri(f"sqlite:///{mlflow_db}")

client = MlflowClient()


def get_experiment_id(experiment_name: str) -> str:
    """Get or create experiment ID"""
    exp = client.get_experiment_by_name(experiment_name)
    if exp:
        return exp.experiment_id
    return client.create_experiment(experiment_name)


def log_model_with_signature(model, model_name: str, X_sample: pd.DataFrame = None, 
                              flavor: str = "sklearn", **kwargs):
    """
    Log model with input signature for better serving.
    
    Args:
        model: Trained model object
        model_name: Name for the model in MLflow
        X_sample: Sample input for signature inference
        flavor: MLflow flavor ("sklearn", "xgboost", "pytorch", "pyfunc")
    """
    from mlflow.models.signature import infer_signature
    
    if X_sample is not None:
        # Get predictions for signature
        if hasattr(model, "predict_proba"):
            y_sample = model.predict_proba(X_sample)
        else:
            y_sample = model.predict(X_sample)
        signature = infer_signature(X_sample, y_sample)
    else:
        signature = None
    
    if flavor == "sklearn":
        mlflow.sklearn.log_model(model, model_name, signature=signature, **kwargs)
    elif flavor == "xgboost":
        mlflow.xgboost.log_model(model, model_name, signature=signature, **kwargs)
    elif flavor == "pytorch":
        mlflow.pytorch.log_model(model, model_name, signature=signature, **kwargs)
    elif flavor == "pyfunc":
        mlflow.pyfunc.log_model(model_name, python_model=model, signature=signature, **kwargs)
    else:
        raise ValueError(f"Unsupported flavor: {flavor}")
    
    return signature


def register_model(model_uri: str, model_name: str) -> int:
    """Register model in MLflow Model Registry"""
    model_version = mlflow.register_model(model_uri, model_name)
    print(f"Registered model '{model_name}' version {model_version.version}")
    return model_version.version


def promote_model(model_name: str, version: int, stage: str = "Production", 
                  archive_existing: bool = True) -> None:
    """
    Promote model version to specified stage.
    
    Args:
        model_name: Name of registered model
        version: Model version number
        stage: Target stage ("Staging", "Production", "Archived")
        archive_existing: Whether to archive current production model
    """
    client.transition_model_version_stage(
        name=model_name,
        version=version,
        stage=stage,
        archive_existing_versions=archive_existing
    )
    print(f"Promoted {model_name} v{version} to {stage}")


def get_production_model(model_name: str):
    """Get the current production model"""
    try:
        model_version = client.get_latest_versions(model_name, stages=["Production"])[0]
        model_uri = f"models:/{model_name}/{model_version.version}"
        model = mlflow.pyfunc.load_model(model_uri)
        print(f"Loaded {model_name} v{model_version.version} from Production")
        return model, model_version.version
    except IndexError:
        print(f"No production model found for {model_name}")
        return None, None


def get_staging_model(model_name: str):
    """Get the current staging model"""
    try:
        model_version = client.get_latest_versions(model_name, stages=["Staging"])[0]
        model_uri = f"models:/{model_name}/{model_version.version}"
        model = mlflow.pyfunc.load_model(model_uri)
        return model, model_version.version
    except IndexError:
        return None, None


def get_model_by_alias(model_name: str, alias: str = "champion"):
    """Get model by alias (e.g., 'champion', 'challenger')"""
    try:
        model_version = client.get_model_version_by_alias(model_name, alias)
        model_uri = f"models:/{model_name}@{alias}"
        model = mlflow.pyfunc.load_model(model_uri)
        return model, model_version.version
    except Exception:
        return None, None


def set_model_alias(model_name: str, version: int, alias: str) -> None:
    """Set alias for model version (e.g., 'champion', 'challenger')"""
    client.set_registered_model_alias(model_name, alias, version)
    print(f"Set alias '{alias}' for {model_name} v{version}")


def archive_old_versions(model_name: str, keep: int = 3) -> None:
    """Archive all but the latest N versions"""
    versions = client.search_model_versions(f"name='{model_name}'")
    versions = sorted(versions, key=lambda v: int(v.version), reverse=True)
    
    for v in versions[keep:]:
        if v.current_stage != "Archived":
            client.transition_model_version_stage(
                name=model_name,
                version=v.version,
                stage="Archived"
            )
            print(f"Archived {model_name} v{v.version}")


def compare_models(model_name: str, version_a: int, version_b: int, 
                   X_test: pd.DataFrame, y_test: pd.Series, 
                   metric_fn=None) -> dict:
    """
    Compare two model versions on test data.
    
    Args:
        model_name: Registered model name
        version_a: First version to compare
        version_b: Second version to compare
        X_test: Test features
        y_test: Test targets
        metric_fn: Custom metric function (default: MAPE for regression, AUC for classification)
    
    Returns:
        Dict with comparison results
    """
    # Load both models
    model_a = mlflow.pyfunc.load_model(f"models:/{model_name}/{version_a}")
    model_b = mlflow.pyfunc.load_model(f"models:/{model_name}/{version_b}")
    
    # Predict
    preds_a = model_a.predict(X_test)
    preds_b = model_b.predict(X_test)
    
    # Default metrics
    if metric_fn is None:
        # Check if classification or regression
        unique_targets = y_test.nunique()
        if unique_targets <= 10 and y_test.dtype in ["int64", "object"]:
            # Classification
            from sklearn.metrics import roc_auc_score, accuracy_score
            metric_fn = lambda y_true, y_pred: roc_auc_score(y_true, y_pred)
            name = "AUC"
        else:
            # Regression
            from sklearn.metrics import mean_absolute_percentage_error
            metric_fn = lambda y_true, y_pred: mean_absolute_percentage_error(y_true, y_pred)
            name = "MAPE"
    
    score_a = metric_fn(y_test, preds_a)
    score_b = metric_fn(y_test, preds_b)
    
    return {
        "model_name": model_name,
        "version_a": version_a,
        "version_b": version_b,
        f"{name}_a": score_a,
        f"{name}_b": score_b,
        "winner": "a" if score_a < score_b else "b" if name == "MAPE" else "a" if score_a > score_b else "b",
        "improvement": abs(score_a - score_b) / max(score_a, score_b) * 100
    }


def promote_if_better(model_name: str, challenger_version: int, 
                       X_test: pd.DataFrame, y_test: pd.Series,
                       metric_fn=None) -> bool:
    """
    Compare challenger with production model and promote if better.
    
    Returns:
        True if challenger was promoted
    """
    prod_model, prod_version = get_production_model(model_name)
    
    if prod_model is None:
        # No production model, promote challenger to production
        promote_model(model_name, challenger_version, "Production")
        return True
    
    # Compare
    comparison = compare_models(model_name, prod_version, challenger_version, 
                                X_test, y_test, metric_fn)
    
    print(f"Comparison: {model_name} v{prod_version} vs v{challenger_version}")
    print(f"  Production: {comparison.get('metric_a', 'N/A')}")
    print(f"  Challenger: {comparison.get('metric_b', 'N/A')}")
    print(f"  Winner: {comparison['winner']}")
    print(f"  Improvement: {comparison['improvement']:.2f}%")
    
    if comparison['winner'] == 'b':  # Challenger won
        promote_model(model_name, challenger_version, "Production")
        # Archive old production
        client.transition_model_version_stage(
            name=model_name,
            version=prod_version,
            stage="Archived"
        )
        print(f"Promoted challenger v{challenger_version} to Production")
        return True
    
    print(f"Keeping current production v{prod_version}")
    return False


def log_ab_test(model_name: str, version_a: int, version_b: int,
                traffic_split: float = 0.1) -> str:
    """
    Log A/B test configuration.
    
    Returns:
        Test ID for tracking
    """
    import uuid
    test_id = str(uuid.uuid4())[:8]
    
    test_info = {
        "test_id": test_id,
        "model_name": model_name,
        "version_a": version_a,
        "version_b": version_b,
        "traffic_split": traffic_split,
        "status": "running"
    }
    
    # Log as MLflow run
    with mlflow.start_run(run_name=f"ab_test_{test_id}"):
        mlflow.log_params(test_info)
    
    return test_id


def complete_ab_test(test_id: str, winner: str, metrics: dict) -> None:
    """Mark A/B test as complete with results"""
    with mlflow.start_run(run_name=f"ab_test_{test_id}_complete"):
        mlflow.log_param("test_id", test_id)
        mlflow.log_param("winner", winner)
        mlflow.log_metrics(metrics)


def get_model_lineage(model_name: str, version: int) -> dict:
    """Get model lineage: training data, params, metrics, artifacts"""
    model_version = client.get_model_version(model_name, version)
    run = client.get_run(model_version.run_id)
    
    return {
        "model_name": model_name,
        "version": version,
        "run_id": model_version.run_id,
        "stage": model_version.current_stage,
        "params": run.data.params,
        "metrics": run.data.metrics,
        "tags": run.data.tags,
        "artifact_uri": run.info.artifact_uri,
    }


def log_model_card(model_name: str, version: int, 
                   description: str = None,
                   use_cases: list = None,
                   limitations: list = None,
                   ethical_considerations: list = None) -> None:
    """
    Log model card (documentation) as artifact.
    
    Follows Google's Model Card Toolkit format.
    """
    import yaml
    
    card = {
        "model_name": model_name,
        "version": version,
        "description": description or "",
        "use_cases": use_cases or [],
        "limitations": limitations or [],
        "ethical_considerations": ethical_considerations or [],
        "generated_at": pd.Timestamp.now().isoformat(),
    }
    
    # Save as YAML
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(card, f)
        card_path = f.name
    
    # Log as artifact
    mlflow.log_artifact(card_path, "model_card")
    print(f"Logged model card for {model_name} v{version}")


if __name__ == "__main__":
    # Example usage
    print("MLflow Utilities Module")
    print("Available functions:")
    print("  - log_model_with_signature()")
    print("  - register_model()")
    print("  - promote_model()")
    print("  - get_production_model()")
    print("  - compare_models()")
    print("  - promote_if_better()")
    print("  - log_ab_test()")
    print("  - get_model_lineage()")
    print("  - log_model_card()")
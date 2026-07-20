"""Admin endpoints — retrain models, audit logs, model status."""

from fastapi import APIRouter, Depends, Query, Request
from typing import Optional
import threading
import subprocess
from datetime import datetime
from pathlib import Path

from src.api.auth.dependencies import get_current_user, require_role, rate_limit_by_user
from src.api.schemas.response import AuditLogResponse, AuditLogEntry, ModelStatusResponse
from src.api.services.audit_service import get_audit_logs, get_audit_stats, log_audit_entry

router = APIRouter(tags=["admin"])

models_ref = {}
model_versions_ref = {}
retrain_status = {
    "running": False, "progress": "", "step": "",
    "started_at": None, "finished_at": None,
    "success": False, "error": None,
}
retrain_lock = threading.Lock()

def get_models_ref():
    return models_ref

def update_models_ref(models: dict, versions: dict):
    models_ref.clear()
    models_ref.update(models)
    model_versions_ref.clear()
    model_versions_ref.update(versions)

@router.get("/models/status", response_model=list[ModelStatusResponse])
async def model_status(user: dict = Depends(get_current_user)):
    status_list = []
    for model_name, version in model_versions_ref.items():
        status_list.append(ModelStatusResponse(
            model=model_name,
            version=version,
            status="loaded" if model_name in models_ref else "not_loaded",
        ))
    return status_list

@router.get("/models/{model_name}/version")
async def get_model_version(model_name: str, user: dict = Depends(get_current_user)):
    if model_name not in model_versions_ref:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Model not found")
    return {"model": model_name, "version": model_versions_ref[model_name]}

@router.post("/models/retrain")
async def trigger_retrain(
    request: Request,
    model_name: str = Query(default="all"),
    user: dict = Depends(get_current_user),
):
    require_role(["admin"])
    rate_limit_by_user(request, max_requests=5)

    global retrain_status
    with retrain_lock:
        if retrain_status["running"]:
            from fastapi import HTTPException
            raise HTTPException(status_code=409, detail="Retraining already in progress")

    def _run_pipeline():
        python_exe = __import__("sys").executable
        cwd = Path(__file__).parent.parent.parent.parent
        steps = [
            ("etl", "ETL Pipeline", ["-m", "src.data.etl"]),
            ("segmentation", "Segmentation", ["-m", "src.models.segmentation"]),
            ("churn", "Churn", ["-m", "src.models.churn"]),
            ("inventory", "Inventory", ["-m", "src.models.inventory"]),
            ("forecasting", "Forecasting", ["-m", "src.models.forecasting"]),
        ]
        for step_id, step_name, args in steps:
            with retrain_lock:
                retrain_status["step"] = step_id
                retrain_status["progress"] = f"Running {step_name}..."
            try:
                subprocess.run(
                    [python_exe] + args, cwd=str(cwd),
                    capture_output=True, text=True, timeout=3600,
                )
            except Exception as e:
                with retrain_lock:
                    retrain_status["error"] = str(e)
                    retrain_status["running"] = False
                    retrain_status["success"] = False
                return
        with retrain_lock:
            retrain_status["progress"] = "All models retrained"
            retrain_status["running"] = False
            retrain_status["success"] = True

    with retrain_lock:
        retrain_status["running"] = True
        retrain_status["progress"] = "Starting..."
        retrain_status["started_at"] = datetime.utcnow().isoformat()
        retrain_status["error"] = None
        retrain_status["success"] = False

    thread = threading.Thread(target=_run_pipeline, daemon=True)
    thread.start()

    return {"message": f"Retraining started for {model_name}", "status": "running"}

@router.get("/models/retrain/status")
async def get_retrain_status_endpoint(user: dict = Depends(get_current_user)):
    with retrain_lock:
        return {k: v for k, v in retrain_status.items()}

@router.get("/admin/audit-logs", response_model=AuditLogResponse)
async def get_audit_logs_endpoint(
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    require_role(["admin"])
    logs = get_audit_logs(limit=limit, offset=offset, user_id=user_id, action=action)
    entries = [AuditLogEntry(**log) for log in logs]
    return AuditLogResponse(total=len(logs), entries=entries, page=(offset // limit) + 1, page_size=limit)

@router.get("/admin/audit-logs/stats")
async def get_audit_stats_endpoint(user: dict = Depends(get_current_user)):
    require_role(["admin"])
    return get_audit_stats()

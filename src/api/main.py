"""FastAPI application entry point.

Loads trained models, initialises service layer, registers routes,
and exposes health-check and Prometheus metric endpoints.
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager

sys.path.append(str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import pandas as pd
import joblib

from src.api.config import CORS_ORIGINS, DATA_PROCESSED
from src.api.auth.router import router as auth_router, setup_default_users
from src.api.routers.forecast import router as forecast_router, init_forecast_service
from src.api.routers.churn import router as churn_router, init_churn_service
from src.api.routers.segments import router as segments_router, init_segment_service
from src.api.routers.inventory import router as inventory_router, init_inventory_service
from src.api.routers.simulator import router as simulator_router, init_simulator_service
from src.api.routers.admin import router as admin_router, update_models_ref
from src.api.middleware import metrics_middleware, audit_middleware
from src.api.services.forecast_service import ForecastService
from src.api.services.audit_service import init_audit_db
from src.api.config import REDIS_URL

models = {}
data = {}
model_versions = {}
_forecast_service = ForecastService()

def load_models():
    global models, data, model_versions
    try:
        seg_path = DATA_PROCESSED / "models" / "kmeans_segmentation.pkl"
        if seg_path.exists():
            models["segmentation"] = joblib.load(seg_path)
            model_versions["segmentation"] = "1.0"

        churn_path = DATA_PROCESSED / "models" / "churn_model.pkl"
        if churn_path.exists():
            artifact = joblib.load(churn_path)
            models["churn"] = artifact
            model_versions["churn"] = "1.0"

        data_files = {
            "customer_features": "customer_features.parquet",
            "customer_segments": "customer_segments.parquet",
            "churn_scores": "churn_scores.parquet",
            "inventory_recommendations": "inventory_recommendations.parquet",
            "forecast_results": "forecast_results.csv",
            "daily_sales": "daily_sales_ts.parquet",
            "ensemble_forecast_results": "ensemble_forecast_results.csv",
        }
        for key, filename in data_files.items():
            path = DATA_PROCESSED / filename
            if path.exists():
                if filename.endswith(".parquet"):
                    data[key] = pd.read_parquet(path)
                else:
                    data[key] = pd.read_csv(path)

        daily_sales = data.get("daily_sales")
        ensemble_results = data.get("ensemble_forecast_results")
        init_forecast_service(daily_sales, ensemble_results)
        init_simulator_service(_forecast_service)

        churn_scores = data.get("churn_scores")
        customer_features = data.get("customer_features")
        churn_model_artifact = models.get("churn")
        init_churn_service(churn_scores, customer_features, churn_model_artifact)

        segments = data.get("customer_segments")
        init_segment_service(segments)

        inventory = data.get("inventory_recommendations")
        init_inventory_service(inventory)

        update_models_ref(models, model_versions)

        print(f"Loaded models: {list(models.keys())}")
        print(f"Loaded data: {list(data.keys())}")
    except Exception as e:
        print(f"Warning: Could not load all models: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_default_users()
    init_audit_db(DATA_PROCESSED / "audit.db")
    load_models()
    yield

app = FastAPI(
    title="RetailPulse API",
    description="AI-Powered Customer Analytics & Demand Forecasting Platform",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(metrics_middleware)
app.middleware("http")(audit_middleware)

app.include_router(auth_router)
app.include_router(forecast_router)
app.include_router(churn_router)
app.include_router(segments_router)
app.include_router(inventory_router)
app.include_router(simulator_router)
app.include_router(admin_router)

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "models_loaded": list(models.keys()),
        "data_loaded": list(data.keys()),
        "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
    }

@app.get("/health/ready")
async def readiness():
    checks = {"models": len(models) > 0, "data": len(data) > 0}
    return {"ready": all(checks.values()), "checks": checks}

@app.get("/health/live")
async def liveness():
    return {"alive": True}

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/")
async def root():
    return {
        "name": "RetailPulse API",
        "version": "2.0.0",
        "description": "AI-Powered Customer Analytics & Demand Forecasting Platform",
        "docs_url": "/docs",
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

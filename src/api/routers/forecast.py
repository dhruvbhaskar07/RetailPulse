"""Demand forecasting endpoint — returns prophet/LSTM ensemble predictions."""

from fastapi import APIRouter, Depends, Request
from src.api.auth.dependencies import get_current_user, rate_limit_by_user
from src.api.schemas.request import ForecastRequest
from src.api.schemas.response import ForecastResponse
from src.api.services.forecast_service import ForecastService
from src.api.services.audit_service import log_audit_entry

router = APIRouter(tags=["forecast"])
forecast_service = ForecastService()

def init_forecast_service(daily_sales, ensemble_results):
    forecast_service.load_data(daily_sales, ensemble_results)

@router.post("/forecast", response_model=ForecastResponse)
async def forecast_demand(
    request: Request,
    forecast_request: ForecastRequest,
    user: dict = Depends(get_current_user),
):
    rate_limit_by_user(request, max_requests=30)
    result = forecast_service.get_forecast(
        forecast_request.store_id,
        forecast_request.product_id,
        forecast_request.horizon,
    )
    log_audit_entry(user.get("sub", "unknown"), "user", "FORECAST",
                    "/forecast", "POST", request.client.host if request.client else "unknown", 200, 0)
    return result

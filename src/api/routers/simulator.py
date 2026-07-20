"""What-if scenario simulator endpoint — promo/price impact analysis."""

from fastapi import APIRouter, Depends, Request
from src.api.auth.dependencies import get_current_user, rate_limit_by_user
from src.api.schemas.request import WhatIfRequest
from src.api.schemas.response import WhatIfResponse
from src.api.services.forecast_service import ForecastService

router = APIRouter(tags=["simulator"])
_forecast_service_ref = None

def init_simulator_service(forecast_service: ForecastService):
    global _forecast_service_ref
    _forecast_service_ref = forecast_service

@router.post("/what-if", response_model=WhatIfResponse)
async def what_if_analysis(
    request: Request,
    whatif_request: WhatIfRequest,
    user: dict = Depends(get_current_user),
):
    rate_limit_by_user(request, max_requests=20)
    if _forecast_service_ref is None:
        raise ValueError("Service not initialized")
    result = _forecast_service_ref.get_what_if(
        whatif_request.store_id,
        whatif_request.product_id,
        whatif_request.promo_lift_pct,
        whatif_request.price_change_pct,
    )
    return result

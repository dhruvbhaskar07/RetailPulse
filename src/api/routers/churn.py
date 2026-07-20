"""Churn prediction endpoint — XGBoost + SHAP explainability."""

from fastapi import APIRouter, Depends, Request
from src.api.auth.dependencies import get_current_user, rate_limit_by_user
from src.api.schemas.request import ChurnRequest
from src.api.schemas.response import ChurnResponse
from src.api.services.churn_service import ChurnService

router = APIRouter(tags=["churn"])
churn_service = ChurnService()

def init_churn_service(churn_scores, customer_features=None, model_artifact=None):
    churn_service.load_data(churn_scores, customer_features, model_artifact)

@router.post("/churn-risk", response_model=ChurnResponse)
async def churn_risk(
    request: Request,
    churn_request: ChurnRequest,
    user: dict = Depends(get_current_user),
):
    rate_limit_by_user(request, max_requests=30)
    result = churn_service.get_churn_risk(churn_request.customer_id)
    return result

@router.get("/churn/summary")
async def churn_summary(
    request: Request,
    user: dict = Depends(get_current_user),
):
    rate_limit_by_user(request, max_requests=60)
    return churn_service.get_summary()

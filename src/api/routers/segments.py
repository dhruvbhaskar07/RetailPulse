"""Customer segmentation endpoint — RFM + K-Means cluster assignment."""

from fastapi import APIRouter, Depends, Request
from src.api.auth.dependencies import get_current_user, rate_limit_by_user
from src.api.schemas.request import SegmentRequest
from src.api.schemas.response import SegmentResponse
from src.api.services.segment_service import SegmentService

router = APIRouter(tags=["segments"])
segment_service = SegmentService()

def init_segment_service(segments):
    segment_service.load_data(segments)

@router.post("/segment", response_model=SegmentResponse)
async def get_segment(
    request: Request,
    segment_request: SegmentRequest,
    user: dict = Depends(get_current_user),
):
    rate_limit_by_user(request, max_requests=30)
    result = segment_service.get_segment(segment_request.customer_id)
    return result

@router.get("/segments/summary")
async def segment_summary(
    request: Request,
    user: dict = Depends(get_current_user),
):
    rate_limit_by_user(request, max_requests=60)
    return segment_service.get_summary()

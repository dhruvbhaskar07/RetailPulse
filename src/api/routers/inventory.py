"""Inventory optimisation endpoint — reorder recommendations and stockout risk."""

from fastapi import APIRouter, Depends, Query, Request
from typing import Optional
from src.api.auth.dependencies import get_current_user, rate_limit_by_user
from src.api.schemas.request import InventoryRequest
from src.api.schemas.response import InventoryResponse
from src.api.services.inventory_service import InventoryService

router = APIRouter(tags=["inventory"])
inventory_service = InventoryService()

def init_inventory_service(inventory):
    inventory_service.load_data(inventory)

@router.post("/inventory", response_model=InventoryResponse)
async def get_inventory(
    request: Request,
    inventory_request: InventoryRequest,
    user: dict = Depends(get_current_user),
):
    rate_limit_by_user(request, max_requests=30)
    items = inventory_service.get_recommendations(
        store_id=inventory_request.store_id,
        product_id=inventory_request.product_id,
        top_n=inventory_request.top_n,
    )
    return {"items": items}

@router.get("/inventory/summary")
async def inventory_summary(
    request: Request,
    user: dict = Depends(get_current_user),
):
    rate_limit_by_user(request, max_requests=60)
    return inventory_service.get_summary()

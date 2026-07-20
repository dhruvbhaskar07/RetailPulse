"""Pydantic response models for token, forecast, churn, segment, inventory, and admin endpoints."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400

class ForecastResponse(BaseModel):
    store_id: int
    product_id: int
    horizon: int
    predictions: List[float]
    dates: List[str]
    model_version: str = "ensemble_v1"

class ChurnResponse(BaseModel):
    customer_id: int
    churn_probability: float = Field(..., ge=0, le=1)
    risk_level: str
    top_factors: Optional[List[Dict[str, Any]]] = None

class SegmentResponse(BaseModel):
    customer_id: int
    cluster: int
    segment_label: str
    rfm_score: Optional[int] = None

class InventoryItem(BaseModel):
    store_id: int
    product_id: int
    stock_level: int
    avg_daily_demand: float
    safety_stock: float
    reorder_point: float
    recommended_order_qty: int
    days_of_supply: float
    urgency_score: float

class InventoryResponse(BaseModel):
    items: List[InventoryItem]

class WhatIfResponse(BaseModel):
    store_id: int
    product_id: int
    base_forecast: List[float]
    scenario_forecast: List[float]
    revenue_impact: float

class ModelStatusResponse(BaseModel):
    model: str
    version: str
    status: str
    metrics: Dict[str, float] = {}

class AuditLogEntry(BaseModel):
    id: int
    timestamp: str
    user_id: str
    user_role: Optional[str] = None
    action: str
    endpoint: str
    method: str
    ip_address: Optional[str] = None
    status_code: int
    duration_ms: float

class AuditLogResponse(BaseModel):
    total: int
    entries: List[AuditLogEntry]
    page: int
    page_size: int

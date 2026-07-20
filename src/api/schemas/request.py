"""Pydantic request models for all API endpoints."""

from pydantic import BaseModel, Field
from typing import Optional, List

class LoginRequest(BaseModel):
    username: str
    password: str

class ForecastRequest(BaseModel):
    store_id: int = Field(..., ge=1, le=1000)
    product_id: int = Field(..., ge=1, le=10000)
    horizon: int = Field(30, ge=1, le=90)

class ChurnRequest(BaseModel):
    customer_id: int = Field(..., ge=1)

class SegmentRequest(BaseModel):
    customer_id: int = Field(..., ge=1)

class InventoryRequest(BaseModel):
    store_id: Optional[int] = None
    product_id: Optional[int] = None
    top_n: int = Field(50, ge=1, le=500)

class WhatIfRequest(BaseModel):
    store_id: int = Field(..., ge=1)
    product_id: int = Field(..., ge=1)
    promo_lift_pct: float = Field(0.0, ge=-100, le=500)
    price_change_pct: float = Field(0.0, ge=-100, le=100)

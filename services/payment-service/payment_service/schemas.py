from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"


class PaymentRequest(BaseModel):
    order_id: str
    amount: float = Field(..., gt=0)


class PaymentSummary(BaseModel):
    payment_id: str
    order_id: str
    amount: float
    status: str
    failure_reason: Optional[str] = None
    created_at: str
    updated_at: str


class RefundRequest(BaseModel):
    reason: Optional[str] = None

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"]


class OrderItem(BaseModel):
    menu_item_id: str
    quantity: int = Field(..., gt=0)


class CreateOrderRequest(BaseModel):
    restaurant_id: str
    items: List[OrderItem]
    customer_reference: Optional[str] = None
    order_id: Optional[str] = Field(default=None, description="Optional client-supplied ID")
    simulation_mode: Optional[Literal["payment_failure", "restaurant_failure"]] = Field(
        default=None,
        description="Optionaler Simulationsmodus für Tests.",
    )


class OrderSummary(BaseModel):
    id: str
    restaurant_id: str
    status: str
    total_amount: Optional[float]
    items: Optional[list]
    payment_reference: Optional[str]
    failure_reason: Optional[str]
    customer_reference: Optional[str]
    created_at: str
    updated_at: str


class CancelOrderRequest(BaseModel):
    reason: Optional[str] = None

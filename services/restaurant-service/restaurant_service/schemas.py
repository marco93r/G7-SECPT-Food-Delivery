from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"]


class Restaurant(BaseModel):
    id: str
    name: str
    status: str


class MenuItem(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    price: float
    available: bool


class OrderLineItem(BaseModel):
    menu_item_id: str = Field(..., description="ID des Menüeintrags")
    quantity: int = Field(..., gt=0, description="Anzahl des Menüeintrags")


class OrderRequest(BaseModel):
    order_id: str = Field(..., description="Eindeutige Order-ID des Order-Service")
    items: List[OrderLineItem]


class ConfirmedOrderLineItem(BaseModel):
    menu_item_id: str
    name: str
    unit_price: float
    quantity: int
    line_total: float


class OrderDecision(BaseModel):
    order_id: str
    restaurant_id: str
    status: Literal["CONFIRMED", "CANCELED"]
    items: List[ConfirmedOrderLineItem]
    total_amount: float
    updated_at: str
    cancellation_reason: Optional[str] = None


class CancelRequest(BaseModel):
    reason: Optional[str] = Field(
        default=None, description="Optionaler Hinweis für die Kompensationsaktion"
    )

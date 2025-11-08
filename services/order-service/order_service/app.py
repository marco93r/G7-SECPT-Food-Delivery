from __future__ import annotations

import os

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .payment_client import HTTPPaymentClient, MockPaymentClient, PaymentClient, PaymentServiceError
from .repository import OrderRepository
from .restaurant_client import RestaurantClient, RestaurantServiceError
from .saga import CreateOrderCommand, OrderSaga
from . import schemas


def get_repository() -> OrderRepository:
    return OrderRepository()


def build_restaurant_client() -> RestaurantClient:
    base_url = os.environ.get("RESTAURANT_SERVICE_URL", "http://restaurant-service:8082")
    return RestaurantClient(base_url)


def build_payment_client() -> PaymentClient:
    mode = os.environ.get("PAYMENT_MODE", "mock").lower()
    if mode == "http":
        base_url = os.environ.get("PAYMENT_SERVICE_URL")
        if not base_url:
            raise RuntimeError("PAYMENT_SERVICE_URL muss gesetzt sein, wenn PAYMENT_MODE=http")
        return HTTPPaymentClient(base_url)
    return MockPaymentClient()


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(
        title="Order Service",
        version="0.1.0",
        description="Koordiniert Bestellungen via Saga-Muster.",
    )
    allowed_origins = [
        origin.strip() for origin in os.environ.get("ALLOWED_ORIGINS", "*").split(",")
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def get_saga(
        repo: OrderRepository = Depends(get_repository),
        restaurant_client: RestaurantClient = Depends(build_restaurant_client),
        payment_client: PaymentClient = Depends(build_payment_client),
    ) -> OrderSaga:
        return OrderSaga(repo, restaurant_client, payment_client)

    @app.get("/healthz", response_model=schemas.HealthResponse)
    async def healthz() -> schemas.HealthResponse:
        return schemas.HealthResponse(status="ok")

    @app.post(
        "/orders",
        response_model=schemas.OrderSummary,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_order(
        payload: schemas.CreateOrderRequest,
        saga: OrderSaga = Depends(get_saga),
    ) -> schemas.OrderSummary:
        if not payload.items:
            raise HTTPException(status_code=400, detail="Mindestens ein Menüeintrag ist erforderlich.")
        try:
            record = saga.place_order(
                CreateOrderCommand(
                    restaurant_id=payload.restaurant_id,
                    items=[item.model_dump() for item in payload.items],
                    customer_reference=payload.customer_reference,
                    order_id=payload.order_id,
                    simulation_mode=payload.simulation_mode,
                )
            )
        except RestaurantServiceError as exc:
            raise HTTPException(status_code=502, detail=str(exc))
        except PaymentServiceError as exc:
            raise HTTPException(status_code=502, detail=str(exc))

        return schemas.OrderSummary(**record.__dict__)

    @app.get("/orders", response_model=list[schemas.OrderSummary])
    async def list_orders(
        limit: int = 50, repo: OrderRepository = Depends(get_repository)
    ) -> list[schemas.OrderSummary]:
        records = repo.list_orders(limit=limit)
        return [schemas.OrderSummary(**record.__dict__) for record in records]

    @app.get("/orders/{order_id}", response_model=schemas.OrderSummary)
    async def get_order(
        order_id: str,
        repo: OrderRepository = Depends(get_repository),
    ) -> schemas.OrderSummary:
        record = repo.get_order(order_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Order nicht gefunden")
        return schemas.OrderSummary(**record.__dict__)

    @app.post("/orders/{order_id}/cancel", response_model=schemas.OrderSummary)
    async def cancel_order(
        order_id: str,
        payload: schemas.CancelOrderRequest,
        repo: OrderRepository = Depends(get_repository),
        saga: OrderSaga = Depends(get_saga),
    ) -> schemas.OrderSummary:
        record = repo.get_order(order_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Order nicht gefunden")
        updated = saga.cancel(record, payload.reason)
        return schemas.OrderSummary(**updated.__dict__)

    return app

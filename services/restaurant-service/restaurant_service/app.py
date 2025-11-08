from __future__ import annotations

import os
from typing import List

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from . import schemas
from .database import init_db
from .repository import (
    MenuItemValidationError,
    OrderItem,
    OrderNotFoundError,
    RestaurantNotFoundError,
    RestaurantRepository,
)


def get_repository() -> RestaurantRepository:
    return RestaurantRepository()


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(
        title="Restaurant Service",
        version="0.1.0",
        description="Bestellt Menues und bestaetigt Orders innerhalb der miFOS-Architektur.",
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

    @app.get("/healthz", response_model=schemas.HealthResponse, tags=["system"])
    async def health() -> schemas.HealthResponse:
        return schemas.HealthResponse(status="ok")

    @app.get(
        "/restaurants",
        response_model=List[schemas.Restaurant],
        tags=["restaurants"],
    )
    async def list_restaurants(
        repo: RestaurantRepository = Depends(get_repository),
    ) -> List[schemas.Restaurant]:
        return [schemas.Restaurant(**row) for row in repo.list_restaurants()]

    @app.get(
        "/restaurants/{restaurant_id}/menu",
        response_model=List[schemas.MenuItem],
        tags=["restaurants"],
    )
    async def get_menu(
        restaurant_id: str, repo: RestaurantRepository = Depends(get_repository)
    ) -> List[schemas.MenuItem]:
        try:
            rows = repo.get_menu(restaurant_id)
        except RestaurantNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
        return [schemas.MenuItem(**row) for row in rows]

    @app.post(
        "/restaurants/{restaurant_id}/orders",
        response_model=schemas.OrderDecision,
        tags=["orders"],
        status_code=status.HTTP_201_CREATED,
    )
    async def confirm_order(
        restaurant_id: str,
        payload: schemas.OrderRequest,
        repo: RestaurantRepository = Depends(get_repository),
    ) -> schemas.OrderDecision:
        try:
            response = repo.confirm_order(
                restaurant_id,
                payload.order_id,
                [OrderItem(**item.model_dump()) for item in payload.items],
            )
        except RestaurantNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
        except MenuItemValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

        return schemas.OrderDecision(**response)

    @app.post(
        "/restaurants/{restaurant_id}/orders/{order_id}/cancel",
        response_model=schemas.OrderDecision,
        tags=["orders"],
    )
    async def cancel_order(
        restaurant_id: str,
        order_id: str,
        payload: schemas.CancelRequest,
        repo: RestaurantRepository = Depends(get_repository),
    ) -> schemas.OrderDecision:
        try:
            response = repo.cancel_order(restaurant_id, order_id, payload.reason)
        except RestaurantNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
        except OrderNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

        return schemas.OrderDecision(**response)

    return app

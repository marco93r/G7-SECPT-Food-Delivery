from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, status

from .database import init_db
from .repository import PaymentRepository
from .schemas import HealthResponse, PaymentRequest, PaymentSummary, RefundRequest
from .service import PaymentDeclined, PaymentProcessor, RefundError


def get_repository() -> PaymentRepository:
    return PaymentRepository()


def build_processor(repo: PaymentRepository = Depends(get_repository)) -> PaymentProcessor:
    return PaymentProcessor(repo)


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(
        title="Payment Service",
        version="0.1.0",
        description="Autorisiert, captured und refundet Zahlungen.",
    )

    @app.get("/healthz", response_model=HealthResponse)
    async def healthz() -> HealthResponse:
        return HealthResponse()

    @app.post("/payments", response_model=PaymentSummary, status_code=status.HTTP_201_CREATED)
    async def create_payment(
        payload: PaymentRequest,
        processor: PaymentProcessor = Depends(build_processor),
    ) -> PaymentSummary:
        try:
            record = processor.create_payment(payload.order_id, payload.amount)
        except PaymentDeclined as exc:
            raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc))
        return PaymentSummary(
            payment_id=record.id,
            order_id=record.order_id,
            amount=record.amount,
            status=record.status,
            failure_reason=record.failure_reason,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    @app.get("/payments/{payment_id}", response_model=PaymentSummary)
    async def get_payment(
        payment_id: str,
        repo: PaymentRepository = Depends(get_repository),
    ) -> PaymentSummary:
        record = repo.get_payment(payment_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Payment not found")
        return PaymentSummary(
            payment_id=record.id,
            order_id=record.order_id,
            amount=record.amount,
            status=record.status,
            failure_reason=record.failure_reason,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    @app.post("/payments/{payment_id}/refund", response_model=PaymentSummary)
    async def refund_payment(
        payment_id: str,
        _: RefundRequest,
        processor: PaymentProcessor = Depends(build_processor),
    ) -> PaymentSummary:
        try:
            record = processor.refund(payment_id)
        except RefundError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return PaymentSummary(
            payment_id=record.id,
            order_id=record.order_id,
            amount=record.amount,
            status=record.status,
            failure_reason=record.failure_reason,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    return app

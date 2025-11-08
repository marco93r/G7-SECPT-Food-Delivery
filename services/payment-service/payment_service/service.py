from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from .repository import PaymentRecord, PaymentRepository


class PaymentDeclined(Exception):
    """Raised when a payment cannot be authorized/captured."""


class RefundError(Exception):
    """Raised when a refund is not possible."""


@dataclass
class PaymentResponse:
    payment_id: str
    status: str
    amount: float


class PaymentProcessor:
    def __init__(self, repository: PaymentRepository, failure_mode: str | None = None):
        self._repo = repository
        mode = (failure_mode or os.environ.get("FAILURE_MODE", "none")).lower()
        self._failure_mode = mode

    def create_payment(self, order_id: str, amount: float) -> PaymentRecord:
        payment_id = f"pay-{uuid.uuid4()}"
        now = datetime.now(timezone.utc).isoformat()
        record = PaymentRecord(
            id=payment_id,
            order_id=order_id,
            amount=amount,
            status="CAPTURED",
            failure_reason=None,
            created_at=now,
            updated_at=now,
        )
        if self._failure_mode in {"authorize", "capture"}:
            record = PaymentRecord(
                id=payment_id,
                order_id=order_id,
                amount=amount,
                status="FAILED",
                failure_reason="Configured failure mode",
                created_at=now,
                updated_at=now,
            )
            self._repo.insert_payment(record)
            raise PaymentDeclined("Payment declined due to configured failure mode.")

        self._repo.insert_payment(record)
        return record

    def refund(self, payment_id: str) -> PaymentRecord:
        record = self._repo.get_payment(payment_id)
        if record is None:
            raise RefundError("Payment not found.")

        if self._failure_mode == "refund":
            self._repo.update_status(payment_id, "FAILED", "Refund blocked by configuration")
            raise RefundError("Refund blocked by failure mode.")

        if record.status == "REFUNDED":
            return record
        updated = self._repo.update_status(payment_id, "REFUNDED", None)
        assert updated is not None
        return updated

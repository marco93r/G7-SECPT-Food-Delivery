from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol

import httpx


@dataclass
class PaymentResult:
    reference: str
    status: str


class PaymentClient(Protocol):
    def authorize_and_capture(self, order_id: str, amount: float) -> PaymentResult: ...

    def refund(self, reference: str, amount: float) -> PaymentResult: ...


class PaymentServiceError(Exception):
    """Represents downstream payment failures."""


class HTTPPaymentClient:
    def __init__(self, base_url: str):
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=5.0)

    def authorize_and_capture(self, order_id: str, amount: float) -> PaymentResult:
        try:
            response = self._client.post(
                f"{self._base_url}/payments",
                json={"order_id": order_id, "amount": amount},
            )
        except httpx.HTTPError as exc:
            raise PaymentServiceError(f"Payment-Service nicht erreichbar: {exc}") from exc

        if response.status_code >= 400:
            raise PaymentServiceError(
                f"Zahlung fehlgeschlagen ({response.status_code}): {response.text}"
            )
        payload = response.json()
        return PaymentResult(reference=payload.get("payment_id", ""), status=payload.get("status", "FAILED"))

    def refund(self, reference: str, amount: float) -> PaymentResult:
        try:
            response = self._client.post(
                f"{self._base_url}/payments/{reference}/refund",
                json={"amount": amount},
            )
        except httpx.HTTPError as exc:
            raise PaymentServiceError(f"Refund fehlgeschlagen: {exc}") from exc
        if response.status_code >= 400:
            raise PaymentServiceError(
                f"Refund fehlgeschlagen ({response.status_code}): {response.text}"
            )
        payload = response.json()
        return PaymentResult(reference=payload.get("payment_id", reference), status=payload.get("status", "FAILED"))


class MockPaymentClient:
    """Fallback, solange kein echter Payment-Service existiert."""

    def authorize_and_capture(self, order_id: str, amount: float) -> PaymentResult:
        reference = f"mock-pay-{uuid.uuid4()}"
        return PaymentResult(reference=reference, status="CAPTURED")

    def refund(self, reference: str, amount: float) -> PaymentResult:
        return PaymentResult(reference=reference, status="REFUNDED")

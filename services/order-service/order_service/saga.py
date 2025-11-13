from __future__ import annotations

import uuid
from dataclasses import dataclass

from .payment_client import PaymentClient, PaymentServiceError
from .repository import OrderRecord, OrderRepository
from .restaurant_client import RestaurantClient, RestaurantServiceError


@dataclass
class CreateOrderCommand:
    restaurant_id: str
    items: list[dict]
    customer_reference: str | None = None
    order_id: str | None = None
    simulation_mode: str | None = None


class OrderSaga:
    def __init__(
        self,
        repository: OrderRepository,
        restaurant_client: RestaurantClient,
        payment_client: PaymentClient,
    ):
        self._repo = repository
        self._restaurant = restaurant_client
        self._payment = payment_client

    def place_order(self, command: CreateOrderCommand) -> OrderRecord:
        order_id = command.order_id or str(uuid.uuid4())
        self._repo.create_order(order_id, command.restaurant_id, command.customer_reference)

        try:
            if command.simulation_mode == "restaurant_failure":
                raise RestaurantServiceError("Simulierter Restaurant-Fehler")
            restaurant_decision = self._restaurant.confirm_order(
                command.restaurant_id, order_id, command.items
            )
        except RestaurantServiceError as exc:
            self._repo.update_order(
                order_id,
                status="CANCELED",
                failure_reason=str(exc),
            )
            raise

        total_amount = restaurant_decision.get("total_amount", 0.0)

        try:
            if command.simulation_mode == "payment_failure":
                raise PaymentServiceError("Simulierte Zahlungsstoerung")
            payment_result = self._payment.authorize_and_capture(order_id, total_amount)
        except PaymentServiceError as exc:
            self._repo.update_order(
                order_id,
                status="CANCELED",
                total_amount=total_amount,
                items=restaurant_decision.get("items"),
                failure_reason=str(exc),
            )
            self._compensate_restaurant(command.restaurant_id, order_id, "payment_failed")
            raise

        self._repo.update_order(
            order_id,
            status="CONFIRMED",
            total_amount=total_amount,
            items=restaurant_decision.get("items"),
            payment_reference=payment_result.reference,
            failure_reason=None,
        )
        return self._repo.get_order(order_id)

    def cancel(self, order: OrderRecord, reason: str | None = None) -> OrderRecord:
        self._compensate_restaurant(order.restaurant_id, order.id, reason or "manual_cancel")
        self._repo.update_order(
            order.id,
            status="CANCELED",
            failure_reason=reason,
        )
        return self._repo.get_order(order.id)

    def _compensate_restaurant(self, restaurant_id: str, order_id: str, reason: str | None) -> None:
        try:
            self._restaurant.cancel_order(restaurant_id, order_id, reason)
        except RestaurantServiceError:
            # Saga best effort; Logging kann später ergänzt werden
            pass

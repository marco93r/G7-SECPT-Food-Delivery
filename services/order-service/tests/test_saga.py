from __future__ import annotations

import sqlite3

import pytest

from order_service.database import apply_schema
from order_service.payment_client import PaymentClient, PaymentResult, PaymentServiceError
from order_service.repository import OrderRepository
from order_service.restaurant_client import RestaurantServiceError
from order_service.saga import CreateOrderCommand, OrderSaga


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "orders.db"

    def connection_factory():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    with connection_factory() as conn:
        apply_schema(conn)

    return OrderRepository(connection_factory=connection_factory)


class SuccessfulRestaurantClient:
    def confirm_order(self, restaurant_id, order_id, items):
        return {
            "order_id": order_id,
            "restaurant_id": restaurant_id,
            "items": [{"menu_item_id": items[0]["menu_item_id"], "quantity": 1, "line_total": 10.0}],
            "total_amount": 10.0,
        }

    def cancel_order(self, restaurant_id, order_id, reason):
        return None


class FailingRestaurantClient(SuccessfulRestaurantClient):
    def confirm_order(self, restaurant_id, order_id, items):
        raise RestaurantServiceError("Restaurant down")


class SuccessfulPaymentClient:
    def authorize_and_capture(self, order_id, amount):
        return PaymentResult(reference="pay-123", status="CAPTURED")

    def refund(self, reference, amount):
        return PaymentResult(reference=reference, status="REFUNDED")


class FailingPaymentClient(SuccessfulPaymentClient):
    def authorize_and_capture(self, order_id, amount):
        raise PaymentServiceError("card declined")


def test_successful_order(repo):
    saga = OrderSaga(repo, SuccessfulRestaurantClient(), SuccessfulPaymentClient())
    record = saga.place_order(
        CreateOrderCommand(
            restaurant_id="resto-roma",
            items=[{"menu_item_id": "roma-carbonara", "quantity": 1}],
        )
    )
    assert record.status == "CONFIRMED"
    assert record.total_amount == 10.0
    assert record.payment_reference == "pay-123"


def test_restaurant_failure(repo):
    saga = OrderSaga(repo, FailingRestaurantClient(), SuccessfulPaymentClient())
    with pytest.raises(RestaurantServiceError):
        saga.place_order(
            CreateOrderCommand(
                restaurant_id="resto-roma",
                items=[{"menu_item_id": "roma-carbonara", "quantity": 1}],
                order_id="order-1",
            )
        )
    record = repo.get_order("order-1")
    assert record.status == "CANCELED"
    assert record.failure_reason == "Restaurant down"


def test_payment_failure_triggers_compensation(repo):
    saga = OrderSaga(repo, SuccessfulRestaurantClient(), FailingPaymentClient())
    with pytest.raises(PaymentServiceError):
        saga.place_order(
            CreateOrderCommand(
                restaurant_id="resto-roma",
                items=[{"menu_item_id": "roma-carbonara", "quantity": 1}],
                order_id="order-2",
            )
        )
    record = repo.get_order("order-2")
    assert record.status == "CANCELED"
    assert record.failure_reason == "card declined"


def test_simulated_payment_failure(repo):
    saga = OrderSaga(repo, SuccessfulRestaurantClient(), SuccessfulPaymentClient())
    with pytest.raises(PaymentServiceError):
        saga.place_order(
            CreateOrderCommand(
                restaurant_id="resto-roma",
                items=[{"menu_item_id": "roma-carbonara", "quantity": 1}],
                order_id="order-3",
                simulation_mode="payment_failure",
            )
        )
    record = repo.get_order("order-3")
    assert record.status == "CANCELED"
    assert record.failure_reason == "Simulierte Zahlungsstoerung"


def test_simulated_restaurant_failure(repo):
    saga = OrderSaga(repo, SuccessfulRestaurantClient(), SuccessfulPaymentClient())
    with pytest.raises(RestaurantServiceError):
        saga.place_order(
            CreateOrderCommand(
                restaurant_id="resto-roma",
                items=[{"menu_item_id": "roma-carbonara", "quantity": 1}],
                order_id="order-4",
                simulation_mode="restaurant_failure",
            )
        )
    record = repo.get_order("order-4")
    assert record.status == "CANCELED"
    assert record.failure_reason == "Simulierter Restaurant-Fehler"


def test_list_orders(repo):
    saga = OrderSaga(repo, SuccessfulRestaurantClient(), SuccessfulPaymentClient())
    saga.place_order(
        CreateOrderCommand(
            restaurant_id="resto-roma",
            items=[{"menu_item_id": "roma-carbonara", "quantity": 1}],
            order_id="order-5",
        )
    )
    entries = repo.list_orders(limit=10)
    assert any(entry.id == "order-5" for entry in entries)

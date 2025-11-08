from __future__ import annotations

import sqlite3
from typing import Iterator

import pytest

from restaurant_service.database import apply_schema
from restaurant_service.repository import (
    MenuItemValidationError,
    OrderItem,
    OrderNotFoundError,
    RestaurantRepository,
)


@pytest.fixture()
def repo(tmp_path) -> Iterator[RestaurantRepository]:
    db_path = tmp_path / "restaurant.db"

    def connection_factory() -> sqlite3.Connection:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    with connection_factory() as conn:
        apply_schema(conn)
        conn.execute(
            "INSERT INTO restaurants (id, name, status) VALUES (?, ?, ?);",
            ("resto-test", "Testaurant", "ONLINE"),
        )
        conn.executemany(
            """
            INSERT INTO menu_items (id, restaurant_id, name, price, available)
            VALUES (?, ?, ?, ?, ?);
            """,
            [
                ("item-1", "resto-test", "Pizza", 10.0, 1),
                ("item-2", "resto-test", "Pasta", 12.0, 1),
            ],
        )
        conn.commit()

    yield RestaurantRepository(connection_factory=connection_factory)


def test_confirm_order_success(repo: RestaurantRepository) -> None:
    decision = repo.confirm_order(
        "resto-test",
        "order-1",
        [OrderItem(menu_item_id="item-1", quantity=2)],
    )

    assert decision["status"] == "CONFIRMED"
    assert decision["total_amount"] == 20.0
    assert decision["items"][0]["quantity"] == 2


def test_confirm_order_unknown_menu_item(repo: RestaurantRepository) -> None:
    with pytest.raises(MenuItemValidationError):
        repo.confirm_order(
            "resto-test",
            "order-2",
            [OrderItem(menu_item_id="unknown", quantity=1)],
        )


def test_cancel_order(repo: RestaurantRepository) -> None:
    repo.confirm_order(
        "resto-test",
        "order-3",
        [OrderItem(menu_item_id="item-2", quantity=1)],
    )

    decision = repo.cancel_order("resto-test", "order-3", "Saga compensation")
    assert decision["status"] == "CANCELED"
    assert decision["cancellation_reason"] == "Saga compensation"

    with pytest.raises(OrderNotFoundError):
        repo.cancel_order("resto-test", "order-does-not-exist", None)

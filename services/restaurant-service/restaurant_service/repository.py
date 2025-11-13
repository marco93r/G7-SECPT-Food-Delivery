from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Sequence

from .database import get_connection


class RestaurantNotFoundError(Exception):
    """Raised when a restaurant identifier is unknown."""


class MenuItemValidationError(Exception):
    """Raised when requested menu items are invalid or unavailable."""


class OrderNotFoundError(Exception):
    """Raised when a restaurant order cannot be located."""


@dataclass(frozen=True)
class OrderItem:
    menu_item_id: str
    quantity: int


class RestaurantRepository:
    """Thin data-access layer that hides direct SQL from the FastAPI handlers."""

    def __init__(self, connection_factory=get_connection):
        self._connection_factory = connection_factory

    @contextmanager
    def _connection(self):
        conn = self._connection_factory()
        try:
            yield conn
        finally:
            conn.close()

    def list_restaurants(self) -> List[dict]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT id, name, status FROM restaurants ORDER BY name ASC;"
            ).fetchall()
            return [dict(row) for row in rows]

    def get_menu(self, restaurant_id: str) -> List[dict]:
        with self._connection() as conn:
            self._assert_restaurant_exists(conn, restaurant_id)
            placeholder = _placeholder(conn)
            rows = conn.execute(
                f"""
                SELECT id, name, description, price, available
                FROM menu_items
                WHERE restaurant_id = {placeholder}
                ORDER BY name ASC;
                """,
                (restaurant_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def confirm_order(
        self, restaurant_id: str, order_id: str, items: Sequence[OrderItem]
    ) -> dict:
        if not items:
            raise MenuItemValidationError("Bestellung enthält keine Positionen.")

        normalized: Dict[str, int] = {}
        for item in items:
            if item.quantity <= 0:
                raise MenuItemValidationError("Mengen müssen größer als 0 sein.")
            normalized[item.menu_item_id] = normalized.get(item.menu_item_id, 0) + item.quantity

        with self._connection() as conn:
            self._assert_restaurant_exists(conn, restaurant_id)
            db_items = self._fetch_menu_items(conn, restaurant_id, normalized.keys())

            if len(db_items) != len(normalized):
                missing = set(normalized.keys()) - {row["id"] for row in db_items}
                raise MenuItemValidationError(
                    f"Unbekannte Menüeinträge angefragt: {', '.join(sorted(missing))}"
                )

            unavailable = [row["id"] for row in db_items if row["available"] == 0]
            if unavailable:
                raise MenuItemValidationError(
                    f"Nicht verfügbare Menüeinträge: {', '.join(unavailable)}"
                )

            payload = []
            total = 0.0
            for row in db_items:
                quantity = normalized[row["id"]]
                line_total = round(row["price"] * quantity, 2)
                total += line_total
                payload.append(
                    {
                        "menu_item_id": row["id"],
                        "name": row["name"],
                        "unit_price": row["price"],
                        "quantity": quantity,
                        "line_total": line_total,
                    }
                )

            now = datetime.now(timezone.utc).isoformat()
            placeholder = _placeholder(conn)
            conn.execute(
                f"""
                INSERT INTO restaurant_orders (
                    order_id, restaurant_id, status, items_json, total_amount,
                    cancellation_reason, updated_at
                ) VALUES ({placeholder}, {placeholder}, 'CONFIRMED',
                          {placeholder}, {placeholder}, NULL, {placeholder})
                ON CONFLICT(order_id) DO UPDATE SET
                    restaurant_id=excluded.restaurant_id,
                    status=excluded.status,
                    items_json=excluded.items_json,
                    total_amount=excluded.total_amount,
                    cancellation_reason=excluded.cancellation_reason,
                    updated_at=excluded.updated_at;
                """,
                (order_id, restaurant_id, json.dumps(payload), total, now),
            )
            conn.commit()

            return {
                "order_id": order_id,
                "restaurant_id": restaurant_id,
                "status": "CONFIRMED",
                "items": payload,
                "total_amount": round(total, 2),
                "updated_at": now,
            }

    def cancel_order(self, restaurant_id: str, order_id: str, reason: str | None) -> dict:
        with self._connection() as conn:
            self._assert_restaurant_exists(conn, restaurant_id)
            placeholder = _placeholder(conn)
            row = conn.execute(
                f"""
                SELECT order_id, restaurant_id, status, total_amount, items_json, updated_at
                FROM restaurant_orders
                WHERE order_id = {placeholder} AND restaurant_id = {placeholder};
                """,
                (order_id, restaurant_id),
            ).fetchone()

            if row is None:
                raise OrderNotFoundError(f"Bestellung {order_id} ist unbekannt.")

            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                f"""
                UPDATE restaurant_orders
                SET status = 'CANCELED',
                    cancellation_reason = {placeholder},
                    updated_at = {placeholder}
                WHERE order_id = {placeholder};
                """,
                (reason, now, order_id),
            )
            conn.commit()

            return {
                "order_id": order_id,
                "restaurant_id": restaurant_id,
                "status": "CANCELED",
                "items": json.loads(row["items_json"]),
                "total_amount": row["total_amount"],
                "cancellation_reason": reason,
                "updated_at": now,
            }

    def _assert_restaurant_exists(self, conn, restaurant_id: str) -> None:
        placeholder = _placeholder(conn)
        exists = conn.execute(
            f"SELECT 1 FROM restaurants WHERE id = {placeholder};", (restaurant_id,)
        ).fetchone()
        if not exists:
            raise RestaurantNotFoundError(f"Restaurant {restaurant_id} ist nicht vorhanden.")

    def _fetch_menu_items(
        self, conn, restaurant_id: str, menu_item_ids: Iterable[str]
    ):
        ids = list(menu_item_ids)
        if not ids:
            return []
        placeholder = _placeholder(conn)
        placeholders = ",".join(placeholder for _ in ids)
        query = f"""
            SELECT id, name, price, available
            FROM menu_items
            WHERE restaurant_id = {placeholder}
              AND id IN ({placeholders});
        """
        return conn.execute(query, [restaurant_id, *ids]).fetchall()


def _placeholder(conn) -> str:
    module = conn.__class__.__module__
    return "%s" if "psycopg" in module else "?"

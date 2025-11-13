from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from .database import get_connection


@dataclass(frozen=True)
class OrderRecord:
    id: str
    restaurant_id: str
    status: str
    total_amount: Optional[float]
    items: Optional[list]
    payment_reference: Optional[str]
    failure_reason: Optional[str]
    customer_reference: Optional[str]
    created_at: str
    updated_at: str


class OrderRepository:
    """Data-access layer for persisting saga state."""

    def __init__(self, connection_factory=get_connection):
        self._connection_factory = connection_factory

    @contextmanager
    def _connection(self):
        conn = self._connection_factory()
        try:
            yield conn
        finally:
            conn.close()

    def create_order(self, order_id: str, restaurant_id: str, customer_reference: str | None) -> OrderRecord:
        now = datetime.now(timezone.utc).isoformat()
        payload = (
            order_id,
            customer_reference,
            restaurant_id,
            "PENDING",
            None,
            None,
            None,
            None,
            now,
            now,
        )
        with self._connection() as conn:
            placeholder = _placeholder(conn)
            conn.execute(
                f"""
                INSERT INTO orders (
                    id, customer_reference, restaurant_id, status, total_amount,
                    items_json, payment_reference, failure_reason, created_at, updated_at
                ) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder},
                          {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder});
                """,
                payload,
            )
            conn.commit()
        return OrderRecord(
            id=order_id,
            restaurant_id=restaurant_id,
            status="PENDING",
            total_amount=None,
            items=None,
            payment_reference=None,
            failure_reason=None,
            customer_reference=customer_reference,
            created_at=now,
            updated_at=now,
        )

    def update_order(
        self,
        order_id: str,
        *,
        status: str,
        total_amount: float | None = None,
        items: list | None = None,
        payment_reference: str | None = None,
        failure_reason: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        items_json = json.dumps(items) if items is not None else None
        with self._connection() as conn:
            placeholder = _placeholder(conn)
            conn.execute(
                f"""
                UPDATE orders
                SET status = {placeholder},
                    total_amount = COALESCE({placeholder}, total_amount),
                    items_json = COALESCE({placeholder}, items_json),
                    payment_reference = COALESCE({placeholder}, payment_reference),
                    failure_reason = {placeholder},
                    updated_at = {placeholder}
                WHERE id = {placeholder};
                """,
                (
                    status,
                    total_amount,
                    items_json,
                    payment_reference,
                    failure_reason,
                    now,
                    order_id,
                ),
            )
            conn.commit()

    def get_order(self, order_id: str) -> OrderRecord | None:
        with self._connection() as conn:
            placeholder = _placeholder(conn)
            row = conn.execute(
                f"""
                SELECT id, restaurant_id, status, total_amount, items_json,
                       payment_reference, failure_reason, customer_reference,
                       created_at, updated_at
                FROM orders
                WHERE id = {placeholder};
                """,
                (order_id,),
            ).fetchone()
            if row is None:
                return None
            return OrderRecord(
                id=row["id"],
                restaurant_id=row["restaurant_id"],
                status=row["status"],
                total_amount=row["total_amount"],
                items=json.loads(row["items_json"]) if row["items_json"] else None,
                payment_reference=row["payment_reference"],
                failure_reason=row["failure_reason"],
                customer_reference=row["customer_reference"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def list_orders(self, limit: int = 50) -> list[OrderRecord]:
        with self._connection() as conn:
            placeholder = _placeholder(conn)
            rows = conn.execute(
                f"""
                SELECT id, restaurant_id, status, total_amount, items_json,
                       payment_reference, failure_reason, customer_reference,
                       created_at, updated_at
                FROM orders
                ORDER BY updated_at DESC
                LIMIT {placeholder};
                """,
                (limit,),
            ).fetchall()

        results: list[OrderRecord] = []
        for row in rows:
            results.append(
                OrderRecord(
                    id=row["id"],
                    restaurant_id=row["restaurant_id"],
                    status=row["status"],
                    total_amount=row["total_amount"],
                    items=json.loads(row["items_json"]) if row["items_json"] else None,
                    payment_reference=row["payment_reference"],
                    failure_reason=row["failure_reason"],
                    customer_reference=row["customer_reference"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            )
        return results


def _placeholder(conn) -> str:
    module = conn.__class__.__module__
    return "%s" if "psycopg" in module else "?"

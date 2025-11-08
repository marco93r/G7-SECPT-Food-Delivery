from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from .database import get_connection


@dataclass(frozen=True)
class PaymentRecord:
    id: str
    order_id: str
    amount: float
    status: str
    failure_reason: Optional[str]
    created_at: str
    updated_at: str


class PaymentRepository:
    def __init__(self, connection_factory=get_connection):
        self._connection_factory = connection_factory

    @contextmanager
    def _connection(self):
        conn = self._connection_factory()
        try:
            yield conn
        finally:
            conn.close()

    def insert_payment(self, record: PaymentRecord) -> None:
        with self._connection() as conn:
            placeholder = _placeholder(conn)
            conn.execute(
                f"""
                INSERT INTO payments (id, order_id, amount, status, failure_reason, created_at, updated_at)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder});
                """,
                (
                    record.id,
                    record.order_id,
                    record.amount,
                    record.status,
                    record.failure_reason,
                    record.created_at,
                    record.updated_at,
                ),
            )
            conn.commit()

    def update_status(self, payment_id: str, status: str, failure_reason: str | None = None) -> PaymentRecord | None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            placeholder = _placeholder(conn)
            conn.execute(
                f"""
                UPDATE payments
                SET status = {placeholder}, failure_reason = {placeholder}, updated_at = {placeholder}
                WHERE id = {placeholder};
                """,
                (status, failure_reason, now, payment_id),
            )
            conn.commit()
        return self.get_payment(payment_id)

    def get_payment(self, payment_id: str) -> PaymentRecord | None:
        with self._connection() as conn:
            placeholder = _placeholder(conn)
            row = conn.execute(
                f"""
                SELECT id, order_id, amount, status, failure_reason, created_at, updated_at
                FROM payments
                WHERE id = {placeholder};
                """,
                (payment_id,),
            ).fetchone()
            if row is None:
                return None
            return PaymentRecord(
                id=row["id"],
                order_id=row["order_id"],
                amount=row["amount"],
                status=row["status"],
                failure_reason=row["failure_reason"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )


def _placeholder(conn) -> str:
    module = conn.__class__.__module__
    return "%s" if "psycopg" in module else "?"

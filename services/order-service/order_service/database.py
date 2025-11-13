from __future__ import annotations

import os
import sqlite3
import time
from typing import Iterable

import psycopg
from psycopg.rows import dict_row

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    customer_reference TEXT,
    restaurant_id TEXT NOT NULL,
    status TEXT NOT NULL,
    total_amount REAL,
    items_json TEXT,
    payment_reference TEXT,
    failure_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _build_database_url() -> str:
    if url := os.environ.get("DATABASE_URL"):
        return url
    user = os.environ.get("DB_USER", "mifos")
    password = os.environ.get("DB_PASSWORD", "mifos")
    host = os.environ.get("DB_HOST", "order-db")
    port = os.environ.get("DB_PORT", "5432")
    name = os.environ.get("DB_NAME", "order_service")
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


DATABASE_URL = _build_database_url()


def get_connection():
    retries = int(os.environ.get("DB_CONNECT_MAX_RETRIES", "30"))
    delay = float(os.environ.get("DB_CONNECT_RETRY_DELAY", "2"))
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            return _connect_once()
        except Exception as exc:  # pragma: no cover
            last_exc = exc
            if attempt == retries - 1:
                raise
            time.sleep(delay)
    raise last_exc  # pragma: no cover


def _connect_once():
    if DATABASE_URL.startswith("sqlite://"):
        path = DATABASE_URL.replace("sqlite:///", "")
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn

    return psycopg.connect(DATABASE_URL, autocommit=True, row_factory=dict_row)


def init_db() -> None:
    with get_connection() as conn:
        apply_schema(conn)


def apply_schema(conn) -> None:
    if hasattr(conn, "executescript"):
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        return

    with conn.cursor() as cur:
        for statement in _split_statements(SCHEMA_SQL):
            cur.execute(statement)
    conn.commit()


def _split_statements(sql_blob: str) -> Iterable[str]:
    for statement in sql_blob.split(";"):
        stmt = statement.strip()
        if stmt:
            yield stmt

from __future__ import annotations

import os
import sqlite3
import time
from typing import Iterable

import psycopg
from psycopg.rows import dict_row

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS restaurants (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ONLINE'
);

CREATE TABLE IF NOT EXISTS menu_items (
    id TEXT PRIMARY KEY,
    restaurant_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL,
    available INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (restaurant_id) REFERENCES restaurants (id)
);

CREATE TABLE IF NOT EXISTS restaurant_orders (
    order_id TEXT PRIMARY KEY,
    restaurant_id TEXT NOT NULL,
    status TEXT NOT NULL,
    items_json TEXT NOT NULL,
    total_amount REAL NOT NULL,
    cancellation_reason TEXT,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (restaurant_id) REFERENCES restaurants (id)
);
"""


def _build_database_url() -> str:
    if url := os.environ.get("DATABASE_URL"):
        return url
    user = os.environ.get("DB_USER", "mifos")
    password = os.environ.get("DB_PASSWORD", "mifos")
    host = os.environ.get("DB_HOST", "restaurant-db")
    port = os.environ.get("DB_PORT", "5432")
    name = os.environ.get("DB_NAME", "restaurant_service")
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


DATABASE_URL = _build_database_url()


def get_connection():
    """Return a connection against Postgres (default) or SQLite when configured."""
    retries = int(os.environ.get("DB_CONNECT_MAX_RETRIES", "30"))
    delay = float(os.environ.get("DB_CONNECT_RETRY_DELAY", "2"))
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            return _connect_once()
        except Exception as exc:  # pragma: no cover - only hits when DB down
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

    conn = psycopg.connect(DATABASE_URL, autocommit=True, row_factory=dict_row)
    return conn


def init_db() -> None:
    with get_connection() as conn:
        apply_schema(conn)
        seed_if_empty(conn)


def apply_schema(conn) -> None:
    if hasattr(conn, "executescript"):
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        return

    statements = _split_statements(SCHEMA_SQL)
    with conn.cursor() as cur:
        for statement in statements:
            cur.execute(statement)
    conn.commit()


def _split_statements(sql_blob: str) -> Iterable[str]:
    for statement in sql_blob.split(";"):
        stmt = statement.strip()
        if stmt:
            yield stmt


def seed_if_empty(conn) -> None:
    restaurants = [
        ("resto-roma", "La Trattoria Roma", "ONLINE"),
        ("resto-kyoto", "Sakura Sushi Kyoto", "ONLINE"),
    ]

    menu_items = [
        ("roma-carbonara", "resto-roma", "Pasta Carbonara", "Mit Pancetta und Pecorino", 12.5, 1),
        ("roma-margherita", "resto-roma", "Pizza Margherita", "San-Marzano-Tomaten & Büffelmozzarella", 10.0, 1),
        ("roma-tiramisu", "resto-roma", "Tiramisu", "Espresso & Mascarpone", 6.0, 1),
        ("kyoto-salmon", "resto-kyoto", "Lachs Nigiri Set", "8 Stück Nigiri", 15.5, 1),
        ("kyoto-ramen", "resto-kyoto", "Shoyu Ramen", "Sojasud mit Hühnchen", 13.0, 1),
        ("kyoto-mochi", "resto-kyoto", "Matcha Mochi", "Gefüllt mit roter Bohnenpaste", 5.5, 1),
    ]

    cursor = conn.execute("SELECT COUNT(1) AS cnt FROM restaurants;")
    row = cursor.fetchone()
    count = 0
    if row is not None:
        if isinstance(row, dict):
            count = row.get("cnt", 0) or 0
        else:
            count = row[0] or 0
    if count > 0:
        return

    placeholder = _placeholder(conn)
    insert_restaurants = (
        f"INSERT INTO restaurants (id, name, status) VALUES ({placeholder}, {placeholder}, {placeholder})"
    )
    insert_menu_items = (
        "INSERT INTO menu_items (id, restaurant_id, name, description, price, available)"
        f" VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})"
    )

    with conn.cursor() as cur:
        cur.executemany(insert_restaurants, restaurants)
        cur.executemany(insert_menu_items, menu_items)
    conn.commit()


def _placeholder(conn) -> str:
    module = conn.__class__.__module__
    return "%s" if "psycopg" in module else "?"

import os
import uuid
import sqlite3
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from pydantic import BaseModel
import logging


DB_PATH = os.environ.get("DB_PATH", "/data/restaurant.db")
API_KEY = os.environ.get("API_KEY", "changeme")

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("restaurant-service")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS menus (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS reservations (
            id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    # seed menu if empty
    cur.execute("SELECT COUNT(1) as c FROM menus")
    if cur.fetchone()[0] == 0:
        items = [
            (str(uuid.uuid4()), "Pizza Margherita", 10.5),
            (str(uuid.uuid4()), "Pasta Carbonara", 12.0),
            (str(uuid.uuid4()), "Caesar Salad", 8.5),
        ]
        cur.executemany("INSERT INTO menus (id, name, price) VALUES (?, ?, ?)", items)
    conn.commit()
    conn.close()


class MenuItem(BaseModel):
    id: str
    name: str
    price: float


class OrderItem(BaseModel):
    name: str
    price: float
    quantity: int = 1


class ReserveRequest(BaseModel):
    order_id: str
    items: List[OrderItem]
    amount: float


class ReserveResponse(BaseModel):
    reservation_id: str
    status: str


class CancelRequest(BaseModel):
    reservation_id: str


app = FastAPI(title="Restaurant Service", version="0.1.0")


def require_api_key(request: Request):
    key = request.headers.get("X-API-Key")
    if API_KEY and key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/menus", response_model=List[MenuItem])
def list_menus(request: Request, _=Depends(require_api_key)):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, price FROM menus ORDER BY name")
        rows = cur.fetchall()
        logger.info("List menus count=%d", len(rows))
        return [MenuItem(id=r["id"], name=r["name"], price=r["price"]) for r in rows]
    finally:
        conn.close()


@app.post("/reserve", response_model=ReserveResponse)
def reserve(req: ReserveRequest, request: Request, _=Depends(require_api_key)):
    if not req.items or req.amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid reservation request")
    reservation_id = str(uuid.uuid4())
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO reservations (id, order_id, status, created_at) VALUES (?, ?, ?, ?)",
            (reservation_id, req.order_id, "RESERVED", datetime.utcnow().isoformat()),
        )
        conn.commit()
        logger.info("Reserved reservation_id=%s order_id=%s amount=%.2f items=%d", reservation_id, req.order_id, req.amount, len(req.items))
        return ReserveResponse(reservation_id=reservation_id, status="RESERVED")
    finally:
        conn.close()


@app.post("/cancel")
def cancel(req: CancelRequest, request: Request, _=Depends(require_api_key)):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT status FROM reservations WHERE id=?", (req.reservation_id,))
        row = cur.fetchone()
        if not row:
            # idempotent cancel on unknown id
            logger.info("Cancel unknown reservation_id=%s -> idempotent CANCELED", req.reservation_id)
            return {"status": "CANCELED"}
        status = row["status"]
        if status == "CANCELED":
            logger.info("Cancel already CANCELED reservation_id=%s", req.reservation_id)
            return {"status": "CANCELED"}
        cur.execute(
            "UPDATE reservations SET status=? WHERE id=?",
            ("CANCELED", req.reservation_id),
        )
        conn.commit()
        logger.info("Canceled reservation_id=%s", req.reservation_id)
        return {"status": "CANCELED"}
    finally:
        conn.close()

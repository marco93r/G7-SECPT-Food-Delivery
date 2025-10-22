import os
import uuid
import sqlite3
from datetime import datetime
from typing import List, Optional

import requests
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging


DB_PATH = os.environ.get("DB_PATH", "/data/order.db")
API_KEY = os.environ.get("API_KEY", "changeme")
RESTAURANT_URL = os.environ.get("RESTAURANT_URL", "http://restaurant-service:8001")
PAYMENT_URL = os.environ.get("PAYMENT_URL", "http://payment-service:8002")

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("order-service")


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
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            amount REAL NOT NULL,
            reservation_id TEXT,
            payment_id TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


class OrderItem(BaseModel):
    name: str
    price: float
    quantity: int = 1


class CreateOrderRequest(BaseModel):
    customer_id: str
    items: List[OrderItem]


class OrderResponse(BaseModel):
    id: str
    status: str
    amount: float
    reservation_id: Optional[str] = None
    payment_id: Optional[str] = None


app = FastAPI(title="Order Service", version="0.1.0")


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


@app.post("/orders", response_model=OrderResponse)
def create_order(req: CreateOrderRequest, request: Request, _=Depends(require_api_key)):
    if not req.items:
        raise HTTPException(status_code=400, detail="No items provided")

    amount = sum(i.price * i.quantity for i in req.items)
    order_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    logger.info("Create order id=%s customer=%s items=%d amount=%.2f", order_id, req.customer_id, len(req.items), amount)

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO orders (id, status, amount, created_at) VALUES (?, ?, ?, ?)",
        (order_id, "PENDING", amount, created_at),
    )
    conn.commit()

    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

    reservation_id = None
    payment_id = None

    try:
        # Step 1: Reserve at restaurant
        r_payload = {
            "order_id": order_id,
            "items": [i.dict() for i in req.items],
            "amount": amount,
        }
        r = requests.post(
            f"{RESTAURANT_URL}/reserve",
            json=r_payload,
            headers=headers,
            timeout=10,
        )
        if r.status_code != 200:
            raise RuntimeError(f"Restaurant reserve failed: {r.text}")
        r_json = r.json()
        if r_json.get("status") != "RESERVED":
            raise RuntimeError(f"Restaurant status not RESERVED: {r_json}")
        reservation_id = r_json.get("reservation_id")
        logger.info("Restaurant reserved reservation_id=%s for order=%s", reservation_id, order_id)

        # Step 2: Authorize payment
        p_auth = requests.post(
            f"{PAYMENT_URL}/authorize",
            json={"order_id": order_id, "amount": amount},
            headers=headers,
            timeout=10,
        )
        if p_auth.status_code != 200:
            raise RuntimeError(f"Payment authorize error: {p_auth.text}")
        p_json = p_auth.json()
        if p_json.get("status") != "AUTHORIZED":
            # Compensation: cancel restaurant reservation
            try:
                requests.post(
                    f"{RESTAURANT_URL}/cancel",
                    json={"reservation_id": reservation_id},
                    headers=headers,
                    timeout=10,
                )
            finally:
                pass
            logger.warning("Authorize failed, compensating: cancel reservation_id=%s for order=%s", reservation_id, order_id)
            _fail_order(conn, order_id)
            raise HTTPException(status_code=409, detail="Payment authorization failed")
        payment_id = p_json.get("payment_id")
        logger.info("Payment authorized payment_id=%s for order=%s", payment_id, order_id)

        # Step 3: Capture payment
        p_cap = requests.post(
            f"{PAYMENT_URL}/capture",
            json={"payment_id": payment_id},
            headers=headers,
            timeout=10,
        )
        if p_cap.status_code != 200:
            # Try to refund/void and cancel reservation
            try:
                requests.post(
                    f"{PAYMENT_URL}/refund",
                    json={"payment_id": payment_id},
                    headers=headers,
                    timeout=10,
                )
            finally:
                try:
                    requests.post(
                        f"{RESTAURANT_URL}/cancel",
                        json={"reservation_id": reservation_id},
                        headers=headers,
                        timeout=10,
                    )
                finally:
                    pass
            logger.warning("Capture failed, refund+cancel reservation_id=%s payment_id=%s order=%s", reservation_id, payment_id, order_id)
            _fail_order(conn, order_id)
            raise HTTPException(status_code=409, detail="Payment capture failed")
        p_cap_json = p_cap.json()
        if p_cap_json.get("status") != "CAPTURED":
            # Same compensation path as above
            try:
                requests.post(
                    f"{PAYMENT_URL}/refund",
                    json={"payment_id": payment_id},
                    headers=headers,
                    timeout=10,
                )
            finally:
                try:
                    requests.post(
                        f"{RESTAURANT_URL}/cancel",
                        json={"reservation_id": reservation_id},
                        headers=headers,
                        timeout=10,
                    )
                finally:
                    pass
            logger.warning("Capture status not CAPTURED, refund+cancel reservation_id=%s payment_id=%s order=%s", reservation_id, payment_id, order_id)
            _fail_order(conn, order_id)
            raise HTTPException(status_code=409, detail="Payment capture failed")

        # Success: set CONFIRMED
        cur.execute(
            "UPDATE orders SET status=?, reservation_id=?, payment_id=? WHERE id=?",
            ("CONFIRMED", reservation_id, payment_id, order_id),
        )
        conn.commit()
        logger.info("Order confirmed id=%s reservation_id=%s payment_id=%s", order_id, reservation_id, payment_id)
        return OrderResponse(
            id=order_id,
            status="CONFIRMED",
            amount=amount,
            reservation_id=reservation_id,
            payment_id=payment_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        # Compensation if reservation already made but something else failed
        if reservation_id:
            try:
                requests.post(
                    f"{RESTAURANT_URL}/cancel",
                    json={"reservation_id": reservation_id},
                    headers=headers,
                    timeout=10,
                )
            except Exception:
                pass
        logger.exception("Order processing error for order=%s", order_id)
        _fail_order(conn, order_id)
        raise HTTPException(status_code=500, detail=f"Order processing error: {e}")
    finally:
        conn.close()


def _fail_order(conn: sqlite3.Connection, order_id: str):
    cur = conn.cursor()
    cur.execute("UPDATE orders SET status=? WHERE id=?", ("CANCELED", order_id))
    conn.commit()


@app.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: str, request: Request, _=Depends(require_api_key)):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, status, amount, reservation_id, payment_id FROM orders WHERE id=?",
            (order_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Order not found")
        return OrderResponse(
            id=row["id"],
            status=row["status"],
            amount=row["amount"],
            reservation_id=row["reservation_id"],
            payment_id=row["payment_id"],
        )
    finally:
        conn.close()


@app.exception_handler(Exception)
def unhandled(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": str(exc)})

import os
import uuid
import sqlite3
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from pydantic import BaseModel
import logging


DB_PATH = os.environ.get("DB_PATH", "/data/payment.db")
API_KEY = os.environ.get("API_KEY", "changeme")
FAIL_AUTHORIZE = os.environ.get("PAYMENT_FAIL_AUTHORIZE", "false").lower() in ("1", "true", "yes")

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("payment-service")


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
        CREATE TABLE IF NOT EXISTS payments (
            id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            amount REAL NOT NULL,
            status TEXT NOT NULL,
            auth_code TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


class AuthorizeRequest(BaseModel):
    order_id: str
    amount: float


class AuthorizeResponse(BaseModel):
    payment_id: str
    status: str


class CaptureRequest(BaseModel):
    payment_id: str


class RefundRequest(BaseModel):
    payment_id: str


app = FastAPI(title="Payment Service", version="0.1.0")


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


@app.post("/authorize", response_model=AuthorizeResponse)
def authorize(req: AuthorizeRequest, request: Request, _=Depends(require_api_key)):
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")

    conn = get_db()
    try:
        cur = conn.cursor()
        payment_id = str(uuid.uuid4())
        if FAIL_AUTHORIZE:
            cur.execute(
                "INSERT INTO payments (id, order_id, amount, status, created_at) VALUES (?, ?, ?, ?, ?)",
                (payment_id, req.order_id, req.amount, "FAILED", datetime.utcnow().isoformat()),
            )
            conn.commit()
            logger.warning("Authorize FAILED payment_id=%s order_id=%s amount=%.2f (FAIL_AUTHORIZE=on)", payment_id, req.order_id, req.amount)
            return AuthorizeResponse(payment_id=payment_id, status="FAILED")

        auth_code = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO payments (id, order_id, amount, status, auth_code, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (payment_id, req.order_id, req.amount, "AUTHORIZED", auth_code, datetime.utcnow().isoformat()),
        )
        conn.commit()
        logger.info("Authorized payment_id=%s order_id=%s amount=%.2f", payment_id, req.order_id, req.amount)
        return AuthorizeResponse(payment_id=payment_id, status="AUTHORIZED")
    finally:
        conn.close()


@app.post("/capture")
def capture(req: CaptureRequest, request: Request, _=Depends(require_api_key)):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT status FROM payments WHERE id=?", (req.payment_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Payment not found")
        status = row["status"]
        if status == "CAPTURED":
            logger.info("Capture idempotent payment_id=%s already CAPTURED", req.payment_id)
            return {"status": "CAPTURED"}
        if status != "AUTHORIZED":
            raise HTTPException(status_code=409, detail=f"Invalid status {status}")
        cur.execute("UPDATE payments SET status=? WHERE id=?", ("CAPTURED", req.payment_id))
        conn.commit()
        logger.info("Captured payment_id=%s", req.payment_id)
        return {"status": "CAPTURED"}
    finally:
        conn.close()


@app.post("/refund")
def refund(req: RefundRequest, request: Request, _=Depends(require_api_key)):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT status FROM payments WHERE id=?", (req.payment_id,))
        row = cur.fetchone()
        if not row:
            # idempotent behavior
            logger.info("Refund unknown payment_id=%s -> idempotent REFUNDED", req.payment_id)
            return {"status": "REFUNDED"}
        status = row["status"]
        if status == "REFUNDED":
            logger.info("Refund idempotent payment_id=%s", req.payment_id)
            return {"status": "REFUNDED"}
        if status not in ("AUTHORIZED", "CAPTURED", "FAILED"):
            raise HTTPException(status_code=409, detail=f"Invalid status {status}")
        cur.execute("UPDATE payments SET status=? WHERE id=?", ("REFUNDED", req.payment_id))
        conn.commit()
        logger.info("Refunded payment_id=%s from status=%s", req.payment_id, status)
        return {"status": "REFUNDED"}
    finally:
        conn.close()

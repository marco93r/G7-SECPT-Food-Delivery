from __future__ import annotations

import sqlite3

import pytest

from payment_service.database import apply_schema
from payment_service.repository import PaymentRepository
from payment_service.service import PaymentDeclined, PaymentProcessor, RefundError


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "payment.db"

    def connection_factory():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    with connection_factory() as conn:
        apply_schema(conn)

    return PaymentRepository(connection_factory=connection_factory)


def test_successful_payment(repo):
    processor = PaymentProcessor(repo, failure_mode="none")
    record = processor.create_payment("order-1", 25.0)
    assert record.status == "CAPTURED"
    fetched = repo.get_payment(record.id)
    assert fetched is not None
    assert fetched.amount == 25.0


def test_authorize_failure(repo):
    processor = PaymentProcessor(repo, failure_mode="authorize")
    with pytest.raises(PaymentDeclined):
        processor.create_payment("order-2", 10.0)


def test_refund(repo):
    processor = PaymentProcessor(repo)
    record = processor.create_payment("order-3", 12.0)
    refunded = processor.refund(record.id)
    assert refunded.status == "REFUNDED"


def test_refund_failure(repo):
    processor = PaymentProcessor(repo, failure_mode="refund")
    record = processor.create_payment("order-4", 12.0)
    with pytest.raises(RefundError):
        processor.refund(record.id)

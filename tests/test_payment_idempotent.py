import pytest
from app.domain import stubs, store

pytestmark = pytest.mark.asyncio

async def test_payment_idempotent(monkeypatch):
    async def noop():
        return
    monkeypatch.setattr(stubs, "flaky_call", noop)

    order = {"order_id": "ord_pay_idem", "items": [{"sku": "A", "qty": 2}]}
    await store.create_order(order["order_id"], {})
    await store.update_order_state(order["order_id"], "validated")

    r1 = await stubs.payment_charged(order, "pay_dup")
    r2 = await stubs.payment_charged(order, "pay_dup")
    assert r1["status"] == "charged" and r2["status"] == "charged"



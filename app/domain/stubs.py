import asyncio, random
from typing import Dict, Any
from app.domain import store

async def flaky_call() -> None:
    """Either raise an error or sleep long enough to trigger an activity timeout."""
    rand_num = random.random()
    if rand_num < 0.33:
        raise RuntimeError("Forced failure for testing")
    if rand_num < 0.67:
        await asyncio.sleep(300)  # Expect the activity layer to time out before this completes

async def order_received(order_id: str, address: dict | None = None) -> Dict[str, Any]:
    await flaky_call()
    await store.create_order(order_id, address or {})
    await store.append_event(order_id, "order_received", {"address": address or {}})
    return {"order_id": order_id, "items": [{"sku": "ABC", "qty": 1}], "address": address or {}}

async def order_validated(order: Dict[str, Any]) -> bool:
    await flaky_call()
    if not order.get("items"):
        await store.append_event(order["order_id"], "validation_failed", {"reason": "no_items"})
        raise ValueError("No items to validate")
    await store.update_order_state(order["order_id"], "validated")
    await store.append_event(order["order_id"], "order_validated", {})
    return True

async def payment_charged(order: Dict[str, Any], payment_id: str) -> Dict[str, Any]:
    """Charge payment after simulating an error/timeout first. Idempotent by payment_id."""
    await flaky_call()
    amount = sum(int(i.get("qty", 1)) for i in order.get("items", []))
    existed = await store.insert_payment(payment_id, order["order_id"], "charged", amount)
    await store.append_event(order["order_id"], "payment_charged", {"payment_id": payment_id, "amount": amount, "already": existed})
    return {"status": "charged", "amount": amount, "payment_id": payment_id}

async def order_shipped(order: Dict[str, Any]) -> str:
    await flaky_call()
    await store.update_order_state(order["order_id"], "shipped")
    await store.append_event(order["order_id"], "order_shipped", {})
    return "Shipped"

async def package_prepared(order: Dict[str, Any]) -> str:
    await flaky_call()
    await store.append_event(order["order_id"], "package_prepared", {})
    return "Package ready"

async def carrier_dispatched(order: Dict[str, Any]) -> str:
    await flaky_call()
    await store.append_event(order["order_id"], "carrier_dispatched", {})
    return "Dispatched"




from temporalio import activity
import structlog
from app.domain import stubs, store

log = structlog.get_logger()

@activity.defn
async def receive_order(order_id: str, address: dict | None) -> dict:
    try:
        result = await stubs.order_received(order_id, address or {})
        log.info("activity_receive_order", order_id=order_id, activity="receive_order")
        return result
    except Exception as e:
        log.error("activity_receive_order_error", order_id=order_id, activity="receive_order", error=str(e))
        raise

@activity.defn
async def validate_order(order: dict) -> bool:
    try:
        ok = await stubs.order_validated(order)
        log.info("activity_validate_order", order_id=order["order_id"], activity="validate_order")
        return ok
    except Exception as e:
        log.error("activity_validate_order_error", order_id=order["order_id"], activity="validate_order", error=str(e))
        raise

@activity.defn
async def charge_payment(order: dict, payment_id: str) -> dict:
    try:
        result = await stubs.payment_charged(order, payment_id)
        log.info("activity_charge_payment", order_id=order["order_id"], activity="charge_payment")
        return result
    except Exception as e:
        log.error("activity_charge_payment_error", order_id=order["order_id"], activity="charge_payment", error=str(e))
        raise

@activity.defn
async def mark_order_shipped(order: dict) -> str:
    try:
        result = await stubs.order_shipped(order)
        log.info("activity_order_shipped", order_id=order["order_id"], activity="order_shipped")
        return result
    except Exception as e:
        log.error("activity_order_shipped_error", order_id=order["order_id"], activity="order_shipped", error=str(e))
        raise

@activity.defn
async def set_order_state(order_id: str, state: str) -> None:
    await store.update_order_state(order_id, state)
    await store.append_event(order_id, f"state_{state}", {})

@activity.defn
async def update_order_address(order_id: str, address: dict) -> None:
    await store.update_address(order_id, address)
    await store.append_event(order_id, "address_updated", {"address": address})

@activity.defn
async def append_event(order_id: str, type_: str, payload: dict | None = None) -> None:
    await store.append_event(order_id, type_, payload or {})




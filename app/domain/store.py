from typing import Any
from app import db

async def create_order(order_id: str, address: dict):
    await db.execute(
        """
        INSERT INTO orders(id, state, address_json)
        VALUES (:id, 'received', CAST(:addr AS JSONB))
        ON CONFLICT (id) DO NOTHING
        """,
        {"id": order_id, "addr": db.json_dumps(address)},
    )

async def update_order_state(order_id: str, state: str):
    await db.execute(
        """
        UPDATE orders
        SET state = :state, updated_at = now()
        WHERE id = :id
        """,
        {"id": order_id, "state": state},
    )

async def update_address(order_id: str, address: dict):
    await db.execute(
        """
        UPDATE orders
        SET address_json = CAST(:addr AS JSONB), updated_at = now()
        WHERE id = :id
        """,
        {"id": order_id, "addr": db.json_dumps(address)},
    )

async def append_event(order_id: str, type_: str, payload: dict | None):
    await db.execute(
        """
        INSERT INTO events(order_id, type, payload_json)
        VALUES (:oid, :type, CAST(:payload AS JSONB))
        """,
        {"oid": order_id, "type": type_, "payload": db.json_dumps(payload or {})},
    )

async def get_order(order_id: str) -> dict | None:
    return await db.fetchone(
        "SELECT id, state, address_json, created_at, updated_at FROM orders WHERE id=:id",
        {"id": order_id},
    )

async def get_payment_by_id(payment_id: str) -> dict | None:
    return await db.fetchone(
        "SELECT payment_id, order_id, status, amount, created_at FROM payments WHERE payment_id=:pid",
        {"pid": payment_id},
    )

async def insert_payment(payment_id: str, order_id: str, status: str, amount: int | float) -> bool:
    # returns True if already existed, False if inserted now
    existing = await get_payment_by_id(payment_id)
    if existing:
        return True
    await db.execute(
        """
        INSERT INTO payments(payment_id, order_id, status, amount)
        VALUES (:pid, :oid, :status, :amount)
        ON CONFLICT (payment_id) DO NOTHING
        """,
        {"pid": payment_id, "oid": order_id, "status": status, "amount": amount},
    )
    return False

async def get_recent_events(order_id: str, limit: int = 20) -> list[dict[str, Any]]:
    rows = await db.fetchall(
        "SELECT id, order_id, type, payload_json, ts FROM events WHERE order_id=:id ORDER BY ts DESC LIMIT :limit",
        {"id": order_id, "limit": limit},
    )
    return rows



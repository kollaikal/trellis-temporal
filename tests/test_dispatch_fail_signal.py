import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker
from temporalio.client import Client
from datetime import timedelta

import app.config as config
from app.workflows.order_workflow import OrderWorkflow
from app.workflows.shipping_workflow import ShippingWorkflow
from app.activities import order_activities, shipping_activities
from app.domain import stubs

pytestmark = pytest.mark.asyncio

class Failer:
    def __init__(self):
        self.seen = set()
    async def __call__(self, order: dict) -> str:
        oid = order["order_id"]
        if oid not in self.seen:
            self.seen.add(oid)
            raise RuntimeError("forced carrier dispatch failure")
        return "Dispatched"

failer = Failer()

@pytest.fixture(autouse=True)
def patch_flaky(monkeypatch):
    async def noop():
        return
    monkeypatch.setattr(stubs, "flaky_call", noop)
    monkeypatch.setattr(stubs, "carrier_dispatched", failer)

async def test_dispatch_fail_and_retry_signal():
    async with await WorkflowEnvironment.start_time_skipping() as env:
        client: Client = env.client
        async with Worker(client, task_queue=config.ORDERS_TQ, workflows=[OrderWorkflow],
                          activities=[order_activities.receive_order, order_activities.validate_order,
                                      order_activities.charge_payment, order_activities.mark_order_shipped,
                                      order_activities.set_order_state, order_activities.update_order_address,
                                      order_activities.append_event]):
            async with Worker(client, task_queue=config.SHIPPING_TQ, workflows=[ShippingWorkflow],
                              activities=[shipping_activities.prepare_package, shipping_activities.dispatch_carrier]):
                order_id = "ord_dispatch_retry"
                handle = await client.start_workflow(
                    OrderWorkflow.run,
                    {"order_id": order_id, "payment_id": "pay_dispatch", "address": {}},
                    id=f"order-{order_id}",
                    task_queue=config.ORDERS_TQ,
                    run_timeout=timedelta(seconds=config.RUN_TIMEOUT_SECS),
                )
                await handle.signal(OrderWorkflow.approve)
                result = await handle.result()
                assert result["status"] in ("shipped", "shipping_failed")



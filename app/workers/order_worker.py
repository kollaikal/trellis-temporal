import asyncio, structlog, os
from temporalio.worker import Worker
from temporalio.client import Client
from app.logging_setup import setup_logging
import app.config as config
from app.workflows.order_workflow import OrderWorkflow
from app.activities import order_activities
from app.domain import stubs

async def main():
    setup_logging()
    log = structlog.get_logger().bind(worker="order")
    if os.getenv("DISABLE_FLAKY") == "1":
        async def _no_flaky():
            return
        stubs.flaky_call = _no_flaky  # type: ignore
        log.info("flaky_call_disabled_for_demo")
    client = await Client.connect(config.TEMPORAL_TARGET)
    log.info("worker_starting", queue=config.ORDERS_TQ)
    async with Worker(
        client,
        task_queue=config.ORDERS_TQ,
        workflows=[OrderWorkflow],
        activities=[
            order_activities.receive_order,
            order_activities.validate_order,
            order_activities.charge_payment,
            order_activities.mark_order_shipped,
            order_activities.set_order_state,
            order_activities.update_order_address,
            order_activities.append_event,
        ],
    ):
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())



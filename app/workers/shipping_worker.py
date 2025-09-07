import asyncio, structlog, os
from temporalio.worker import Worker
from temporalio.client import Client
from app.logging_setup import setup_logging
import app.config as config
from app.workflows.shipping_workflow import ShippingWorkflow
from app.activities import shipping_activities
from app.domain import stubs

async def main():
    setup_logging()
    log = structlog.get_logger().bind(worker="shipping")
    if os.getenv("DISABLE_FLAKY") == "1":
        async def _no_flaky():
            return
        stubs.flaky_call = _no_flaky  # type: ignore
        log.info("flaky_call_disabled_for_demo")
    client = await Client.connect(config.TEMPORAL_TARGET)
    log.info("worker_starting", queue=config.SHIPPING_TQ)
    async with Worker(
        client,
        task_queue=config.SHIPPING_TQ,
        workflows=[ShippingWorkflow],
        activities=[shipping_activities.prepare_package, shipping_activities.dispatch_carrier],
    ):
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())



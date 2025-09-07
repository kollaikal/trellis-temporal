from temporalio import activity
import structlog
from app.domain import stubs

log = structlog.get_logger()

@activity.defn
async def prepare_package(order: dict) -> str:
    try:
        result = await stubs.package_prepared(order)
        log.info("activity_prepare_package", order_id=order["order_id"], activity="prepare_package")
        return result
    except Exception as e:
        log.error("activity_prepare_package_error", order_id=order["order_id"], activity="prepare_package", error=str(e))
        raise

@activity.defn
async def dispatch_carrier(order: dict) -> str:
    try:
        result = await stubs.carrier_dispatched(order)
        log.info("activity_dispatch_carrier", order_id=order["order_id"], activity="dispatch_carrier")
        return result
    except Exception as e:
        log.error("activity_dispatch_carrier_error", order_id=order["order_id"], activity="dispatch_carrier", error=str(e))
        raise




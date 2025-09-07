import os
from datetime import timedelta
from temporalio.common import RetryPolicy

ORDERS_TQ = os.getenv("ORDERS_TQ", "orders-tq")
SHIPPING_TQ = os.getenv("SHIPPING_TQ", "shipping-tq")
TEMPORAL_TARGET = os.getenv("TEMPORAL_TARGET", "localhost:7233")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/temporal_demo")

RUN_TIMEOUT_SECS = int(os.getenv("RUN_TIMEOUT_SECS", "15"))
CHILD_RUN_TIMEOUT_SECS = int(os.getenv("CHILD_RUN_TIMEOUT_SECS", "8"))
MANUAL_REVIEW_SECS = int(os.getenv("MANUAL_REVIEW_SECS", "2"))

# Activity options to be used at workflow call sites
ACTIVITY_KWARGS = dict(
    start_to_close_timeout=timedelta(seconds=3),
    schedule_to_close_timeout=timedelta(seconds=6),
    retry_policy=RetryPolicy(
        maximum_attempts=5,
        initial_interval=timedelta(milliseconds=200),
        backoff_coefficient=2.0,
        maximum_interval=timedelta(seconds=2),
    ),
)



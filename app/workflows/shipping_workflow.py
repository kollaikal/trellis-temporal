from __future__ import annotations
from typing import Any
from temporalio import workflow
import app.config as config
from app.activities import shipping_activities

@workflow.defn
class ShippingWorkflow:
    @workflow.run
    async def run(self, inputs: dict) -> dict[str, Any]:
        order: dict = inputs["order"]

        await workflow.execute_activity(
            shipping_activities.prepare_package,
            args=[order],
            **config.ACTIVITY_KWARGS,
        )

        try:
            await workflow.execute_activity(
                shipping_activities.dispatch_carrier,
                args=[order],
                **config.ACTIVITY_KWARGS,
            )
        except Exception as e:
            if workflow.info().parent_workflow_id:
                parent = workflow.get_external_workflow_handle(workflow.info().parent_workflow_id)
                await parent.signal("dispatch_failed", str(e))
            raise

        return {"status": "dispatched"}




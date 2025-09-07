from __future__ import annotations
from dataclasses import dataclass
from datetime import timedelta
from temporalio import workflow
from typing import Optional

import app.config as config
from app.activities import order_activities
from app.workflows.shipping_workflow import ShippingWorkflow


@dataclass
class OrderState:
    order_id: str
    address: dict
    validated: bool = False
    payment_status: Optional[str] = None
    shipping_attempts: int = 0
    cancelled: bool = False
    approved: bool = False
    last_error: Optional[str] = None
    current_step: str = "start"


@workflow.defn
class OrderWorkflow:
    def __init__(self) -> None:
        self.state: Optional[OrderState] = None
        self._dispatch_failed_reason: Optional[str] = None

    @workflow.signal
    def cancel(self) -> None:
        if self.state:
            self.state.cancelled = True

    @workflow.signal
    def update_address(self, address: dict) -> None:
        if self.state:
            self.state.address = address
            workflow.start_activity(
                order_activities.update_order_address,
                self.state.order_id,
                address,
                **config.ACTIVITY_KWARGS,
            )

    @workflow.signal
    def approve(self) -> None:
        if self.state:
            self.state.approved = True

    @workflow.signal
    def dispatch_failed(self, reason: str) -> None:
        self._dispatch_failed_reason = reason
        if self.state:
            self.state.last_error = reason

    @workflow.query
    def status(self) -> dict:
        s = self.state
        return {
            "order_id": s.order_id if s else None,
            "current_step": s.current_step if s else None,
            "validated": s.validated if s else False,
            "payment_status": s.payment_status if s else None,
            "shipping_attempts": s.shipping_attempts if s else 0,
            "cancelled": s.cancelled if s else False,
            "approved": s.approved if s else False,
            "last_error": s.last_error if s else None,
        }

    @workflow.run
    async def run(self, inputs: dict) -> dict:
        order_id: str = inputs["order_id"]
        payment_id: str = inputs["payment_id"]
        address: dict = inputs.get("address") or {}

        self.state = OrderState(order_id=order_id, address=address)
        self.state.current_step = "receive_order"

        order = await workflow.execute_activity(
            order_activities.receive_order,
            args=[order_id, address],
            **config.ACTIVITY_KWARGS,
        )

        self.state.current_step = "validate_order"
        await workflow.execute_activity(
            order_activities.validate_order,
            args=[order],
            **config.ACTIVITY_KWARGS,
        )
        self.state.validated = True

        # Manual review wait: poll for approval up to MANUAL_REVIEW_SECS
        self.state.current_step = "manual_review"
        end_time = workflow.now() + timedelta(seconds=config.MANUAL_REVIEW_SECS)
        while not self.state.approved and workflow.now() < end_time:
            await workflow.sleep(timedelta(milliseconds=100))

        if self.state.cancelled:
            self.state.current_step = "cancelled"
            await workflow.execute_activity(
                order_activities.set_order_state,
                args=[order_id, "cancelled"],
                **config.ACTIVITY_KWARGS,
            )
            return {"status": "cancelled"}

        self.state.current_step = "charge_payment"
        pay = await workflow.execute_activity(
            order_activities.charge_payment,
            args=[order, payment_id],
            **config.ACTIVITY_KWARGS,
        )
        self.state.payment_status = pay.get("status")

        if self.state.cancelled:
            self.state.current_step = "cancelled"
            await workflow.execute_activity(
                order_activities.set_order_state,
                args=[order_id, "cancelled"],
                **config.ACTIVITY_KWARGS,
            )
            return {"status": "cancelled"}

        # Start shipping child workflow and handle retry on dispatch failure
        max_attempts = 2
        while self.state.shipping_attempts < max_attempts:
            self.state.shipping_attempts += 1
            self.state.current_step = f"shipping_attempt_{self.state.shipping_attempts}"
            self._dispatch_failed_reason = None

            handle = await workflow.start_child_workflow(
                ShippingWorkflow.run,
                {"order": order},
                id=f"ship-{order_id}-{self.state.shipping_attempts}",
                task_queue=config.SHIPPING_TQ,
                run_timeout=timedelta(seconds=config.CHILD_RUN_TIMEOUT_SECS),
            )

            try:
                await handle.result()
                break
            except Exception as e:
                self.state.last_error = str(e)
                await workflow.execute_activity(
                    order_activities.append_event,
                    args=[order_id, "dispatch_failed", {"reason": self._dispatch_failed_reason or str(e)}],
                    **config.ACTIVITY_KWARGS,
                )
                if self.state.shipping_attempts >= max_attempts or self.state.cancelled:
                    await workflow.execute_activity(
                        order_activities.set_order_state,
                        args=[order_id, "shipping_failed"],
                        **config.ACTIVITY_KWARGS,
                    )
                    self.state.current_step = "shipping_failed"
                    return {"status": "shipping_failed", "reason": self._dispatch_failed_reason or str(e)}

        self.state.current_step = "order_shipped"
        await workflow.execute_activity(
            order_activities.mark_order_shipped,
            args=[order],
            **config.ACTIVITY_KWARGS,
        )
        return {"status": "shipped"}




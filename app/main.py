import structlog
from fastapi import FastAPI, HTTPException
from temporalio.client import Client
from datetime import timedelta

from app.logging_setup import setup_logging
import app.config as config
from app.schemas import StartOrderRequest, UpdateAddressRequest, StatusResponse
from app.domain import store
from app.workflows.order_workflow import OrderWorkflow

setup_logging()
log = structlog.get_logger().bind(service="api")

app = FastAPI(title="Trellis Temporal Demo")
temporal_client: Client | None = None

@app.on_event("startup")
async def on_startup():
    global temporal_client
    temporal_client = await Client.connect(config.TEMPORAL_TARGET)
    log.info("startup_complete", temporal=config.TEMPORAL_TARGET)

def wf_id(order_id: str) -> str:
    return f"order-{order_id}"

@app.post("/orders/{order_id}/start")
async def start_order(order_id: str, req: StartOrderRequest):
    assert temporal_client
    try:
        handle = await temporal_client.start_workflow(
            OrderWorkflow.run,
            {"order_id": order_id, "payment_id": req.payment_id, "address": req.address},
            id=wf_id(order_id),
            task_queue=config.ORDERS_TQ,
            run_timeout=timedelta(seconds=config.RUN_TIMEOUT_SECS),
        )
        return {"workflow_id": handle.id, "run_id": handle.first_execution_run_id}
    except Exception as e:
        raise HTTPException(status_code=409, detail=str(e))

@app.post("/orders/{order_id}/signals/cancel")
async def signal_cancel(order_id: str):
    assert temporal_client
    handle = temporal_client.get_workflow_handle(wf_id(order_id))
    await handle.signal(OrderWorkflow.cancel)
    return {"ok": True}

@app.post("/orders/{order_id}/signals/update-address")
async def signal_update_address(order_id: str, req: UpdateAddressRequest):
    assert temporal_client
    handle = temporal_client.get_workflow_handle(wf_id(order_id))
    await handle.signal(OrderWorkflow.update_address, req.address)
    return {"ok": True}

@app.post("/orders/{order_id}/signals/approve")
async def signal_approve(order_id: str):
    assert temporal_client
    handle = temporal_client.get_workflow_handle(wf_id(order_id))
    await handle.signal(OrderWorkflow.approve)
    return {"ok": True}

@app.get("/orders/{order_id}/status", response_model=StatusResponse)
async def get_status(order_id: str):
    assert temporal_client
    handle = temporal_client.get_workflow_handle(wf_id(order_id))
    wf = {}
    try:
        wf = await handle.query(OrderWorkflow.status)
    except Exception as e:
        wf = {"error": str(e)}

    events = await store.get_recent_events(order_id, limit=20)
    order_row = await store.get_order(order_id)
    return StatusResponse(workflow=wf, events=events, db_order=order_row)




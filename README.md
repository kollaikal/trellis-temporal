## Trellis Temporal (Order → Payment → Shipping)

### Overview

- Parent `OrderWorkflow` on `orders-tq`: Receive → Validate → Manual review timer/signal → Charge → start child Shipping.
- Child `ShippingWorkflow` on `shipping-tq`: PreparePackage → DispatchCarrier; on dispatch failure, signals parent `dispatch_failed` and rethrows; parent retries bounded attempts.
- Activities call stubs that always call `flaky_call()` first to simulate failures/timeouts.
- Persistence: Postgres (orders, payments, events). Payment idempotency via `payments.payment_id` upsert.
- Observability: structured JSON logs; `/status` combines workflow query + last 20 events.
- Time limits: parent run timeout 15s; child run timeout 8s; activities 3s start-to-close w/ retries.

### Prereqs

- Docker + Docker Compose
- Temporal open‑source dev server (brew install)

### Quickstart (Open‑source Temporal dev server)

```bash
# 0) Start Temporal dev server locally (open‑source)
brew install temporal || true
temporal server start-dev  # RPC: 7233, UI: 8233

# 1) In another terminal, start Postgres only
make up

# 2) Apply DB migration
make migrate

# 3) Start workers and API
make workers
make api

# 4) Start a workflow
curl -sS -X POST http://localhost:8000/orders/ord_123/start \
  -H 'content-type: application/json' \
  -d '{"payment_id":"pay_123","address":{"line1":"123 Main","city":"Davis"}}' | jq

# 5) Approve to bypass manual timer
curl -sS -X POST http://localhost:8000/orders/ord_123/signals/approve | jq

# 6) Update address (before shipping dispatch)
curl -sS -X POST http://localhost:8000/orders/ord_123/signals/update-address \
  -H 'content-type: application/json' -d '{"address":{"line1":"456 Oak"}}' | jq

# 7) Optional cancel (before ship)
curl -sS -X POST http://localhost:8000/orders/ord_123/signals/cancel | jq

# 8) Inspect status
curl -sS http://localhost:8000/orders/ord_123/status | jq
```

### Alternate: Run Temporal via Docker (sqlite)

```bash
docker rm -f temporal || true
docker run --rm -d --name temporal -e DB=sqlite -p 7233:7233 temporalio/auto-setup
# workers/API already point to TEMPORAL_TARGET=host.docker.internal:7233
```

### Design notes

- Determinism: all randomness/sleeps only inside activities via `flaky_call()`. Workflows only use timers/signals/child workflows.
- Timeouts & retries: activities use short timeouts to demonstrate timeouts vs the 300s sleeps in `flaky_call()`.
- Idempotency: `INSERT ... ON CONFLICT DO NOTHING` by `payment_id`. Replays/retries are safe; duplicates are no-ops.
- Signals:
  - `cancel`: marks cancelled and exits early if before shipping.
  - `update_address`: persists new address via activity.
  - `approve`: bypasses manual review wait.
  - Child → parent: `dispatch_failed(reason)`; parent appends event and retries up to 2 times.
- Status endpoint: returns workflow `status()` query + last 20 DB events + current DB `orders` row.

### Run tests

```bash
make test
```

### Services

- Temporal dev server: `temporal server start-dev` (UI: http://localhost:8233, RPC: 7233)
- `db`: Postgres 16
- `api`: FastAPI service on 8000
- `order-worker` & `shipping-worker`: Temporal workers for respective task queues

### Troubleshooting

- Temporal UI: http://localhost:8233 (namespace `default`).
- If API not ready: retry `curl http://localhost:8000/docs` after a few seconds.
- If activities hang: ensure workers are up and Temporal server is running.
- Logs: `docker compose logs -f order-worker|shipping-worker|api`.

### Submission checklist

- Start via brew Temporal dev server and Makefile targets works on a fresh machine.
- `make test` passes.
- Endpoints respond and events appear in DB and Temporal UI.

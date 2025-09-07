SHELL := /bin/bash

up:
	docker compose up -d db

up-temporal-dev:
	@which temporal >/dev/null 2>&1 || brew install temporal
	@echo "Starting Temporal dev server..."
	@pkill -f "temporal server start-dev" 2>/dev/null || true
	@nohup temporal server start-dev >/tmp/temporal-dev.log 2>&1 &

migrate:
	docker compose run --no-deps -e PYTHONPATH=/app --rm api sh -c "pip install -r requirements.txt && python -m app.migrate"

api:
	docker compose up -d api

workers:
	docker compose up -d order-worker shipping-worker

seed-run:
	curl -sS -X POST http://localhost:8000/orders/ord_123/start \
		-H 'content-type: application/json' \
		-d '{"payment_id":"pay_123","address":{"line1":"123 Main","city":"Davis"}}' | jq

logs:
	docker compose logs -f

down:
	docker compose down -v

test:
	docker compose up -d db
	docker compose run --no-deps -e PYTHONPATH=/app --rm api sh -c "pip install -r requirements.txt && python -m app.migrate && pytest -q"


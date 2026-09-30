.PHONY: db api web worker test migrate

db:
	docker compose up -d

migrate:
	cd apps/api && .venv/bin/alembic upgrade head

api:
	cd apps/api && .venv/bin/uvicorn app.main:app --reload --port 8000

worker:
	cd apps/api && .venv/bin/python -m app.worker

web:
	cd apps/web && npm run dev

test:
	cd apps/api && .venv/bin/pytest

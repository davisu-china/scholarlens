.PHONY: install dev api worker web test lint fmt eval infra

install:
	uv sync --extra dev
	cd apps/web && npm install

infra:
	docker compose -f deploy/docker-compose.yml up -d

api:
	uv run uvicorn apps.api.main:app --reload --port 8000

worker:
	uv run celery -A apps.worker.celery_app worker -l info

web:
	cd apps/web && npm run dev

test:
	uv run pytest -q

lint:
	uv run ruff check core apps eval tests
	uv run mypy core

fmt:
	uv run ruff format core apps eval tests

eval:
	uv run python -m eval.cli $(SUITE)

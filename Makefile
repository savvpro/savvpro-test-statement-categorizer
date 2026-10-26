.PHONY: setup backend frontend test lint build

setup:
	cd backend && python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
	cd frontend && npm install

backend:
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && .venv/bin/python scripts/fetch_reference_samples.py && .venv/bin/pytest
	cd frontend && npm test

lint:
	cd backend && .venv/bin/ruff check .
	cd frontend && npm run lint && npm run typecheck

build:
	docker compose build

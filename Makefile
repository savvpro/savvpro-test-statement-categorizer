.PHONY: setup dev lint fmt typecheck test test-fast eval fe-test fe-build e2e openapi guard check up down samples clean

BACKEND := backend
FRONTEND := frontend

setup:
	cd $(BACKEND) && uv sync --frozen
	cd $(FRONTEND) && npm ci
	uvx pre-commit install

dev:
	@trap 'kill 0' EXIT; (cd $(BACKEND) && uv run uvicorn app.main:create_app --factory --reload --port 8000) & (cd $(FRONTEND) && npm run dev); wait

lint:
	cd $(BACKEND) && uv run ruff check . && uv run ruff format --check .
	cd $(FRONTEND) && npm run lint

fmt:
	cd $(BACKEND) && uv run ruff format . && uv run ruff check --fix .

typecheck:
	cd $(BACKEND) && uv run mypy app
	cd $(FRONTEND) && npm run typecheck

test:
	cd $(BACKEND) && uv run pytest --cov=app --cov-fail-under=85

test-fast:
	cd $(BACKEND) && uv run pytest -x -q tests/unit

eval:
	cd $(BACKEND) && uv run python ../scripts/evaluate_brain.py --gate

fe-test:
	cd $(FRONTEND) && npm run test -- --run

fe-build:
	cd $(FRONTEND) && npm run build

e2e:
	cd $(FRONTEND) && npx playwright test

openapi:
	cd $(BACKEND) && uv run python ../scripts/export_openapi.py && cd ../frontend && npm run gen:api

guard:
	bash scripts/check_no_llm_deps.sh

check: lint typecheck test eval guard fe-test fe-build

up:
	docker compose up -d --build --wait

down:
	docker compose down

samples:
	python scripts/generate_samples.py

clean:
	rm -rf $(BACKEND)/.pytest_cache $(BACKEND)/.mypy_cache $(BACKEND)/.ruff_cache $(BACKEND)/htmlcov $(BACKEND)/.coverage $(BACKEND)/coverage.xml $(BACKEND)/junit.xml
	rm -rf $(FRONTEND)/.next $(FRONTEND)/out $(FRONTEND)/coverage $(FRONTEND)/playwright-report $(FRONTEND)/test-results
	find $(BACKEND) -name __pycache__ -type d -prune -exec rm -rf {} +

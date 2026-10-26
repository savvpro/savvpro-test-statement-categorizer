# Developer shortcuts. Run `make help` for the list.
PYTHON ?= python3
VENV := backend/.venv
BIN := $(VENV)/bin

.PHONY: help setup backend frontend test lint eval clean

help:
	@echo "make setup     create backend/.venv and install backend + frontend dependencies"
	@echo "make backend   run the API on http://localhost:8000 (auto-reload)"
	@echo "make frontend  run the UI on http://localhost:5173 (proxies /api to :8000)"
	@echo "make test      backend pytest + frontend vitest"
	@echo "make lint      ruff check + ruff format --check + oxlint"
	@echo "make eval      score the brain against the hand-labelled golden set"
	@echo "make clean     remove the venv, node_modules, build output, caches and the local DB"

setup:
	cd backend && $(PYTHON) -m venv .venv && .venv/bin/pip install --quiet --upgrade pip \
		&& .venv/bin/pip install --quiet -e ".[dev]"
	@# macOS + Python 3.14 skips .pth files that carry the "hidden" flag, which breaks the
	@# editable install. Clearing the flag is harmless elsewhere.
	@if [ "$$(uname)" = "Darwin" ]; then chflags nohidden $(VENV)/lib/python3*/site-packages/*.pth; fi
	cd frontend && npm ci

backend:
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && .venv/bin/pytest -q
	cd frontend && npm test

lint:
	cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check .
	cd frontend && npm run lint

eval:
	cd backend && .venv/bin/python scripts/evaluate.py

clean:
	rm -rf $(VENV) backend/data backend/.pytest_cache backend/.ruff_cache backend/.coverage \
		backend/*.egg-info frontend/node_modules frontend/dist
	find backend -name __pycache__ -type d -prune -exec rm -rf {} +

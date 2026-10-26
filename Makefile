.PHONY: help install test test-backend test-frontend lint run-backend run-frontend build

help:
	@echo "Available commands:"
	@echo "  make install        Install backend and frontend dependencies"
	@echo "  make test           Run all backend and frontend tests"
	@echo "  make test-backend   Run pytest backend test suite"
	@echo "  make test-frontend  Run vitest frontend tests"
	@echo "  make lint           Run ruff linter on backend"
	@echo "  make run-backend    Start FastAPI backend server on :8000"
	@echo "  make run-frontend   Start Vite frontend server on :5173"
	@echo "  make build          Build production assets"

install:
	pip install -r backend/requirements.txt
	cd frontend && npm install

test: test-backend test-frontend

test-backend:
	PYTHONPATH=backend pytest backend/tests -v

test-frontend:
	cd frontend && npm test

lint:
	ruff check backend

run-backend:
	PYTHONPATH=backend uvicorn app.main:app --app-dir backend --reload --port 8000

run-frontend:
	cd frontend && npm run dev

build:
	cd frontend && npm run build

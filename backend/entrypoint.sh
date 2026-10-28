#!/bin/sh
# Apply migrations, then replace this shell with the API server (PID 1 gets signals).
set -eu

alembic upgrade head
exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --proxy-headers

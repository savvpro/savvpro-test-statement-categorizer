# syntax=docker/dockerfile:1

# ---- build: resolve locked dependencies into /app/.venv ----
FROM python:3.13-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /uvx /usr/local/bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---- runtime: no toolchain, non-root, app code only ----
FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --home-dir /app --shell /usr/sbin/nologin app \
 && install -d -o 10001 -g 10001 -m 0750 /app/data

WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY app ./app
COPY rules ./rules
COPY migrations ./migrations
COPY alembic.ini entrypoint.sh ./
RUN chmod 0755 /app/entrypoint.sh

USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)" || exit 1

ENTRYPOINT ["./entrypoint.sh"]

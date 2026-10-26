# Build context: repository root (so the fake sample statements can be bundled).
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:////data/ledgerlite.db \
    SAMPLE_DATA_DIR=/app/sample_data

WORKDIR /app/backend

COPY backend/pyproject.toml ./
COPY backend/app ./app
RUN pip install --no-cache-dir . \
    && useradd --create-home --uid 1000 ledgerlite \
    && mkdir -p /data && chown ledgerlite /data

COPY sample_data /app/sample_data

USER ledgerlite
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

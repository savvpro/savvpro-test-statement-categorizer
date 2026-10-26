# Build from the repo root so the sample files can be copied in:
#   docker build -f backend/Dockerfile .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATABASE_URL=sqlite:////data/app.db \
    SAMPLES_DIR=/app/samples \
    CORS_ORIGINS=http://localhost:8080

WORKDIR /app
RUN useradd --create-home --uid 10001 app && mkdir /data && chown app /data

COPY backend/pyproject.toml backend/README.md ./
COPY backend/app ./app
RUN pip install .

COPY samples ./samples

USER app
EXPOSE 8000
VOLUME ["/data"]
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

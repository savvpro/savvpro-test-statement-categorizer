# 08 — CI/CD & DevOps

## 1. Local developer experience
- **Makefile** targets: `setup` (uv sync, npm ci, pre-commit install), `dev` (backend uvicorn --reload + next dev), `lint`, `fmt`, `typecheck`, `test`, `test-fast`, `eval`, `fe-test`, `e2e`, `openapi` (export + gen TS), `check` (= CI), `up`/`down` (compose), `samples` (regenerate fake data), `clean`.
- Windows note in README: `make` via Git Bash, or equivalent `npm`/`uv` commands listed.
- **pre-commit** (`.pre-commit-config.yaml`): trailing-whitespace, end-of-file-fixer, check-yaml, check-merge-conflict, check-added-large-files (500 KB), ruff (lint + format), mypy (backend), prettier + eslint (frontend, via local hook), gitleaks.
- `.editorconfig`, `.gitattributes` (`* text=auto eol=lf`; `samples/**/*crlf*.csv -text`), `.gitignore` (py, node, .env, data/, coverage, playwright-report, .next).

## 2. Docker
**backend/Dockerfile** (multi-stage)
```
FROM python:3.13-slim AS build   → install uv, `uv sync --frozen --no-dev` into /app/.venv
FROM python:3.13-slim AS runtime → copy .venv + app + rules + migrations + alembic.ini
  useradd -u 10001 app; USER app; ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
  HEALTHCHECK python -c "urllib.request.urlopen('http://127.0.0.1:8000/healthz')"
  ENTRYPOINT ["./entrypoint.sh"]  # alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
```
**frontend/Dockerfile**
```
FROM node:24-alpine AS deps   → npm ci
FROM node:24-alpine AS build  → npm run build (output: standalone)
FROM node:24-alpine AS runtime→ copy .next/standalone + static + public; USER node; HEALTHCHECK wget /; CMD node server.js
```
`.dockerignore` for both (node_modules, .venv, tests, .git, data).

**docker-compose.yml**
- `api`: build backend, env from `.env` (optional), volume `appdata:/app/data`, healthcheck, `expose: 8000` (not published by default).
- `web`: build frontend, env `API_INTERNAL_URL=http://api:8000`, `ports: 3000:3000`, `depends_on: api: condition: service_healthy`.
- Profile `dev` overrides publish api `8000:8000` for Swagger.
- Read-only root FS + tmpfs `/tmp` for api (writable only the data volume).

## 3. CI — `.github/workflows/ci.yml`
Triggers: `push` (all branches), `pull_request` (main). `concurrency: ci-${{ github.ref }}` cancel-in-progress. `permissions: contents: read`.

| Job | Steps |
|---|---|
| `backend` | checkout · setup-uv (cache) · `uv python install 3.13` · `uv sync --frozen` · `ruff check` · `ruff format --check` · `mypy app` · `pytest --cov=app --cov-fail-under=85 --junitxml` · upload coverage artifact |
| `brain-eval` (needs backend) | `uv run python scripts/evaluate_brain.py --json --gate` · write metrics to `$GITHUB_STEP_SUMMARY` (markdown table visible in Actions UI) |
| `contract` | export openapi → `npm run gen:api` → `git diff --exit-code` (drift) |
| `frontend` | checkout · setup-node 24 (npm cache) · `npm ci` · `npm run lint` · `npm run typecheck` · `npm run test -- --run` · `npm run build` |
| `no-llm-guard` | `scripts/check_no_llm_deps.sh` |
| `docker` (needs backend, frontend) | buildx build both images (no push), cache gha |
| `e2e` (needs docker) | `docker compose up -d --wait` · `npx playwright install --with-deps chromium` · `npx playwright test` · upload report on failure · `docker compose down` |

## 4. Security — `.github/workflows/security.yml`
Triggers: push to main/candidate branch, PR, weekly cron. Jobs: `gitleaks` (gitleaks-action or CLI with full history), `pip-audit` (from uv export), `npm audit --audit-level=high`, `bandit -r app -ll`, optional Trivy image scan (`aquasecurity/trivy-action`, severity HIGH,CRITICAL, ignore-unfixed).

## 5. CD — `.github/workflows/release.yml`
Trigger: tag `v*.*.*`. `permissions: contents: write, packages: write`.
Steps: run full CI (reusable workflow call) → build & push images to **GHCR** `ghcr.io/syedashhermajid/statement-categorizer-{api,web}:{version,latest}` with OCI labels + SBOM/provenance (`docker/build-push-action` `sbom: true, provenance: true`) → create GitHub Release with changelog (generated notes).
Deployment: documented `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d` pulling GHCR images (prod override: no api port, `APP_ENV=production`, restart policies, resource limits). We will tag `v1.0.0` on the fork to demonstrate one real release run (link in PR).
Reusability: `ci.yml` exposes `workflow_call` so release reuses it (DRY).

## 6. Dependabot — `.github/dependabot.yml`
Ecosystems: `pip` (/backend, uv-compatible via `uv` ecosystem if available else pip), `npm` (/frontend), `github-actions` (/), `docker` (/backend, /frontend). Weekly, grouped minor/patch, limit 5 PRs.

## 7. Repo hygiene files
`CODEOWNERS` (`* @SyedAshherMajid`), `.github/pull_request_template.md`, `.github/ISSUE_TEMPLATE/bug.md`, `SECURITY.md`, `CHANGELOG.md` (keep-a-changelog), `LICENSE`? — **No**: upstream repo has none; don't add one (not our call).

## 8. Branching
Work on `candidate-SyedAshherMajid`; short-lived local feature branches/worktrees merged into it (fast-forward or squash per feature). CI runs on the fork for every push. Upstream PR CI may require maintainer approval — PR links to fork's green run + release run.

## 9. Observability (lightweight, production-minded)
JSON logs to stdout (container-native), request-id correlation (frontend passes `X-Request-ID` through rewrites), `/healthz` `/readyz`, timing per request in logs. Optional P2: `/metrics` via prometheus-fastapi-instrumentator.

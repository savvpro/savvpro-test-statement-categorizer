# Ledgerly — Statement Categorizer for Landlords

[![CI](https://github.com/SyedAshherMajid/savvpro-test-statement-categorizer/actions/workflows/ci.yml/badge.svg?branch=candidate-SyedAshherMajid)](https://github.com/SyedAshherMajid/savvpro-test-statement-categorizer/actions/workflows/ci.yml)

> **Candidate:** Syed Ashher Majid · GitHub [@SyedAshherMajid](https://github.com/SyedAshherMajid) · applied with syedashhermajid@gmail.com

Upload a bank or credit card statement (CSV or OFX/QFX). Ledgerly sorts every transaction onto **IRS Schedule E, Part I** for a small residential landlord, keeps non-tax items (transfers, security deposits, loan principal…) out of the totals, and **asks you about every row it isn't sure of**. Fix those rows, then export.

The decision-making is plain, deterministic Python. **No AI model decides anything**, and CI enforces it. How the brain works: [DESIGN.md](DESIGN.md). How AI was used to build it: [AI_USAGE.md](AI_USAGE.md).

```
Upload statement → Read transactions → The brain → Category for each row → You review the result
```

## Run it (Docker, recommended)

Requires Docker with Compose.

```bash
docker compose up --build
```

Open **http://localhost:3000** and choose **Checking, Jan to Mar** under *No statement handy?* to load a fictional sample. The web app is published on `127.0.0.1` only because the app has no login.

## Run it locally (development)

Prerequisites: [uv](https://docs.astral.sh/uv/) (it installs Python 3.13 for you), Node 24 LTS and npm.

```bash
# backend (terminal 1)
cd backend
uv sync
uv run alembic upgrade head          # creates data/app.db
export APP_ENV=development            # enables the /docs API explorer (default is production)
uv run uvicorn app.main:create_app --factory --reload # http://localhost:8000  (API docs at /docs)

# frontend (terminal 2)
cd frontend
npm ci
npm run dev                          # http://localhost:3000, proxies /api to :8000
```

`make setup`, `make dev`, `make check` wrap these on Linux/macOS or Git Bash. Run `make help`-style targets from the [Makefile](Makefile).

## Test it

| What | Command |
|---|---|
| Everything CI runs | `make check` |
| Backend lint, types, tests, 85% coverage gate | `cd backend && uv run ruff check . && uv run mypy app && uv run pytest --cov=app --cov-fail-under=85` |
| **Brain accuracy on the labelled fake statements** | `cd backend && uv run python ../scripts/evaluate_brain.py --gate` |
| Frontend lint, types, unit tests, contrast, build | `cd frontend && npm run lint && npm run typecheck && npx vitest run && npm run contrast && npm run build` |
| End-to-end (needs the Docker stack up) | `cd frontend && npx playwright install chromium && npm run e2e` |

Current brain evaluation on 126 labelled rows: **100% auto precision, 100% review recall, 71% sorted without asking** (details in [DESIGN.md](DESIGN.md#5-evaluation)).

## What it handles

- **Formats:** CSV (any header order, debit/credit or signed amount columns, BOM, Windows-1252, `;` delimiters, decimal commas, preamble/footer rows, ambiguous dates) and OFX/QFX 1.x (SGML) and 2.x (XML).
- **Landlord traps:** refunds are not income; security deposits are not income; returned tenant payments reverse rent; mortgage payments need an interest/principal split; big repairs may be capital improvements; mixed-use stores; payments to individuals (1099 flag); transfers and card autopay are not spending; duplicates (pending/posted, repeat uploads).
- **Review flow:** per-row reasons, keyboard-driven triage (`J`/`K`, `1`–`9`, `Enter`, `U` to undo, `?` for help), "Remember for this merchant", "Also apply to N similar rows", Schedule E summary, CSV export safe against formula injection.

Limits: 5 MB per file, 20,000 rows. Full list in [DESIGN.md](DESIGN.md#7-trade-offs-and-limits).

## Configuration

All optional. Copy [.env.example](.env.example) to `.env` to override.

| Variable | Default | Purpose |
|---|---|---|
| `APP_ENV` | `development` | `production` disables the API docs UI |
| `APP_DATABASE_URL` | `sqlite:///./data/app.db` | Any SQLAlchemy URL (Postgres works) |
| `APP_CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowlist |
| `APP_MAX_UPLOAD_BYTES` / `APP_MAX_ROWS` | 5 MB / 20,000 | Upload limits |
| `APP_AUTO_THRESHOLD` / `APP_MARGIN_THRESHOLD` | 0.85 / 0.20 | When the brain is sure enough to sort without asking |
| `APP_DE_MINIMIS_CENTS` | 250000 | Repairs above this are asked about (possible improvement) |
| `APP_CONTRACTOR_1099_CENTS` | 60000 | Per-person total that raises a 1099 flag |
| `APP_RATE_LIMIT` | `30/minute` | Upload rate limit |
| `API_INTERNAL_URL` | `http://localhost:8000` | Where the web app proxies `/api` |

## Project layout

```
backend/    FastAPI app: domain, brain, ingest, normalize, services, db, api  (+ rules/*.yaml, tests)
frontend/   Next.js (App Router, TypeScript, Tailwind) review UI
samples/    Fictional statements + hand-checked expected results
scripts/    evaluate_brain.py, generate_samples.py, export_openapi.py, guards
docs/       plan/ (engineering plan), adr/ (decisions), reviews/ (independent reviews), ai-log/
.github/    CI, security scan, release (GHCR images), Dependabot
```

## Documents

[DESIGN.md](DESIGN.md) use case and how the brain decides · [AI_USAGE.md](AI_USAGE.md) AI tools, mistakes, tokens · [SECURITY.md](SECURITY.md) · [docs/plan/](docs/plan/00-INDEX.md) engineering plan · [docs/adr/](docs/adr/) decisions · [docs/reviews/](docs/reviews/) independent review reports

All data in this repository is fictional. Ledgerly is an organizational aid, not tax advice.

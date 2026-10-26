# Ledgerline - Statement Categorizer

> **SAVV Pro Assessment submission** - Statement Categorizer (Test 1)

Ledgerline categorizes bank and credit-card statement rows to IRS **Schedule C** lines for US freelancers and sole proprietors. Upload a CSV or OFX export, review flagged transactions, and export a tax-ready Schedule C summary.

---

## Features

- **Upload any bank export** - CSV (any layout) and OFX/QFX; auto-detects encoding, delimiter, sign convention, date format, split debit/credit columns
- **Pure deterministic brain** - no LLM decides anything; confidence scoring uses a curated merchant dictionary + keyword rules + user rules
- **Explains every decision** - each transaction carries an ordered reason trail ("Normalized → Kind detected → Keyword match → Below threshold")
- **Needs Review queue** - keyboard-driven one-at-a-time workflow; corrections create rules for future imports
- **Schedule C export** - summary by line + CSV export; refunds are netted against the original category
- **12-page UI** - professional "Ledger & Highlighter" design; light/dark/system themes; responsive 375 → 1440+

---

## Quick start

### Option A - Docker (recommended)

```bash
git clone <repo>
cd savvpro-test-statement-categorizer
cp .env.example .env
docker compose up --build
```

Open http://localhost:3000. Click **Try with demo data** to seed sample transactions.

### Option B - Manual (Windows)

#### Backend (Python 3.12+)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pip install "sqlalchemy[asyncio]"
uvicorn app.main:app --reload
# API at http://localhost:8000
# Docs at http://localhost:8000/api/docs
```

#### Frontend (Node 20+)

```powershell
cd frontend
npm install
npm run dev
# App at http://localhost:3000
```

### Option C - Manual (macOS / Linux)

```bash
# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pip install "sqlalchemy[asyncio]"
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

---

## Running tests

```bash
cd backend
pytest                          # all 122 tests
pytest tests/unit               # unit tests only (no DB)
pytest tests/integration        # API integration tests
pytest --cov=app --cov-report=term-missing  # with coverage
```

---

## Uploading sample data

Three sample CSV files are in `sample_data/`:

| File | Account type | What it tests |
|------|-------------|---------------|
| `northwind_bank_checking.csv` | Checking | Preamble rows, refund, IRS payment, mixed-use |
| `contoso_card.csv` | Credit card | Sign inversion (purchases positive), CC payment |
| `fabrikam_cu_debit_credit.csv` | Checking | Split debit/credit columns, ATM/owner draw |

Upload via the **Upload** page or seed the built-in demo data from the **Settings** page.

---

## Project structure

```
backend/           Python 3.12 + FastAPI
  app/brain/       Deterministic categorization engine (pure functions)
  app/ingest/      File parsing (CSV + OFX)
  app/api/         REST endpoints
  app/models/      SQLAlchemy 2.0 ORM
  tests/           122 tests (unit + integration)
frontend/          Next.js 15 + React 19 + TypeScript
  app/(app)/       12-page app shell
  app/page.tsx     Landing page
  components/      UI + app components
sample_data/       Fictional CSV files for testing
DESIGN.md          Architecture + design decisions
AI_USAGE.md        AI tooling disclosure
```

---

## API

Interactive docs at http://localhost:8000/api/docs once the backend is running.

Key endpoints:
- `GET /api/v1/health`
- `POST /api/v1/demo/seed` - seed demo data
- `POST /api/v1/imports` - upload file (returns draft)
- `POST /api/v1/imports/{id}/commit` - finalize import
- `GET /api/v1/dashboard` - KPIs + chart data
- `GET /api/v1/review/queue` - transactions needing review
- `GET /api/v1/reports/summary?year=2026` - Schedule C summary
- `GET /api/v1/reports/schedule-c.csv` - CSV export

---

## Tech stack

| Layer | Stack |
|-------|-------|
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0, SQLite, aiosqlite |
| Frontend | Next.js 15, React 19, TypeScript strict, Tailwind CSS v4, Framer Motion, TanStack Query/Table, Recharts |
| Testing | pytest, httpx AsyncClient, in-memory SQLite |
| CI | GitHub Actions |

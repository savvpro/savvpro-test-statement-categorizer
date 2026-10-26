# CLAUDE.md — LedgerLite (Statement Categorizer)

LedgerLite reads a freelance designer's (fake user "Sara Khan") business credit card
statement (CSV), categorizes every transaction for tax time, and sends anything it is
unsure about to **Needs Review** instead of guessing.

## Hard rules

- **The brain is our own code.** `backend/app/engine/` is pure, rule-based Python.
  NEVER call any LLM API (OpenAI, Anthropic, Gemini, ...) anywhere in app code.
- **Fake data only.** No real people, no real bank statements. No secrets in code;
  configuration comes from environment variables (see `.env.example`).
- **Tests for every module** (`backend/tests`, pytest). Every messy case gets a test.
- **Git:** work ONLY on branch `candidate-Rahatali8`. Never commit to `main`, never create
  other branches or git worktrees. Do not commit or push — the human commits.

## Layout

- `backend/` — Python 3.11, FastAPI, SQLModel (SQLite), pytest, ruff.
  - `app/engine/` — the brain: `normalizer.py`, `rules.py` (loads `rules.yaml`), `classifier.py`, `duplicates.py`. No FastAPI/DB imports here.
  - `app/parsing/csv_parser.py` — tolerant CSV reader.
  - `app/api/routes.py`, `app/main.py`, `app/db.py`, `app/models.py`.
- `frontend/` — Next.js (App Router) + TypeScript + Tailwind + lucide-react.
- `sample_data/` — fake CSV statements.
- `docs/api-contract.md` — the API contract both sides follow.

## Commands

```bash
cd backend && .venv/bin/pytest --cov=app      # tests
cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check .
cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev                    # http://localhost:3000
docker compose up --build                     # whole app
```

## UI design rules

Light grey page `#F7F9F9`, white cards, 1px `#E5EAE9` borders, `rounded-xl`, minimal or no
shadow. One teal accent `#1F7A68`. Inter font. lucide-react outline icons in soft tinted
circles. Small rounded status pills: Auto (teal), Needs Review (amber), Learned (blue),
Duplicate (red), Not spending (grey). Amounts right-aligned with `tabular-nums`; money
coming back shown in green. NO emoji, NO gradients, NO glassmorphism, NO neon, no big animations.

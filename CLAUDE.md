# Ledgerly — contributor guide (humans and AI agents)

Statement categorizer for small landlords: CSV/OFX upload → every transaction mapped to an IRS Schedule E line or excluded → uncertain rows go to review.

## Source of truth
- Plans: `docs/plan/` (00-INDEX first). Brain = 02, ingestion = 03, edge cases = 04, security = 05, tests = 06, UI = 07 + 07a, CI = 08.
- Read only the plan sections your task names.

## Non-negotiables
- **The brain is our own code.** Never add an LLM/ML SDK (openai, anthropic, google-genai, langchain, transformers…). CI enforces this.
- `domain/` and `brain/` import no framework (no FastAPI, no SQLAlchemy). Pure and deterministic.
- Money is **integer cents** (`int`). Use `Decimal` only while parsing. Never `float` for money.
- API JSON is snake_case. TS types are generated from `backend/openapi.json`; never hand-edit `frontend/src/lib/api/schema.d.ts`.
- Changing the contract (`backend/app/api/schemas.py`, `openapi.json`) needs orchestrator approval.
- Every change ships with tests. Name edge-case tests with their catalog ID: `test_D12_refund_reduces_repairs`.
- Fake data only. No secrets in the repo.
- Sub-agents do not commit. The orchestrator reviews diffs and commits.

## Layout
`backend/app/{core,domain,ingest,normalize,brain,services,db,api}` · `backend/rules/*.yaml` · `backend/tests/{unit,property,golden,integration,security}` · `frontend/src/{app,components,lib}` · `samples/` · `scripts/`

## Commands
- Backend: `cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest`
- Brain evaluation: `uv run --project backend python scripts/evaluate_brain.py --gate`
- Frontend: `cd frontend && npm run lint && npm run typecheck && npm test && npm run build`
- Everything (Linux/CI): `make check`

## Style
- Python 3.13, ruff (line length 100), mypy strict, type hints everywhere, small pure functions, docstrings only where intent isn't obvious.
- TypeScript strict. Components are small. Follow the design tokens in 07a. No `dangerouslySetInnerHTML`.

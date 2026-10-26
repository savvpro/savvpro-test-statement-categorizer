# Statement Categorizer

Rule-based tax prep helper for **freelance designers**: upload a business credit card CSV, auto-categorize each transaction, and fix rows marked **Needs Review**.

See [TASK.md](./TASK.md) for the assessment brief, [DESIGN.md](./DESIGN.md) for use case and brain logic, and [AI_USAGE.md](./AI_USAGE.md) for AI tooling notes.

## Stack

- **Backend:** Python 3.11+, FastAPI
- **Frontend:** React + TypeScript (Vite)
- **Brain:** Regex and rule pipeline (no LLM at runtime)

## Quick start

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs: http://127.0.0.1:8000/docs

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173 — the dev server proxies `/api` to the backend.

### 3. Try a sample file

Upload `sample_data/freelance_designer_statement.csv` (fake data only).

## Tests

```bash
cd backend
source .venv/bin/activate
pytest -q
```

## Project layout

```
backend/
  app/
    brain/categorizer.py    # Rule-based categorizer
    parser/statement_parser.py
    main.py                 # REST API
  tests/
frontend/                   # React upload + review UI
sample_data/                # Fake CSV statements
DESIGN.md
AI_USAGE.md
```

## Assessment submission

```bash
git checkout -b candidate-<your-github-username>
# commit your work
git push origin candidate-<your-github-username>
```

Open a PR against `savvpro/savvpro-test-statement-categorizer` `main` with title: `feat: complete statement-categorizer assessment`.

Fork/clone steps for the original repo are in the upstream README history; this file focuses on running the app.

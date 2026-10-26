# Statement Categorizer

A web app that reads a freelance designer's bank/credit card statement and auto-sorts every transaction into tax-ready categories. Built this for the savvpro assessment.

The idea: upload a CSV or OFX file → every row gets a category assigned → review anything the app wasn't sure about → get a spending summary by category.

---

## Use Case

Freelance designer. They have a business credit card and need to categorize transactions at tax time. Things like Adobe CC, Figma, Uber rides to client meetings, conference tickets etc. should be sorted automatically. Anything ambiguous gets flagged for manual review rather than guessed wrong.

---

## Tech

- **Backend:** Python + FastAPI
- **Frontend:** Next.js 15 + React + Tailwind CSS
- **Categorization:** Rule-based (no AI/ML at runtime)

---

## Running It

### Requirements
- Python 3.11+
- Node 18+

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API runs at `http://localhost:8000` — you can check `http://localhost:8000/docs` for the interactive API docs.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App at `http://localhost:3000`.

---

## Tests

```bash
# backend
cd backend
pytest tests/ -v

# frontend
cd frontend
npm test
```

---

## Project Layout

```
├── backend/
│   ├── app/
│   │   ├── main.py         # FastAPI routes
│   │   ├── categorizer.py  # the brain - rule-based categorizer
│   │   ├── parser.py       # reads CSV and OFX files
│   │   └── models.py       # pydantic models
│   ├── tests/
│   ├── sample_data/
│   │   └── sample_statement.csv   # fake data to test with
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── app/
│       ├── components/
│       └── lib/api.ts
├── DESIGN.md
└── AI_USAGE.md
```

---

## API Endpoints

| Method | Path | What it does |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/upload` | Upload statement file |
| `PATCH` | `/transactions/{session}/{id}` | Override a category |
| `GET` | `/sessions/{session}/summary` | Category totals |
| `GET` | `/categories` | List of all categories |

---

## File Formats Supported

- **CSV** — auto-detects date/description/amount columns, handles different column naming conventions
- **OFX / QFX** — both SGML and XML variants

---

## Notes

- Session state is in-memory, so restarting the server clears sessions (would use Redis/Postgres in production)
- Don't upload real bank statements — use the sample CSV in `backend/sample_data/` for testing
- No API keys or secrets needed, everything runs locally

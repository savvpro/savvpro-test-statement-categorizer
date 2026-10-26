# Feature 3: FastAPI API Layer

## Goal
Build the FastAPI application with REST endpoints that tie together the parser and brain, serving the frontend.

## Dependencies
- Feature 1 (models & brain) must be complete.
- Feature 2 (parser & sample data) must be complete.

---

## Files to Create

### 1. `backend/app/main.py`
FastAPI application with:

**App Setup:**
- Create FastAPI app with `title="Statement Categorizer API"`, `version="1.0.0"`
- Add CORS middleware allowing `http://localhost:5173` (Vite dev server) and `http://localhost:3000`
- Allow all methods, all headers

**Endpoints:**

#### `POST /api/upload`
- Accepts: `UploadFile` (multipart form data)
- Validates file extension is `.csv` (return 400 otherwise)
- Calls `parse_csv(file.read(), file.filename)`
- Creates `StatementBrain()` instance
- Categorizes each `TransactionRaw` → `TransactionCategorized`
- Calculates `TaxSummary` from all categorized transactions
- Returns `CategorizeResponse` with filename, parsed_count, warnings, transactions, summary

#### `POST /api/recalculate`
- Accepts: `RecalculateRequest` body (JSON list of TransactionCategorized)
- Recalculates `TaxSummary` from the provided (potentially user-edited) transactions
- Returns the updated `TaxSummary`
- Purpose: After user edits categories in the UI, recalculate totals without re-uploading

#### `GET /api/categories`
- Returns the `TAX_CATEGORIES` dictionary
- Frontend uses this to populate category dropdowns and colors

#### `GET /api/sample`
- Reads `sample_data/sample_statement.csv` from disk
- Runs it through the full pipeline (parse → classify → summarize)
- Returns same `CategorizeResponse` as upload endpoint
- Purpose: "Try Demo" button in frontend that doesn't require file upload

**Error Handling:**
- Return 400 for invalid file types with clear message
- Return 400 for unparseable CSV with parser warnings
- Return 422 for invalid JSON body
- Return 500 for unexpected errors with error message (never expose stack traces)

---

## Acceptance Criteria

- [x] `uvicorn app.main:app --reload` starts successfully on port 8000
- [x] `POST /api/upload` with `sample_statement.csv` returns 200 with all transactions categorized
- [x] `POST /api/upload` with a `.txt` file returns 400 error
- [x] `POST /api/recalculate` with edited transactions returns updated tax summary
- [x] `GET /api/categories` returns all 13 category entries
- [x] `GET /api/sample` returns the demo data fully categorized
- [x] CORS headers allow requests from `localhost:5173`
- [x] Swagger docs available at `http://localhost:8000/docs`

## Verification
```bash
cd backend
uvicorn app.main:app --reload --port 8000
# In another terminal:
curl http://localhost:8000/api/sample
curl http://localhost:8000/api/categories
curl -X POST -F "file=@sample_data/sample_statement.csv" http://localhost:8000/api/upload
```

## Git Commit
```bash
git add backend/app/main.py
git commit -m "feat(backend): add FastAPI app with upload, recalculate, categories, and sample endpoints"
git push origin candidate-sikandarhussain6858
```

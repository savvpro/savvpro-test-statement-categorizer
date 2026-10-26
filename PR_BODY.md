LedgerLens turns a consultant's CSV statement into an explainable, reviewed accountant handoff. The local FastAPI/SQLite backend and React/TypeScript frontend support preview/mapping, persistent corrections, duplicate review, reconciled summaries, and CSV exports.

The categorizer is deterministic Python with versioned token-boundary rules and evidence traces. Unknown credits, ambiguous merchants, and conflicting evidence require review. Refunds offset expenses; transfers stay outside spending. Invalid imports are atomic, stale edits are rejected with a reload action, workspace/export reads remain internally consistent under concurrent edits, and duplicate candidates are never silently removed.

Run from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.lock
npm --prefix frontend ci
npm --prefix frontend run build
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 and explore the bundled synthetic example through the normal import workflow.

Validation performed: 102 backend tests, 4 frontend unit tests, 8 real Chromium workflow/accessibility tests, Ruff, strict TypeScript, production build, and a fresh-install rehearsal. A 5,000-row local import reconciled successfully. Exact observations, real screenshots, and sanitized AI token evidence are in `evidence/`.

Limitations: documented CSV formats only; one currency per statement; local single-user operation; conservative merchant catalog; no tax advice, PDF/OCR, or cross-statement deduplication. One upstream Starlette HTTPX-adapter deprecation warning remains; tests pass. Hosted CI is configured but is not claimed to have run before this PR.

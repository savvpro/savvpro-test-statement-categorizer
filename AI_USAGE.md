# AI Usage & Attribution Log

This document honestly and transparently outlines how AI tools were utilized during the design, implementation, and verification of the **Statement Categorizer** assessment.

---

## 1. Tools Utilized

- **AI Assistant**: Google Antigravity (Advanced Agentic Pair Programmer powered by Gemini 3.8 Flash).
- **External AI Models for Categorization**: **NONE**. In strict adherence to `TASK.md` and assessment requirements, the transaction categorization brain is 100% deterministic Python standard code. No network calls, OpenAI, Anthropic, Gemini, or third-party AI APIs are used to classify transactions.

---

## 2. Areas Where AI Assisted

1. **Architecture & Project Scaffolding**:
   - Proposed clean multi-directory structure (`backend/` with FastAPI, `frontend/` with React/Vite).
   - Designed schema models (`models.py`), CSV parser (`parser.py`), in-memory session store (`store.py`), and REST endpoints (`main.py`).
2. **Deterministic Brain Implementation**:
   - Built the regex- and rule-based priority hierarchy in `categorizer.py` matching merchant names, checking for transfer phrases, handling refunds, and routing unknown/ambiguous items to `Needs Review`.
3. **Frontend Dashboard Components**:
   - Created the React UI with drag-and-drop CSV upload, interactive category correction dropdowns, summary cards, and spending breakdown bars.
4. **Comprehensive Automated Test Suite**:
   - Authored 29 unit and integration tests across `test_categorizer.py`, `test_parser.py`, `test_summary.py`, and `test_api.py`.
5. **Documentation**:
   - Created `README.md`, `DESIGN.md`, and this `AI_USAGE.md`.

---

## 3. Mistakes Caught & Corrected During Development

Running automated tests and terminal verification surfaced several genuine issues that were promptly diagnosed and resolved:

### Issue 1: Word Boundary Regex Mismatch on Airline Names
- **What happened**: When running `pytest backend/tests/test_categorizer.py`, the test `test_travel_categorization` failed for the description `"DELTA AIRLINES 2940"`.
- **Root Cause**: The keyword list contained `"delta air"`. Because word boundary regex `\b` was enforced after `air`, it did not match `"airlines"` because `l` is a word character.
- **Fix**: Expanded the keyword list to include `"delta"`, `"delta airlines"`, and `"airlines"`. Re-running pytest confirmed all 29 tests passed.

### Issue 2: Scaffolding Dependency Conflict (`oxlint` in Vite Scaffolding)
- **What happened**: When running `npm install` inside `frontend/`, npm 10.8.2 threw `TypeError: Cannot read properties of null (reading 'edgesOut')`.
- **Root Cause**: Inspected `npm-debug.log`, which revealed that a newly scaffolded linter dependency (`oxlint`) was fetching `canvas` and encountering peer dependency graph bugs in npm 10.8.2.
- **Fix**: Removed `oxlint` from `package.json` and pinned standard dependencies (`react`, `react-dom`, `vite`, `@vitejs/plugin-react`). `npm install` then succeeded in 37 seconds.

### Issue 3: Python Module Path Resolution on Uvicorn Startup
- **What happened**: Running `python -m uvicorn app.main:app` from the repository root failed with `ModuleNotFoundError: No module named 'app'`.
- **Root Cause**: The Python module `app` resides within the `backend/` directory.
- **Fix**: Executed uvicorn with working directory set to `backend/` and documented the exact command in `README.md`.

---

## 4. Token & Usage Details

In compliance with instructions never to fabricate token numbers or invent unavailable logs:
- **Conversation Session ID**: `a915cfa9-22c5-47ff-9cfc-d283d589e516`
- **Session Transcript Log Location**:
  `C:\Users\HP\.gemini\antigravity\brain\a915cfa9-22c5-47ff-9cfc-d283d589e516\.system_generated\logs\transcript.jsonl`
- **Total Tool Operations Executed**: 38 autonomous operations (including terminal commands, file edits, and pytest test runs).
- **Environment**: Local Windows environment, Python 3.13, Node.js v20.20.2.

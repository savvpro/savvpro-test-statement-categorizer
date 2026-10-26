# Implementation Plan (6 hour budget)

Start time: ______  Hard stop: start + 6h. Cut scope before cutting tests or docs.
Claude never commits, pushes or opens the PR. The user does that.

| Phase | Time | Work | Done when |
|---|---|---|---|
| 0. Setup | 0:00-0:30 | Repo layout, conda env `assigment`, Next.js app, `.gitignore`, sample CSV in place | Both servers start |
| 1. Brain | 0:30-2:30 | Parser, normalizer, rules, confidence, Needs Review, duplicate/refund/transfer logic | Sample CSV categorizes correctly in a script |
| 1b. DESIGN.md | right after Phase 1 works | Create `DESIGN.md` from the first working brain | File exists and matches the code |
| 2. API | 2:30-3:30 | FastAPI endpoints and schemas | All endpoints work via curl |
| 3. Frontend | 3:30-4:45 | Upload, table, filters, inline edit, totals | Full flow works in the browser |
| 4. Tests | 4:45-5:30 | pytest for brain and API | Tests pass |
| 5. Docs and handoff | 5:30-6:00 | README, final `DESIGN.md`, `AI_USAGE.md` | Docs complete, user opens the PR |

`DESIGN.md` is updated after every finished task from Phase 1b onward.

## Phase details

### 0. Setup
- `backend/` (FastAPI) and `frontend/` (Next.js) folders
- `conda create -n assigment python=3.11 -y`, install libraries there, keep `backend/requirements.txt` current
- `.gitignore`: `.env`, `.venv`, `node_modules`, `graphify-out/`, `__pycache__`
- Plugins (caveman, ponytail, graphify) are already installed. Run `/graphify .` after the first modules exist.

### 1. Brain (most important phase)
1. `parser.py`: read CSV, parse dates with `%d-%m-%Y`, merge Debit/Credit into a signed Decimal amount.
2. `normalizer.py`: uppercase, collapse spaces, strip `*`, trailing store numbers, card digits.
3. `rules.py` or `rules.yaml`: ordered rules (exact merchant, keyword/regex, amount hints).
4. `engine.py`: run rules, produce category, confidence (0 to 1), reason. Below threshold means Needs Review.
5. Special passes: transfers, refunds and reversals, duplicates.

### 1b. DESIGN.md
- Create only once the first working brain is finished.
- Sections: use case, categories, brain decisions, special passes, tradeoffs, known limits, progress notes.

### 2. API
- `POST /upload` parse and categorize, return transactions
- `GET /transactions` list, with `?needs_review=true` filter
- `PATCH /transactions/{id}` user fixes a category
- `GET /summary` totals per category, income vs spending
- In-memory store by default. Supabase only if persistence is truly required.

### 3. Frontend
- One page: upload box, table colored by category, Needs Review filter, inline category dropdown, totals panel
- Plain CSS, no design time

### 4. Tests
- Normalizer, each rule type, confidence threshold, duplicates, refunds, transfers
- API tests with `TestClient` using the sample CSV
- Assert the Needs Review rows from the PRD edge-case table

### 5. Docs and handoff
- README: setup and run steps for both apps, including the conda env
- DESIGN.md: final pass
- AI_USAGE.md: tools used, where they helped, where they were wrong, token logs or screenshots
- Tell the user the work is ready. The user commits, pushes and opens the PR.

## Cut list (drop in this order if behind)
1. Learn-from-corrections rules
2. Supabase / any persistence
3. Duplicate detection UI polish
4. Charts (keep the totals table)

## Never cut
Needs Review behavior, tests, README, DESIGN.md, AI_USAGE.md.
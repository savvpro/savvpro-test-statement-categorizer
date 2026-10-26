# Progress

Mark `[x]` when done. Update after each finished task.

## Setup
- [x] Task chosen (Statement Categorizer)
- [x] Repo forked and cloned, branch `candidate-bilalnadeem614` created
- [x] Sample PKR CSV and generator (`sample_statement_pkr.csv`, `gen_sample_statement.py`)
- [x] `CLAUDE.md` and project memory files
- [x] Install caveman, ponytail, graphify
- [x] Conda env `assigment` created, libraries installed
- [x] `backend/requirements.txt`
- [x] Backend folder structure
- [x] Frontend Next.js app
- [x] `.gitignore`

## Brain
- [x] CSV parser (dates, signed amount)
- [x] Normalizer
- [x] Rule set and engine
- [x] Confidence and Needs Review threshold
- [x] Transfer detection
- [x] Refund and reversal handling
- [x] Duplicate detection

## DESIGN.md (create after first working brain, update after every task)
- [x] Created after the first working version
- [x] Updated after brain tasks
- [x] Updated after API tasks
- [x] Updated after frontend tasks
- [x] Final pass (rewritten for readers, checked against the code)

## API
- [x] `POST /upload`
- [x] `GET /transactions`
- [x] `PATCH /transactions/{id}`
- [x] `GET /summary`

## Brain tweaks
- [x] Travel & Transport, Entertainment categories

## Frontend
- [x] Upload
- [x] Transactions table
- [x] Needs Review filter
- [x] Inline category edit
- [x] Category totals
- [x] GUI restyle: header, stat cards, category bars, sticky table, tabs + search, drag-drop upload, toast, skeleton, dark mode (screenshot-checked light only)
- [X] Click-test by hand (Bilal): drag-drop, tabs, edit toast, dark mode

## Tests
- [x] Normalizer tests
- [x] Rule and engine tests
- [x] Edge-case tests (refund, transfer, duplicate, reversal)
- [x] API tests
- [x] Frontend helper tests (Vitest)

## Final checks
- [x] pytest (74), ruff check and format, Vitest (11), eslint, `next build`
- [x] End to end on the sample: 75 rows, 7 Needs Review + 1 duplicate, edit updates summary
- [x] Secret, PII and LLM-import scans clean
- [x] Bug fixed: `backend/requirements.txt` pins matched the wrong pip (user site, Python 3.14), now match env `assigment`

## Docs and delivery
- [x] README.md (every command run)
- [x] AI_USAGE.md written; usage screenshots in `docs/token-usage/`
- [X] Handed off to user (user commits, pushes, opens PR)

## Time log
| Phase | Planned | Actual |
|---|---|---|
| Setup | 0:30 | not tracked |
| Brain | 2:00 | not tracked |
| API | 1:00 | not tracked |
| Frontend | 1:15 | not tracked |
| Tests | 0:45 | not tracked |
| Docs and handoff | 0:30 | not tracked |
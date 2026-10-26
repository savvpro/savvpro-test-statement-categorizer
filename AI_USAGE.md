# AI usage

AI tools were used to **build** this project. **No AI is used inside the app:** every
category is decided by the deterministic rule engine in `backend/app/brain/` (see
[DESIGN.md](DESIGN.md)). Neither `backend/pyproject.toml` nor `frontend/package.json` lists an
AI SDK, and the brain makes no network calls.

## Tools

| Tool | Used for |
|---|---|
| **Claude (chat)** | Planning. It wrote the plan (use case, taxonomy, brain design, messy-case list, architecture) and the phase breakdown, and drafted every prompt sent to Claude Code. After each phase, its output (tests, evaluation numbers, the "AI usage report" it was asked to return) was reviewed there before the next prompt was sent. |
| **Claude Code** (CLI, Opus) | Implementation, one phase per prompt (phase numbers below follow the plan; some prompts merged several phases): code, tests, sample data, golden labels, evaluation script, CI/Docker/Makefile and these docs. It ran ruff, pytest, the evaluator, vitest and the build before every commit, and kept the per-phase log in [`docs/ai-usage/session-log.md`](docs/ai-usage/session-log.md). |

## Workflow

```
plan (chat) -> one prompt per phase -> Claude Code implements + tests
            -> verify: ruff, pytest, evaluate.py, npm test/lint/build
            -> review the reported results and the diff -> commit -> next phase
```

Rules given to the coding agent in every phase:
- stay inside the phase;
- money is `Decimal`, never float;
- categorization must never call an AI model;
- fake data only;
- every check green before a commit;
- conventional commit messages with no AI tool names or trailers;
- log what went wrong.

## Per phase: what the AI did, what it got wrong, how it was caught

| Phase | What the AI did | What it got wrong | How it was caught and fixed |
|---|---|---|---|
| 1. Scaffold | `.gitignore`, FastAPI skeleton, config, JSON logging, ruff and pytest setup | Nothing blocking. The machine only had Python 3.14 | n/a |
| 2. Domain + DB | Schedule C taxonomy YAML and loader, domain types, SQLAlchemy models with integer cents, money schemas, `/api/categories` | Made the first commit on `main` instead of a candidate branch. `Mapped[date]` shadowed the `date` type under Python 3.14's lazy annotations. A plain `TestClient` would have created `data/app.db` during tests | Branch moved to `candidate-cheenafly`. Switched to `dt.date`. Tests use an in-memory engine and set `DATABASE_URL` in `conftest.py`. Also enabled the SQLite FK pragma so cascades really work |
| 3. Parser + samples | Pure CSV/XLSX parser, sign normalization, four invented sample statements and a deterministic generator | **`\u` escapes became literal invisible characters** in written files (unicode minus, NBSP, BOM), giving unreadable source and ruff errors. A "TOTAL" check would have dropped real "TOTAL WINE" purchases. The CR/DR regex used `\b` and missed `45.00CR`. One test wrongly expected `Amount ($)` to be unmapped. The xlsx sample was not deterministic (openpyxl writes the save time) | Caught by ruff and a non-ASCII grep, by writing edge-case tests, and by a byte-for-byte "regenerate and compare" test. Escapes were rebuilt via a script. TOTAL rows are only skipped without a valid date. The regex now anchors on a digit. The test expectation was fixed. Zip and core timestamps are pinned |
| 4-6. Brain + edge cases + golden set | Normalizer, signals, engine, refunds, duplicates, ambiguity policy, 134 hand labels, `evaluate.py` | **The multi-dot domain regex** let `AWS.AMAZON.CO` and `HELP.UBER.COM` leak into merchant keys. **`UPWORK *SERVICE FEE` matched both the bank-fee and platform-fee rules** (a guaranteed conflict). **AWS tripped the Amazon ambiguity rule.** **rapidfuzz `token_set_ratio` scores a subset as 100** ("BEST" vs "BEST BUY"). **Hidden `.pth` files:** Python 3.14 on macOS skipped the editable install, so `evaluate.py` could not import `app`. **Golden-set overfitting:** the rules were written with the samples in view | Normalizer tests and reading the rule files. Fixes: the regex accepts multi-label hosts; lookaheads exclude platform names from bank fees and AWS from Amazon; fuzzy also needs `ratio >= 80`, a key of at least 5 characters, and no exact hit; the script adds itself to `sys.path` (the `.pth` flag was later cleared for real). Overfitting is guarded by 10 unseen rows and a review-rate cap of 35% |
| 7. REST API | Ingest/review/summary/export services, routers, error handler, learned-rule loop, 35 API tests, uvicorn + curl check | **Rule hit-count bug:** a duplicate row that stays in review was counted as a rule hit (3 instead of 2). **Wrong test assumption:** expected a re-uploaded statement to get a new id, but SQLite reuses freed ids | Both caught by the new API tests. A hit now counts only when the rule auto-assigned the row. The test checks that the transactions table is empty instead of comparing ids |
| 8-9. Review UI + frontend tests | Vite + React + TS single page, typed client, 18 Vitest tests, Vite proxy | **Node was not installed.** The agent installed Node 24 LTS into `~/.local/node` (outside the repo, checksum verified). The Vite template ships oxlint, not ESLint. **Wrong test assumption:** `getByText` found the same text twice (description and merchant key are equal in the fixture). **The UI was not visually checked by the AI:** it had no browser, only jsdom tests and proxy curls | The failing test was rewritten to query by the row's label, and the table got a real accessible name. The visual check was left to the human (below) |
| 10-12. CI, Docker, docs, audit | Makefile, CI, Dockerfiles and compose, secret scan, README/DESIGN/AI_USAGE, final audit, PR | The prompt said Node 18+ and Python 3.11+; Vite 8 needs Node 20.19+, and only 3.12 and 3.14 are tested. `npm install --package-lock-only` silently dropped the `libc` fields from the lockfile. A `.dockerignore` rule (`**/data`) would have excluded the brain's YAML rule files. Docker is not installed, so the images were not built. Two DESIGN claims were inaccurate in the first draft (upload buffering, the foreign-merchant case) | Caught by checking engines, reading the lockfile diff and re-reading the docs against the code. Prerequisites now say Python 3.12+ and Node 20.19+. The original lockfile was restored with a minimal edit. The ignore rule was narrowed to `backend/data`. The README says Docker is "provided, not verified". The claims were corrected |

## What the human verified

- Read every phase's reported results (pytest summary, `evaluate.py` table, git log and the
  agent's own list of mistakes) before sending the next prompt.
- Reviewed the hand-written golden labels in `samples/labels/`, in particular which rows
  should be `needs_review`.
- Ran the app manually: tried the samples, fixed review rows, used "remember for this
  merchant", and exported the CSV.

What was automated and re-run by the agent before each commit: ruff check, ruff format
check, pytest (343 tests), the golden-set evaluation, oxlint, Vitest (18 tests) and the
production build.

## Token usage

Measured with [`ccusage`](https://github.com/ryoppippi/ccusage), which reads Claude Code's
local session logs. The full reports are in
[`docs/ai-usage/ccusage-session.txt`](docs/ai-usage/ccusage-session.txt) and
[`docs/ai-usage/ccusage-daily.txt`](docs/ai-usage/ccusage-daily.txt).

The machine also ran Claude Code for other, unrelated projects, which show up in those
reports. This project is **only session `06ac5964…`** (the one Claude Code session that built
this repo, all phases):

| Metric | This project (session `06ac5964…`) |
|---|---|
| Model | claude-opus-5-5 |
| Input tokens | 294 |
| Output tokens | 271,264 |
| Cache creation tokens | 434,625 |
| Cache read tokens | 21,211,987 |
| **Total tokens** | **21,918,170** |
| Cost (API-equivalent, as computed by ccusage) | **$13.15** |

- Most tokens are **cache reads**: the agent re-reads its cached context on every step.
  Fresh input and output are a small fraction.
- The numbers were captured just before the final docs commit, so the last few steps of the
  final phase (commit, push, PR) are not included.
- Claude **chat** usage (planning and writing the prompts) is not visible to ccusage and
  could not be measured. Exact token counts for it were not available from the tools used.

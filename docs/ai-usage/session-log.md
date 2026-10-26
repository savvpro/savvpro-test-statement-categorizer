# AI session log

One entry per phase: what was asked, what went wrong, how it was fixed.

## Phase 1: repo hygiene and scaffold

- **Asked:** add a `.gitignore` (Python, Node, env, SQLite, OS/editor and local working files),
  keep `docs/ai-usage/` tracked, write local assistant rules, and scaffold the backend
  (FastAPI app with `/api/health`, pydantic-settings config, structured logging, ruff and
  pytest config, health test) plus empty `samples/` and `frontend/` folders.
- **What went wrong:** nothing blocking. The machine only has Python 3.14, so the venv uses
  3.14; the project still declares `>=3.11`.
- **How it was fixed:** n/a. Verified with `git check-ignore -v` that `docs/ai-usage/` is not
  ignored and that the working files are, then ran ruff and pytest until green.

## Phase 2: taxonomy, domain models and database

- **Asked:** move work to a `candidate-<username>` branch and reset local `main` to upstream;
  add the Schedule C taxonomy (`categories.yaml` + validated, cached loader), pure domain types,
  SQLAlchemy 2.0 models with money stored as integer cents, API schemas that serialize money as
  strings, `GET /api/categories`, and tests that never touch `data/app.db`.
- **What went wrong:**
  - The scaffold commit had been made on `main` instead of a candidate branch.
  - A column named `date` with `Mapped[date]` would shadow the `date` type inside the class body,
    which breaks under Python 3.14's lazily evaluated annotations.
  - A plain `TestClient(create_app())` would run the lifespan `init_db` against the default
    engine and could create `data/app.db` during tests.
  - Starlette warns about `httpx` vs `httpx2` on every test run.
- **How it was fixed:**
  - Branched to `candidate-cheenafly` and pointed local `main` back at `origin/main`.
  - Used `import datetime as dt` and `Mapped[dt.date]` in the ORM and schema modules.
  - `create_app` accepts an `engine`; tests use an in-memory `StaticPool` engine with `get_db`
    overridden, and `conftest.py` sets `DATABASE_URL=sqlite://` before any app import as a backstop.
  - Enabled `PRAGMA foreign_keys=ON` per SQLite connection so `ON DELETE CASCADE` really works
    (covered by a test that deletes via raw SQL).
  - Filtered only that exact Starlette message in pytest config.

## Phase 3: statement parser and fake samples

- **Asked:** a pure parser (no DB/web imports) for CSV and XLSX bank and card statements. It had
  to cover header and synonym detection below junk lines, Decimal-only amount parsing, a
  per-column date order, sign normalization (debit/credit, DR/CR type, card auto-detect with an
  override), summary/blank/pending rows and row-level errors. Also a deterministic generator
  for four invented sample statements, plus tests.
- **What went wrong:**
  - `\u` escapes I wrote (unicode minus, non-breaking space, BOM) were turned into literal
    invisible characters on the way into the files. That gave unreadable source and ruff
    ambiguous-character errors.
  - The first summary-row check would have treated any row with a "TOTAL" cell as a footer.
    That would drop real purchases at merchants named "TOTAL ...".
  - The skipped-row warning named the `OPENING BALANCE` row by its date cell, not the matched text.
  - The CR/DR regex used `\b`, so it missed `45.00CR` written without a space.
  - My own header test expected `Amount ($)` to be unmapped, but it correctly maps to `amount`.
  - The xlsx sample looked deterministic in two quick runs but was not: openpyxl writes the
    current time into `docProps/core.xml` on save.
  - zsh aborted a command because of an unquoted `--include=*.py` glob.
- **How it was fixed:**
  - Rewrote the affected characters as ASCII `\uXXXX` escapes (or `codecs.BOM_UTF8`) with a
    script that builds the backslash via `chr(92)`, and checked with `grep -P '[^\x00-\x7F]'`.
  - TOTAL rows are only skipped when the date cell is blank or invalid. Balance rows must match
    the whole cell. A test keeps a dated `TOTAL WINE` purchase.
  - The warning now reports the matched cell, and the marker regex anchors on a digit or `)`.
  - Fixed the test expectation and used `Amt` as the unknown-header case.
  - The generator now pins both the zip entry times and `dcterms:modified`. A test regenerates
    the samples into a temp dir and compares bytes with the committed files.
  - Added a subprocess test that importing `app.parsing` loads no SQLAlchemy/FastAPI modules.
    pandas turned out to be unused and was removed from the dependencies.

## Phase 4: categorization engine, edge cases and golden evaluation (plan phases 4-6)

- **Asked:** a pure, deterministic rule engine. It needed a merchant normalizer, YAML rule data
  validated against the taxonomy, seven signals, a direction check, aggregation with agreement
  bonus, auto/review thresholds and forced review for ambiguous merchants. Also refund linking,
  duplicate/pending/chargeback handling, a hand-labelled golden set for all 134 sample rows, an
  evaluator and tests.
- **What went wrong:**
  - Normalizer: the first domain regex only handled one dot, so `AWS.AMAZON.CO` and
    `HELP.UBER.COM` leaked into merchant keys.
  - Rule collisions found on review: `UPWORK *SERVICE FEE` matched both the bank-fee and
    platform-fee patterns (a guaranteed conflict), and `AWS.AMAZON.CO` tripped the Amazon
    ambiguity rule.
  - `rapidfuzz.token_set_ratio` scores a pure subset as 100 ("BEST" vs "BEST BUY"). Used alone it
    would auto-assign on one shared word.
  - ruff's auto-fix expanded the US-states set into a 45-line list.
  - `scripts/evaluate.py` could not import `app`. The venv's `.pth` files carry the macOS
    `hidden` flag, and Python 3.14 skips hidden `.pth` files, so the editable install was
    silently inactive; pytest only worked because it adds the rootdir itself.
  - The golden set scores 100%, but the rules were written with the samples in view. That is
    partly overfitting, not proof of generality.
- **How it was fixed:**
  - Domain regex accepts multi-label hosts.
  - Bank-fee pattern has a negative lookahead for platform names. The Amazon rule excludes AWS.
  - Fuzzy matches also need a plain `ratio >= 80` and a key of at least 5 characters, and fuzzy
    only runs when no exact merchant hit exists.
  - Rewrote the set by hand with `# fmt: skip`.
  - The evaluator puts `backend/` on `sys.path` itself instead of depending on the install.
  - Added 10 hand-written unseen rows (unknown merchants must go to review) and a review-rate
    ceiling, so precision cannot be bought by asking about everything.

## Phase 7: REST API, services, learned rules

- **Asked:** fix the venv import issue for real; thin services (ingest, review with learned
  merchant rules, summary, export); routers under `/api`; ErrorOut error handling; upload
  limits; API tests; prove it end to end with uvicorn and curl.
- **What went wrong:**
  - A delete test assumed a re-uploaded statement gets a new id. SQLite reuses the freed id
    (no AUTOINCREMENT), so the assertion was wrong, not the code.
  - Learned-rule hit counts came out as 3 instead of 2: a same-day duplicate that stays in
    review still carried the rule id, so it counted as a hit.
  - httpx request logs from the test client cluttered the JSON log output.
- **How it was fixed:**
  - The test now checks the transactions table is empty after delete and that the same file
    can be uploaded again.
  - A hit counts only when the rule actually auto-assigned the row (`rule_hit`).
  - The `httpx` logger is set to WARNING.
- **README note (for Phase 11):** on macOS with Python 3.14, if `import app` fails outside
  `backend/`, run `chflags nohidden .venv/lib/python3.*/site-packages/*.pth`. Python 3.14
  skips `.pth` files that carry the `hidden` flag.

## Phase 8: review UI and frontend tests (plan phases 8-9)

- **Asked:** a Vite + React + TypeScript single page with plain CSS (light/dark): upload with
  samples, statement list, import notes, summary cards and category totals, a review table with
  tabs, search, inline category editing and "remember for this merchant", CSV export. Typed API
  client, Vitest + Testing Library tests with fetch mocked, proxy to the backend.
- **What went wrong:**
  - Node was not installed (no node, nvm, fnm, volta or Homebrew).
  - The current Vite template ships oxlint instead of ESLint.
  - One test failed on its first run: the fixture's description and merchant key were the same
    text, so `getByText` found two elements. The test was wrong, not the UI.
  - A first draft queried the transactions table by an empty accessible name, which only
    worked by accident.
- **How it was fixed:**
  - Installed the official Node v24.22.1 LTS tarball (checksum verified) into `~/.local/node`.
    User space, no sudo. Add `~/.local/node/bin` to PATH.
  - Kept oxlint and run it with `--deny-warnings` as `npm run lint`.
  - The test now finds rows by their category select's label. The table gets
    `aria-labelledby` pointing at its heading, so tests and screen readers both get a real
    name.

## Phase 10-12: CI, Docker, docs and final audit

- **Asked:** Makefile, GitHub Actions CI (Python 3.12 + 3.14, Node 22), backend and frontend
  Dockerfiles with compose, a secret/real-data scan, the root README, DESIGN.md, AI_USAGE.md
  with token usage, a final audit against TASK.md, then push and open the PR.
- **What went wrong:**
  - The requested prerequisites (Python 3.11+, Node 18+) were not accurate. Vite 8 requires
    Node ^20.19 or >=22.12, and only Python 3.12 and 3.14 are tested.
  - `npm install --package-lock-only`, used to sync the new `engines` field, silently dropped
    the `libc` constraints from the Linux native-binary entries in the lockfile.
  - The first `.dockerignore` rule `**/data` would also have excluded `app/brain/data/`, the
    rule YAML files.
  - The first DESIGN draft said an oversize upload is never fully buffered. Starlette spools
    the whole multipart body first. It also misdescribed the foreign-merchant test and the
    unseen rows.
  - Docker is not installed, so the images could not be built.
  - The push was rejected: the GitHub CLI token lacks the `workflow` scope needed to push
    `.github/workflows/ci.yml`.
  - `ccusage` has no per-project filter, and its reports include unrelated projects on the
    same machine.
- **How it was fixed:**
  - `requires-python` is now `>=3.12`, and `engines` says Node `^20.19.0 || >=22.12.0`. The
    README states both.
  - Restored the original lockfile and edited only the name and `engines`; verified with
    `npm ci`.
  - Narrowed the ignore rule to `backend/data`.
  - Corrected the DESIGN claims after re-reading the code and tests.
  - The README marks Docker as "provided, not verified on this machine".
  - The push and PR wait for `gh auth refresh -s workflow`.
  - AI_USAGE reports only this repo's session (`06ac5964…`) and explains the rest.

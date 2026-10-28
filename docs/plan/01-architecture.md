# 01 — Architecture

## 1. Style & principles

- **Modular monolith**, clean/hexagonal layering. One backend service, one frontend app, one repo.
- Dependencies point inward: `api → services → (ingest, normalize, brain, db) → domain`. `brain` and `domain` import nothing from frameworks (no FastAPI, no SQLAlchemy) — pure, deterministic, trivially testable.
- **Contract-first**: Pydantic API schemas → exported `openapi.json` → generated TS types. CI fails on drift.
- **Rules are data** (YAML, validated at startup), the engine is code.
- **Stateless API process**; state in DB. Horizontal scale possible by swapping SQLite→Postgres (`DATABASE_URL`).

## 2. Request flow

```
Browser ── POST /api/v1/statements (multipart: file, account_type)
  └─ api.statements.upload
       ├─ core.security.validate_upload (size, ext, sniff)       → 413/415/422
       ├─ services.ingestion.process_upload
       │    ├─ ingest.detect_format(bytes) → csv | ofx
       │    ├─ ingest.csv.parse / ingest.ofx.parse → RawTransaction[] + ParseWarning[]
       │    ├─ normalize.normalize(raw, account_type) → Transaction[]
       │    ├─ db: load MerchantRules, prior fingerprints
       │    ├─ brain.categorize(transactions, BrainContext) → Decision[]
       │    └─ db: persist Statement + Transactions(+Decision columns) in one unit of work
       └─ 201 StatementOut {id, counts, warnings}
Browser ── GET /statements/{id}/transactions, PATCH /transactions/{id}, GET /summary, GET /export.csv
```

## 3. Backend module map

```
backend/app/
  main.py                 # app factory create_app(settings); middleware; routers; lifespan (load rules)
  core/
    config.py             # Settings (pydantic-settings)
    logging.py            # JSON logging, request-id contextvar
    errors.py             # AppError hierarchy + problem+json handlers
    security.py           # upload validation, security headers middleware, csv-escape
    ratelimit.py          # slowapi limiter
  domain/
    enums.py              # Category, CategoryKind, Status, Direction, AccountType, Flag, SourceFormat
    models.py             # RawTransaction, Transaction, Candidate, Decision, ParseWarning (frozen dataclasses)
    taxonomy.py           # CategoryInfo (code, label, kind, schedule_e_line, allowed_directions)
  ingest/
    detect.py             # detect_format
    csv_reader.py         # decode, sniff, header-find, column-map, row parse
    ofx_reader.py         # SGML (v1) tokenizer + XML (v2) via defusedxml
    amounts.py, dates.py  # parsing helpers
  normalize/
    merchant.py           # clean_description → merchant_key, channel, counterparty
    normalizer.py         # RawTransaction → Transaction (direction, sign convention, fingerprint)
  brain/
    engine.py             # categorize(): runs stages, resolver, cross-row passes
    rules.py              # RuleSet loading/validation from YAML
    stages/               # structural.py, direction.py, memory.py, merchant.py, keyword.py, fuzzy.py, policy.py
    resolver.py           # noisy-OR aggregation, thresholds, status
    crossrow.py           # duplicates, recurring, YTD aggregates
    explain.py            # reason strings
  services/
    ingestion.py, review.py (corrections, remember, apply_similar), summary.py, export.py
  db/
    base.py, session.py   # engine, SessionLocal, get_session dependency
    models.py             # ORM tables
    repositories.py       # StatementRepo, TransactionRepo, MerchantRuleRepo, CorrectionRepo
  api/
    deps.py, schemas.py
    routers/ statements.py, transactions.py, categories.py, health.py
backend/rules/  categories.yaml merchants.yaml keywords.yaml patterns.yaml mixed_use.yaml
backend/migrations/  (Alembic)
```

## 4. Domain model (pure Python)

```python
class Direction(StrEnum): INFLOW="inflow"; OUTFLOW="outflow"
class AccountType(StrEnum): CHECKING="checking"; CREDIT_CARD="credit_card"
class Status(StrEnum): AUTO="auto"; NEEDS_REVIEW="needs_review"; USER_CONFIRMED="user_confirmed"; DUPLICATE="duplicate"
class CategoryKind(StrEnum): INCOME="income"; EXPENSE="expense"; NON_PNL="non_pnl"

@dataclass(frozen=True) class RawTransaction:
    row_index: int; date_raw: str; description_raw: str; amount_raw: str | None
    debit_raw: str | None; credit_raw: str | None; memo_raw: str | None
    fitid: str | None; trntype: str | None; extra: Mapping[str, str]

@dataclass(frozen=True) class Transaction:
    row_index: int; posted_date: date; amount_cents: int   # signed: + inflow, - outflow (account holder view)
    direction: Direction; description: str; memo: str | None
    merchant_key: str; channel: str | None; counterparty: str | None
    account_type: AccountType; fitid: str | None; fingerprint: str; is_pending: bool

@dataclass(frozen=True) class Candidate:
    category: Category; score: float; source: str; rule_id: str; reason: str

@dataclass(frozen=True) class Decision:
    category: Category | None; status: Status; confidence: float
    reasons: tuple[str, ...]; rule_ids: tuple[str, ...]; flags: frozenset[Flag]
    is_refund: bool; duplicate_of_row: int | None; suggestion: Category | None
```

## 5. Database schema (SQLAlchemy 2.0, Alembic)

`statements`
| col | type | notes |
|---|---|---|
| id | str(36) PK | uuid4 |
| filename | str(255) | sanitized basename only |
| source_format | str(8) | csv/ofx |
| account_type | str(16) | |
| file_sha256 | str(64) idx | exact re-upload detection |
| uploaded_at | datetime(tz) | |
| period_start, period_end | date | min/max posted |
| row_count | int | |
| warnings | JSON | list of {code, message, row_index?} |

`transactions`
| col | type | notes |
|---|---|---|
| id | str(36) PK | |
| statement_id | FK → statements.id, cascade delete, idx | |
| row_index | int | original order |
| posted_date | date idx | |
| amount_cents | BigInteger | signed |
| direction | str(8) | |
| description, memo | Text | |
| merchant_key | str(128) idx | |
| channel, counterparty | str(64) nullable | |
| fitid | str(255) nullable | |
| fingerprint | str(64) idx | |
| brain_category | str(40) nullable | brain's pick / suggestion |
| category | str(40) nullable | **effective** category (user or brain) |
| status | str(16) idx | |
| confidence | Float | 0–1 (score, not money — float OK) |
| reasons, rule_ids, flags | JSON | |
| is_refund | bool | |
| duplicate_of_id | FK self nullable | |
| updated_at | datetime | |
Unique: (statement_id, row_index).

`merchant_rules` — id, merchant_key **unique**, category, created_at, updated_at, hit_count, source_transaction_id (nullable FK).
`corrections` — id, transaction_id FK, from_category, to_category, from_status, remember bool, applied_to_similar int, created_at. (Immutable audit trail.)

Why store decision on the transaction row: one read path for the table view; history is in `corrections`.

## 6. API contract (v1)

All JSON snake_case. Errors: `application/problem+json` `{type, title, status, detail, instance, errors?}`. Every response has `X-Request-ID`.

### POST `/api/v1/statements` — multipart
Fields: `file` (required), `account_type` (`checking|credit_card`, required).
201 → `StatementOut`
```json
{"id":"…","filename":"jan-checking.csv","source_format":"csv","account_type":"checking",
 "uploaded_at":"…","period_start":"2026-01-01","period_end":"2026-01-31","row_count":64,
 "counts":{"auto":51,"needs_review":9,"user_confirmed":0,"duplicate":4},
 "warnings":[{"code":"AMBIGUOUS_DATE_ORDER","message":"…","row_index":null}]}
```
Errors: 413 too large, 415 unsupported type, 422 unparseable (with row-level details), 409 identical file already uploaded (returns existing id in `detail`; client may proceed to it).

### GET `/api/v1/statements` → `StatementOut[]` (newest first)
### GET `/api/v1/statements/{id}` → `StatementOut`
### DELETE `/api/v1/statements/{id}` → 204 (user can purge their data)

### GET `/api/v1/statements/{id}/transactions`
Query: `status`, `category`, `q` (description contains), `sort` (`date|amount|confidence`), `order`, `limit` (≤500, default 200), `offset`.
→ `{items: TransactionOut[], total: int}`
```json
TransactionOut = {"id","row_index","posted_date","amount_cents","direction","description","memo",
 "merchant_key","category","brain_category","status","confidence","reasons":[...],
 "flags":[...],"is_refund":false,"duplicate_of_id":null,"similar_count":3}
```

### PATCH `/api/v1/transactions/{id}`
Body `{category: Category, remember?: bool=false, apply_to_similar?: bool=false}` → `{updated: TransactionOut[], rule_created: bool}`
Rules: sets `category`, `status=user_confirmed`; `remember` upserts MerchantRule; `apply_to_similar` updates other rows in same statement with same merchant_key whose status != user_confirmed. Category must be direction-compatible (422 otherwise, e.g. RENT on an outflow unless reversal).

### POST `/api/v1/transactions/{id}/restore-duplicate` → marks a DUPLICATE row as real (re-runs brain on it). 
### POST `/api/v1/transactions/{id}/split` (P1) body `{parts:[{category, amount_cents}]}` sum must equal original.

### GET `/api/v1/statements/{id}/summary`
```json
{"income":{"RENT":540000},"expenses":{"REPAIRS":-123450,...},
 "schedule_e":[{"line":"3","label":"Rents received","category":"RENT","total_cents":540000},...],
 "total_income_cents":…,"total_expense_cents":…,"net_cents":…,
 "excluded":{"TRANSFER":…,"SECURITY_DEPOSIT_RECEIVED":…,"LOAN_PRINCIPAL":…,"CAPITAL_IMPROVEMENT":…},
 "unresolved":{"count":9,"total_abs_cents":…},"duplicates":{"count":4}}
```
Totals include `auto` + `user_confirmed` only. Refunds net against their category.

### GET `/api/v1/statements/{id}/export.csv`
Columns: date, description, amount, category, category_label, schedule_e_line, status, confidence, flags, reasons. Cells escaped (see 05-security). `Content-Disposition: attachment; filename="<safe>-categorized.csv"`.

### GET `/api/v1/categories` → `[{code,label,kind,schedule_e_line,allowed_directions}]`
### GET `/healthz` (liveness) · `/readyz` (DB reachable + rules loaded)

## 7. Configuration (`core/config.py`, env prefix `APP_`)

| Var | Default | Purpose |
|---|---|---|
| APP_ENV | `development` | `production` disables docs UI, tightens logs |
| APP_DATABASE_URL | `sqlite:///./data/app.db` | Postgres-ready |
| APP_CORS_ORIGINS | `http://localhost:3000` | comma list |
| APP_MAX_UPLOAD_BYTES | 5_242_880 | |
| APP_MAX_ROWS | 20_000 | |
| APP_AUTO_THRESHOLD | 0.85 | brain |
| APP_MARGIN_THRESHOLD | 0.20 | brain |
| APP_DE_MINIMIS_CENTS | 250_000 | capital improvement flag |
| APP_CONTRACTOR_1099_CENTS | 60_000 | |
| APP_FUZZY_MIN_RATIO | 88 | |
| APP_RATE_LIMIT | `30/minute` | uploads |
| APP_LOG_LEVEL | `INFO` | |
| APP_RULES_DIR | `./rules` | |

## 8. Error model

`AppError(code, status, title)` subclasses: `UploadTooLarge(413)`, `UnsupportedFileType(415)`, `ParseError(422, row errors)`, `DuplicateStatement(409)`, `NotFound(404)`, `InvalidCorrection(422)`. Unhandled → 500 problem+json with request id only (no stack to client; stack logged).

## 9. Cross-cutting

- **Logging:** JSON lines: ts, level, logger, request_id, method, path, status, duration_ms, statement_id. Never log descriptions/amounts at INFO.
- **Middleware order:** RequestID → SecurityHeaders → CORS → body-size guard → rate limit (upload route).
- **Transactions:** one DB transaction per request (session dependency, commit on success).
- **Startup (lifespan):** load + validate rules (fail fast), run `alembic upgrade head` in container entrypoint (not in app).

## 10. ADRs to write (docs/adr/)

| ADR | Decision | Rejected alternatives |
|---|---|---|
| 001 | Deterministic layered rule engine with confidence | ML classifier (needs real labeled data), LLM (forbidden) |
| 002 | Integer cents for money | float (precision), Decimal in SQLite (stored as float) |
| 003 | Own OFX parser + defusedxml | ofxparse (unmaintained), ofxtools (larger surface, XML via stdlib) |
| 004 | SQLite via SQLAlchemy, Postgres-ready | in-memory only (no persistence/memory), Postgres required (heavier setup) |
| 005 | Contract-first OpenAPI → TS types, drift check in CI | hand-written TS types |
| 006 | Status separate from category | "NEEDS_REVIEW" as a category (loses the suggestion) |
| 007 | Monorepo, modular monolith | microservices (overkill) |

# Build Ledgerly statement categorizer with deterministic rules

Freelance designers need to organize business statement transactions without counting transfers as spending or refunds as income. This adds a Python/FastAPI backend and React/TypeScript workspace that imports CSVs, explains rules, flags uncertain rows, persists manual reviews, and exports transaction/category reports.

The categorization brain is repository-owned Python code. There are no runtime AI calls or external categorization services. Specific merchant rules can propose expenses; ambiguous credits, mixed-use merchants, reversals, pending charges, and possible duplicates require review. Explicit refunds reduce their expense category. Internal transfers and card payments are excluded from business spending.

## Included

- Strict bank-signed, card-signed, and debit/credit CSV adapters with explicit date/currency settings, exact cents, row-level validation, and atomic imports.
- SQLite persistence, idempotent re-uploads, cross-import duplicate warnings, optimistic review versions, and before/after audit history.
- Responsive upload, category overview, searchable/sortable/paginated transaction table, native review dialog, review history, and draft/final exports.
- Server-enforced financial invariants, final-export gate, upload limits, local host/origin restrictions, formula-safe CSV, and non-root Docker configuration.
- Fictional fixtures, setup/design/AI-usage/security documentation, pinned dependencies, tests, and CI definitions.

## Validation

- 119 Python tests passed; 98% backend line coverage, including 100% engine/reporting coverage.
- 11 React tests passed; TypeScript and production build passed.
- 5 browser workflows passed against the actual Python API.
- The production frontend was also opened directly from FastAPI, with no observed page errors or document overflow at 1440, 1024, 768, 390, and 320 px.
- Ruff, formatting, dependency consistency, and source-archive checks passed.

See `docs/VERIFICATION.md` for the tested environment and observed warning. Browser validation used a separately available Chromium executable after the standard browser download failed.

## Scope and remaining requirements

CSV-only, one local single-user workspace, reports scoped to the selected import. No PDF/OCR, multi-user authentication, FX conversion, automatic tax deductions, split allocations, or year-wide aggregation. Docker configuration is included but was not executed in the authoring environment.

`AI_USAGE.md` discloses substantial AI coding assistance and concrete corrections. Exact development token counts and provider usage screenshots are unavailable in this session; their fields are explicitly null rather than fabricated. Authentic usage evidence still needs to be attached if required for submission.

**This file is a prepared PR description, not evidence of a published PR.** The user selected file delivery first and declined GitHub access. No remote repository was changed or PR opened.

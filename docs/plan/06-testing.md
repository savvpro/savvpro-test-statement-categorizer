# 06 — Testing Strategy

## 1. Pyramid
| Level | Tool | Scope | Speed |
|---|---|---|---|
| Unit | pytest | pure functions: amounts, dates, merchant, each brain stage, resolver, escaping | ms |
| Property | hypothesis | parsers/normalizer/brain invariants | s |
| Golden | pytest + evaluator | samples → expected labels; precision gates | s |
| Integration | pytest + FastAPI TestClient + temp SQLite | API flows, persistence, memory | s |
| Security | pytest | S01–S10, ReDoS, CSV escaping | s |
| Frontend unit | Vitest + Testing Library + MSW | components & hooks | s |
| E2E | Playwright (Chromium) against docker compose | upload → fix → summary → export | ~1 min |

## 2. Backend test files
```
tests/
  conftest.py                  # settings override, tmp db, app client, rules fixture, factories
  factories.py                 # make_txn(**overrides), make_raw(...)
  unit/
    test_amounts.py            # P09 table-driven, decimal comma, CR/DR, errors
    test_dates.py              # P10, P11, OFX dates, future/old
    test_detect.py             # magic bytes, ext mismatch P21
    test_csv_reader.py         # P01–P08, P14–P16, P22
    test_ofx_reader.py         # P17–P20, S04, S05, S10
    test_merchant.py           # 03 §8 example table + 30 more raw strings
    test_normalizer.py         # sign conventions P12/P13, pending, fingerprint occurrence
    test_rules_integrity.py    # real YAML: ids unique, categories valid, regex compile, alias collisions
    brain/
      test_structural.py test_direction.py test_memory.py test_merchant_stage.py
      test_keyword.py test_fuzzy.py test_policy.py test_resolver.py test_crossrow.py
      test_explain.py
    test_csv_export_escape.py  # OWASP payloads
    test_summary.py            # totals, refunds net, excluded, unresolved
  property/
    test_amount_props.py       # format(cents) → parse → same cents
    test_merchant_props.py     # idempotent, never empty (UNKNOWN), ≤128 chars
    test_brain_props.py        # any Transaction → valid Decision; AUTO ⇒ category not None & no blocking flag; deterministic
  golden/
    test_samples.py            # parametrized over samples/*.expected.json; per-row assert + gates
  integration/
    test_upload_api.py         # 201, 409, 413, 415, 422 shapes (problem+json)
    test_transactions_api.py   # filters, pagination, PATCH, remember, apply_to_similar, restore-duplicate, 422 direction
    test_summary_export_api.py
    test_memory_flow.py        # D42 across two uploads
    test_health.py
  security/
    test_upload_abuse.py       # S01–S03, S06, S07, S09
    test_redos.py
```
Naming: edge-case IDs in test names, e.g. `test_D12_home_depot_refund_reduces_repairs`.

## 3. Key invariants (asserted in many places)
- AUTO ⇒ category set, confidence ≥ AUTO_THRESHOLD, no blocking flag.
- NEEDS_REVIEW ⇒ category None until user confirms; suggestion may exist.
- Refund never categorized as income; transfers/card payments never in Sch E totals.
- Summary: income − |expenses| = net; excluded + included + unresolved + duplicates = all rows.
- Determinism: categorize twice → identical decisions.

## 4. Frontend tests
```
frontend/src/**/__tests__/
  UploadForm.test.tsx        # validation, account type required, error display (413/415/422 messages)
  TransactionsTable.test.tsx # renders rows, status tabs counts, confidence badge, reasons tooltip
  CategorySelect.test.tsx    # direction-filtered options, remember/apply-similar checkboxes
  SummaryView.test.tsx       # Sch E lines, unresolved warning, export link
  api.test.ts                # client error mapping (problem+json → message)
```
MSW mocks built from generated OpenAPI types (type-safe fixtures).

## 5. E2E (Playwright) `frontend/e2e/happy-path.spec.ts`
1. Open `/`, upload `checking_q1_2026.csv` as checking.
2. Land on review; Needs Review tab count > 0.
3. Fix `JOES CAFE` → Personal, tick remember; count decreases.
4. Open summary; RENT total equals expected value from labels; export downloads a CSV whose header matches.
5. a11y smoke: `@axe-core/playwright` no serious violations on the 3 pages.

## 6. Gates (CI-enforced)
- Backend line coverage ≥ 85% (`--cov-fail-under=85`); `brain/` ≥ 95% (separate report check).
- Golden: auto_precision = 1.00, review_recall = 1.00.
- mypy `--strict` clean on `app/`; ruff clean.
- Frontend: `tsc --noEmit`, eslint, vitest pass; `next build` succeeds.
- OpenAPI drift: regenerate `openapi.json` + TS types → `git diff --exit-code`.
- E2E green.

## 7. Commands
`make test` (backend all) · `make test-fast` (unit only) · `make eval` · `make fe-test` · `make e2e` · `make check` (everything CI does, locally).

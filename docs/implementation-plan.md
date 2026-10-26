# Ledgerly implementation plan

Build a local-first statement review tool for freelance designers. Python/FastAPI,
React/TypeScript, SQLite, no paid services and no model in the decision pipeline.

1. Preserve the assessment history and candidate branch.
2. Test and implement strict CSV parsing (signed amounts or debit/credit columns,
   explicit date/sign conventions, integer cents, limits, actionable row errors).
3. Test and implement explainable ordered rules with conservative review fallback.
4. Add atomic SQLite imports, idempotency, saved corrections, optimistic locking,
   audit history, summaries and spreadsheet-safe CSV export.
5. Build responsive upload, overview, searchable/filterable transactions,
   keyboard-accessible review dialog, statement history and export controls.
6. Add fake sample statements, setup/start scripts, design and AI-use documentation.
7. Run backend and browser workflow tests, inspect desktop/mobile layout, build
   and start the production frontend with the API at http://127.0.0.1:8000.

Scope: CSV only, one two-decimal currency per statement. No tax-deductibility claims,
OCR, bank integration, authentication, or public hosting. Uncertain credits,
ambiguous merchants and possible duplicate rows always need human review.
User requested autonomous implementation and local testing before submission.

Alternative considered: arbitrary PDF/OCR parsing increases extraction uncertainty
and setup cost; a documented CSV contract makes failures visible and reproducible.

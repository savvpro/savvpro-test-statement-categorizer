## Summary

<!-- What changed and why, in 2-4 sentences. -->

## Plan references

<!-- e.g. docs/plan/02-brain.md §3, docs/plan/04 edge case D12 -->

## Checks

- [ ] `make check` passes locally (or the CI run on this branch is green)
- [ ] Every behaviour change has a test; edge-case tests use their catalog ID (e.g. `test_D12_refund_reduces_repairs`)
- [ ] No LLM/ML SDK added (`scripts/check_no_llm_deps.sh`)
- [ ] Money stays integer cents; no `float` for money
- [ ] API contract change? If yes, `backend/openapi.json` and `frontend/src/lib/api/schema.d.ts` are regenerated and orchestrator-approved
- [ ] No secrets, real personal data, or fixtures outside `samples/` fake data

## Screenshots / evidence

<!-- For UI changes: screenshots at 1440 / 1024 / 390 px. For brain changes: evaluate_brain output. -->

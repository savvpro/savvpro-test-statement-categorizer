# AI usage disclosure

## Tools and scope

OpenAI Codex was used in this conversation to brainstorm the customer, design the deterministic classifier and accounting model, implement Python/React, generate fictional fixtures, write tests and documentation, run checks, and inspect results. The built-in Image Gen tool produced the interface concept at `docs/design/concept.png`. Image Gen was used for design only, not transaction decisions. No other AI coding tools were used in this implementation session.

The shipped app contains no model call, API key requirement, hosted inference, embedding similarity, or model-generated runtime category. The brain is inspectable in `backend/app/engine.py`; parsing and money calculations are regular Python. All statement data is invented.

## Where AI helped

- Separated transaction type, category and business purpose to avoid treating merchant recognition as tax eligibility.
- Proposed conservative handling for Pakistani account transfers, remittances, foreign subscriptions, card repayments, and mixed household/work spending.
- Generated the initial implementation and fake examples, then used tests and browser evidence to revise it.
- Created setup/design documentation and CI.

## Mistakes and corrections

1. Initial rules matched `GITHUB COPILOT` as both AI tools and general GitHub software. A test failed; the broader rule now excludes Copilot. The regression case remains.
2. The first PDF fixture used pipe-delimited text rather than a credible table. It was replaced with a styled synthetic bank table, known-layout extraction, and row-count reconciliation.
3. The first export formatted money through floating point. Backend exports now use Decimal, matching integer accounting.
4. Early overlap recovery advice required a fresh workspace. Users can now remove an incorrect statement, correct the source, and reimport while preserving rules.
5. The first stylesheet fetched a Google font. That request was removed; the shipped UI uses system-font fallbacks.
6. Browser checks exposed a Windows executable-path issue in the test harness and an unreliable exact implicit-label lookup. The harness now quotes an absolute Python path; review controls have explicit accessible names. All browser flows were rerun.
7. Visual inspection found that the extended review form stretched the page. It now uses its own bounded scroll area, aligned with the review notice.

Browser-discovered issues and fixes are recorded in `docs/design/QA.md` after verification. Passing tests do not establish universal bank compatibility or correct tax treatment; unsupported formats are documented.

## Actual token evidence

`docs/ai-usage/token-usage.json` contains token-count events from this conversation's local Codex rollout. `scripts/export_ai_usage.py` copies **only timestamps and counters**, never messages, tool outputs, environment values or credentials. The private raw rollout is not committed.

The captured numerical totals are in [docs/ai-usage/SUMMARY.md](docs/ai-usage/SUMMARY.md), generated from the same final event as the JSON log.

Counters are cumulative conversation snapshots, including earlier brainstorming. Input totals include repeated context and cached input, so they are not unique words written or a billing estimate. The JSON records input, cached input, output, reasoning output and total tokens where supplied. Its final event is the authoritative captured snapshot; later handoff/PR messages may not be included. Image Gen usage is not exposed by that tool and is not fabricated.

To refresh locally (substitute your private rollout path):

```sh
uv run python scripts/export_ai_usage.py /path/to/this-conversation-rollout.jsonl
```

Do not commit the raw rollout. Actual token logs are included instead of a usage screenshot. Review the app and rules before submission and be ready to explain its uncertainty policy and accounting invariants.

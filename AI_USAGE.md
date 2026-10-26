# AI usage

## Existing implementation

The working tree supplied at the start of this improvement already contained the
backend, frontend and tests. Its previous AI usage document attributed initial
implementation to Antigravity and testing to Claude. Those earlier sessions,
model identities, usage counts and screenshots are not available in this session
and have not been independently verified. Prior estimated token totals and
claims of manual developer attestation have been removed rather than presented
as measured evidence.

## Codex improvement session - 2026-10-26

Tool: OpenAI Codex coding agent. The user requested: "ok improve this project and
then commit it". Codex inspected the supplied code and local Next.js documentation,
installed dependencies, edited code/documentation, ran checks and created a Git
commit. No other agents were delegated work.

Assistance included:

- Finding a parser crash caused by extra CSV cells and rejecting duplicate headers.
- Bounding monetary values and limiting reads of uploaded file content.
- Fixing row-order-dependent refund category totals and retaining prior-period refunds.
- Holding unresolved rows out of operating totals and preserving review status
  for unknown or contradictory corrections.
- Preventing negative refund descriptions from matching ordinary expense rules.
- Replacing generic-token purchase linking with unique merchant/date matching.
- Making frontend edits atomic with summary updates and surfacing failed saves.
- Adding accurate statement years, draft export labels, accessible control labels,
  spreadsheet-safe text export, regression tests and CI checks.

Verification: the initial 52 backend tests passed but did not expose the CSV
extra-cell crash, order-sensitive totals or stale frontend-save behavior. New
regression tests cover the backend failures. Frontend lint and production
compilation passed; this session did not perform browser automation or obtain
independent human review. Automated checks are not a substitute for that review.

## Usage evidence and limits

Exact input/output token counters and billing exports are not exposed to this
coding session. No token count is asserted, and no token logs or usage screenshots
have been fabricated. The assessment's request for actual usage logs/screenshots
still requires an export from the AI tools used before submission.

The categorizer itself uses zero AI inference calls: all runtime decisions are
made by the Python rules engine. Development assistance does not change that rule.

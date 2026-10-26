# AI usage — honest disclosure

## Tools and scope

The candidate used **OpenAI Codex**, with session metadata reporting **`gpt-6-astra`** and both **medium and low reasoning** settings across turns, to assist with planning, code generation, tests, UI implementation, debugging, documentation, and local Git work. The candidate chose the assessment direction and CSV scope, supplied priorities, authenticated GitHub, created the fork manually, and required explicit approval before remote publishing.

No extra coding agents were intentionally spawned. The application itself makes **no LLM, embedding, speech-model, or external categorization calls**. Classification is inspectable Python code and versioned rule data.

The assistant generated most of the implementation and tests. This is not presented as unaided human code. Automated results and screenshots were produced by actual tools, not invented. The candidate's subsequent manual review is not claimed here unless it actually occurred.

## Verification rather than generation alone

- Ran parser/engine tests, isolated-database API tests, and TypeScript/build checks.
- Used Playwright against the actual compiled frontend and FastAPI server, including persistence after reload, corrections, duplicate controls, export, invalid data, and a mobile viewport.
- Inspected real Chromium screenshots and exercised a correction manually through browser automation.
- Used axe to detect accessibility issues; fixed detected contrast problems and reran the checks.
- Inspected dependency audit output and upgraded affected test tooling.

See `evidence/verification.md` for the recorded executed results. Configuring CI is not claimed as a successful hosted CI run.

## Actual mistakes encountered and corrected

1. **Dependency-install timing:** an initial pytest invocation ran before pip finished installing, producing “No module named pytest.” The installation was allowed to complete; the tests were then run successfully.
2. **Initial test-tool version:** the first Vitest version pulled dependencies with npm audit advisories. Audit output identified the affected tooling; Vitest was upgraded to a patched release and the audit rerun.
3. **Ambiguous browser labels:** the first desktop/mobile workflow tests timed out finding an exact `Category` label on a select nested in a label. Explicit accessible names were added; the real browser scenarios then passed.
4. **Low contrast:** the initial muted text palette failed an axe contrast check. The palette was darkened and supporting text enlarged; accessibility checks were rerun, rather than disabled.
5. **Working-directory mistakes:** two edit commands used a root-relative filename while already inside the frontend directory, so they failed without changing that file. The edits were reapplied from the correct directory and verification rerun.
6. **Raw input fidelity:** review identified that parsing stripped description whitespace. The implementation was corrected to retain raw descriptions and a regression test added.
7. **Last-item review navigation:** the final audit found that selecting “Next review” on the only remaining unresolved item could incorrectly announce completion. The handler now keeps that item open and explains that it must be resolved; a real-browser regression test verifies this.

8. **Concurrent export consistency:** a regression test reproduced a final export accepting older unresolved rows after a concurrent correction. Explicit read snapshots and aggregation from the exported rows fixed the race; the test now passes.
9. **Dialog keyboard behavior:** browser tests showed that native modal behavior alone allowed Tab to leave its buttons and failed to restore the trigger focus after unmounting. Explicit button cycling and layout-effect focus restoration fixed both failures.

These are observed development events, not hypothetical examples. A successful build was never treated as sufficient proof of runtime correctness.

## Token usage evidence

[`evidence/ai-usage.json`](evidence/ai-usage.json) contains the latest captured cumulative token counters from the primary Codex session. It includes the model/effort, UTC timestamp, and allowlisted usage fields. It intentionally excludes messages, tool arguments, credentials, local paths, account identifiers, and private session metadata.

The export was generated with `scripts/capture_usage.py` from actual local `event_msg/token_count` records. Use the **latest cumulative value once**; summing periodic cumulative events would overcount. Cached input is already part of input tokens. Reasoning tokens are already part of output tokens. `total_tokens` is the recorded input-plus-output count, not an additional quantity.

The snapshot covers planning and implementation in this primary conversation up to its timestamp. It is not a final lifetime total: later review or publication work can add usage. It does not claim to include platform-internal processes or another session. No monetary cost or remaining subscription quota is inferred from these counters.

No fabricated screenshots, token estimates, benchmarks, test passes, or human actions are included. If the evidence is refreshed later, keep its capture timestamp and scope explicit.

# AI Usage

## AI tools used

- **Copilot SDK in VS Code** (the AI assistant used for this assessment).
  The specific underlying model/version was not exposed in the repository or
  tool results available for this work.

The assistant helped inspect `TASK.md` and the repository, implement the
FastAPI CSV parser and deterministic categorizer, write backend tests, build
the Vite/React/TypeScript frontend, write documentation, and interpret
validation output. The candidate should confirm this list is complete and
amend it if they used any other AI tools.

No AI model is used by the application to decide transaction categories.
Those decisions are made by explicit Python matching rules.

## Mistakes and corrections

- The first frontend build failed because TypeScript did not have Vite's
  `import.meta.env` type declarations or the Node types required by the Vite
  config. The Vite client type reference and Node type dependency were added;
  the production build then passed.
- The first Vite proxy smoke test used a backend port other than the proxy's
  configured target, so the proxy returned a connection error. The test was
  rerun with the backend on port `8000`, after which the CSV upload through
  Vite succeeded.
- The finite merchant rules cannot confidently classify every transaction.
  The implementation leaves unmatched descriptions and refunds with unknown
  merchants flagged for review instead of claiming comprehensive coverage.

## Token usage and required evidence

**Actual token counts: unavailable.** No per-assessment token totals, model
usage report, raw usage log, or screenshot was exposed in the tools available
for this repository task. The session-usage records that could be queried
contained no matching records. Counts are therefore not estimated or
fabricated.

`TASK.md` specifically asks for how many tokens were used and token logs or
usage screenshots from the tools. It does not describe an alternative
documentation method when those records are unavailable. No log or screenshot
is attached because none was available to this assistant.

**Candidate action required before submission:** obtain the actual usage
summary/log or screenshot from the Copilot/AI tool's own usage interface or
account history, add it here or include it as an attachment in the submission,
and enter any actual token totals it provides. If the tool does not expose
assessment-specific token totals or exportable evidence, state that limitation
and ask the assessment contact how they want the requirement documented.
Do not substitute estimates for missing measurements. Review the tool list
above and add any tools used outside this session.

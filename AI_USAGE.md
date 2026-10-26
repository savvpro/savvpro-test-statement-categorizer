# AI usage disclosure

## Tools used and what they did

This repository was authored with **OpenAI Codex in ChatGPT Work Mode**, acting as the coding assistant in the conversation. It used terminal/file-editing tools to implement code, install dependencies, run tests, inspect failures, and package the result. Web search was used to check primary FastAPI, React, Vite, and Python documentation.

AI assistance covered scope selection (a freelance designer's business account), architecture, the deterministic rules, parsing/validation, persistence, UI components and styling, synthetic fixtures, tests, documentation, and code review/fixes. It was not limited to autocomplete. No autonomous sub-agents were used. The user requested clean maintainable code with comments, fake data, tests, and all deliverable files, then selected **Deliver files first** and declined GitHub installation.

**No AI model is used by the running application.** Transaction decisions are made exclusively by `backend/statement_categorizer/engine.py` plus deterministic pending/duplicate checks in `store.py`. No API keys are required. ChatGPT helped write this code; ChatGPT does not classify uploaded transactions.

## Where the initial work was wrong or incomplete

The assistant did not assume its initial output was correct:

1. Initial Python imports were not consistently ordered. Ruff reported these and they were corrected and formatted.
2. Initial transfer matching was too broad: `TRANSFER FROM CLIENT` could be mistaken for an internal transfer. The rule was restricted to explicit own-account labels, and a regression test was added for client/contractor transfers.
3. Early summary export covered expense categories but omitted accepted Income, Transfers, and Personal totals. Those categories were added as separate non-expense summary rows so an accountant can see cash movement without inflating expenses.
4. Some initial React tests used a Playwright-style `exact` option that Testing Library's `ByRoleOptions` does not support. Unit execution passed, but the TypeScript production build caught the mismatch. Those options were removed.
5. The first real-browser run found a narrow-screen overflow. Browser DOM measurements were used to identify the layout cause rather than hiding the page overflow globally.
6. Two browser selectors were too broad/brittle: an exact text-label lookup for a nested select, and a generic `status` locator while both a notification and loading status existed. They were changed to the relevant combobox role and specific status message. The product behavior itself was then tested with the real backend.

The standard Playwright browser download failed in the authoring environment because its downloaded archive was invalid. An independently installed Chromium binary was used for browser validation through the existing executable-path override. This was a test-environment workaround; no browser binaries or serverless Chromium package are included in the application repository.

See `docs/VERIFICATION.md` for final test results and actual limits. Test coverage is evidence about the tested behavior, not proof that every possible bank export or tax scenario is handled.

## Token accounting: unavailable, not invented

**Exact input, output, cached, and reasoning token counts are not exposed to this assistant by this ChatGPT Work Mode session.** The underlying model/version identifier and a provider-generated usage screenshot/export were also not exposed. Therefore:

- The token fields in `docs/ai/usage.json` are `null`, meaning **unavailable**, not zero.
- `docs/ai/session-log.jsonl` is an activity/evidence log, **not an authoritative token log**.
- No token number, cost, provider screenshot, or benchmark has been fabricated.
- No GPT/Claude/Gemini categorization usage occurs at runtime; that is separate from the unavailable development-assistance token count.

The assignment's requirement for an **exact token count plus tool usage logs/screenshots remains incomplete** until the user supplies an authentic usage export or screenshot from their AI tool/account. If one is available, add the original evidence under `docs/ai/`, redact any secrets, replace the null values with its reported totals, and state its scope (this session versus the whole account). Do not label an estimated tokenizer count as provider-reported usage.

## Authorship and review

The coding assistant executed the validations recorded in the verification document and inspected the application in Chromium. This does not imply that the user independently reviewed every line. A human reviewer should focus on the business-account assumption, conservative abstention policy, money-sign normalization, review/export invariants, and local-only deployment scope.

There was no remote GitHub write and no pull request: the user chose file delivery first and declined GitHub access. A prepared PR body is provided in `PULL_REQUEST.md` for later submission.

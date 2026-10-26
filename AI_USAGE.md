# AI Usage Log

This assessment was built with **Cursor (Composer)** as the primary AI-assisted coding tool.

## Tools used

| Tool | Role |
|------|------|
| Cursor Agent (Composer) | Project scaffolding, FastAPI backend, rule engine, React UI, tests, documentation |
| Cursor codebase search / terminal | Running pytest, npm, verifying endpoints |

**Not used for categorization:** No GPT, Claude, Gemini, or other large models are called at runtime to assign categories. The “brain” is deterministic Python (`backend/app/brain/categorizer.py`).

## How AI helped

- **Speed:** Boilerplate for FastAPI, Pydantic models, Vite React, and pytest layout.
- **Edge cases:** Prompted thinking about refunds vs income, transfers, debit/credit CSV columns, and “Needs Review” defaults.
- **UX copy:** Header text and table layout for review workflow.

## Where AI needed correction / human judgment

- **Initial vite scaffold:** Default template was replaced with the categorizer UI (not shipped as-is).
- **Categorization rules:** AI-suggested broad patterns (e.g. all “CAFE”) were kept at **medium** confidence or **Needs Review** to honor “wrong guess is worse than asking.”
- **Production concerns:** In-memory session store is intentional for scope; a real product would use auth + persistent storage.

## Token usage

Token counts are reported by the Cursor session billing/usage UI, not exported into this repo automatically.

| Session | Approx. usage | Notes |
|---------|----------------|-------|
| Statement Categorizer build (Oct 26, 2026) | *See Cursor Settings → Usage* | Single agent session: backend, frontend, tests, docs |

**Action for reviewers:** Open Cursor → account/usage for this date and attach a screenshot to this PR if required by your process.

### Placeholder log (update from your Cursor usage screen)

```
Model: Composer (agent)
Estimated input tokens:  
Estimated output tokens: [paste from usage UI]
Total:                   [paste from usage UI]
```

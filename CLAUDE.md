# Project: Statement Categorizer (SAVV Pro assessment)

## What we're building
A tax-time statement categorizer for a FREELANCE SOFTWARE DEVELOPER in Pakistan.
User uploads a CSV bank/card statement → app parses rows → rule-based brain assigns
category + kind + confidence + reason → user reviews and fixes "Needs Review" rows
→ sees totals per category → can export the categorized CSV.

## Hard rules
- The categorization brain is rule-based Python code. NEVER call any LLM/AI API
  (OpenAI, Anthropic, Gemini, etc.) or ML model from application code.
- Never run git commit, push, checkout, reset, or any git command that changes state.
  The developer reviews and commits everything himself.
- Fake data only. No real people, real account numbers, or real statements.
- Never write secrets into files. Config via environment variables, with .env.example only.
- Money is always Decimal, never float. Never modify raw_description.
- When unsure, a row goes to Needs Review. A wrong guess is worse than asking.

## Stack
- Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy + SQLite, pytest
- Frontend: Vite + React + TypeScript
- Rules stored as data in YAML, not hardcoded if-statements
- CI: GitHub Actions running pytest

## Layout
backend/app/{main.py, api/, core/, ingest/, brain/, db.py, models.py, schemas.py}
backend/tests/
frontend/
sample_data/
docs/
README.md, DESIGN.md, AI_USAGE.md in repo root

## Categories
Software & Subscriptions, Hosting & Cloud, Hardware & Equipment, Internet & Phone,
Travel, Meals, Office Supplies, Professional Services, Bank Fees, Income, Transfer,
Refund, Personal, Tax Withheld, Needs Review
Kinds: expense, income, transfer, refund, fee, tax
Summary: rows with kind `tax` get their own total ("Tax already paid"), separate from expenses.

## Working style
- Small, focused changes. Explain what you changed and why after each task.
- Write tests alongside code, parametrized for edge cases.
- Don't build ahead of the current task.

## AI usage log (mandatory after every task)
After completing ANY task, append an entry to docs/ai-usage/log.md in this format:

### <YYYY-MM-DD HH:MM> — <short task title>
- **Asked:** one-line summary of what the developer asked for
- **Generated/changed:** list of files created or modified
- **Assumptions I made:** decisions taken without being told (be explicit)
- **Unsure about / please check:** anything that might be wrong or needs review
- **Developer review:** _(to be filled by Dawood: what was wrong, what he changed)_
- **Tokens:** _(to be filled by Dawood from usage screenshot)_

Rules:
- Never invent or estimate token counts. Leave the Tokens field for the developer.
- Be honest about assumptions and uncertainty. That section matters most.
- Never fill in the Developer review field.

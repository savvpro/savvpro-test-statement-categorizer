# Active Context

Update this at the start and end of every session. Keep it short.

## Now
- All phases done, GUI click-tested by Bilal: brain, API, Next.js frontend, GUI restyle, tests, README, DESIGN.md, AI_USAGE.md.
- Final checks run: 74 pytest, ruff, 11 Vitest, eslint, `next build`, end-to-end on the sample, secret and LLM scans.
- Branch: `candidate-bilalnadeem614` (user handles all git actions)

## Waiting on Bilal
1. Commit, push, open the PR

## Decisions made
- Task chosen: Statement Categorizer. Use case: freelance developer, PKR statement, fictional bank
- Stack: FastAPI, React/Next.js, in-memory state, no database
- Threshold 0.7; first matching rule wins; Needs Review sets category, duplicates keep category but set `needs_review`
- Failed ATM + reversal use category Transfer (not spending); duplicates count as spending
- Netflix is Entertainment; Liberty Books, JazzCash top-up, AMZN, M/S, Raast stay in Needs Review
- Categories: Travel & Transport (PSO, Careem), Entertainment
- API money is serialized as strings; PATCH rejects Needs Review as a target
- Claude never commits or pushes
- Root `README.md` (the fork instructions from the task template) was replaced by the project README

## Open questions
- None

## Blockers
- None

## Notes
- Use `conda run -n assigment python -m <tool>` (bare `pytest`/`uvicorn` can resolve to `~/.local/bin`, Python 3.14); run tests from `backend/`
- `summarize_sample.py` prints the sample result
- Frontend: `npm run dev`, `npm test`, `npm run lint`, `npm run build`
- Frontend never does money math except Net (BigInt cents); Intl formats Decimal strings

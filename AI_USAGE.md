# AI usage

This file lists the AI tools used to build the project, how they helped, where they were wrong, and how many tokens were used.

**No AI model makes categorization decisions at runtime.** The brain is plain rule-based Python (`backend/app/rules.py`, `engine.py`, `passes.py`). There is no LLM or other AI client in the application code, the API or the tests. The AI tools below were used only to help write the code, tests and documents.

## Tools used

| Tool | What for |
|---|---|
| Claude (chat, claude.ai) | Choosing the task and use case, planning and time-boxing the six hours, generating the fake PKR sample CSV, and writing `CLAUDE.md` and the project memory files |
| Claude Code (CLI/IDE agent) | Building the project in separate sessions: setup and brain, API, frontend, UI restyle, and the final docs and checks. The local session logs show the model `claude-sonnet-5-5` for all five sessions |
| caveman plugin | Terse chat replies from Claude Code, to save tokens. Not used for the shipped docs |
| ponytail plugin | Pushes toward the smallest working solution. `ponytail:` comments mark deliberate shortcuts (for example the single in-memory store) |
| graphify plugin | Builds a knowledge graph of the code for orientation. Run with `--code-only` (see below). `graphify-out/` is git-ignored |

The model used in the Claude chat was not recorded.

## How they helped

- **Planning and time-boxing.** The chat produced a phased plan (setup, brain, API, frontend, tests, docs) with a cut list, so the highest-risk part, the brain, got the most time.
- **Memory-file workflow.** `CLAUDE.md`, `prd.md`, `implementation_plan.md`, `active_context.md`, `progress.md` and `system_patterns.md` give Claude Code the same context in every session. Each session starts by reading them and ends by updating `active_context.md` and `progress.md`. The files are committed on purpose, to show the workflow.
- **Rule engine and tests.** Claude Code wrote the parser, normalizer, ordered rule list, confidence threshold, and the transfer, refund, reversal and duplicate passes, with pytest coverage of every rule type and each edge case from the PRD.
- **API.** The FastAPI endpoints, Pydantic schemas, string-encoded money, upload validation and API tests.
- **Frontend.** The Next.js page, typed fetch helpers, formatting helpers with Vitest tests, filters and inline category edit.
- **UI restyle.** The dashboard layout, stat cards, category bars, drag-and-drop upload, toast, skeleton and a dark palette.
- **Final pass.** The README, a rewrite of `DESIGN.md` against the code, and the final checks (tests, lint, build, end-to-end run, secret and LLM-import scans).

## Where AI got things wrong or needed correction

- **`backend/requirements.txt` pins did not match the installed environment.** The first fix synced them, but to the wrong place. In the final session the pins (`fastapi==0.139.2`, `uvicorn==0.51.0`, `pydantic==2.13.4`) turned out to come from a `pip` in `~/.local` (Python 3.14), not from the conda env `assigment`, which has `fastapi==0.162.0`, `uvicorn==0.54.0` and `pydantic==2.14.1`. They are now synced to the env, and `backend/tests/test_requirements.py` fails if they drift again.
- **Bare `pytest` and `uvicorn` ran from the wrong Python.** Inside `conda run -n assigment`, `pytest` and `uvicorn` resolved to `~/.local/bin` (Python 3.14). The README therefore uses `conda run -n assigment python -m pytest` and `python -m uvicorn`.
- **`npm i -D vitest` failed** on a `@types/node` peer conflict. Fixed by bumping `@types/node` to 22.
- **graphify's document indexing needs an LLM key.** It was run with `--code-only`, so the docs are not in the graph.
- **The `frontend-design` skill lookup found nothing**, so the visual direction was chosen manually.
- **The agent did not click through the UI in a browser.** It was screenshot-checked at 1440 px and 390 px in light mode only. Bilal tested the interactions by hand.
- **Extra categories needed a human decision.** Claude Code could not decide alone whether to add Entertainment and Travel & Transport. Bilal decided.
- **Leftover scaffolding.** `create-next-app` boilerplate (`frontend/README.md`, unused SVGs in `frontend/public/`) was not cleaned up by the agent. The root `README.md` still held the task's fork instructions until the final session replaced it.

## Human decisions

Bilal chose the task (Statement Categorizer), the use case (a freelance developer with a PKR statement from a fictional bank), the stack, the categories (including Entertainment and Travel & Transport), and the rule that only Bilal runs `git add`, `commit`, `push` and opens the pull request. Claude never ran those commands.

## Token usage

Proof files go in [`docs/token-usage/`](docs/token-usage/README.md). Figures marked "session log" were summed from the local Claude Code session logs (`~/.claude/projects/`, assistant message usage, de-duplicated by message id). They are what the logs record, not a billing statement, so use them as a cross-check against the `/cost` screenshots. "Input" is the uncached input plus cache write plus cache read. Cache reads dominate because every turn re-reads the cached context.

| Tool | Purpose | Input (uncached / cache write / cache read) | Output | Total | Proof file |
|---|---|---|---|---|---|
| Claude chat | Task choice, planning, sample CSV, memory files | Not shown by claude.ai (usage page reports percent of plan limit only) | n/a | n/a | `docs/token-usage/claude-chat-usage-SS.png` |
| Claude Code, session 1 | Setup and brain (Phase 0-1) | 26 / 87,716 / 949,907 (session log) | 33,939 | 1,071,588 | `docs/token-usage/claude-code-session-logs.txt` |
| Claude Code, session 2 | Brain tweaks and API (Phase 2) | 28 / 56,122 / 953,654 (session log) | 13,471 | 1,023,275 | `docs/token-usage/claude-code-session-logs.txt` |
| Claude Code, session 3 | Frontend (Phase 3) | 34 / 54,265 / 1,127,517 (session log) | 13,922 | 1,195,738 | `docs/token-usage/claude-code-session-logs.txt` |
| Claude Code, session 4 | UI restyle | 40 / 88,444 / 1,819,364 (session log) | 25,933 | 1,933,781 | `docs/token-usage/claude-code-session-logs.txt` |
| Claude Code, session 5 (final docs and checks) | README, DESIGN.md, AI_USAGE.md, final checks | 58 / 83,176 / 2,396,493 (session log, snapshot) | 22,851 | 2,502,578 | `docs/token-usage/current-session.txt`; `docs/token-usage/claude-code-usage-SS.png` |

Notes:

- The screenshots (`claude-code-usage-SS.png`, `claude-code-usage-SS-other-session.png`, `claude-chat-usage-SS.png`) are the Claude "Account & Usage" and Settings usage panels. They show percent of the plan limit (session 21%, week 7% at capture time), not token counts, and the limits are shared across chat and Claude Code. The token counts in the table therefore come from the local session logs.
- Closed sessions are covered by the logs only, not by per-session `/cost` screenshots.
- The session 5 row is a snapshot taken while the session was still running, so it is lower than the final figure.
- `/cost` is a command only the user can type, so the figures here were not taken from it.
- The session-to-phase mapping comes from the first prompt of each session log.

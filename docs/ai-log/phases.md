# AI work log — phases, agents, models, tokens

Sub-agent token counts come from each agent's completion notice. Main-session (Opus) usage comes from the `/cost` screenshots in `screenshots/`.

## P0–P3 (setup + parallel build) — 2026-10-26

| Agent | Model | Scope | Tokens | Duration | Outcome |
|---|---|---|---|---|---|
| Orchestrator | Opus 5.5 | fork/clone/branch, domain contract, brain (rules, stages, resolver, cross-row), brain tests, evaluator | see /cost | — | — |
| devops-builder | Haiku 5.5 | Docker, compose, Makefile, pre-commit, CI/security/release workflows, Dependabot, agent defs | 113,326 | 5.8 min | done |
| fixture-builder | Haiku 5.5 | sample generator, 6 fake statements + labels, coverage script | 155,831 | 6.8 min | done; 53/66 catalog IDs, gaps covered by unit tests |
| backend-builder | Sonnet 5.5 | ingest, normalize, core, db, services, API, tests | 232,067 | 29.0 min | done; 265 tests, 95% coverage, ruff + mypy strict clean |
| frontend-builder | Sonnet 5.5 | Next.js UI per 07/07a | 133,137 | 26.4 min | done; lint/types/21 tests/build green |

Decisions:
- Four builders ran in parallel in disjoint directories of one tree instead of separate worktrees. With contracts frozen first there was no merge risk, and it saved worktree setup and merge time.
- Agents used `general-purpose` + a model override with the brief from `.claude/agents/*`, avoiding a session restart.

## P4 (integration) — orchestrator
- Bound the frontend's hand-written API types to the generated OpenAPI schema. That surfaced 3 real contract mismatches (optional request fields, untyped error rows), all fixed.
- Brain tuning loop (evaluator): 97.5% → 100% auto precision, 100% review recall, 71% coverage.

## P5 (review wave) — 5 read-only reviewers in parallel
| Agent | Model | Scope | Tokens | Findings |
|---|---|---|---|---|
| security-reviewer | Sonnet 5.5 | OWASP / plan 05 | | |
| edge-case-reviewer | Sonnet 5.5 | unseen adversarial transactions vs brain | | |
| architecture-reviewer | Sonnet 5.5 | layering, contract, tests | | |
| ui-reviewer | Sonnet 5.5 | Nielsen heuristics, 07a anti-template, a11y | | |
| cicd-reviewer | Haiku 5.5 | workflows vs real repo + live CI logs | | |

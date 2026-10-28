# AI usage

## 1. Tools and models

| Tool | Use |
|---|---|
| **Claude Code** (VS Code extension, Claude Pro plan) | The only AI tool used. It planned, wrote, tested, reviewed and committed the code |
| Claude **Opus 5.5** | Orchestrator: planning, contracts, **the brain** (rules, stages, resolver, cross-row passes), brain tuning, integration |
| Claude **Sonnet 5.5** | Builders (backend, frontend) and 4 of the 5 independent reviewers, plus 2 fix agents |
| Claude **Haiku 5.5** | Mechanical work: fake-data generator, Docker/CI files, CI/CD review |
| Claude Fable | Not used |

**No AI model is part of the product.** The brain is plain Python in `backend/app/brain/`. `scripts/check_no_llm_deps.sh` runs in CI and fails the build if any LLM/ML SDK appears in the Python or Node dependencies.

## 2. How the work was organised

1. **Plan first.** Before writing code, the orchestrator wrote 13 plan files (architecture, brain, ingestion, 79 edge cases, security, tests, UI design system, CI/CD, orchestration, runbook), kept in [docs/plan/](docs/plan/00-INDEX.md). Sub-agents read these files instead of a chat history, which kept briefs short.
2. **Contract first.** The orchestrator wrote the domain model, taxonomy, rule loader and API contract before any builder started, so four builders could run **in parallel in disjoint directories** with no merge conflicts.
3. **Build in parallel.** Backend, frontend, fixtures and DevOps ran as four background agents while the orchestrator wrote the brain.
4. **Measure, don't guess.** A labelled evaluation (`scripts/evaluate_brain.py`) drove brain tuning: 97.5% → 100% auto precision.
5. **Independent review wave.** Five read-only reviewers (security, edge cases, architecture, UI/UX, CI/CD) ran in parallel and wrote reports to [docs/reviews/](docs/reviews/). Every High/Medium finding was triaged and fixed by two scoped fix agents or by the orchestrator.
6. **Agent definitions** for all ten roles are committed in [.claude/agents/](.claude/agents/).

Sub-agents never committed. The orchestrator reviewed results and committed in small, conventional commits under the author's identity.

### Model routing

| Job | Model | Why |
|---|---|---|
| Orchestration, the brain, integration | Opus | Judgment-heavy and correctness-critical; the most graded part |
| Backend and frontend builds, 4 reviews, 2 fix passes | Sonnet | Well-specified by the plan files; strong coding at lower cost |
| Fixtures, Docker/CI files, CI review | Haiku | Mechanical and template-like |

## 3. How AI helped

- **Brain:** layered rule engine with noisy-OR confidence, direction logic, refund handling, duplicate/recurring/1099 passes, and plain-English reasons for every decision.
- **Ingestion:** CSV (encodings, delimiters, header detection, date and amount inference) and an own OFX reader (SGML and XML, XXE-safe).
- **Product:** FastAPI + SQLAlchemy + Alembic backend, a keyboard-driven review UI built to the HCI rules in `docs/plan/07a`, Docker, CI/CD, security scanning.
- **Tests:** 288 backend tests (96% coverage), 26 frontend tests, a golden evaluation, property tests, security tests.
- **Review:** the five reviewers found real defects the builders missed (below).

## 4. Where AI got things wrong

Full log: [docs/ai-log/mistakes.md](docs/ai-log/mistakes.md). Highlights, each caught by a test, evaluator, reviewer or CI:

| # | What went wrong | Caught by | Fix |
|---|---|---|---|
| 1 | Brain's first evaluation had **97.5% auto precision**: a keyword anchor failed on trailing text, a bank fee matched the returned-item rule, and a person-name fallback fired before keyword rules | Golden evaluator + unit tests | Rules and stage order fixed; 100% precision |
| 2 | Bare `WATER` keyword auto-sorted `NEW WATER HEATER INSTALL` as a **utility bill** (wrong confident answer) | Edge-case reviewer, which probed ~100 unseen inputs | Require utility context; generic `WATER` can only suggest |
| 3 | `PARENT'S RENT HELP` (a gift) auto-sorted as tenant rent | Edge-case reviewer | Exclusion words for rent-by-word |
| 4 | Backend agent's partial-import rule rejected a 14-row file with 2 bad rows | Golden evaluator | Refuse only when bad rows > max(2, 5%) |
| 5 | Fixture agent numbered rows differently from the parser, shifting labels | Golden evaluator | Labels realigned; human-reviewed |
| 6 | Frontend lockfile generated on Windows lacked Linux packages: **CI `npm ci` failed** (two jobs) | GitHub Actions emails | Regenerated in a clean directory; verified with `npm ci --dry-run` |
| 7 | DB commit ran in a dependency teardown, so a commit failure could surface after the response was sent. Identical concurrent uploads could both succeed | Architecture reviewer | Explicit commits; unique hash constraint; 409 on race |
| 8 | Compose published the web app on all network interfaces although the app has no login | Security reviewer | Bound to `127.0.0.1` |
| 9 | Undo after Confirm did not return the row to the review list; focus was lost; toast overlapped the mobile sheet | UI reviewer | Fixed in the fix pass |
| 10 | `winget` hung on a hidden prompt; `uv sync` deadlocked on a lock held by two agents; slow network caused download timeouts | Orchestrator | Killed, switched installer, longer timeouts |

Known gap, left in place: the API cannot "un-confirm" a row, so after Undo the UI reopens it locally and the server's confirmed count differs until the row is confirmed again. Documented here rather than hidden.

## 5. What stayed human-decided

The use case (landlord, Schedule E), CSV and OFX scope, the rule that the brain must be own code, all expected labels in `samples/*.expected.json` (reviewed by the orchestrator against the catalog, not generated blindly), thresholds and the precision-first policy, the scope cuts below, and the decision to run reviews and fixes as separate steps.

Scope cut for the 2-hour limit: the transaction **split** endpoint, a live release run, and `unsafe-inline` removal from the CSP (needs nonces). All are documented.

## 6. Token usage

Sub-agent token counts are exact, taken from each agent's completion notice.

| Phase | Agent | Model | Tokens |
|---|---|---|---:|
| Build | backend-builder | Sonnet 5.5 | 232,067 |
| Build | frontend-builder | Sonnet 5.5 | 133,137 |
| Build | fixture-builder | Haiku 5.5 | 155,831 |
| Build | devops-builder | Haiku 5.5 | 113,326 |
| Review | security-reviewer | Sonnet 5.5 | 93,674 |
| Review | edge-case-reviewer | Sonnet 5.5 | 70,369 |
| Review | architecture-reviewer | Sonnet 5.5 | 108,301 |
| Review | ui-reviewer | Sonnet 5.5 | 94,178 |
| Review | cicd-reviewer | Haiku 5.5 | 94,823 |
| Fix | backend fix pass | Sonnet 5.5 | 106,656 |
| Fix | frontend fix pass | Sonnet 5.5 | 98,200 |
| | **Sub-agents total** | | **1,300,562** |

Split: build 634,361 (49%), independent review 461,345 (35%), fixes 204,856 (16%).

**Main session (Opus orchestrator, then Sonnet for fixes and docs):** Claude Code does not expose an exact per-session token count in the editor. The usage panel after the build, review and fix phases showed **65% of the 5-hour session limit and 48% of the weekly limit** used ([screenshot](docs/ai-log/screenshots/usage-1.png)). The panel attributes 14% of usage to the `general-purpose` sub-agents. Per-phase detail is in [docs/ai-log/phases.md](docs/ai-log/phases.md).

### Token-saving practices actually used
- Plan files and `CLAUDE.md` as shared context; briefs reference sections, not pasted text.
- Sub-agent reports capped at 120–150 words; reviewers wrote details to files.
- The cheapest model that could do each job: Haiku for mechanical work, Sonnet for building and reviewing, Opus only for the brain and coordination.
- Parallel agents in disjoint directories (no ping-pong between agents); one review wave and one fix pass.
- No background polling: every long task ran as a background job with a completion notification.
- Unused MCP servers disabled for the session; GitHub work done through the `gh` CLI.
- Switched the main session from Opus to Sonnet once the brain and integration were done.

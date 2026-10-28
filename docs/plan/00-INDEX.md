# Plan Index — Statement Categorizer (Landlord · CSV + OFX)

Master overview: [PLAN.md](../PLAN.md). These files are the **single source of truth** for execution.
During P0 they are copied into the repo at `docs/plan/` (evidence of engineering process for graders).

| # | File | Answers |
|---|---|---|
| 01 | [01-architecture.md](01-architecture.md) | Layers, modules, domain model, DB schema, full API contract, config, errors, ADRs |
| 02 | [02-brain.md](02-brain.md) | The categorization engine: algorithm, scoring math, rule files, every rule, evaluation |
| 03 | [03-ingestion.md](03-ingestion.md) | CSV/OFX parsing, format detection, normalization, merchant cleaning |
| 04 | [04-edge-cases-and-fixtures.md](04-edge-cases-and-fixtures.md) | Edge-case catalog with IDs + expected outcome; fake data generator spec |
| 05 | [05-security.md](05-security.md) | Threat model (STRIDE), controls, secure defaults, verification |
| 06 | [06-testing.md](06-testing.md) | Test pyramid, every test file, gates |
| 07 | [07-frontend.md](07-frontend.md) | Pages, components, state, API client, UX states, accessibility |
| 07a | [07a-ux-design-system.md](07a-ux-design-system.md) | HCI principles → features, design tokens, wireframes, anti-template self-review, microcopy, design validation |
| 08 | [08-cicd-devops.md](08-cicd-devops.md) | GitHub Actions (CI + CD), Docker, compose, pre-commit, Makefile, release |
| 09 | [09-ai-orchestration.md](09-ai-orchestration.md) | Agents, models, briefs, token discipline, logs |
| 10 | [10-execution-runbook.md](10-execution-runbook.md) | Ordered step-by-step execution with commands, checks, commits |
| 11 | [11-docs-and-submission.md](11-docs-and-submission.md) | README / DESIGN / AI_USAGE outlines, PR body, final checklist |

## Global conventions (apply everywhere)

- **Languages/runtimes:** Python 3.13 (uv), Node 24 LTS (npm). Exact library versions resolved at P0 and frozen by lockfiles.
- **Money:** integer cents (`int`) end-to-end in backend; `Decimal` only during parsing; never `float`.
- **Dates:** `datetime.date` (posted date), ISO-8601 strings on the wire. Timestamps UTC.
- **IDs:** UUID4 strings.
- **Naming:** Python snake_case, TS camelCase in code / snake_case on the wire (API JSON is snake_case; TS types generated from OpenAPI keep snake_case — no mapping layer).
- **Line endings:** LF everywhere (`.gitattributes`), except fixtures that deliberately test CRLF (marked `-text`).
- **Commits:** Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `ci:`, `chore:`, `refactor:`), small, one concern each. Author `SyedAshherMajid <i230007@isb.nu.edu.pk>`. **No AI co-author / "Generated with" lines.**
- **Definition of Done (every task):** code + tests + lint + types pass locally; no TODOs without an issue note; docs touched if behavior changed.

## Global Definition of Done (submission)
1. Every TASK.md requirement ticked in PLAN.md §0.
2. `make check` green locally; CI green on fork.
3. `docker compose up` → app usable at http://localhost:3000 with a sample file.
4. Golden evaluation: auto-precision = 100%, review-rate reported.
5. README, DESIGN, AI_USAGE complete with screenshots/token logs.
6. PR open against `savvpro/savvpro-test-statement-categorizer:main`.

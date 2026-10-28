# 09 — AI Orchestration & Token Discipline

Graded as heavily as the code (per HR). Goal: show *deliberate* use — right model per job, parallelism where safe, reviews that catch real defects, measured token spend.

## 1. Model routing
| Model | Used for | Why |
|---|---|---|
| **Opus 5.5** (main session) | orchestration, contracts, the brain, label review, integration, final decisions | judgment-heavy, correctness-critical, needs full context |
| **Sonnet 5.5** | backend/frontend building, security/edge-case/architecture/UI reviews | strong coding at lower cost; work is well-specified by plan files |
| **Haiku 5.5** | fixture generator script, Docker/CI files, CI review, process audit, doc formatting | mechanical, template-like |
| **Fable 5.1** | not used by default | only if a blocking problem defeats Opus; logged with justification |

Effort: Haiku `low`, Sonnet builders `medium`, Sonnet reviewers `high` (finding bugs needs depth), Opus default.

## 2. Agent definitions (`.claude/agents/*.md`, committed)
Frontmatter fields: `name`, `description`, `tools`, `model`. Body = role, inputs (which plan files), rules, output format.

| File | model | tools | Inputs | Output |
|---|---|---|---|---|
| `backend-builder.md` | sonnet | Read, Write, Edit, Glob, Grep, Bash | CLAUDE.md, plan 01, 03, 05, 06 | code + tests; ≤150-word report |
| `frontend-builder.md` | sonnet | Read, Write, Edit, Glob, Grep, Bash | CLAUDE.md, plan 07 + **07a**, openapi.json; frontend-design skill for critique; context7 for library docs | code + tests + Playwright screenshots it has looked at; report |
| `fixture-builder.md` | haiku | Read, Write, Edit, Bash | plan 04 | generator + samples + draft labels; report |
| `devops-builder.md` | haiku | Read, Write, Edit, Glob, Bash | plan 08 | Docker/CI/Make/pre-commit; report |
| `security-reviewer.md` | sonnet | Read, Glob, Grep, Bash, Write(report only) | plan 05 + code | `docs/reviews/security.md` |
| `edge-case-reviewer.md` | sonnet | Read, Glob, Grep, Bash, Write(report only) | plan 02, 04 + evaluator output | `docs/reviews/edge-cases.md` (+ proposed new fixture rows) |
| `architecture-reviewer.md` | sonnet | Read, Glob, Grep, Write(report only) | plan 01 + code | `docs/reviews/architecture.md` |
| `ui-reviewer.md` | sonnet | Read, Glob, Grep, Bash, Write(report only) | plan 07 + 07a §2/§5/§8, screenshots at 3 widths, axe output | `docs/reviews/ui.md` (Nielsen heuristic scores + walkthrough T1–T5 results) |
| `cicd-reviewer.md` | haiku | Read, Glob, Grep, Write(report only) | plan 08 + workflows | `docs/reviews/cicd.md` |
| `process-auditor.md` | haiku | Read, Glob, Grep, Write(report only) | `docs/ai-log/*`, `docs/reviews/*` | `docs/reviews/process.md` |

Reviewers instructed: "Do not modify code. Write findings only to your report file." (Write is restricted by instruction; reviewers get Edit removed.)
Note: custom agents are discovered at session start → after creating them in P0, restart the session (`/clear` is not enough; reopen) or fall back to `general-purpose` + `model` override with the definition file's body as the prompt.

## 3. Brief template (every spawn)
```
ROLE: <agent>
GOAL: <one sentence>
READ FIRST: CLAUDE.md, docs/plan/<nn>.md §<x>   (nothing else unless needed)
TOUCH ONLY: <paths>
ACCEPTANCE: <commands that must pass>, <behaviors>
DO NOT: change contracts (schemas/openapi), add dependencies without listing them, commit.
REPORT (≤150 words): files changed, commands run + result, open issues.
```
Builders never commit — orchestrator reviews diff and commits as the user (keeps authorship + history clean).

## 4. Review report template (`docs/reviews/<area>.md`)
```
# <Area> review — <date> — <agent> (<model>)
Scope: … | Method: … (files read, commands run)
| ID | Severity (High/Med/Low) | Location | Finding | Recommendation | Status |
Summary: counts by severity; verdict.
```
Orchestrator triages: High/Med → fix tasks; Low → fix or "won't fix (reason)". Status column updated after fix pass (evidence loop).

## 5. Parallelism plan
- P1: architecture-reviewer ‖ edge-case-reviewer on the design (design-only, cheap).
- P3: brain (Opus, main tree) ‖ backend-builder (worktree A) ‖ frontend-builder (worktree B, against frozen openapi.json + MSW) ‖ devops-builder (worktree C). Contracts frozen before start → no merge conflicts by construction (disjoint directories).
- P5: 5 reviewers in parallel, one wave.
- P6: fixes grouped per directory, parallel where disjoint.

## 6. Token discipline (concrete rules)
1. Plan files + CLAUDE.md are the context; briefs reference sections, never paste them.
2. Sub-agent reports ≤150 words; reviewers write detail to files, orchestrator reads the summary table only.
3. Grep before Read; read file ranges, not whole files; never re-read a just-edited file.
4. No exploratory "look around the repo" spawns.
5. One review wave + one fix pass; no ping-pong. Re-review only High findings.
6. `/compact` at phase boundaries with a phase summary.
7. MCP/plugins: disable unauthenticated servers (Atlassian, Datadog, Linear, Notion, Slack) and the failing GitHub MCP for this project via `/mcp`; GitHub via `gh` CLI. Engineering plugin skills used on demand only (e.g. none needed for ADRs since plan 01 §10 already specifies them). Installed plugins used deliberately: **frontend-design** (enable for P3/P5 UI work only), **context7** (library docs lookups, on demand), **dataviz** skill (Summary bars only). `feature-dev` not needed — the plan files replace its workflow.
8. Haiku/Sonnet for everything that a plan file fully specifies.
9. Fail fast: builders run tests themselves; orchestrator only re-runs the gate commands.

## 7. Measurement → AI_USAGE.md
- `docs/ai-log/phases.md`: per phase — date, agents spawned (name, model, effort), tokens & duration from each agent's completion notice, main-session `/cost` delta, outcome, notable AI mistakes.
- `docs/ai-log/mistakes.md`: running list — what AI produced, how it was caught (test/reviewer/evaluator/human), fix.
- **User action:** screenshot `/cost` (and `/usage` if available) at end of each phase → `docs/ai-log/screenshots/phase-N.png`.
- Final table in AI_USAGE.md: tokens per model, per phase, % spent on review vs build, what was deliberately human-decided (use case, labels truth, thresholds, scope).

## 8. CLAUDE.md (repo root, committed) — contents
Project one-liner · how to run checks (`make check`) · architecture rules (layers, no framework in brain/domain) · money = int cents · API snake_case · contract change requires orchestrator · tests required with every change, edge-case IDs in names · no secrets, fake data only · no LLM libs · commit policy (agents don't commit) · pointers to docs/plan files. Kept < 80 lines (it's loaded into every agent's context).

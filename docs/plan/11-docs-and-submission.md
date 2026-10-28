# 11 — Docs & Submission

## 1. README.md outline
1. Title + one-line pitch + CI badge (fork) + **Candidate line**: "Submitted by Syed Ashher Majid — GitHub @SyedAshherMajid — applied with syedashhermajid@gmail.com".
2. What it does (landlord, Schedule E, CSV/OFX) + 3 screenshots (upload, review, summary).
3. Quick start (Docker): `docker compose up --build` → http://localhost:3000 → "Try a sample".
4. Local development: prerequisites (Python 3.13 + uv, Node 24), `make setup`, `make dev`; Windows equivalents.
5. Running tests & checks: `make check`, `make eval` (shows metrics), `make e2e`.
6. Configuration table (env vars, from 01 §7).
7. Project structure tree (short).
8. Supported formats & limits.
9. Links: DESIGN.md, AI_USAGE.md, SECURITY.md, docs/plan, docs/adr, docs/reviews.
10. Disclaimer: fake data, not tax advice.

## 2. DESIGN.md outline
1. Use case & user story (Dana the landlord at tax time).
2. Category taxonomy + Schedule E mapping table; non-P&L rationale.
3. Architecture diagram (from 01 §2) + layer rules.
4. **How the brain decides**: pipeline diagram, each stage with example, noisy-OR scoring with a worked example, thresholds, blocking flags table, "why" explanations, learning from corrections.
5. Being honest about uncertainty: when and why rows go to review; precision-first philosophy.
6. Edge cases: catalog summary table (ID, case, handling) → link to plan 04.
7. Evaluation results: metrics table + confusion matrix (from `make eval`).
8. Security design summary (link SECURITY.md / plan 05).
9. Trade-offs & ADR links; known limitations; future work (per-property, split UI improvements, PDF, auth/multi-tenant, Postgres).

## 3. AI_USAGE.md outline (required by TASK.md)
1. **Tools & models**: Claude Code (Opus 5.5 orchestrator, Sonnet 5.5 builders/reviewers, Haiku 5.5 mechanical), VS Code extension. What was *not* used (no LLM in product — enforced by CI guard).
2. **How we worked**: plan-first (docs/plan), contract-first, orchestration diagram (orchestrator → builders in worktrees → review wave → fix pass → audit), agent definitions in `.claude/agents`.
3. **Model routing rationale** table (09 §1).
4. **How AI helped**: concrete examples per phase.
5. **Where AI got things wrong** (from `docs/ai-log/mistakes.md`): each item — what, how caught (test / reviewer / evaluator / human), fix. Honest, specific.
6. **What stayed human-decided**: use case, category truth labels, thresholds philosophy, scope cuts, final review of every diff.
7. **Token usage**: per phase × model table; totals; % build vs review vs planning; token-saving techniques used (09 §6) and their effect.
8. **Evidence**: screenshots (`docs/ai-log/screenshots/`), links to review reports and process audit.

## 4. PR body (`docs/PR_BODY.md`)
```
## Summary
Statement categorizer for small landlords: upload CSV/OFX bank or card statements → every transaction mapped to IRS Schedule E or excluded (transfers, deposits, principal, improvements) → uncertain rows go to Needs Review → user fixes (with memory) → Schedule E summary + CSV export.

## The brain
Deterministic layered rule engine (no LLM; CI-enforced). Confidence via noisy-OR, margin + blocking flags force review. Golden evaluation: auto-precision 100%, review recall 100%, coverage X%.

## How to run
docker compose up --build → http://localhost:3000

## Quality
Tests (unit/property/golden/integration/security/e2e), coverage X%, CI + security scans + release to GHCR: <links to green runs>.

## Docs
README · DESIGN.md · AI_USAGE.md · SECURITY.md · docs/plan · docs/adr · docs/reviews

Candidate: Syed Ashher Majid (@SyedAshherMajid) — applied with syedashhermajid@gmail.com
```

## 5. Final submission checklist
- [ ] Every PLAN.md §0 row satisfied (re-read TASK.md one last time)
- [ ] `git log` — all commits authored by SyedAshherMajid <i230007@isb.nu.edu.pk>, no AI trailers (`git log --format='%an %ae%n%b' | grep -i claude` → empty)
- [ ] `gitleaks detect` clean; no `.env`, no `data/`, no real data
- [ ] `make check` green locally; CI, security, release runs green on fork
- [ ] `docker compose up --build` from a fresh clone works (test in a temp dir)
- [ ] README quick start followed verbatim by a fresh shell works
- [ ] DESIGN metrics match latest `make eval`
- [ ] AI_USAGE has token numbers + screenshots
- [ ] Review reports: no open High/Medium
- [ ] PR opened to upstream `main` with correct title; branch name `candidate-SyedAshherMajid`
- [ ] Before deadline

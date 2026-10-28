# 10 — Execution Runbook

## Time & budget box (binding)
Hard limits: **≈2 hours wall-clock** and **≤ ~90% of the session limit**. Timeline:
| Phase | Budget |
|---|---|
| P0 setup | 10 min |
| P1 contracts + rules | 15 min |
| P2 + P3 build (parallel agents) | 40 min |
| P4 integrate + eval tuning | 20 min |
| P5 + P6 review wave + fix | 20 min |
| P7 + P8 audit, docs, release, PR | 15 min |
Adjustments for the box:
- **No session restart for custom agents.** Spawn `general-purpose` with `model` override and pass the matching `.claude/agents/<name>.md` body as the brief. The files are still committed as evidence.
- **Cut order if behind:** (1) split endpoint, (2) release tag/GHCR run (keep the workflow file), (3) Playwright reduced to one smoke test, (4) property tests trimmed to the brain invariants, (5) process-auditor folded into the AI_USAGE writing. **Never cut:** brain + golden gates, review UI, tests, security basics, CI, the 3 required docs.
- Orchestrator checks the clock at each phase end. User watches session usage and says so at ~50% and ~75%.

Follow top to bottom. Each step: **Do → Check → Commit**. ✅ gates must pass before moving on. Commit messages are exact; author is the user; no AI trailers.

---

## P0 — Setup (Opus, ~no sub-agents)

0.1 Disable unused MCP servers for this project (`/mcp`) — user action, confirm.
0.2 Fork & clone
```bash
gh repo fork savvpro/savvpro-test-statement-categorizer --clone=true --remote=true -- D:/Savv_Pro_Assesment/savvpro-test-statement-categorizer
cd D:/Savv_Pro_Assesment/savvpro-test-statement-categorizer
git config user.name "SyedAshherMajid"; git config user.email "i230007@isb.nu.edu.pk"
git checkout -b candidate-SyedAshherMajid
```
Check: `git remote -v` shows origin=fork, upstream=savvpro; `git config user.email` correct.
0.3 Toolchain: `uv python install 3.13`; Node 24 (`nvm`/`fnm` or confirm `node -v`; if only Node 25 available, use it locally, CI pins 24).
0.4 Scaffold: root files (`.gitignore`, `.gitattributes`, `.editorconfig`, `README.md` stub, `CLAUDE.md`, `SECURITY.md`, `CHANGELOG.md`), `docs/plan/` (copy plan files + PLAN.md), `docs/adr/`, `docs/reviews/`, `docs/ai-log/{phases.md,mistakes.md,screenshots/}`.
0.5 Backend skeleton: `uv init --app backend`, add deps: `fastapi uvicorn[standard] pydantic-settings sqlalchemy alembic python-multipart defusedxml rapidfuzz pyyaml slowapi`; dev: `pytest pytest-cov hypothesis httpx ruff mypy types-PyYAML bandit pip-audit`. Configure ruff/mypy/pytest in `pyproject.toml`. `app/main.py` with `/healthz`.
0.6 Frontend skeleton: `npx create-next-app@latest frontend --ts --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm`; add `@tanstack/react-query @tanstack/react-table openapi-fetch @radix-ui/react-{select,tooltip,tabs,popover,dialog} lucide-react`; dev `openapi-typescript vitest @testing-library/react @testing-library/jest-dom jsdom msw @playwright/test @axe-core/playwright prettier eslint-plugin-jsx-a11y`.
0.7 `.claude/agents/*.md` per 09 §2. `Makefile` minimal (setup, test, lint).
✅ `uv run pytest` (1 health test) passes; `npm run build` passes.
Commits:
- `chore: initialize repository structure and tooling`
- `docs: add engineering plan and architecture decision records`
- `chore: add agent definitions and contributor guide`
Push: `git push -u origin candidate-SyedAshherMajid`. Log phase in `docs/ai-log/phases.md`. 📸 user screenshot.
**Restart session** so custom agents load.

## P1 — Contracts & design (Opus + 2 reviewers parallel)
1.1 `domain/enums.py`, `domain/models.py`, `domain/taxonomy.py` (from 01 §4, 02 §3).
1.2 `rules/*.yaml` seeded (02 §S1–S7) + `brain/rules.py` loader + `test_rules_integrity.py`.
1.3 `api/schemas.py` all request/response models (01 §6); routers stubbed returning 501; `scripts/export_openapi.py` → `backend/openapi.json`; `npm run gen:api` → `frontend/src/lib/api/schema.d.ts`.
1.4 `DESIGN.md` v1 (use case, taxonomy, brain overview, edge-case list) and ADR 001–007.
1.5 Spawn **architecture-reviewer** ‖ **edge-case-reviewer** (design scope only). Triage; apply changes.
✅ contracts frozen (openapi.json committed); rules integrity test green.
Commits: `feat(domain): add domain model and category taxonomy` · `feat(brain): add rule files and validated loader` · `feat(api): define v1 API contract and generate client types` · `docs: add design document v1` · `docs: record design review findings`.

## P2 — Fixtures (Haiku)
2.1 Spawn **fixture-builder**: `scripts/generate_samples.py` + `samples/*` + draft `*.expected.json` per 04 §2.
2.2 Opus **hand-reviews every label** (truth must be human-owned) and fixes.
✅ every catalog ID in 04 appears in at least one fixture (script `scripts/check_catalog_coverage.py` greps IDs embedded in expected.json `case_id`).
Commit: `test: add deterministic fake statements and labeled expectations`.

## P3 — Build (parallel)
Main tree (Opus): **brain** — stages, resolver, crossrow, explain + all brain unit/property tests + `scripts/evaluate_brain.py`.
Worktree A (backend-builder): ingest (detect, csv, ofx, amounts, dates), normalize, db models + Alembic initial migration, repositories, services, routers, core (config, logging, errors, security, ratelimit), integration + security tests.
Worktree B (frontend-builder): all of 07 + 07a against MSW mocks from generated types; unit tests; design tokens in Tailwind theme first, then pages; `scripts/check_contrast.mjs`; Playwright screenshot critique loop at 1440/1024/390 (07a §8) — builder must view its own screenshots and fix before reporting. Enable **frontend-design** plugin before this phase.
Worktree C (devops-builder): Dockerfiles, compose (+dev/prod overrides), Makefile full, pre-commit, workflows (ci, security, release), dependabot, PR template, CODEOWNERS, `check_no_llm_deps.sh`.
Rules for all: TOUCH ONLY own dirs; contracts frozen; tests must pass in their tree.
✅ per tree: its test command green.
Commits (orchestrator, after reviewing each diff, in this order):
`feat(ingest): add CSV and OFX parsing with format detection` · `feat(normalize): add merchant cleaning and sign normalization` · `feat(brain): implement layered categorization engine` · `feat(brain): add cross-row duplicate, recurring and 1099 passes` · `feat(db): add persistence layer and initial migration` · `feat(api): implement statements, transactions, summary and export endpoints` · `feat(security): harden uploads, headers, CORS and rate limiting` · `feat(web): add upload, review and summary pages` · `build: add Docker images and compose stack` · `ci: add CI, security and release workflows`.

## P4 — Integrate (Opus)
4.1 Merge worktrees (disjoint dirs → clean). Wire frontend to real API (rewrites).
4.2 `make eval` → tune per 02 §7 until gates pass. Log every tuning change.
4.3 Playwright e2e on compose.
4.4 `make check` green; push; **CI green on fork**.
✅ golden gates (precision 1.00, review recall 1.00); e2e green.
Commits: `feat: wire frontend to API` · `fix(brain): …` (one per tuning fix) · `test(e2e): add upload-to-export happy path`.

## P5 — Review wave (5 reviewers parallel, read-only)
security · edge-case (runs evaluator + tries new nasty rows) · architecture · ui (runs vitest/build, reads components) · cicd. Each writes `docs/reviews/<area>.md`.
Commit: `docs: add independent review reports`.

## P6 — Fix pass
Orchestrator triages into tasks grouped by directory; Sonnet builders fix (parallel if disjoint); High findings re-reviewed by the same reviewer (short brief). Update report Status column.
✅ zero open High/Medium; `make check` green; CI green.
Commits: `fix(<area>): <finding id> <summary>` (grouped sensibly) · `docs: update review statuses`.

## P7 — Process audit (Haiku)
process-auditor → `docs/reviews/process.md`. Opus applies any doc-level fixes.
Commit: `docs: add AI process audit`.

## P8 — Docs, release, PR (Opus)
8.1 Final README, DESIGN.md (with evaluation metrics table), AI_USAGE.md (11 §3) with screenshots + token tables.
8.2 Tag `v1.0.0` on fork → release workflow → GHCR images (demonstrates CD).
8.3 Final checklist (11 §5).
8.4 PR:
```bash
gh pr create --repo savvpro/savvpro-test-statement-categorizer --base main \
  --head SyedAshherMajid:candidate-SyedAshherMajid \
  --title "feat: complete statement-categorizer assessment" --body-file docs/PR_BODY.md
```
(Body has **no** "Generated with" line.)
Commits: `docs: finalize README, design and AI usage report` · `chore: release v1.0.0`.

---
## Risk register
| Risk | Mitigation |
|---|---|
| Custom agents not loaded mid-session | restart after P0; fallback general-purpose + model override |
| Windows path/line-ending issues | `.gitattributes`, LF, CI on ubuntu is source of truth |
| Python 3.14 local vs 3.13 pinned | `uv python install 3.13`, uv uses pinned `.python-version` |
| Fork PR CI not running upstream | link fork runs in PR |
| Brain over-tuned to fixtures | edge-case-reviewer adds unseen rows in P5; tuning log |
| Scope creep | P1/P2 features only after P0 scope gates green |
| Deadline | P0 scope first; P1 items (split, e2e, release) cut in reverse order if short |

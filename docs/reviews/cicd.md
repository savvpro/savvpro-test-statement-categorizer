# CI/CD review — 2026-10-26 — cicd-reviewer (Haiku 5.5)

Scope: `.github/workflows/{ci,security,release}.yml`, `.github/dependabot.yml`, `Makefile`, `docker-compose{,.dev,.prod}.yml`, `backend/Dockerfile`, `backend/entrypoint.sh`, `frontend/Dockerfile`, `.pre-commit-config.yaml`, `scripts/check_no_llm_deps.sh`, `frontend/playwright.config.ts` | Spec: `docs/plan/08-cicd-devops.md`
Method: Read all in-scope files; verified every referenced path, npm script (`frontend/package.json`), `backend/pyproject.toml` settings, `scripts/evaluate_brain.py`, `scripts/export_openapi.py`, `backend/openapi.json`, `frontend/e2e`, `backend/tests/unit`, `frontend/scripts/copy-samples.mjs` exists. Ran `gh run list` and `gh run view --log-failed` on runs 40376602437, 40376602356 (older commit, `chore:` head), 40377573646 (CI, HEAD `676714d`) and 40377573633 (Security, HEAD `676714d`). Run 40377573646 finished `failure` after the 4-minute watch; Security run finished `success`.

| ID | Severity (High/Med/Low) | Location | Finding | Recommendation | Status |
|---|---|---|---|---|---|
| CI-1 | High | `frontend/package-lock.json` (no `node_modules/@emnapi/runtime` entry); blocks `.github/workflows/ci.yml:121` (contract), `:142` (frontend), `:205` (e2e) and `frontend/Dockerfile:8` | `npm ci` fails with EUSAGE: lock file is out of sync with `package.json`. Missing `@emnapi/runtime@1.11.3` and `@emnapi/core@1.11.3`. This blocks the frontend, contract and e2e jobs; `docker` and `e2e` are skipped on the current commit, so they have never run. | On Node 24, run `cd frontend && npm install` to regenerate the lock, verify `npm ci` passes locally, and commit `package-lock.json`. | Open |
| CI-2 | Med | `frontend/playwright.config.ts:12` (`reporter: [["list"]]`); `.github/workflows/ci.yml:214-219` | CI uploads `frontend/playwright-report` on failure, but the reporter never writes that directory, so the artifact upload is a no-op and failure diagnosis is lost. | Add `["html", { open: "never" }]` to the reporter list. | Open |
| CI-3 | Med | `.pre-commit-config.yaml:28-35` | Plan 08 §1 requires prettier and eslint (frontend, via local hooks); neither is configured. Only ruff, mypy, gitleaks and hygiene hooks exist. | Add local hooks for `npm run lint` and `prettier --check` scoped to `^frontend/`. | Open |
| CI-4 | Low | `.github/workflows/release.yml:7-9` | Top-level `permissions: contents: write, packages: write` applies to every job, including the reusable `ci` call. Only `images` needs `packages: write`, and only `release` needs `contents: write`. | Set top-level `permissions: contents: read` and grant write per job, as `images` already does. | Open |
| CI-5 | Low | `.pre-commit-config.yaml:15` (`ruff-pre-commit` rev `v0.8.4`); `backend/uv.lock` (ruff `0.17.2`) | Pre-commit ruff version differs from the locked ruff version, so local hook results can disagree with CI (`uv run ruff`). | Set the pre-commit rev to match the lock (`v0.17.2`), or add a check that they agree. | Open |
| CI-6 | Low | `.github/workflows/release.yml:26,28,42`; `docker-compose.prod.yml:7,33` | Image names are `ghcr.io/syedashhermajid/ledgerly-{api,web}`. The prod compose and release match each other, but plan 08 §5 specifies `statement-categorizer-{api,web}`. | Decide on one name; update either the plan or the workflow and compose files. | Open |
| CI-7 | Low | `.github/workflows/ci.yml:164-190` (docker job tags `ledgerly-*:ci`), `:207` (e2e `docker compose up --build`) | The docker job builds both images, then the e2e job rebuilds them through compose. The docker job's tags are never consumed, so the build is duplicated. | Either drop the docker job's separate build, or have e2e load its images, or accept the cost and note it. | Open |
| CI-8 | Low | `backend/Dockerfile:4,5,16` (`python:3.13-slim`, `ghcr.io/astral-sh/uv:0.8`); `frontend/Dockerfile:4,11,21` (`node:24-alpine`) | Base images are tag-pinned only, not digest-pinned. Plan 08 asks for pinned base images. Dependabot's `docker` ecosystem covers updates. | Pin by digest (`@sha256:…`), with the tag kept as a comment. | Open |
| CI-9 | Low | `.github/workflows/security.yml` | Optional Trivy image scan from plan 08 §4 is absent. | Add it as a follow-up job on `docker` images if time allows. | Open (optional) |
| CI-10 | Info | Runs 40376602437 / 40376602356 (older `chore:` commit) and 40377573646 | Earlier failures are resolved on HEAD `676714d`. (a) Guard failed with "required file missing: frontend/package.json"; now passes. (b) Brain eval failed with `can't open file '../scripts/evaluate_brain.py'`; now passes (run 40377573646, job 121764927931). (c) setup-node cache failed "Some specified paths were not resolved" because `frontend/package-lock.json` was missing; the file now exists. | None. | Resolved on `676714d` |
| CI-11 | Info | `ci.yml:42`, `Makefile:26`, plan 08 §3; `ci.yml:162`, `scripts/check_no_llm_deps.sh` | Pass. Coverage gate is consistent at 85 everywhere. No-LLM guard is present in CI and passes. Every referenced path and npm script exists (`gen:api`, `lint`, `typecheck`, `test`, `build`, `dev`). Dependabot covers uv, npm, actions and docker. Release jobs use `packages: write` only in `images`. Security run `40377573633` passed (gitleaks, pip-audit, npm audit, bandit). | None. | Pass |

## Real CI failures (run 40377573646, HEAD `676714d`)

Job `Frontend (lint, types, tests, build)`, step `Install dependencies` (`npm ci`), job 121764715526:
```
npm error code EUSAGE
npm error `npm ci` can only install packages when your package.json and package-lock.json or npm-shrinkwrap.json are in sync. Please update your lock file with `npm install` before continuing.
npm error Missing: @emnapi/runtime@1.11.3 from lock file
npm error Missing: @emnapi/core@1.11.3 from lock file
```
Job `OpenAPI contract drift`, step `Install frontend dependencies` (`npm ci`), job 121764715271: same EUSAGE and missing `@emnapi` entries.

The `Brain evaluation gate`, `Backend`, `No LLM dependencies` and Security jobs all passed on this commit.

Jobs `Docker build (no push)` and `End-to-end (Playwright)` were skipped because their `needs` jobs failed, so they have not yet been exercised in CI.

Older run 40376602437 errors (resolved on HEAD): `check_no_llm_deps: required file missing: frontend/package.json`; `…/backend/../scripts/evaluate_brain.py: [Errno 2] No such file or directory`; setup-node `Some specified paths were not resolved, unable to cache dependencies` (missing `frontend/package-lock.json`).

Summary: High 1 · Med 2 · Low 6 · Info 2 (CI-10, CI-11). Verdict: **not green**. CI-1 is the only blocker; it fails the frontend and contract jobs and prevents the docker and e2e jobs from running. After CI-1, expect the docker and e2e jobs to be exercised for the first time; CI-2 affects their diagnostics. Fix CI-1 first, then re-run CI and confirm the e2e job passes.

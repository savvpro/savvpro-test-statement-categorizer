# Security Policy

## Scope

Ledgerly is a statement categorizer for small landlords. It runs as a single-user, self-hosted stack: a FastAPI backend (`backend/`) and a Next.js frontend (`frontend/`), packaged with Docker Compose.

In scope:
- Backend API and ingestion of CSV and OFX/QFX uploads
- Frontend application and its same-origin API rewrites
- Docker images, compose files and GitHub workflows in this repository

Out of scope:
- Deployments you run yourself with your own network, TLS or reverse-proxy setup
- Findings that require physical access to the host

## Authentication model

Ledgerly has **no authentication**. It is designed for one user on a trusted machine or a private network. Do not expose the API or web port to the public internet without adding an access-control layer in front of it. The API is not published by default; `docker-compose.dev.yml` binds it to `127.0.0.1` only.

## Reporting a vulnerability

Please do not open a public issue. Use GitHub's private vulnerability reporting: open the repository's **Security** tab and choose **Report a vulnerability**. Include the affected version or commit, steps to reproduce, and the impact you expect.

Reports are triaged as soon as practical. Fixes ship in a new tagged release and are recorded in `CHANGELOG.md`.

## Controls summary

The full set of controls is in `docs/plan/05-security.md`. Highlights:

- Upload limits, strict parsing (`defusedxml` for OFX), and no formula injection on CSV export
- Integer-cent money handling and no LLM or ML dependencies (enforced by `scripts/check_no_llm_deps.sh` in CI)
- Secrets never committed: gitleaks runs in pre-commit and in the security workflow
- Dependency and code scanning: pip-audit, `npm audit --audit-level=high`, bandit, Dependabot
- Containers: multi-stage builds, non-root users (uid 10001 for the API, `node` for the web), read-only API root filesystem, `cap_drop: ALL`, `no-new-privileges`
- CI permissions are read-only by default; package writes happen only in the release workflow

## Data

All data is fake and stored in the local `appdata` volume. Users can delete their statements and data through the API.

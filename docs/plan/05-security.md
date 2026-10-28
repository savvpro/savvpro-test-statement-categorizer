# 05 — Security

## 1. Assets & trust boundaries
Assets: financial transaction data (sensitive PII-adjacent), user corrections, the service's availability.
Boundaries: browser ↔ frontend (Next.js) ↔ backend API ↔ SQLite file. All uploaded content is untrusted.

## 2. Threat model (STRIDE)
| Threat | Vector | Control |
|---|---|---|
| **S**poofing | No auth (single-user local) | Documented scope; bind backend to localhost/compose network; `workspace_id` seam for future auth (ADR) |
| **T**ampering | Malicious upload altering parsing / DB | ORM only, Pydantic validation, size/row limits, strict parsers |
| **T** | CSV formula injection in export | Escape cells (§4) |
| **R**epudiation | Who changed a category | `corrections` audit table, request-id logs |
| **I**nfo disclosure | Logs leak descriptions; stack traces to client; verbose docs in prod | PII-free INFO logs; problem+json without trace; `/docs` disabled when `APP_ENV=production` |
| **I** | XXE via OFX XML | defusedxml; SGML path has no entity expansion |
| **I** | Path traversal via filename | store sanitized basename only; never write upload to disk by name |
| **D**oS | Huge files, row bombs, billion laughs, regex catastrophic backtracking | 5 MB streamed limit, 20k rows, defusedxml, depth limits, **all regexes reviewed for ReDoS** (no nested quantifiers) + test with 10k-char strings under time budget, rate limit on upload |
| **E**levation | Container breakout / root | non-root user, read-only root FS where possible, no shell needed at runtime, minimal base image |

## 3. Upload handling (`core/security.py`)
1. Stream request body; abort > `MAX_UPLOAD_BYTES` (413) — check `Content-Length` and count while reading (header can lie).
2. Filename: `PurePath(name).name`, strip control chars, cap 255; only used as display label.
3. Extension allowlist + magic-byte deny list + text-decode check (03-ingestion §1).
4. Processed in memory; raw bytes discarded after parse; only `sha256` kept.
5. Row/field caps: 20k rows, 512 chars per description (truncated + warning), 64 columns.

## 4. CSV export escaping
For every cell string: if first char ∈ `= + - @ \t \r` (or after leading whitespace), prefix `'`. Use `csv.writer` (QUOTE_MINIMAL) — never string concatenation. Unit test with OWASP payload list. Numbers written as plain numbers (not escaped) so negative amounts stay numeric — amounts are formatted by us, never user text.

## 5. HTTP hardening
- Security headers (backend + Next.js `headers()`): `Content-Security-Policy` (default-src 'self'; frame-ancestors 'none'), `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`, `Permissions-Policy` (camera=(), microphone=(), geolocation=()), `Cross-Origin-Opener-Policy: same-origin`.
- CORS: explicit allowlist from env, `allow_credentials=False`, methods GET/POST/PATCH/DELETE.
- Rate limit uploads (`30/minute` per IP) via slowapi.
- Request IDs: accept `X-Request-ID` only if it matches `^[A-Za-z0-9-]{8,64}$`, else generate.
- In compose, frontend proxies `/api` → backend via Next.js rewrites; backend port not published in production profile.

## 6. Frontend
- React escapes by default; **no `dangerouslySetInnerHTML`** (ESLint rule `react/no-danger` = error).
- Descriptions rendered as text only; no linkification.
- Downloads via `Content-Disposition` from API (no client-side CSV building).
- No secrets/tokens in frontend; `NEXT_PUBLIC_*` only for API base URL.

## 7. Secrets & data hygiene
- No secrets needed by the app. `.env.example` documents config; `.env*` gitignored (except example).
- gitleaks in pre-commit + CI.
- `data/` (SQLite) gitignored; Docker volume.
- Fake data only (04), generator seeded; README states it.
- DELETE statement endpoint = user can purge their data.

## 8. Supply chain
- Lockfiles committed (`uv.lock`, `package-lock.json`); CI uses `uv sync --frozen`, `npm ci`.
- pip-audit, `npm audit --audit-level=high`, bandit (`-ll`), Dependabot (pip, npm, actions, docker) weekly.
- GitHub Actions pinned to major version tags from official orgs (`actions/*`, `astral-sh/setup-uv`); minimal `permissions: contents: read` per workflow; `packages: write` only in release job.
- **LLM-dependency guard**: CI script greps `pyproject.toml`/`uv.lock`/`package.json` for `openai|anthropic|google-generativeai|google-genai|langchain|transformers|llama|mistral|cohere|ollama` → fail. Proves the brain rule mechanically.
- Docker: pinned base image tags (`python:3.13-slim`, `node:24-alpine`), multi-stage, `--no-install-recommends`, non-root uid 10001.

## 9. Verification
- Tests S01–S10 (04) in `tests/security/`.
- ReDoS test: every compiled rule regex run on adversarial 10k strings must finish < 50 ms.
- `security-reviewer` agent pass (09) with this file as checklist; findings → `docs/reviews/security.md`; all High/Medium fixed before PR.
- `SECURITY.md` at repo root: scope, reporting, what's in/out.

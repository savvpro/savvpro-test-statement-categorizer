# Security and operational scope

Ledgerly is a **local, single-user demo**, configured for loopback access. The supplied fixture data is synthetic. Do not expose this app to a shared network or internet as if it were an authenticated financial service.

## Implemented controls

- Whole-request and file-byte limits before CSV processing; content-type is not trusted as the sole file validation.
- Strict UTF-8, row-count, field-length, currency, amount, date, and status validation.
- Server-enforced review invariants; user input cannot count a positive amount as an expense.
- Parameterized SQL, transaction-scoped write locks, foreign keys, unique file hashes, and optimistic review versions.
- Safe metadata-only handling of uploaded filenames; uploads cannot choose a server path.
- Escaped React text; no raw HTML insertion. CSV text beginning with spreadsheet formula markers receives an apostrophe. Numeric amount cells remain numeric.
- Explicit local CORS origins and write-origin checks; a Host allowlist limits accidental exposure/DNS-rebinding patterns. Requests without an Origin header remain allowed for local tools.
- CSP for the built app, `nosniff`, frame denial, no-referrer, and no-store responses. API docs use their framework assets and are exempted from the app CSP.
- A non-root container and a loopback-only Compose port. Dependency locks are committed; databases, uploads, credentials, virtual environments, and build outputs are ignored.
- No LLM/API key, external bank connection, remote analytics, or categorization network calls.

## Not provided

- Authentication, session management, separate user data/authorization, request quotas, distributed rate limiting.
- Encryption at rest, automatic backups/restores, secure file erasure, malware scanning, or a tamper-proof audit trail.
- A full dependency vulnerability assessment, penetration test, WCAG conformance audit, or production certification.

## Before hosting

Add authentication and per-user/account authorization to every query, configure trusted HTTPS origins/hosts rather than disabling the checks, add CSRF/session protections for the chosen auth design, enforce reverse-proxy body/time/concurrency limits, protect and back up the database, and set retention/deletion policies. Choose migrations and a database appropriate to concurrent multi-user writes. Run dependency/security scans and test backup recovery. The included origin checks are not an authentication system.

Review-history events contain before/after transaction data and user notes. Deleting an import deletes its history too; this is deliberate and surfaced by the UI confirmation. Only import fictional data while evaluating this submission.

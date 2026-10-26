# AI usage

## How AI assistance was used

AI assistance was used as a development tool to:

- Interpret the assessment requirements.
- Compare possible use cases.
- Identify edge cases such as refunds, transfers, positive/negative amount conventions, missing dates, and ambiguous merchants.
- Review security risks.
- Draft tests and documentation.

## What the application does not do

The running application does not send transaction data to an AI model and does not use a large AI model to decide categories. Categorization is implemented in [backend/app/brain.py](backend/app/brain.py) with explicit rules and a review fallback.

## Human decisions and verification

The important product decisions were reviewed manually:

- A wrong confident guess is worse than Needs Review.
- Personal corrections override shared defaults.
- User corrections are private by default.
- Shared candidates require review before publication.
- Workspace access must be checked server-side.
- Demo authentication is included for review convenience but is not claimed as a complete public identity system.

The implementation was verified with:

- Python unit tests for parsing and rule precedence.
- Python bytecode compilation.
- React/Vite production build.
- API smoke tests for upload, login, workspace isolation, audit history, and admin authorization.
- Direct SQLite inspection.

## Known limitations

This is an assessment-quality MVP. It still needs managed production identity, password reset and MFA, rate limiting, encrypted backups, HTTPS termination, stronger session storage/revocation, and a production database for public use.

## Token and tool logs

The coding environment records model/tool usage outside the repository. No private statements, credentials, API keys, or personal data were supplied to the AI. The repository contains fake sample data only.
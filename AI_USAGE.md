# AI Usage

## Tools Used

GitHub Copilot in VS Code was used as a coding assistant during this assessment. It helped with:

- Turning the task brief into staged implementation work
- Drafting the product design and rule precedence
- Writing the FastAPI endpoints and React UI
- Generating focused tests and identifying validation gaps
- Troubleshooting the frontend dependency installation

## Runtime Categorization

No AI model is called by the application at runtime. Transaction decisions are made by the local deterministic rules in `backend/app/categorizer.py`.

## Where Assistance Needed Correction

- The initial frontend dependency setup used `latest` versions and caused a Rolldown native-binding failure. The dependencies were pinned to stable versions.
- An early test command ran from the wrong persistent terminal directory. The test command was rerun from the repository root/backend path.
- The first UI was only a placeholder. It was extended with upload, results, review filtering, category editing, totals, and CSV export.

All generated code was reviewed against the requirements, and the categorization rules were tested with explicit examples rather than delegated to an AI model.

## Token and Log Record

This workspace does not expose a complete per-request token counter or an exportable Copilot usage screenshot. No token count is being invented here. The available development record is the VS Code Copilot chat/session log associated with this repository session.

For submission, attach the relevant Copilot usage screenshot or exported session log if the assessment environment provides one.

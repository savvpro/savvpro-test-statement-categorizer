# AI Usage Disclosure

## 1. AI Tools Used

**Tool:** ChatGPT by OpenAI

**Purpose:** Development assistance, debugging, code review guidance, and documentation preparation.

## 2. How AI Assistance Was Used

ChatGPT was used during development to help:

- Diagnose frontend-to-backend upload errors involving multipart form data.
- Investigate why the dashboard and CSV export displayed historical transactions and duplicate records.
- Review the FastAPI endpoints, SQLAlchemy relationships, and frontend data-loading flow.
- Propose changes to filter transactions and financial summaries by statement ID.
- Prepare setup instructions, architecture documentation, and this AI usage disclosure.

The developer reviewed and applied the suggested changes locally.

## 3. Where AI Assistance Needed Correction or Verification

AI-generated suggestions are not guaranteed to be correct. During development:

- Upload failures required investigation of the actual request format and backend validation response.
- Dashboard output revealed that historical database records were being returned together, requiring inspection of the statement-to-transaction relationship.
- Suggested code changes needed to be applied to the existing project structure and checked against the actual files.
- Proposed behavior and documentation examples must be verified against the implementation and tests before being treated as confirmed results.

AI suggestions were therefore treated as development assistance, not as a substitute for running the application and validating its behavior.

## 4. Categorization and AI Boundaries

The transaction categorization path uses deterministic rules implemented in the application. ChatGPT was used to assist with development and debugging, not to classify individual uploaded transactions at runtime.

Known transaction patterns are assigned categories by application code. Unknown transactions should be routed to Needs Review rather than being assigned unsupported categories.

## 5. Token Usage and Evidence

**Exact token usage:** Not available to the developer from the ChatGPT information visible during this work.

I cannot provide a verified per-project token count or an authentic token-usage log from the chat interface. No numerical token count is claimed in this document.

**Usage screenshots or logs:** Add an authentic screenshot or export from the relevant tool if one is available. Do not fabricate screenshots, token counts, or logs. If no per-session usage evidence is available, this disclosure records that limitation.

## 6. Verification

AI-assisted code changes should be verified through:

- Automated backend tests.
- Manual upload tests with known and unknown merchants.
- Checking that unknown transactions remain reviewable.
- Checking that dashboard metrics and CSV exports correspond to the selected statement.
- Reviewing the final Git diff before submitting the pull request.

## 7. Responsibility

The developer is responsible for reviewing the code, testing the application, verifying the final behavior, and ensuring the submitted repository meets the assessment requirements.

# AI Usage

## Tool used

ChatGPT was used during development.

## How it helped

ChatGPT provided substantial implementation assistance, including:

- Breaking the assessment into manageable steps.
- Choosing a freelance-designer use case.
- Generating Python parsing, categorization, summary, and API code.
- Generating the React interface and CSS.
- Generating backend tests.
- Explaining commands and troubleshooting import errors.
- Drafting documentation and submission instructions.

The code was copied into the local project and executed locally.
Test results and errors were shared back for further assistance.

## Runtime decision-making

The application does not use an LLM to categorize transactions.
Classification is performed by deterministic Python rules.

No AI API keys are required by the application.

## Mistakes and limitations encountered

- ChatGPT initially stated that the test suite contained 25 cases.
  Actual execution showed 24 passing tests; the count was corrected.
- Incremental instructions led to import errors while helper functions
  were missing or not saved. Complete file contents and import checks
  helped resolve them.
- The initial visual design needed another styling iteration.
- The generated solution uses temporary in-memory storage and limited
  merchant rules. These limitations are documented rather than described
  as production-ready behavior.

## Validation

- Backend: 24 tests passed.
- Frontend: production build passed.
- Frontend: ESLint passed.
- API sample upload and correction results were checked manually.

## Token usage

An exact token count has not been obtained for this development session.
No measured token total is claimed.

## Evidence

AI interaction screenshots or available usage logs should accompany
this disclosure. Any interaction screenshots demonstrate assistance,
not a measured token total unless a token count is actually displayed.
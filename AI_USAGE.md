# AI Usage

AI-assisted development tools were used during this assessment.

## Tools Used

ChatGPT was used for:

- discussing project architecture
- generating initial boilerplate
- debugging React/Vite setup issues
- reviewing FastAPI structure
- suggesting test cases
- improving documentation

## Categorization Logic

AI is not used during runtime to determine transaction categories.

The categorization decisions are made entirely by deterministic Python rules defined in:

backend/categorizer.py

## Human Review

All generated code was reviewed and tested manually.

Changes were made where required to ensure:

- the application runs correctly
- categorization rules behave as expected
- unknown transactions are marked for review
- frontend and backend communicate correctly

## AI Limitations Encountered

One issue encountered during development was the frontend Vite dependency setup.

The initial setup did not install Vite correctly, causing:

'vite' is not recognized as an internal or external command

This was manually debugged by checking Node/npm versions, reinstalling dependencies, and verifying the Vite installation.

## Verification

The application was manually tested using a synthetic CSV statement.

Automated backend tests were also created using pytest.

## Token / Usage Evidence

AI usage screenshots or usage information can be included here as required by the assessment instructions.
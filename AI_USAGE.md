# AI Usage Disclosure

## 1. AI Tools Used

- **Tool:** ChatGPT
- **Purpose:** Learning support and clarification of project requirements and technical concepts.
- **Human responsibility:** I implemented and reviewed the solution, ran the application locally, executed tests, and verified the results.

## 2. How AI Assisted

AI assistance helped me understand the assessment requirements and technical concepts during development. I used it to:

- Understand the assessment requirements and plan the application structure.
- Clarify concepts related to Python, FastAPI, CSV processing, and validation.
- Understand rule-based transaction categorization.
- Learn about backend testing and API validation.
- Understand React and TypeScript frontend integration.
- Clarify debugging issues and documentation practices.

## 3. Where AI Suggestions Needed Verification

AI suggestions were reviewed and verified through local testing.

- CSV files can contain leading blank lines or unexpected headers. I tested and corrected a sample CSV parsing issue.
- A keyword-based engine cannot confidently recognize every merchant or transaction description. Unknown transactions are therefore marked `Needs Review`.
- Refund and transfer rules depend on the available description text. They cannot guarantee that every refund or transfer will be recognized.
- The frontend currently keeps reviewed changes in application state. The user must export the results to retain those changes outside the current session.

These limitations are documented so that users understand where manual review is necessary.

## 4. Human Verification

I ran the backend test suite locally. At the time of recording this disclosure, all eight tests passed:

- Four categorization tests.
- Four API tests covering the home endpoint, valid CSV upload, unsupported file type, and missing required columns.

I also tested uploading synthetic sample transactions through the local application and checked that the returned categories were displayed.

Test results should be rerun before final submission if the code changes.

## 5. Token Usage and Evidence

AI assistance was used during interactive development. An exact token count is not available to me, so I have not provided an estimated total.

Evidence to include with this submission:
- A screenshot showing relevant development assistance, if required.
- A screenshot of the successful local test run.
- Any available tool usage or token report, if required and available.

Screenshots should not contain passwords, API keys, personal information, or real financial records.

## 6. Data and Privacy

The sample transactions used for development are synthetic. No real bank statement or financial account credentials should be committed to this repository.

## 7. Final Note

AI was used to support learning and clarify technical concepts during development. The transaction categorization decision engine uses explicit Python rules and does not delegate transaction classification to a large language model.

# AI Usage Disclosure

## Assistance used
OpenAI ChatGPT was used as a coding assistant to help plan the project structure, draft portions of the React interface and CSS, draft the FastAPI parser and deterministic categorization rules, and prepare documentation and test cases.

## Decision engine
No large language model is used by the application to classify transactions. Category decisions are made by explicit Python regular-expression rules and conservative fallback logic in `backend/main.py`. The model is not called at runtime.

## Review and limitations
AI-generated code can contain defects, overly broad merchant patterns, and assumptions that need validation. The implementation should be reviewed and tested locally before submission. Confidence scores are illustrative rule weights, not calibrated probabilities. The included test suite is a starting point and should be expanded with more bank CSV fixtures and adversarial edge cases.

## Token and usage logs
The ChatGPT interface used for this work does not expose a verifiable per-project token ledger or exportable token-usage log in this conversation. Therefore, exact token counts and screenshots cannot honestly be supplied here. No token count has been invented. If the assessment platform requires usage screenshots, attach a genuine screenshot from the AI tool's usage interface if one is available to you; otherwise, disclose that exact usage records were unavailable.

## Human verification
Before submission, run the documented tests, launch both services, try the sample workflow, inspect the diff, and correct any failures. This disclosure should be updated to reflect any additional AI tools or material changes actually used by the candidate.

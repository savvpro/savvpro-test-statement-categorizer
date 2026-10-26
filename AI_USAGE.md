# AI Usage

## Tool Used

I used Claude in the Claude app, including its built-in code workspace, to assist with planning reviews, implementation, debugging, testing, and documentation.

The project's scope, initial design, and key decisions were mine. I guided the implementation step by step, reviewed important parts of the code and application behavior, and directed fixes when issues were identified.

The application does not use an AI model for categorization. Transactions are categorized using Python rules in `backend/app/categorizer/`.

## How I Used AI

- **Design review:** Reviewed my initial `Scope.md` and `DESIGN.md` against the assignment requirements and identified missing edge cases.
- **Implementation:** Assisted with building the FastAPI backend, React and Tailwind frontend, statement parsers, categorization rules, tests, and fictional sample statements.
- **Debugging:** Helped investigate issues found during testing and sample imports. I reviewed the results and directed the necessary corrections.
- **Documentation:** Assisted with refining the documentation to reflect the implemented application.

## Issues Identified and Fixed

1. **Refund matching:** A refund transaction could be mistaken for an original purchase. The matching logic was corrected, and a regression test was added.
2. **PDF parsing:** Page footers could be interpreted as transaction rows. The parser was adjusted to avoid treating footer text as a transaction.
3. **OCR:** Scanned statement text sometimes had spaces missing between words, causing merchant rules to fail. The Tesseract configuration was adjusted after testing alternative modes.
4. **Error messages:** An invalid amount was modified when displayed in an error message. The handling was corrected to preserve the original input.
5. **Test cases:** Some tests used ambiguous dates or patterns that could not match under the implemented rules. The test data was corrected rather than weakening the intended validation.

## Verification

The following checks were completed during development:

- 104 automated tests using `pytest`, including a scanned PDF processed with Tesseract.
- Backend linting with `ruff`.
- Frontend linting with `eslint`.
- All four fictional sample statements imported through the API, with results reviewed row by row.
- UI checks after uploading a statement, correcting a category, creating a rule, and viewing the interface at a mobile-sized viewport.

## Token Usage

Usage was measured using the conversation's token log.

| Metric | Tokens |
|---|---:|
| Model requests | 104 |
| Uncached input | 204 |
| Input written to cache | 292,822 |
| Input read from cache | 37,693,139 |
| Output | 188,754 |
| **Total processed** | **38,174,919** |

These figures were recorded at 05:39 Pakistan time on 26 October 2026, when the project was packaged. A final review pass was still running and is not included.

Most processed tokens were cached input from the ongoing conversation. Output tokens include generated code, tests, explanations, and documentation; they do not represent code alone.

Supporting usage logs and screenshots are included in `docs/ai-usage/`.

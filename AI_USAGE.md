# AI Usage

## Rule followed

No AI model decides any category. The brain is plain Python in
`backend/app/categorizer.py` and `rules.py`. AI tools were used only to help
write and debug code.

## Tools used

| Tool | Used for |
|---|---|
| Claude (claude.ai) | Debugging a failing test, building the FastAPI endpoints and the React frontend, writing docs |
| <ADD: any other tool, e.g. GitHub Copilot, Cursor, ChatGPT> | <ADD> |

## How AI helped

- Explained a failing pytest result and traced it to the refund logic.
- Wrote the FastAPI upload endpoint with validation (file type, size,
  user rule checking).
- Wrote the React frontend: upload panel, summary cards, review table with
  category dropdowns, CSV export.
- Wrote API tests and the first draft of the docs.

## Where AI got things wrong

1. **First fix for the failing refund test did not work.**
   The failing test was `test_same_word_two_categories_is_not_trusted_for_refunds`.
   The AI first blamed `_money_in()` (treating a conflict marker `None` like
   "never seen"), from reading the code only, without seeing the test. The
   change was reasonable but the test still failed. After the real test and
   pytest output were shared, the actual cause was found in `categorize_all`:
   a charge that landed in Needs Review was never recorded as a conflict, so a
   refund still matched the other charge confidently. The fix was to mark the
   merchant word as untrusted whenever a charge cannot be placed.
   Lesson: ask for the failing test and the real output before diagnosing.
2. **Frontend file cards showed no code.** Several `.jsx` files were generated
   but did not display, so the code had to be sent again as plain text.
3. **Untested assumptions.** The API code assumed names in `rules.py` and that
   a sample merchant would go to review. These were verified by running the
   tests and the app, not trusted.

## What I checked myself

- Ran the full pytest suite after every change.
- Ran backend and frontend together and uploaded `sample_data/fake_statement.csv`.
- Checked refunds, transfers, review rows and totals by hand against the CSV.

## Token usage

<ADD: total tokens or message count from your tool's usage page>

Screenshots of usage logs:

- <ADD: screenshot file, e.g. docs/usage/claude-usage.png>
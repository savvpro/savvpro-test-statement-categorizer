# AI Usage

## Tools

- **Claude Code** in VS Code, used as a pair-programming assistant

## How I used it

I used the assistant the way I would use a fast pair programmer: I set the direction and it handled most of the typing.

- **Scope and product decisions (mine):**
  - chose the use case: UK sole traders preparing their SA103
  - decided on a review-first approach
  - picked the extra features: learning from corrections, the Self Assessment estimate, recurring-payment detection and bulk fixes
  - asked for a layered, SOLID-based architecture
- **Implementation:** the assistant generated the code for the parser, the classifier chain, the API, the React components and the tests to that brief, in small steps.
- **Verification:** I checked every change by running the test suite, the frontend build and the full app against the sample statement. Failures were investigated before anything was accepted.

The categorization engine is plain, deterministic Python rules. No AI model is called at runtime.

## Where it got things wrong, and how it was caught

- **Wrong row number in a test.** It expected the broken sample row to be row 18. The parser correctly reported row 20. The test was wrong, not the code.
- **A "conflict" test that tested nothing.** The input contained a strong merchant (`ADOBE`), so no conflict was actually exercised. It was replaced with a genuine tie.
- **Tax tests that ignored the trading allowance.** Two tax tests forgot that the £1,000 trading allowance applies automatically when expenses are small. The calculation was right, so the test inputs were corrected.
- **Misleading flag on tax payments.** It flagged HMRC payments as "possible capital asset". This was spotted in the end-to-end output, and the flag is now limited to business expenses.
- **Repo setup.** The first clone used the README's placeholder URL, which left a broken folder that had to be removed.

These are why every generated change was checked against tests and real output rather than taken on trust.

## Token usage

Figures come from the Claude Code session usage log (37 model requests). They were captured at submission time.

| Metric | Tokens |
|--------|-------:|
| Input (uncached) | 74 |
| Output | 86,474 |
| Cache write | 113,793 |
| Cache read | 3,195,288 |
| **Total processed** | **3,395,629** |

Cache reads make up most of the total. They come from the same project context being re-read on every request. They are not newly written content.

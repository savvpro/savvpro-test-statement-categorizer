# AI Usage

## Tools used

| Tool | What I used it for |
|---|---|
| Gemini  | Writing some of the code, one phase at a time: skeleton, fake data generator, parser, categorizer, API, React UI, Docker Compose |

## How I worked

 I chose the use case (a Pakistani PC hardware shop), the scope (PKR only, CSV only, Docker Compose), and the brain's design: evidence scoring, conflict detection, a two reasons rule, recurring payment detection and counterparty memory I then proceeded to give those ideas to gemini, and used it as my main tool for writing most of the code, running the tests and the app after each phase. The brain is deterministic Python rules and scoring. No AI model was used.


## Where the AI got things wrong

| # | What went wrong | How I found it | What I did |
|---|---|---|---|
| 1 | The parser flipped debit signs twice (`--185000`), so money out became positive | Parser tests failed | Forced the sign by column type. I also noted that forcing the sign could hide a wrong value in a credit column |
| 2 | Lint error: the AI caught the broad `Exception` class | Ruff `BLE001` | Replaced it with specific errors (`ValueError`, `KeyError`, `InvalidOperation`) |
| 3 | Merchant tests failed, so the AI copied alias entries into keyword lists. That made aliases and keywords the same and weakened the +5 vs +3 distinction. It also called a 0.56 score "comfortably above" a 0.5 threshold | I reviewed the explanation |
| 4 | Direction-conflict logic flagged `TCS COD SETTLEMENT` wrongly, because it contains both an expense word and an income word | Test failure | Rewrote the check so it considers money direction, and added tests for both directions |
| 5 | Missing `tsconfig.node.json` for the Vite setup | Editor error | Added the file |
| 6 | The counterparty check used strict equality, so conflicts were wrong | Review of conflicts output | Changed it to compare the payee's role (supplier or customer) with the chosen category |
| 7 | The duplicate hash included the running balance, so duplicate rows with different balances were not caught. Same-day payments also created zero day gaps in the recurring check | Sample data showed an unflagged duplicate | Removed balance from the hash and used unique dates for gap calculation |
| 8 | Reviewing sample output showed many rows (K-ELECTRIC, FACEBK ADS, TCS COURIER, SALARY USMAN) going to Needs Review with "name versus history" or "evidence disagrees", because the supplier label was applied to any frequently paid payee. Refund rows were also sent to review, duplicates showed as Not Spending, and CASH DEPOSIT was called a known customer | I read the full sample output |

## Lessons

- AI code passed its own tests but made wrong design choices, so I checked behavior on full sample statements, not only the tests.
- I read the AI's explanations critically, because some claims were inaccurate.

## Token usage

| Tool | Where to find it |
|---|---|---|
| Gemini | [ saved as `docs/usage/gemini.png`] |



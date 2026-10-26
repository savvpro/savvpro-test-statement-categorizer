# AI usage

The author directed this project and used an AI coding assistant to plan, draft and check
it. The author was kept informed at every step, set the requirements and changed course
several times. This file says what was used, what it did, where it was wrong, and where the
usage numbers come from.

## Tools

| Tool                                                                           | Used for                                                                                                                                                                  |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Claude Code (VS Code extension, model Claude Sonnet 5.5)                       | Designing the architecture, writing the Python backend, the tests, the React frontend, the documentation and the sample data scripts                                      |
| Claude Code subagents (separate parallel sessions inside the same run)         | Three bounded pieces of work in parallel: the React frontend, the ISO 20022 camt.053 and SWIFT MT940 readers, and hardening the PDF and header parsing against real files |
| Claude Code web search and fetch                                               | Finding public sample statements and standards sample files, and reading their licences                                                                                   |
| Headless Edge driven by Playwright (an existing local install, used read-only) | Loading the running app, uploading a sample and taking screenshots to check the layout                                                                                    |

No AI model is used inside the application. The categorization brain is deterministic Python
(see [DESIGN.md](DESIGN.md)); there is no API key and no network call in the decision path.

## What the author decided and directed

- Which assessment to take, and the scope: a working product from upload to reviewed result,
  not only a table.
- The use case (a freelance designer's business card) and the "ask rather than guess" rule.
- The input formats: CSV, Excel, PDF and the standard bank formats (OFX, ISO 20022
  camt.053, SWIFT MT940), with size, row and page caps, rate limiting and automatic
  handling of broken files.
- Testing against real-world published files instead of only hand-made ones.
- The look of the frontend: minimal, white background, Outfit font, no gradients, dark
  focus outlines, soft shadows.
- No em dashes anywhere in the repository, and a clean, meaningful commit history.
- Each change of direction during the build, for example adding the real-world data, the
  upload caps and rate limiting, the extra input formats and the frontend design rules.

## How the assistant helped

- Proposed the architecture and the decision rules, drafted the code, tests and documents,
  and iterated against failing tests.
- Reported progress after each stage so the author could redirect the work.
- Ran the parsers over the real sample files, read the output and fixed what was wrong.
- Split independent work (frontend, standards readers, PDF hardening) across parallel
  sessions with explicit file ownership so they did not overwrite each other.
- Took screenshots of the running app and found layout problems that unit tests do not see.

## Where it got things wrong

These were all caught by tests or by looking at real output, then fixed:

1. **Amount parsing:** the first version turned `--5` into +5 because of a double sign
   (caught by a unit test).
2. **Merchant normalization:** the processor prefix `SP` was stripped from `SPOTIFY`,
   leaving `OTIFY` (caught by running the demo statement). Trailing country codes were
   also removed before reference numbers, so `AMZN MKTP US*2K4...` kept its `US`, and
   references glued to words (`ADS3847261`) were not split.
3. **`CR`/`DR` suffixes** were only recognized when separated by a space.
4. **PDF dates:** the "this date has no year" check mistook the day number `01` in
   `Mar 01` for a two-digit year, so the year warning never fired.
5. **Summary rows:** a `TOTAL` label in the date column was reported as an unreadable date
   instead of a summary line.
6. **Sample data:** the first OFX sample had the wrong sign on a refund, which made the
   result look broken when the input was.
7. **Over-confident rules:** an early brand list included one-word names that collide with
   everyday words (`OLA`, `GOTO`, `LEON`, `BOOTS`, `SAGE`). They were removed or tightened
   because a wrong confident guess is the failure the task warns about.
8. **Layout:** in the real browser, a review card with three suggestion chips squeezed its
   text column to one word per line. The unit tests passed; only the screenshot showed it.
9. **Tooling:** long shell heredocs failed several times and files had to be written with
   the file tool instead.
10. **Licensing:** the first search results were dominated by pages selling fake bank
    statement templates. They were discarded, and only openly licensed or public-body data
    was used. Files with no stated licence (the PostFinance ISO 20022 and MT940 samples) are
    downloaded by a script and are not committed.

## Verification

Generated code was never trusted on sight. Each module has tests that were run, the demo statements were read row by row, the parsers were checked against the true transaction counts and ground-truth CSVs shipped with the real sample files, and the reconciliation of credits and debits against opening and closing balances is asserted for the bank-standard
samples.

The AI-run checks above were not the only ones. The author also did all of the verification
and testing personally, with the backend and frontend deployed and running locally: running
the services, uploading statements, checking the results and running the test suites. The
assistant's own checks supplemented that work and did not replace it.

## Usage numbers

These are **estimates**, not measured counts. Claude Code cannot read its own token counters
from inside a session. The three subagent totals are the totals each helper session reported
when it finished (the tool does not split them into input and output), and the input/output
split for them is an estimate. The main session figure is an estimate from the length of the
work: roughly 300 tool calls with a context that grew to about 200k tokens, almost all of
it re-read from the prompt cache. Exact figures can be taken from the `/cost` output or the
usage page and will replace these if they differ.

| Source                               | Total tokens      | Input (est.)       | Output (est.) | Notes                                                        |
| ------------------------------------ | ----------------- | ------------------ | ------------- | ------------------------------------------------------------ |
| Claude Code main session             | about 25 million  | about 24.9 million | about 100k    | Over 95% of the input is cached context re-read on each turn |
| Subagent: frontend                   | 149,701 (reported) | about 120k        | about 30k     | Resumed three times for design and contract changes          |
| Subagent: camt.053 and MT940 readers | 107,677 (reported) | about 85k         | about 25k     | One run                                                      |
| Subagent: PDF and header hardening   | 432,569 (reported) | about 340k        | about 90k     | One run, 137 tool calls                                      |
| **All sessions (estimate)**          | about 25.7 million | about 25.4 million | about 245k   |                                                              |

Screenshots or exported logs, if any, are kept under `docs/ai-usage/`.

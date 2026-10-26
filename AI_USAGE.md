# AI usage

This file was drafted by Claude Code, using only `docs/ai-usage/log.md` and the developer's own
description of how the work was done. Anything that comes from the developer and not from the log
is marked *(developer-reported)*. The log has the detail for every task: what was asked, which
files changed, the assumptions the AI made, what it was unsure about, my review and the tokens.

## 1. Tools

| Tool | Used for | Evidence |
|---|---|---|
| Claude Code (Opus 5.5 for the first three tasks, Sonnet 5.5 for the rest) | Implementation, tests, sample data, audits, docs, CI | 22 tasks logged up to 19:12 in [docs/ai-usage/log.md](docs/ai-usage/log.md), each with measured tokens |

Claude Code is the only AI tool used *(developer-reported)*.

## 2. How I worked

- **I did the design and told Claude Code what to build** *(developer-reported)*. I wrote the
  constraints and the first design outline myself: `CLAUDE.md` was created with content as I gave
  it (14:21), and the first `DESIGN.md` outline already existed when the agent first updated it
  (14:52). I then gave Claude Code one written task at a time (the "Asked" line of each log entry).
- **Written constraints for the agent** in [CLAUDE.md](CLAUDE.md): the categorization brain is
  rule-based code and never calls an LLM or ML model; the agent never runs a git command that
  changes state; money is Decimal and `raw_description` is never modified; fake data only; no
  secrets in files; when unsure, a row goes to Needs Review.
- **The agent did not commit or push. I reviewed and committed everything myself**
  *(developer-reported; the log notes that only read-only git commands were used in the
  verification task, 18:54)*.
- **One task at a time, each from a written spec.** Each log entry records what was asked, the
  files changed and the test results.
- **A running log of every task** with the agent's assumptions and doubts, my own review, and
  measured tokens.
- **A read-only verification pass before submission (18:54):** automated checks, a fresh-clone
  run, an end-to-end scenario, a browser check and a requirements audit. It found the
  uncommitted frontend, the missing `README.md` and `AI_USAGE.md`, and a narrow-screen bug.

## 3. What I decided vs. what the AI produced

**My decisions.** The design is mine: the use case, the categories and kinds, the rule order and
the limits *(developer-reported)*. Beyond that, from my Developer review fields in the log:
- Scope: replace the fork guide with setup docs and move the guide to `docs/SUBMISSION_GUIDE.md`;
  CSV only; a rules engine with no ML; SQLite with CSV export; persistent "remember this
  merchant" rules (exploration entry).
- The sample labels: the UBER EATS row is tagged `specific_beats_generic` because it tests
  exact-merchant priority; withholding tax gets its own category (14:24) and its own kind, `tax`,
  because it is an advance tax credit and not a business expense (14:41, 14:47).
- The rule settings: keep the 0.75 keyword default and give the keyword rules the labels rely on
  (CAFE, COMPUTERS, STATIONERS, HOSTING) an explicit 0.85; every merchant rule has `direction: out`;
  refunds and reversals move up into the structural section so money coming back is never income
  (15:57).
- After the rules audit I ranked the findings by risk, chose the three that could put a row in
  the wrong place unnoticed (income rules firing on a card statement, the bare `REV`, `RAILWAY`),
  fixed those, and kept the rest as known limits (17:00, 17:03).
- I wrote the full spec for the persistence and API task and asked for DESIGN.md to match it
  (17:34). I decided that Personal spending stays out of expenses and gets its own block (17:45).
- I specified the frontend structure, the editor and the tests (18:35), made the three UI polish
  changes after looking at the page (18:41), and chose the six changes after the verification:
  scroll fix, error boundary, CI, README move and rewrite, log (19:02).

**What the AI produced.** Nearly all of the code, the tests, the sample data and expected labels,
the CI workflow and the README were written by Claude Code from my specifications, as is the `rules.yaml` rule set (the
"Generated/changed" line of each log entry lists the files). The first outline of `DESIGN.md` is
mine; Claude Code expanded and updated it to match the code (14:52, 17:15, 17:42, 17:45, 18:42),
keeping my wording where it was still true. Every `expected_category` in the sample data is the
AI's opinion of the right tax answer (14:24). My changes to it were the UBER EATS case tag and the
withholding-tax rows.

**`rules.yaml`.** I designed the rules and Claude Code produced the file from my design
*(developer-reported)*. The log records the first version (the rule format and two example rules per
section, 15:57), Claude Code's audit of the rule set (17:00) and three changes made at my request
(17:03). The rule settings I chose are listed above.

## 4. Where AI got things wrong

| What went wrong | How it was caught | What happened |
|---|---|---|
| `parse_amount` read `1rs2` as 12 and `5 USD 5` as 55: it stripped currency words and spaces anywhere in the text. Its first tests passed anyway | Claude Code ran odd inputs against its own function after it had written the first version of the log (15:31) | Fixed in the same task: a currency marker is only allowed at one end. New tests cover those inputs |
| Rules in `rules.yaml` that could put a row in the wrong place without anyone noticing: income rules that also fire on a card statement, the bare `REV` in the reversal rule, `RAILWAY` matching any description with that word | Claude Code's audit of the rule set, with about 45 probe descriptions (17:00) | I ranked the findings and fixed these three (17:03). Each fix has a test that gives the wrong result on the old rule. The other findings are listed as known limits |
| Personal spending was counted as an expense in the first API summary | The agent built what my spec listed and raised Personal as an open decision (17:34, 17:42) | I decided to exclude it and show it in its own block (17:45) |
| Expected labels: withholding tax was labelled Needs Review / fee, and the UBER EATS case tag did not describe what the row tests | My review of the sample data (14:24) | The row is now Tax Withheld (14:41) with kind `tax` (14:47); the tag is `specific_beats_generic` |
| Keyword rules default to 0.75, below the 0.8 threshold, so the keyword rows the labels expect to be trusted would all have gone to review | Claude Code flagged it in its own entry (15:57) | I kept the default and gave specific keyword rules an explicit 0.85 |
| A keyboard test assumed that Enter on a select box submits a form | Claude Code, while writing the tests (18:35) | The test now tabs to Save and presses Enter |
| Visually hidden text added by Claude Code made the page scroll sideways on narrow screens | The browser check in the verification (18:54) | Fixed (19:02) and checked at 375 px. A smaller overflow at 320 px remains |
| The README example rule had the same id as an existing rule | Claude Code tested the example while writing the README (19:02) | Replaced with a new rule that loads |
| DESIGN.md went out of date three times: after the API (17:34), after the frontend (18:42) and after the CI and README work (19:02) | Claude Code's own check at the end of each task | Updated at 17:42 and 18:42; the third update is the task that produced this file |

**Where my own log was wrong.** Two of my Developer reviews (14:47, 14:52) claimed checks that had
no code behind them yet, and the 15:31 review credited me with a fix the AI had found. The
verification task flagged this (18:54) and I rewrote them.

## 5. Tokens

The figures are measured, not estimated. They are summed from the `usage` fields in the Claude Code
session transcript, for all model requests made while answering the prompt behind each log entry
(method in the log header). "Uncached input" is small because most input is served from the prompt
cache. Input processed = uncached input + cache write + cache read.

| Time | Task | Model | Output | Cache write | Cache read | Uncached input |
|---|---|---|---:|---:|---:|---:|
| before 14:21 | Explore the repo (read-only) | Opus 5.5 | 4,288 | 2,940 | 113,556 | 8 |
| 14:21 | Create CLAUDE.md and .gitignore | Opus 5.5 | 1,465 | 3,380 | 136,043 | 8 |
| 14:24 | Generate fake sample data | Opus 5.5 | 20,650 | 21,857 | 166,435 | 8 |
| 14:35 | Add AI usage log rule and log file | Sonnet 5.5 | 4,912 | 6,464 | 179,918 | 6 |
| 14:41 | Two label fixes and Tax Withheld category | Sonnet 5.5 | 1,897 | 2,379 | 199,674 | 8 |
| 14:47 | Add `tax` kind | Sonnet 5.5 | 1,951 | 1,997 | 138,360 | 6 |
| 14:52 | Add tax totals and tax-refund rules to DESIGN.md | Sonnet 5.5 | 1,327 | 2,769 | 287,477 | 10 |
| 15:31 | Backend skeleton and ingest/parse layer | Sonnet 5.5 | 20,918 | 22,766 | 1,080,489 | 22 |
| 15:57 | Normalizer, classification engine, duplicate post-check | Sonnet 5.5 | 41,811 | 48,220 | 2,031,872 | 26 |
| 17:00 | Verify the developer's rules.yaml against the labels | Sonnet 5.5 | 15,387 | 26,681 | 1,202,062 | 14 |
| 17:03 | Three rules.yaml fixes with regression tests | Sonnet 5.5 | 5,132 | 6,092 | 1,330,627 | 14 |
| 17:15 | Bring DESIGN.md up to date and design the next phase | Sonnet 5.5 | 11,814 | 14,069 | 1,160,489 | 12 |
| 17:24 | Fill measured token counts for the newer log entries | Sonnet 5.5 | 3,418 | 4,915 | 750,257 | 8 |
| 17:34 | Persistence and REST API | Sonnet 5.5 | 56,114 | 61,096 | 4,104,009 | 30 |
| 17:42 | Update DESIGN.md to match the code | Sonnet 5.5 | 5,312 | 6,519 | 1,282,690 | 10 |
| 17:45 | Keep Personal out of expenses in the summary | Sonnet 5.5 | 5,071 | 5,033 | 1,310,091 | 10 |
| 18:35 | Frontend (Vite, React, TypeScript) | Sonnet 5.5 | 53,047 | 57,587 | 5,005,960 | 30 |
| 18:41 | Three UI polish fixes | Sonnet 5.5 | 6,637 | 6,738 | 1,176,255 | 8 |
| 18:42 | Check the log and DESIGN.md against the frontend | Sonnet 5.5 | 7,571 | 10,054 | 2,003,652 | 12 |
| 18:54 | Full verification before submission (read-only) | Sonnet 5.5 | 44,487 | 58,803 | 13,490,026 | 68 |
| 19:02 | Narrow-screen fix, error boundary, CI workflow and README | Sonnet 5.5 | 21,026 | 24,426 | 6,753,148 | 30 |
| 19:12 | Fill the last measured token counts and list blank reviews | Sonnet 5.5 | 5,958 | 6,454 | 2,024,995 | 10 |

| Model | Tasks | Output | Cache write | Cache read | Uncached input | Input processed |
|---|---:|---:|---:|---:|---:|---:|
| Opus 5.5 | 3 | 26,403 | 28,177 | 416,034 | 24 | 444,235 |
| Sonnet 5.5 | 19 | 313,790 | 373,062 | 45,512,051 | 334 | 45,885,447 |
| **All** | **22** | **340,193** | **401,239** | **45,928,085** | **358** | **46,329,682** |

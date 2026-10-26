# AI usage

## Rule compliance

**No AI model decides any category.** The brain ([`backend/app/brain/`](backend/app/brain/)) is plain Python plus a JSON rules file. The backend has no AI SDK and makes no network calls. AI tools were used only to help write and review the code, as the task allows.

## Tools

| Tool | Used for |
| --- | --- |
| **Claude Code** (desktop app), model **Claude Sonnet 5.5** (`claude-sonnet-5-5`) | Planning, writing the backend, tests, frontend and docs; running tests; driving the app in a browser to check it |
| A design skill loaded inside Claude Code (Hallmark) | Guardrails for the UI: tokens, dark mode, contrast, focus states, mobile layout |

The work started from a step-by-step starter plan (itself AI-written) supplied along with the task statement. It was treated as a draft to review, not as a spec. Several parts of it were wrong (below).

## How AI helped

- **Scaffolding and boilerplate:** project layout, FastAPI app factory, pydantic models, settings, CI workflow, Next.js components.
- **Test generation:** 255 backend tests and 17 frontend tests, including property-style tests over thousands of random descriptions.
- **Edge-case brainstorming:** the list in [DESIGN.md](DESIGN.md) (refunds, cash, conflicting rules, payout with the wrong sign, ISO dates, NaN amounts, CSV injection, and so on).
- **Verification:** running the suites, linting, building, and checking the real UI (desktop, phone width, light and dark) against the running backend.

## Where the AI was wrong, and what fixed it

Each of these was **checked by running code**, not assumed.

1. **The starter plan's parser misread dates.** `dateutil.parse(..., dayfirst=True)` turns the ISO date `2026-10-01` into **10 January 2026** and fills a missing day from today (`10/2026` → 26 Oct 2026, checked in this session). `float("nan")` also parses as a valid amount. *Fix:* ISO dates are read as ISO; dates parsed against two different defaults so missing parts are rejected; amounts must fully match a number pattern; a 2-decimal limit. Tests: `test_parse_date`, `test_parse_amount_rejects_garbage`.
2. **Substring matching in the plan's rules.** `re.search("SHELL|PSO|...")` matches `PSOLUTIONS PVT LTD` as **Fuel** and `TOLL` inside `STOLLEN BAKERY`; `JAZZ` matches inside `JAZZCASH`. *Fix:* whole-word matching built into the rules loader. Tests: `test_patterns_match_whole_words_only`, `PSOLUTIONS`/`STOLLEN` cases.
3. **The plan's fuzzy match would swallow merchants.** `token_set_ratio` scores **100** when one name is a subset of another; a learned `ALI` would claim `ALI AND SONS WORKSHOP SUPPLY` (`token_sort_ratio` scores 19). *Fix:* `token_sort_ratio` and a confidence scale that turns loose matches into suggestions. Test: `test_a_short_learned_name_does_not_swallow_longer_ones`.
4. **Transfers and autopay hid real spending.** The plan's `TRANSFER (TO|FROM)` rule marks `TRANSFER TO ALI KHAN` (possibly paying someone) as "not spending"; `AUTOPAY` marks a `JAZZ AUTOPAY` phone bill as a card payment. *Fix:* a two-tier transfer rule (own account = 0.99, generic = 0.6 → review) and a narrower card-payment rule.
5. **The plan used `float` for money, a global dict for all users, and a global learned memory.** *Fix:* `Decimal`, per-statement storage keyed by an unguessable id, learning scoped to a statement. The plan's UI also only allowed fixing Needs Review rows; every row is fixable here because the brain can be wrong.
6. **My own first normalizer was too timid.** It only stripped numbers of three or more digits, so `SHELL PETROL STN #9` did not match the learned `SHELL PETROL STN`. A test caught it; the normalizer now strips every bare number token. (Code and tests were both AI-written, so a human reviewer should look at test *independence*, not just the pass count.)
7. **Tooling surprises.** The Next.js scaffold left a nested `.git` inside `frontend/` (removed). A stray `pnpm-lock.yaml` in a parent folder made Turbopack pick the wrong workspace root and fail the build (fixed by pinning `turbopack.root`). `vitest` required `@types/node` ≥ 22 while the scaffold pinned 20 (the types package was aligned with the Node 24 runtime instead of forcing the install). An attempt to download an extra PyPI package was blocked by the sandbox and dropped; it was not needed.

## Human checks still recommended

- Review `rules.json` against real, anonymized statements: the patterns are plausible, not validated on real data.
- Treat the tax figures as estimates; a tax professional should confirm the treatment of each category.

## Usage and tokens

| Measure | Value | Source |
| --- | --- | --- |
| Model | Claude Sonnet 5.5 | Claude Code session |
| Context window in use when this was written | **299,279 tokens** (30% of a 1,000,000-token window; 221,586 of it conversation messages) | Claude Code session usage report |
| Plan usage when this was written | 9% of the 5-hour limit, 4% of the weekly limit (Pro plan) | Claude Code session usage report |
| Prompts typed by the user | 1 (the task statement plus the starter plan, with the request to build it) | Conversation |

The usage report gives the *current context size*, not a cumulative count of billed input and output tokens, so no total is invented here.

### Token logs and screenshots

> **To add before submitting:** attach your own usage screenshots (Claude Code `/usage` or the desktop app's usage card, and your account's usage page) under a `docs/usage/` folder and link them here. If you use other AI tools or send further prompts, add them to the tools table and the prompt count above.

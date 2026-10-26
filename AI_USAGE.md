# AI_USAGE.md

## Tools used
- **ChatGPT (OpenAI):** first draft of the project structure, FastAPI API, rule-based categorizer,
  React UI, sample data, tests and docs.
- **Claude (Anthropic, Claude Code):** review of the draft against TASK.md, running the tests/build,
  finding bugs, fixing them (see below), expanding tests and docs.
- The categorizer itself calls **no AI model**; all category decisions come from Python rules.

## How AI helped
Scaffolding, boilerplate (CSV parsing, React table/filters), test cases, and a systematic edge-case review.

## Where the AI got things wrong (found by testing, then fixed)
| Problem in the first draft | Fix |
|---|---|
| "UBER EATS" categorized as Travel | Meals rule + `uber(?! ?eats)` |
| "TRAINING COURSE UDEMY" matched "train" -> Travel (plain substring match) | Word-boundary regex rules |
| "INTERNET TRANSFER FEE" silently became Phone & Internet | Conflicting categories now go to Needs Review |
| "PAYMENT THANK YOU -500" (card payment) went to review | Added card-payment transfer patterns |
| "CLIENT PAYMENT -100" counted as income | Sign/wording mismatch -> Needs Review |
| Negative non-refund rows were silently turned into positive expenses | Negative amount without refund wording -> Needs Review |
| `package.json` used `"latest"` for every dependency | Pinned exact versions, added `vite.config.js` |
| Export CSV allowed spreadsheet formula injection (`=CMD()`) | Cells starting with `= + - @` get a `'` prefix |
| Category list duplicated in backend and frontend | Backend is the single source (`/api/categories`) |
| Hard-coded API URL and CORS | `VITE_API_URL` and `CORS_ORIGINS` env variables |
| Only 7 tests, none for the API | 40+ tests including API end-to-end |

## Token usage and logs
> TODO before submitting: add your real usage. The chat tools do not give an exact per-project token count,
> so put screenshots from your ChatGPT and Claude usage pages in `docs/usage/` and list them below.
> Do not invent figures.

- ChatGPT usage: _(add screenshot / number)_
- Claude usage: _(add screenshot / number)_

## Verification done
`pytest` (all passing), `npm run build`, and a browser test of: upload -> edit a Needs Review row -> export.

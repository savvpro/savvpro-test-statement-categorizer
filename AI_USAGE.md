# AI Usage

## Tools used

| Tool | Used for |
|---|---|
| Claude (claude.ai chat) | Planning, choosing the test, code for the parser, brain, API and UI, git and environment help |
| [Other tool, if any] | [what for] |

I am a .NET developer and was new to this Python/FastAPI/React stack, so I used AI as a pair
programmer and checked its output by running tests and the app.

## How AI helped

1. **Choosing the test.** I read both TASK.md files and asked for a comparison. I picked Statement
   Categorizer because it is deterministic and easy to test, unlike speech input.
2. **Design of the brain.** AI suggested the rule pipeline (normalize, sign check, keyword match,
   Needs Review fallback). I kept it because it follows the task's rule: "a wrong guess is worse than asking".
3. **Code.** AI wrote the first versions of the normalizer, classifier, CSV parser, FastAPI endpoints,
   React UI, and the pytest tests. I pasted them in, ran them and fixed what broke.
4. **Messy cases.** AI listed cases to cover (refunds, transfers, duplicates, `(45.00)` amounts, bad rows).
   I built `data/messy_statement.csv` and checked every number in the UI by hand.
5. **Git and environment.** AI guided fork, branch, push and the Codespaces setup.

## Where AI got things wrong or I had to correct it

- **Environment assumption.** AI assumed Python was installed on my Windows machine. It was not, and
  `winget` was blocked. We switched to GitHub Codespaces, which cost time.
- **Git workflow.** The first push from Codespaces was rejected (non-fast-forward) because the
  branch already existed remotely with a different commit. Fixed with `git pull --rebase`.
- **Terminal pasting.** Large multi-line pastes into the terminal broke a test file and ran commands
  inside the running uvicorn terminal. I reverted with `git checkout` and moved edits into the editor.
- **[Add your own: a bug AI introduced, something you rejected, a rule you changed.]**

## How I verified AI output

- 47 automated tests (`pytest`) for the normalizer, classifier, parser and API
- Manual run with `data/messy_statement.csv`; every category total checked against hand-calculated values
- Edited a Needs Review row in the UI and confirmed totals update
- No AI model is called by the app. The categorization is plain Python rules.

## Usage evidence

- Token or usage screenshots: `docs/ai-usage/` ([list files])
- Approximate usage: [number of messages / tokens, as shown by your plan]
- [Other tool usage numbers]

## What I did myself

- Chose the test and the use case, reviewed and ran all code, tested edge cases, wrote the sample data,
  and decided the assumptions listed in DESIGN.md (day-first dates, negative = money out).
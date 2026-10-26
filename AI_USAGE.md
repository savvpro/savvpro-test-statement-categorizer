# AI Usage

## Tools used

| Tool | How I used it |
|---|---|
| Claude (claude.ai chat) | Assistant for planning, first drafts of code, tests and docs, and for reviewing my work |

**The categorisation brain contains no AI model.** No GPT, Claude or Gemini call is made
anywhere in the app to decide a category. The rules are plain Python and JSON. AI was only
used to help me write and review the code.

## How I used AI

- Asked it to explain the task and break it into steps
- Discussed the project structure (parser / brain / services / api, and a React frontend)
- Used it to draft the backend, the sample CSV, tests and docs, then read, ran and changed them
- Used it to help build the React UI and to debug setup errors (missing packages,
  empty scaffold files, a 500 error)
- Before submitting, asked it to review the repo against the task. I then made the fixes myself

## Where AI got things wrong (and what I did)

1. **Silent duplicate removal.** The first plan said to "not count" duplicate rows. That hides
   data and can drop genuine repeats. I changed it to flag duplicates as Needs Review.
2. **Missed foreign currency.** The first version had no handling for non-USD rows. I added a
   currency check.
3. **Empty scaffold files.** The scaffold created empty files, so the server failed with
   import errors until each file had its code.
4. **Empty `requirements.txt` and `.gitignore`.** Both were left empty. The README said to run
   `pip install -r requirements.txt`, which would install nothing, and the empty `.gitignore`
   would have committed virtual environments and `node_modules`. I filled both in.
5. **Leftovers and outdated docs.** An old duplicate `frontend/frontend/` folder, a README that
   still said the frontend was "work in progress", and a lint error in `client.js`. I removed
   the folder, rewrote the README and fixed the lint error.

## What I checked myself

- Ran the app on `sample_data/fake_statement.csv` and checked the categories by hand
- Ran `pytest` (95 tests) and fixed failures
- Ran `npm run lint` and `npm run build`
- Checked `git status` before committing so no virtual environment, `node_modules`,
  `__pycache__` or build files were included
- Confirmed there are no keys or passwords in the repo and that all data is fake

## Token usage

I used the free version of claude.ai, which does not show token counts or a usage page.
These numbers are rough estimates, not exact figures. For this project I used one chat for
building the project and one chat for the final review.

| Tool | Date | Input tokens | Output tokens | Total |
|---|---|---|---|---|
| Claude (claude.ai, free) | 2026-10-26 | ~60,000 (estimate) | ~30,000 (estimate) | ~90,000 (estimate) |

Screenshots of the chats are in `docs/ai-usage/`:

- `docs/ai-usage/claude-chat-1.png`
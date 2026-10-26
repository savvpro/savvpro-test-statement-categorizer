# AI usage

## Tools

| Tool | Used for |
| --- | --- |
| Claude Code (Claude Opus 5.5) | Turning my project plan into the build: backend code, tests, Docker/CI, docs drafts, and help with git/GitHub when the push failed |
| Claude Code subagent (general-purpose) | Built the Next.js frontend **in parallel** with the backend, working from `docs/api-contract.md` |
| `taste-impeccable-workflow` skill | Frontend design. Stage 1 (taste) set the direction and made the first build; stage 2 (Impeccable) detected, critiqued, audited, fixed and polished it. Notes are in `frontend/.design/` |
| Project subagent definitions | `.claude/agents/test-writer.md`, `.claude/agents/reviewer.md` |

**No AI is used inside the app.** The categorizer is plain Python rules. CI fails if
`openai|anthropic|gemini` appears anywhere in `backend/app/`.

## How the work was split

1. **Plan → rules.** I first wrote my own project plan in Roman Urdu (use case, features,
   brain design, messy cases, UI rules, phases) and gave it to Claude Code. The plan was a
   personal working document, so it is not part of the repo; its decisions live on in
   `CLAUDE.md`, `DESIGN.md` and `docs/api-contract.md`.
   It wrote `CLAUDE.md` (hard rules: no LLM in the brain, fake data only, branch
   `candidate-Rahatali8` only, the human commits) and the folder scaffold.
2. **Contract first.** Before any parallel work it wrote `docs/api-contract.md`, so the
   frontend and backend had one agreed source of truth.
3. **Parallel.** A frontend subagent built `/frontend` while the main session built
   `/backend`. Each owned its own folder, neither committed, and no worktrees or extra
   branches were used.
4. **Backend phases:** fake sample CSVs → parser + tests → brain + tests → API + DB + tests
   → Docker + CI → docs. After each step the agent ran the code on the sample files and
   compared the output with TASK.md before moving on.
5. **I reviewed, ran and committed** the work myself, opened the PR, and clicked through
   the app in the browser.

## Where the AI got things wrong (and how it was caught)

| # | What went wrong | How it was caught | Fix |
| --- | --- | --- | --- |
| 1 | `dateutil` with `dayfirst=True` silently read ISO `2026-05-03` as **5 March** | Smoke-running the parser on `messy.csv` showed the row as `2026-03-05` | ISO dates are parsed explicitly before dateutil; covered by `test_iso_dates_are_never_flipped_by_day_first` |
| 2 | The "not spending" total **netted** transfers out against card payments in (−500 + 800 = 300 instead of 1300) | `test_summary_totals` failed | Not-spending and review totals now add up absolute amounts |
| 3 | `datetime.utcnow()` crashed every DB write; the installed SQLModel version requires timezone-aware datetimes | 13 API tests failed on the first run | Switched to `datetime.now(UTC)` |
| 4 | The first rules made `JOES CAFE` → Meals (keyword `CAFE`, 75%), but the task says this exact merchant must go to Needs Review | Comparing the classifier output against TASK.md | `CAFE`/`COFFEE` became *weak* keywords (50%), so the row goes to review with a "Meals" hint |
| 5 | A test expected `BLUE DOOR STUDIO 22` to be the same merchant as `BLUE DOOR STUDIO`, but the normalizer keeps short numbers on purpose (`MICROSOFT 365`) | Failing test | The test was wrong, not the code; fixed the test input |
| 6 | My plan put learned rules *after* special rules, so a user's fix on a "transfer" row would never stick | Design review while writing the brain | Learned rules (exact merchant) now run first; documented in DESIGN.md |
| 7 | The Needs Review tab and sidebar badge said **7** while the stat card said **8**: the UI left out the duplicate row, which also needs review | Looking at a screenshot of the running app | The tab now uses the `needs_review` flag, the same as the backend |
| 8 | The `taste-skill` / `Impeccable` skills were not installed, so the subagent did the critique and audit by hand against the same rubric, plus `npx impeccable detect` | The agent's own notes in `frontend/.design/` | Findings and fixes are logged in `frontend/.design/findings.md`: grey text contrast, a nested card, tab keyboard access, the mobile upload button |
| 9 | After a rebuild, a stale `next start` server on port 3000 showed "Application error: a client-side exception" | I opened `localhost:3000` and saw the error page | Not a code bug: the old server was asking for a JS chunk that no longer existed (HTTP 400). Stopping it and running `docker compose up --build` fixed it |
| 10 | The agent tried to kill processes with `pkill -f "next start ..."`, which also matched its own shell and killed the command, so the screenshot step silently never ran | Exit code 144 and an unchanged screenshot timestamp | Looked up the real PID with `ss -ltnp` instead |

Non-AI problem worth noting: my first `git push` failed with **403 "denied to
shahmirDev"**, because this computer's saved git credential belonged to another GitHub
account. Claude Code found the cause in `~/.git-credentials` (`credential.helper store`).
After I cleared the old credential, VS Code supplied my own GitHub login on the next push.

## Tokens

Counted from Claude Code's own session logs. Full breakdown and the script that produced
it: [`docs/ai-usage/token-usage.md`](docs/ai-usage/token-usage.md).

| Session | API calls | Output tokens | Total tokens (incl. cache) |
| --- | ---: | ---: | ---: |
| Main session: plan → backend, tests, Docker, CI, docs, git/PR help | 84 | 94,134 | 12,411,241 |
| Frontend subagent: Next.js UI with taste → Impeccable | 43 | 52,465 | 3,574,266 |
| **Total** | **127** | **146,599** | **15,985,507** |

About 97% of the total is **cache reads**: the agent re-reading the conversation, plan and
files on every turn. Those are much cheaper than fresh input. The model actually wrote
about 147K tokens of code, tests, docs and replies.

## What I'd do differently

- **Commit after every phase.** My plan said to make small commits, but in the end I made two
  big commits. The history would have been easier to review with `feat: add csv parser`,
  `feat: add rule-based brain` and so on.
- **Write the API contract even earlier.** Writing `docs/api-contract.md` first is what let
  the frontend and backend be built at the same time without mismatches. Next time I would
  write it during planning.
- **Check git accounts before the deadline day.** The 403 push error cost time at the end. I
  would run one test push as soon as I create the branch.
- **Keep checking the AI's output against the task.** Most mistakes (the JOES CAFE rule,
  the ISO date bug, the 7-vs-8 count) were caught by running the app or the tests and
  comparing with TASK.md, not by reading the code. Tests and screenshots were the real
  safety net.

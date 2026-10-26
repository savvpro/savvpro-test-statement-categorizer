# AI usage

## Tools

- **Claude** (Anthropic, Opus 5.5 model) as a coding assistant.

No AI model is used at runtime. The categorization brain is plain Python rules and scoring.

## How it helped

- Read the assessment email and TASK.md, and suggested the Statement Categorizer
  because it fit the remaining time.
- Wrote the code: CSV parser, rule-based brain, FastAPI service, React UI and tests.
- Wrote the README, DESIGN and this file.
- Ran the test suite (26 tests) and the frontend production build.

## Where it got things wrong / needed correction

- A large shell heredoc it used to create the frontend failed to parse, so no files were
  written. It rewrote the files one by one.
- Its first version of the amount parser had a convoluted double-negative expression for
  leading `-` signs. It was simplified to `negative = not negative`.
- Rules overlap (e.g. `UBER` vs `UBER EATS`). It handled this with a negative lookahead,
  plus a "two categories score about the same -> ask the user" rule instead of guessing.
- The keyword list is a starting point, not complete; rules need human review as new merchants appear.

## Token usage

About **135k tokens** used to build the project. The [log](docs/ai-usage/token-usage-log.json) was captured after submitting, so it shows ~165k for the whole session.

# AI Usage - Ledgerline

## Tool used
Claude Code, as a coding assistant in the terminal.

## How I used it
I used it to help write and debug the FastAPI backend and the Next.js frontend, and to write tests and fix lint and type errors. I reviewed and ran the generated code myself.

The categorization brain (`backend/app/brain/`) is plain deterministic Python. No LLM or external API is called at runtime, so the app runs offline with no keys. All sample statements are fake.

## Decisions
I picked the Statement Categorizer because it is deterministic and easy to test. For the brain, I decided that money is stored as integer cents, refunds are their own kind rather than income, and mixed-use merchants (Amazon, Costco and similar) always go to review, since a wrong guess is worse than asking.

## Mistakes along the way
- The first version of the frontend used API field names that did not match the backend (`slug` instead of `id`, wrong pagination keys). I found this by testing in the browser and fixed it.
- The rules toggle returned a 422, and card-statement imports skipped sign detection on commit. Both are fixed and covered by tests.

## Testing
127 backend tests pass, `ruff` and `mypy` are clean, and `next build` passes. I imported all the sample files end to end, including a duplicate upload and a card file with inverted signs.

## Not built
A command palette, a print stylesheet, and committed frontend tests.

## Tokens
Exact token counts were not recorded for this build.

# AI Usage

> **Fill this in with your own real numbers before submitting.** The sections below are a starting point.

## Tools used
- Claude (chat): generated the first version of the backend, tests, frontend and docs from `TASK.md`.
- The categorization decisions themselves use **no AI**: only code in `backend/app/brain.py`.

## How it helped
- Scaffolded the FastAPI backend, parsing, rule pipeline, tests and Next.js page.
- Proposed the edge-case list in `DESIGN.md`.

## Where it got things wrong / what I changed
- _Add your real examples here (e.g. bugs you found, rules you corrected, things you rewrote)._
- One tooling slip during generation: a first script run failed because directory creation used shell
  brace expansion that `sh` does not support; it was rerun with explicit paths.

## Token usage
- _Paste token logs or usage screenshots from each tool here. Tokens were not measured in this chat._

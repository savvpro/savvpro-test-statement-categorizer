# Where AI got things wrong (and how it was caught)

| # | Phase | What the AI did | How it was caught | Fix |
|---|---|---|---|---|
| 1 | P0 | Tried `winget install` for uv/make; it hung on a hidden prompt for 5 min | Orchestrator noticed no progress | Switched to uv's official standalone installer. make isn't needed locally (CI runs on Linux) |
| 2 | P0 | Issued an `rmdir` of an empty folder that the safety check flagged | Claude Code safety check | Dropped the step; create-next-app accepts an empty dir |
| 3 | P2 | Fixture agent labelled the D35 typo merchant (`HOEM DEPOT`) as `auto`, but the catalog says auto only if the fuzzy score clears the threshold | Orchestrator label review against plan 04 | Label corrected to the engine's documented behaviour (fuzzy match → review) |
| 4 | P2 | Fixture agent numbered rows in the messy CSV without counting blank/malformed lines, but the parser numbers physical data lines (so users can find a row in the file) | Golden evaluator: labels were shifted by one to two rows | Labels realigned to the parser's convention |
| 5 | P3 | Brain: first evaluation 97.5% auto precision. Keyword `$` anchor failed on a trailing space; NSF fee hit the returned-item rule; a person-name fallback fired before keyword rules (a utility name looked like a person) | Golden evaluator + unit test D36 | Fixed in rules/stages; now 100% precision, 100% review recall |
| 6 | P3 | Backend agent's partial-import rule (refuse if > 5% bad rows) rejected a 14-row file with 2 bad rows | Golden evaluator | Policy changed to refuse only if bad rows > max(2, 5%) |

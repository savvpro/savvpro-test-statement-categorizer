# Direction contract

Written at the end of Phase 1 (taste stage, run manually: taste-skill not installed).
Read in Phases 3-5 (Impeccable stage).

- **Surface:** LedgerLite statement review dashboard (product UI, data table heavy)
- **Lane:** product
- **taste variant:** minimalist-ui (per workflow guidance for dashboards)
- **Dials:** VARIANCE 2 / MOTION 2 / DENSITY 7
- **Design language (one sentence):** A calm bookkeeping ledger: grey page, white bordered cards, one teal accent, numbers set in tabular figures, every automatic decision explained in plain words next to the row.
- **References (2-3):** Stripe Dashboard payments table, Linear settings density, Mercury transactions list
- **Type pairing:** display Inter 600 / body Inter 400, tabular-nums for all money and counts
- **Palette intent:** page #F7F9F9, white cards, 1px #E5EAE9 borders, single teal accent #1F7A68; semantic tints only for status (amber review, blue learned, red duplicate, green money in, grey not spending)
- **Motion intent:** none beyond 150ms colour/opacity transitions on hover/focus; skeleton pulse for loading
- **Deliberate risks we are keeping:** Inter (brand font mandated by CLAUDE.md); reason text shown inline under each merchant (explainability over minimalism)

## Do not
- No emoji, gradients, glassmorphism, neon, glows, big animations
- No shadows beyond a hairline; borders carry the structure
- No second accent colour; status colours appear only inside pills, bars and the review rail
- No nested cards; one card per job
- Never crash on API errors: always show the backend `detail`

## Changelog
- 2026-10-26 created in Phase 1

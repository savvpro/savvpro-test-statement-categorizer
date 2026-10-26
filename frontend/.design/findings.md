# Findings (Phase 3)

Sources: `npx impeccable detect` on source (exit 0, no findings) and on the rendered
production build (exit 2, 5 findings); manual critique + audit (Impeccable skill not
installed, so critique/audit were done by hand against the same rubric).

| # | Bucket | Severity | Finding | Source | Conflicts with contract? | Resolution |
|---|---|---|---|---|---|---|
| 1 | color | major | `--color-faint` #7d8b87 is 3.6:1 on white (brand subtitle, breadcrumb, user role, table headers) | detect | no | darkened to #66736f (4.9:1 white, 4.7:1 page) |
| 2 | color | minor | green #17803d on green-soft pill is 4.46:1 | audit | no | green -> #14733a (5.3:1) |
| 3 | typography | minor | overused-font: Inter | detect | yes (CLAUDE.md mandates Inter) | waived: brand font |
| 4 | structure | major | nested cards: dashed dropzone inside a bordered card | detect | no ("no nested cards") | flattened: dropzone is the single card |
| 5 | structure | minor | Total spending stat truncates large currency values at narrow widths (hides money) | critique | no | removed truncate, value wraps |
| 6 | states | minor | tabs lack `aria-controls`/tabpanel and arrow-key navigation | audit | no | added tabpanel id + Left/Right arrow handling |
| 7 | responsive | minor | Upload button sits awkwardly left-aligned under header on phones | critique | no | full-width on phone, auto on sm+ |
| 8 | states | minor | Delete learned rule has no confirmation | critique | no | kept: one click is cheap to redo (re-pick a category); noted |
| 9 | responsive | info | wide transaction table on phone | audit | no | already scrolls inside its card (min-w 960px) |

Recurring finding to remember: grey helper text must stay >= 4.5:1 (use `text-faint` token only).

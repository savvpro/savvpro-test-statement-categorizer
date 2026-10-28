# 07a — UX & Design System

Follows the installed **frontend-design** skill process: brief → token system → wireframes → self-review against generic defaults → build → screenshot critique. Applies HCI principles explicitly so every choice is defensible in DESIGN.md.

## 1. Brief

- **Subject:** a landlord's tax-time bookkeeping. Vernacular: ledgers, ruled accounting paper, the Schedule E form with its numbered lines, rent rolls.
- **Audience:** a self-managing landlord (not an accountant), mid-40s, uses it **once or twice a year for an hour**, has a stack of statements, and wants to be done and confident. Secondary audience: the CPA who receives the export.
- **Primary job:** get every transaction into the right Schedule E line, *knowing which ones the app was unsure about*, in the fewest decisions.
- **Success:** the user resolves all review items without reading docs, trusts the totals, and exports.
- **Emotional target:** calm and in control. Tax time is stressful, so the UI should feel like a tidy, competent bookkeeper, not a flashy SaaS.

## 2. HCI principles → concrete features

### Nielsen's 10 heuristics
| Heuristic | How we meet it |
|---|---|
| 1 Visibility of system status | Process bar Upload → Review → Summary; review progress "7 of 9 left"; upload parsing state; live Schedule E totals update on confirm |
| 2 Match with real world | Uses the landlord's words and the actual Schedule E line numbers and labels; amounts as money, not cents; dates as "Mar 4" |
| 3 User control & freedom | **Undo** on every confirm (toast + `U` key) instead of "are you sure?" dialogs; restore duplicates; change any confirmed row |
| 4 Consistency & standards | One vocabulary (§6 glossary); an action keeps its name end-to-end ("Confirm" → "Confirmed") |
| 5 Error prevention | Category list filtered by money direction (can't put a deposit-in under Repairs); "Apply to 12 similar" shows the list before applying; client-side file checks before upload |
| 6 Recognition over recall | Suggested category pre-selected; the 5 most-used categories first; reasons shown next to the decision, not in a help page |
| 7 Flexibility & efficiency | Keyboard triage: `J/K` move, `1–9` pick category, `Enter` confirm, `R` toggle remember, `U` undo, `?` shortcut sheet. Mouse users get large targets in the decision panel |
| 8 Aesthetic & minimalist | One accent color; no decorative cards/gradients; the reasons panel is collapsed past two lines |
| 9 Help recognize/recover from errors | Upload errors say what happened and how to fix it ("Row 14 has no date. Fix it in your spreadsheet or remove the row, then upload again.") with row numbers |
| 10 Help & docs | Inline "Why this category?" per row; `?` sheet; one-line explanations for flags ("Over $2,500, so this may be an improvement rather than a repair") |

### Other laws applied
- **Hick's law:** the category picker is grouped (Income / Schedule E expenses / Not counted), with the suggestion and recent categories first. That's about 5 choices most of the time, not 25.
- **Fitts's law:** primary actions sit in a fixed decision panel next to the list, with big targets and no tiny inline popovers for the main flow.
- **Gestalt (proximity/similarity):** similar rows (same merchant) are grouped in the review queue, so one decision covers several.
- **Norman:** constraints (direction filtering), feedback (each confirm visibly moves money into a Schedule E line), mapping (the summary mirrors the paper form's line order).
- **Progressive disclosure:** confidence is shown as a word (High/Medium/Low), with the exact score and rule IDs on expand.
- **Peak-end rule:** the end state is a completed Schedule E view with "All rows reviewed" and a clear export, a satisfying finish.

### Accessibility (WCAG 2.2 AA)
- Text contrast ≥ 4.5:1, verified by a script over the tokens in CI (`scripts/check_contrast.mjs`).
- Visible focus ring (2px accent + offset) on everything.
- Target size ≥ 24×24 px.
- Color is never the only signal: status has text plus a shape.
- `aria-live` for confirms and undo; table semantics kept (not div soup).
- `prefers-reduced-motion` respected; zoom to 200% without loss.
- Keyboard-complete flow, tested in e2e.

## 3. Token system (v1, after self-review §5)

### Color (6 named values)
| Token | Hex | Role |
|---|---|---|
| `paper` | `#F5F7F6` | app background: cool, faintly green-grey like accounting paper (deliberately *not* warm cream) |
| `ink` | `#1E2B2F` | text, dark slate-blue (not tinted near-black) |
| `ledger` | `#1D6B57` | the single accent: primary actions, "counted" state, focus ring. Bookkeeping-pad green |
| `rule` | `#D5E0DB` | table rule lines and borders, like the ruled lines of a ledger |
| `attention` | `#8A5A0B` text / `#FBEFD9` fill | **only** for "Needs your review" |
| `muted` | `#5F6E73` | secondary text, "Not counted" rows |
| (system) `error` | `#A3261B` | errors only |
Rows are white (`#FFFFFF`) on paper. Inflow amounts use `ledger`; outflows use `ink`. We don't use red for spending, since spending isn't an error. Contrast of every text pair is checked by script.
Dark mode: out of scope (once-a-year office task); documented as future work.

### Type
- **One family: IBM Plex Sans**, chosen for its engineered, form-like character that fits tax paperwork, and because it has true **tabular figures** (`font-variant-numeric: tabular-nums`) so amounts align in columns. It is not one of the usual defaults (Inter, Geist, system-ui).
- Fallback if licensing or loading fails: Public Sans (also has tabular figures). Loaded via `next/font/google` (self-hosted at build, no runtime CDN).
- Scale (ratio 1.2, base 15px for a data-dense UI): 12.5 / 15 / 18 / 21.6 / 26. Weights: 400 body, 500 labels, 600 headings. Sentence case everywhere. **No all-caps labels, no monospace data labels.**
- Line length ≤ 72ch for any prose (empty states, help sheet).
- Amounts are right-aligned, tabular, with a currency sign. Negatives use a minus sign, not parentheses, in the UI. Parentheses are only in the CPA export, if configured.

### Shape, spacing, motion
- 4px spacing grid. Radius by hierarchy: 2px for inputs and chips, 6px for panels, 0 for table rows (ruled ledger lines, not cards).
- No drop shadows except the decision panel (one elevation level) and the toast.
- **One motion moment:** on Confirm, the row slides out of the review queue and the matching Schedule E line total in the side summary briefly highlights and counts up (≤ 400ms). Everything else is instant. Under reduced motion, there's no slide and only the highlight.

## 4. Layout & wireframes

Left-aligned throughout. Top bar plus content. The process bar is a real sequence, so the numbered steps are justified.

### Upload `/`
```
┌──────────────────────────────────────────────────────────────────────┐
│ Ledgerly            (1) Upload  ─  (2) Review  ─  (3) Summary        │
├──────────────────────────────────────────────────────────────────────┤
│ Sort your rental statements for Schedule E                           │
│ Upload a bank or credit card statement. We'll sort every transaction │
│ and ask you about the ones we're unsure of.                          │
│                                                                      │
│ Account   (•) Checking   ( ) Credit card                             │
│ ┌──────────────────────────────────────────────────────────────┐     │
│ │  Drop a CSV or OFX file here, or choose a file               │     │
│ │  Up to 5 MB. Exports from most US banks work.                │     │
│ └──────────────────────────────────────────────────────────────┘     │
│ No statement handy? Use a sample: Checking, Jan–Mar · Credit card    │
│                                                                      │
│ Recent statements                                                    │
│ ───────────────────────────────────────────────────────────────────  │
│ checking_q1_2026.csv   Jan 1 – Mar 31   64 rows   3 need review      │
└──────────────────────────────────────────────────────────────────────┘
```
(The sample links' separator is a plain comma in the build; the dot above is only wireframe shorthand.)

### Review `/statements/[id]`: master-detail, the main work surface
```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Ledgerly   checking_q1_2026.csv (Jan 1 – Mar 31)      (1)─(2) Review─(3)     │
├──────────────────────────────────────────────────────────────────────────────┤
│ Needs your review 9   All 64   Not counted 11   Duplicates 4    [Search   ]  │
├───────────────────────────────────────────────┬──────────────────────────────┤
│ Mar 04  ZELLE FROM MARIA K LOPEZ    +1,850.00 │ Zelle from Maria K Lopez     │
│ Mar 06  HOME DEPOT #4410          −3,412.00 ◀ │ −$3,412.00   Mar 6           │
│ Mar 09  AMAZON MKTP                  −56.20   │                              │
│ Mar 11  CHECK #1042                 −400.00   │ Why we're asking             │
│ Mar 15  GRANITE HOME LENDING      −1,912.44   │ Over $2,500, so this may be  │
│   …                                           │ an improvement (depreciated) │
│                                               │ rather than a repair.        │
│                                               │                              │
│                                               │ Category                     │
│                                               │ [Repairs (line 14)  suggested▾]│
│                                               │ [ ] Remember for Home Depot  │
│                                               │ [ ] Also apply to 2 similar  │
│                                               │                              │
│                                               │ [ Confirm ]   Skip for now   │
│ 7 of 9 left ███████░░                         │ Schedule E so far: Repairs   │
│                                               │ $1,204.18 → updates on save  │
└───────────────────────────────────────────────┴──────────────────────────────┘
```
- The list is a ledger: ruled lines, tabular amounts, and the selected row marked by an accent bar on its left edge.
- In the **All** tab, rows show their category as plain text plus a status shape: ● counted, ◐ needs review, ○ not counted.
- Below 900px the decision panel becomes a bottom sheet.

### Summary `/statements/[id]/summary`: **the one memorable element**
It's a rendering of the actual **Schedule E (Part I) form**: line numbers 3–19 in the form's order, filled in as rows are resolved, with unresolved amounts shown as pending against their suggested line.
```
┌───────────────────────────────────────────────────────────────────┐
│ Schedule E, Part I · Jan 1 – Mar 31, 2026            [Export CSV] │
│ 2 rows still need review ($1,968.20). Resolve them →              │
├───────────────────────────────────────────────────────────────────┤
│  3  Rents received                              16,650.00         │
│  5  Advertising                                     45.00         │
│  9  Insurance                                      612.00         │
│ 12  Mortgage interest paid to banks          pending 1,912.44     │
│ 14  Repairs                                      1,204.18         │
│ 16  Taxes                                        2,210.00         │
│ 17  Utilities                                      388.40         │
│ 19  Other                                          120.00         │
│ ─────────────────────────────────────────────────────────────     │
│ 20  Total expenses                               4,579.58         │
│ 21  Income or (loss)                            12,070.42         │
│                                                                   │
│ Not counted on Schedule E                                         │
│ Security deposits held 3,700.00   Transfers 5,000.00 …            │
└───────────────────────────────────────────────────────────────────┘
```
(Final copy drops the middle dot and the arrow per §5. The arrow is wireframe shorthand.)
- A horizontal bar beside each expense line shows its share of total expenses. It's built with the **dataviz** skill, loaded on demand only for this view.

## 5. Self-review against generic defaults (skill step 2)

| First instinct | Why it's generic | Revised to |
|---|---|---|
| Dashboard hero with 4 KPI cards (Income, Expenses, Net, Review) | the "big number + small label" SaaS kit | The Schedule E form *is* the summary; numbers live on their form lines |
| Rounded cards for each transaction | SaaS-card kit | Ruled ledger table, 0 radius rows |
| Warm cream background + serif headings | the #1 AI tell | Cool green-grey paper, a single sans |
| Purple/indigo primary, red for negatives | default palette; spending isn't an error | Ledger green accent; ink for outflows |
| All-caps tracked labels ("CATEGORY", "AMOUNT") | template chrome | Sentence-case labels, only where needed |
| Emoji in empty state ("All done 🎉") | generated-copy tell | "All rows reviewed. Your Schedule E is ready to export." |
| Popover per row to fix category | high travel distance, hidden state | Persistent decision panel (Fitts, visibility) |
| Arrows on buttons ("Continue →") | template chrome | Plain verbs: "Confirm", "Export CSV" |
| Fade-up animations on every section | scattered motion | One motion moment (confirm → total) |
| Inter / Geist | default families | IBM Plex Sans with tabular figures |

## 6. Content & microcopy

### Glossary (one vocabulary)
| System term | User-facing term |
|---|---|
| status `auto` | Sorted |
| status `user_confirmed` | Confirmed by you |
| status `needs_review` | Needs your review |
| status `duplicate` | Duplicate (skipped) |
| kind `non_pnl` | Not counted on Schedule E |
| confidence ≥ 0.85 / 0.6–0.85 / < 0.6 | High / Medium / Low |
| MerchantRule | "Remember for <merchant>" |

### Copy rules
- Sentence case, active voice, buttons named for their result ("Confirm", "Export CSV", "Upload statement").
- Errors state what happened and how to fix it, with no apologies.
- Empty states invite an action.
- No marketing tone.
- The only disclaimer is in the footer: "Helps you organize; not tax advice. Sample data is fictional."

## 7. Product name
"Ledgerly" (placeholder, short and subject-grounded). The user can rename it; it's one constant in `src/lib/brand.ts`.

## 8. Design validation (how we prove the quality)
1. **Screenshot critique loop:** Playwright captures each page at 1440 / 1024 / 390 px. The frontend-builder and the ui-reviewer **look at the images** (cheaper and more accurate than reading CSS) and fix issues.
2. **Heuristic evaluation:** the ui-reviewer scores each Nielsen heuristic, with severity 0–4 for each issue → `docs/reviews/ui.md`.
3. **Cognitive walkthrough** (scripted tasks with targets) on the sample file:
   - T1 Upload a checking statement: ≤ 3 actions.
   - T2 Resolve all review items keyboard-only: no mouse needed (asserted in e2e).
   - T3 Find out why a row needs review: answer visible without clicking.
   - T4 Undo a wrong confirm: 1 action.
   - T5 Export for the CPA: ≤ 2 actions from Review.
4. **axe** with zero serious/critical issues, and the contrast script passes.
5. The screenshots go into the README and DESIGN.md.

## 9. Tooling notes
- **frontend-design** plugin is installed but not active in this session. Enable it for the build phase (`/plugin`). The frontend-builder brief references this file, so the design decisions are already made here, and the skill is used for the critique pass.
- **context7** plugin (installed): use it on demand for current Next.js, TanStack and Tailwind API docs instead of guessing. That avoids wrong-API rework, which costs more tokens than the lookup.
- **dataviz** skill: only for the Summary bars.
- Component primitives: Radix (behavior and accessibility only, unstyled) plus our own Tailwind tokens. **No shadcn default theme**, since its stock look is a recognizable template; if we use its code, we restyle it to these tokens.

# UI review — 2026-10-26 — ui-reviewer (Sonnet)
Scope: frontend/src (all components, globals.css, layout, lib/categories, lib/format) vs docs/plan/07a §2/§3/§5/§6/§8 and 07. Method: code read only (docker stack at localhost:3000 was not running, so NO screenshots, NO axe run, no e2e run). Grepped for uppercase/tracking/gradient/shadow/rounded-xl/arrow/emoji/mono. Contrast ratios computed with a node snippet. Findings that depend on rendered appearance (layout at 390 px, focus ring visibility) are inferred from code and marked "verify visually".

Severity here is High/Med/Low (Nielsen 0-4 mapping: High=3-4, Med=2, Low=1).

| ID | Severity | Location | Finding | Recommendation | Status |
|---|---|---|---|---|---|
| UI-1 | Med | components/UploadForm.tsx:344-356, 322-338 | The real file input is `sr-only`; the visible drop zone is its `<label>` with no `focus-within`/peer focus style. A keyboard user tabbing to the input sees no focus ring anywhere (violates 07a focus-visible on everything, WCAG 2.4.7). | Add `has-[:focus-visible]` / `peer-focus-visible:outline` on the label (or `focus-within:outline`). | Open |
| UI-2 | Med | components/ReviewWorkspace.tsx:459-461 with DecisionPanel `key={sel.id}` | After Confirm the selection advances and the panel remounts, destroying the focused Confirm button, so focus falls to `<body>`. Keyboard still works through the window handler, but screen reader and Tab users lose their place. No announcement of the newly selected row. | Restore focus to the Confirm button (or panel heading) after remount, or avoid remount via key; announce the new row in the polite region. | Open |
| UI-3 | Med | ReviewWorkspace.tsx:270-317 (undo) | Undo calls `api.fix(row, {category: prior})`. If the backend marks any fix as `user_confirmed`, an undone row does not return to "Needs your review" (and a row whose prior category was null is skipped entirely, line 300). The user sees "Change undone." but the queue count does not go back up. Verify against backend `fix` semantics. | Add a backend revert (restore prior status) or an undo endpoint; add an e2e assertion that count returns to N. | Open (verify) |
| UI-4 | Med | components/Toast.tsx:116 vs globals.css:120-126 | On <900 px the decision panel is a fixed bottom sheet (z-20, 44vh); the toast is fixed `bottom-4` z-30, so it sits on top of the panel's Confirm/Skip row and the Undo button competes with controls. Toast auto-dismisses at 8 s (Toast.tsx:111), a timing limit on the only visible Undo (U key still works, but is undiscoverable on touch). Verify visually at 390 px. | Offset the toast above the sheet on mobile (`bottom: calc(44vh + 1rem)`), pause the timer on hover/focus, extend to 10-12 s. | Open |
| UI-5 | Med | DecisionPanel.tsx:601-622 | "Also apply to N similar" does not list the rows before applying (07a heuristic 5 says it must). Bulk change relies solely on toast undo. | Show the similar merchants/rows (expandable list or count with dates and amounts) next to the checkbox. | Open |
| UI-6 | Low | TransactionList.tsx:7-13 | Status shape deviates from spec: non-P&L ("Not counted") rows get filled ● (counted) in the All tab; ○ is used only for duplicates. Sorted vs Confirmed-by-you are visually identical (word only for screen readers, line 17). Contradicts "● counted, ◐ needs review, ○ not counted". | Pass category kind into StatusMark; show ○ for non_pnl and for duplicates a distinct mark. | Open |
| UI-7 | Low | ReviewWorkspace.tsx:383-396 | `role="tablist"`/`role="tab"` without `role="tabpanel"`, `aria-controls`, or arrow-key roving; incorrect ARIA pattern (tabs filter a single list). | Use plain buttons with `aria-pressed`/`aria-current`, or implement the full tab pattern. | Open |
| UI-8 | Low | DecisionPanel.tsx:574-577 | Unselected quick-pick buttons use `border-rule` (#D5E0DB) on white: 1.35:1 non-text contrast (WCAG 1.4.11 needs 3:1) so the buttons read as bare text. Selection state is fine (border + tint + weight). | Use `border-muted` (5.3:1) for the quick-pick buttons. | Open |
| UI-9 | Low | DecisionPanel.tsx:567-583 | Quick picks omit the Schedule E line number that 07a wireframe shows ("Repairs (line 14)"); only the dropdown has it. Weakens "match with real world" and recognition. | Append muted "line 14" to each pick. | Open |
| UI-10 | Low | components/HelpSheet.tsx:18, TopBar.tsx:206, Toast/ReviewWorkspace panel-shadow | Anti-template drift: shadow on the help dialog (spec allows only decision panel and toast); `rounded-full` step circles (spec radii: 2/6/0). Minor. | Drop the dialog shadow (use border); use rounded-xs or a square badge. | Open |
| UI-11 | Low | ReviewWorkspace.tsx:218,227,444-451 | Progress "7 of 9 left" uses a client-side high-water mark; after a reload mid-session it resets ("3 of 3 left", bar empty). Misreports status (heuristic 1). | Derive total from reviewed+needs_review counts (user_confirmed vs auto) from the API. | Open |
| UI-12 | Low | ReviewWorkspace.tsx:234-247 | Gestalt grouping of same-merchant rows in the queue (07a "similar rows grouped") not implemented: order is by row_index only. Mitigated by the "Also apply to N similar" checkbox. | Sort needs_review by merchant_key then row_index, or show a merchant divider. | Open |
| UI-13 | Low | ReviewWorkspace.tsx (no h1); SummaryView.tsx:454 | Review page has no `<h1>` (panel starts at h2; statement name only in TopBar div). Summary Export link falls back to `href="#"` while statement loads. | Add visually hidden or visible h1; render a disabled button until the statement id is known. | Open |
| UI-14 | Low | Toast.tsx:116-131; ReviewWorkspace.tsx:314 | Error toasts (failed confirm) auto-dismiss in 8 s with the same dark style, no `role="alert"`; the user may miss why a row bounced back. | Keep errors until dismissed and mark `role="alert"`. | Open |
| UI-15 | Low | repo (no `scripts/check_contrast.mjs`) | 07a §2/§8 require a CI contrast script; none exists (only copy-samples.mjs in frontend/scripts). I computed the ratios below by hand and all text pairs pass, but nothing guards them. Also not verified: axe zero serious/critical, screenshots at 3 widths (no running app). | Add the script (the snippet below is enough) and wire into CI; run axe + screenshots once the stack is up. | Open |

Summary: High 0, Med 5, Low 10. Verdict: solid, spec-faithful build with no template tells; fix UI-1 to UI-5 before submission, and run the screenshot and axe pass that this review could not do. No High issues found from code.

## Anti-template check (07a §5): PASS
No uppercase/tracking classes, gradients, emoji, "→" arrows or gradient/rounded-xl cards (grep clean). IBM Plex Sans via next/font, tabular-nums on amounts (`.num`), sentence case, ledger table with 0-radius rows, single accent, no red for outflows, empty state copy "All rows reviewed. Your Schedule E is ready to export." matches. One motion moment honored, reduced-motion handled (globals.css:89-100). Only deviations are UI-10.

## Contrast (computed, WCAG ratios)
| Pair | on paper #F5F7F6 | on white | on attention fill #FBEFD9 |
|---|---|---|---|
| ink | 13.54 | 14.57 | 12.80 |
| ledger | 5.93 | 6.38 | 5.60 |
| muted | 4.92 | 5.30 | 4.65 |
| attention | 5.50 | 5.92 | 5.20 |
| error | 6.85 | 7.37 | 6.47 |
White on ledger 6.38 (Confirm, toast uses white on ink). All text pairs >= 4.5. Non-text: `rule` on white 1.35 (see UI-8; fine for decorative table rules).

## Accessibility notes
Good: table semantics with captions and sr-only headers; `aria-live` status in Toast and upload; labelled search; `:focus-visible` 2px ledger outline offset 2 globally; 24 px min-height; fieldset/legend for account type; Radix Dialog for the help sheet (focus trap); status shapes paired with sr-only text; progress element labelled; role=alert on errors. Gaps: UI-1, UI-2, UI-4, UI-7.

## Nielsen heuristics (0 = none, 4 = catastrophe; severity of worst issue found)
| # | Heuristic | Score | Basis |
|---|---|---|---|
| 1 | Visibility of system status | 1 | Process bar, progress, live total flash, upload busy text all present; UI-11 progress resets |
| 2 | Match with real world | 0 | Schedule E lines, "Mar 4", money format, plain-language flags (FLAG_TEXT); UI-9 minor |
| 3 | User control & freedom | 2 | Toast Undo + U + restore duplicate, no confirm dialogs; UI-3 undo may not restore queue state, UI-4 toast timing |
| 4 | Consistency & standards | 1 | Glossary matches STATUS_LABEL exactly; Confirm/Confirmed consistent; UI-6 mark mismatch |
| 5 | Error prevention | 1 | Direction filtering (allowedFor), client file checks (size/ext/empty); UI-5 similar list not shown |
| 6 | Recognition over recall | 1 | Suggested pre-selected, ranked picks, reasons inline; UI-9 |
| 7 | Flexibility & efficiency | 1 | J/K, 1-9, Enter, R, U, ? implemented; UI-2 focus loss; no hint of keys beside picks except numbers |
| 8 | Aesthetic & minimalist | 0 | Anti-template pass; reasons collapsed after 2; UI-10 trivial |
| 9 | Error recovery | 1 | Row-numbered upload errors with fix text, existing-statement link, Try again; UI-14 |
| 10 | Help & documentation | 0 | Why-this-category in panel and list row, ? sheet, flag one-liners |

## Cognitive walkthrough (judged from code; not executed)
| Task | Target | Result | Notes |
|---|---|---|---|
| T1 Upload checking statement | <= 3 actions | PASS | Checking default; choose file auto-uploads and routes (1-2 actions); sample link is 1 action. Caveat: credit-card file needs radio first. UI-1 hurts keyboard users. |
| T2 Resolve all review items keyboard-only | no mouse | PASS with caveats | J/K, 1-9, Enter work; review tab default when items exist. Focus drops to body after confirm (UI-2); tabs/search need Tab. Not verified by running e2e. |
| T3 Why does a row need review | visible without click | PASS | First reason shown under description in list (TransactionList:77) and "Why we are asking" in panel with flag text. |
| T4 Undo wrong confirm | 1 action | PASS (UI) / RISK (behavior) | Undo in toast or U = 1 action; 8 s window (UI-4); state restoration needs verifying (UI-3). |
| T5 Export for CPA | <= 2 actions | PASS | Review > "Schedule E summary" link > Export CSV = 2 actions; or 1 from the all-reviewed empty state. Export is allowed with unresolved rows, flagged by the banner. |

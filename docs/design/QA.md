# Interface and workflow verification

Reference: `concept.png` (1536 x 1024). Inspected using `view_image` alongside the latest Playwright desktop capture. Also inspected the mobile capture at 390 x 844 and the rendered synthetic PDF page.

Browser plugin was not available in this session, so regular Playwright Chromium was used. Its reproducible workflow lives in `frontend/e2e/workflow.spec.ts`. API and Vite ran on loopback ports 8001/5174 with an isolated SQLite database.

## Checks and evidence

| Check | Result |
| --- | --- |
| Page identity | SortedHisab title, expected local route |
| Meaningful render | Workspace, table, import and review controls present |
| Framework overlay | None observed |
| JavaScript runtime | No page errors or console errors in the full desktop flow |
| CSV flow | Upload 36 rows -> validate -> import -> review NAYATEL at 60% -> persist -> overview -> export |
| Invalid rows | All four invalid rows shown; import unavailable |
| Mobile | Demo -> search -> open/close review; document has no horizontal overflow |
| Other formats | Supported PDF and XLSX each import all 12 rows |
| Accounting evidence | PKR 4,200 mixed expense becomes PKR 2,520 business + PKR 1,680 personal |

## Concept comparison ledger

| Area | Reference and implementation | Resolution |
| --- | --- | --- |
| Layout | Deep teal left navigation, four metrics, table and right review pane | Preserved; mobile uses a top navigation rail |
| Palette | White surfaces, cool gray canvas, teal controls, amber uncertainty | Preserved as flat tokens, without the generated lighting |
| Typography | Sans hierarchy, compact table and label text | System-font fallback; working text is denser to accommodate full provenance and transaction types |
| Icons | Thin outline navigation and financial controls | Lucide outline family, consistent sizing |
| Review geometry | Concept has shorter form | Added explicit type/confidence/rule scope; bounded internal scroll prevents page stretching |
| Copy | Brand, navigation, main heading, actions and status tabs | Preserved; functional explanations and correct computed fixture values replace invented concept values |
| Summary placement | Concept puts category strip below table | Intentional extension: complete reconciled category totals live in Overview with a summary export |
| Data integrity | Concept has decorative amounts and broad confirmation labels | Actual engine results distinguish categorized from user-confirmed and retain outstanding reviews |
| Responsive | Concept calls for a scrolling table and full-width mobile review | Verified at 390px; table scroll is confined to its panel |

Above-the-fold copy was checked against the token inventory. Added account/currency selectors, source/uncertainty explanations and all-account metric scope labels are required functional extensions, recorded in `TOKENS.md`. No marketing section or decorative raster asset was added.

Fixed during verification: Windows executable quoting in test setup; explicit accessible review-control names; overlong review form; label caption wrapping; merchant-rule conflict; table text size. The implemented screen was visually checked against the reference's design system with the intentional functional differences above. It is not claimed to be a pixel-identical screenshot replica.

Remaining scope: Chromium only; no real bank or personal statements; PDF compatibility limited to the documented synthetic table; category defaults are editable assumptions. Backend test output includes an upstream Starlette TestClient/httpx deprecation warning; tests pass. This warning does not arise in the app's browser workflow.

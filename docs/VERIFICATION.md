# Verification record

Executed on **2026-10-26** with synthetic data only. This records observed local results, not an assertion that a remote CI run or Docker deployment occurred.

| Check | Observed result |
| --- | --- |
| Python tests (`pytest`) | **119 passed** |
| Backend line coverage (`pytest-cov`) | **98% overall**; **100% engine** and **100% reporting** |
| Python imports/style (`ruff check backend scripts`) | Passed |
| Python formatting (`ruff format --check backend scripts`) | Passed |
| Python dependency consistency (`pip check`) | No broken requirements found |
| React unit/component tests (`npm test`) | **11 passed** across 4 files |
| Frontend formatting (Prettier) | Applied; checked before packaging |
| TypeScript + production bundle (`npm run build`) | Passed |
| Real API browser workflows (`npm run test:e2e`) | **5 passed** |
| Built React served directly by FastAPI | Opened successfully; review dialog opened, selection worked, and cancellation worked |
| Browser page errors in production smoke check | None observed |
| Responsive document widths | No page overflow at **1440, 1024, 768, 390, or 320 px** |
| Source archive | ZIP integrity and per-file SHA-256 manifest checked during packaging |

## End-to-end cases

1. Load the synthetic sample via the real upload endpoint; inspect an unknown merchant; choose Meals; save a note; verify the expense total changes from $182.48 to $200.88; reload; inspect persisted review history; download a draft CSV containing the saved note.
2. Upload a separate CSV through the file input; automatically categorize an expense, refund, and transfer; verify $10.00 net expense and final CSV refund semantics.
3. Upload invalid dates/amounts/currencies; show row-level errors and confirm no statement was partially stored.
4. Dismiss the native review dialog with Escape; re-import identical sample bytes; verify idempotent reuse and unchanged totals.
5. Use the review queue at a 390 px viewport; verify no document-level horizontal overflow.

Browser tests start their own FastAPI and Vite processes and use a fresh temporary database. No categorization or review endpoint is mocked in these tests. React unit tests mock the HTTP client intentionally to test error and form states in isolation.

## Sample accounting assertions

- 20 rows imported; 11 auto-sorted; 9 need review.
- Accepted spending: **20,248 cents**.
- Accepted refunds: **2,000 cents**.
- Net accepted expenses: **18,248 cents**.
- Confirmed income before review: **0 cents**.
- Transfers: **80,000 cents out**, **20,000 cents in**.
- Unknown/flagged amounts remain outside accepted category totals.
- Raw signed cash flow equals the sum of accepted, unresolved, and excluded signed cash flow.

## Environment and limitations

- Python **3.12.14**, Node.js **24.22.1**, npm **11.9.0**.
- Backend dependency versions are in `requirements.txt` / `requirements-dev.txt`; frontend versions are in `frontend/package-lock.json`.
- Chromium **153.0.8010.0** was used through `PLAYWRIGHT_CHROMIUM_EXECUTABLE`. The standard Playwright browser download returned an invalid ZIP in this environment. A separate local browser binary was installed for testing and is **not shipped** with the project.
- One upstream Starlette warning was emitted: its use of the installed `httpx` TestClient adapter is deprecated in favor of `httpx2`. The existing adapter passed all tests. No warning suppression is configured.
- npm emitted an authoring-environment proxy-config warning; it did not block builds or tests.
- Docker is not available in the authoring runtime: **the Docker image and Compose flow were not executed**. Their setup is included, while native setup and Python static hosting were tested.
- GitHub access was declined: **the supplied CI workflow has not run remotely and no PR was created**.
- There was no penetration test, real statement import, tax-accuracy certification, or full accessibility audit.
- AI provider token telemetry was not available. See `AI_USAGE.md`; no exact token total or provider usage screenshot is claimed.

An earlier browser run revealed and helped fix a screen-reader label escaping the mobile table's scroll container. The table now establishes its own positioning context; hiding overflow on the entire page was not used as a workaround. Earlier test-selector mismatches and a TypeScript test-option mismatch were also corrected before the passing runs above.

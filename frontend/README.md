# Statement Categorizer - frontend

React + TypeScript single-page app for uploading a credit-card statement (CSV, Excel, PDF, OFX, ISO 20022 XML or SWIFT MT940),
reviewing the automatic categorization, fixing uncertain rows and exporting the result.

## Setup

```sh
npm install
cp .env.example .env   # optional
npm run dev            # http://localhost:5173
```

The dev server proxies `/api` to `http://localhost:8000`, so start the backend first.
Set `VITE_API_BASE_URL` to point at a differently hosted API (leave empty for same-origin).

## Scripts

| Script              | What it does                    |
| ------------------- | ------------------------------- |
| `npm run dev`       | Vite dev server on port 5173    |
| `npm run build`     | Typecheck and production build  |
| `npm run preview`   | Serve the production build      |
| `npm test`          | Unit/component tests (vitest)   |
| `npm run lint`      | ESLint                          |
| `npm run typecheck` | `tsc --noEmit`                  |

## Layout

- `src/api/client.ts` - typed fetch wrapper and `ApiError`
- `src/hooks/useStatement.ts` - upload / correction state
- `src/components/` - upload, summary, review queue, transaction table, etc.
- `src/format.ts` - currency, date and percent helpers
- `src/test/` - test setup and fixtures

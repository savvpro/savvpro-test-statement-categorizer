# Statement Categorizer: frontend

Next.js (App Router) + TypeScript + Tailwind v4. A single page that uploads a statement,
shows how each row was categorized and why, and lets the user fix the rows that need review.

See the [root README](../README.md) for how to run the whole project.

```bash
cp .env.example .env.local   # optional: point at a different backend
npm install
npm run dev                  # http://localhost:3000
npm run lint
npm run build
```

## Layout

| Path | What it is |
| --- | --- |
| `app/page.tsx` | Server component that renders `StatementApp` |
| `app/globals.css` | Design tokens (OKLCH, light and dark) |
| `components/StatementApp.tsx` | All page state: upload, fix, filter, notices |
| `components/UploadPanel.tsx` | Drop zone, options, sample button |
| `components/StatementSummary.tsx` | Tax-time totals and per-category table |
| `components/ReviewBar.tsx` | Progress and the All / Needs review filter |
| `components/TransactionTable.tsx` | The rows; becomes stacked cards on phones |
| `components/CategorySelect.tsx` | Grouped native `<select>` for fixing a row |
| `lib/api.ts` | The only code that talks to the backend |
| `lib/types.ts` | Response types mirroring the backend models |

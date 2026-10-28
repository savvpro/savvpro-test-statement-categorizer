# 07 — Frontend

> Visual design, HCI rules, wireframes, tokens and copy are in **[07a-ux-design-system.md](07a-ux-design-system.md)**. Where 07a and this file differ (e.g. layout of the review page = master-detail with decision panel, not popovers), **07a wins**.

## 1. Stack
Next.js (App Router, latest stable at P0) · TypeScript strict · Tailwind CSS · TanStack Query (server state) · TanStack Table (table) · `openapi-typescript` + `openapi-fetch` (typed client) · Radix UI primitives (accessible Select/Dialog/Tooltip/Tabs) · lucide-react icons · Vitest + Testing Library + MSW · Playwright + axe.
No global client state library — server state lives in TanStack Query; UI state is local.

## 2. Routes
| Route | Purpose |
|---|---|
| `/` | Upload: drag-drop zone, account type (Checking / Credit card) radio, "Try a sample" buttons, recent statements list |
| `/statements/[id]` | Review: header (file, period, counts), tabs **Needs review (n)** · **All** · **Excluded** · **Duplicates**, search box, table |
| `/statements/[id]/summary` | Schedule E summary, excluded totals, unresolved banner, Export CSV |
Data fetching client-side via Query (API is the backend; Next rewrites `/api/*` → backend so same-origin, no CORS in compose).

## 3. Components (`src/components`)
- `UploadDropzone` — accept `.csv,.ofx,.qfx`, client-side size pre-check (5 MB) for fast feedback (server still enforces), progress state.
- `AccountTypeToggle`
- `StatementHeader` — counts chips, period, warnings accordion (parse warnings in plain English).
- `StatusTabs`
- `TransactionsTable` — columns: Date · Description (+ memo muted) · Amount (green inflow / default outflow, tabular-nums, `Intl.NumberFormat` USD) · Category (chip or `CategorySelect` when editing/needs review) · Confidence (badge: High ≥0.85 / Medium / Low) · Why (info icon → tooltip listing reasons + flags) · Actions.
- `CategorySelect` — grouped by kind (Income / Expenses (Sch E line) / Not counted), filtered by row direction (mirrors backend compatibility table, fetched from `/categories`); suggestion pre-selected and labelled "Suggested".
- `FixRowPopover` — select + `Remember for "<merchant>"` checkbox + `Apply to N similar rows` checkbox (N from `similar_count`) + Save.
- `FlagBadge` — human labels for flags.
- `SummaryTable` — Sch E line, label, total; income/expense/net footer; excluded section; unresolved banner linking back to Needs review tab.
- `ExportButton` — plain link to export endpoint.
- `ErrorState`, `EmptyState`, `LoadingSkeleton`, `Toast`.

## 4. Data layer (`src/lib/api`)
- `schema.d.ts` generated from `backend/openapi.json` (`npm run gen:api`), committed, drift-checked in CI.
- `client.ts` — `createClient<paths>({ baseUrl: "/api" })`; `toAppError(problem)` maps problem+json to friendly messages per code (413 "File is larger than 5 MB", 415 "Only CSV or OFX/QFX files", 422 row errors list, 409 "Already uploaded — open it?").
- `hooks.ts` — `useStatements`, `useStatement(id)`, `useTransactions(id, filters)`, `useSummary(id)`, `useCategories`, `useUpload`, `useFixTransaction` (optimistic update of the row + invalidate counts & summary).

## 5. UX rules
- Default landing after upload = **Needs review** tab if count > 0, else summary-first hint.
- Every row explains itself (Why tooltip). Never hide uncertainty.
- Keyboard: tab through rows, Enter opens fix popover, Esc closes; focus returns to row.
- States for every view: loading skeleton, empty ("All rows reviewed. Your Schedule E is ready to export."), error with retry.
- Disclaimer footer: "Organizational aid, not tax advice. Demo uses fake data."
- Responsive: table → stacked cards below 768px.
- Accessibility: labels on all inputs, Radix primitives, color not sole signal (badges have text), contrast AA, `aria-live` for toast.

## 6. Structure
```
frontend/
  src/app/layout.tsx, page.tsx, providers.tsx (QueryClientProvider), statements/[id]/page.tsx, statements/[id]/summary/page.tsx
  src/components/…  src/lib/api/…  src/lib/format.ts (money/date)  src/lib/categories.ts
  public/samples/ (copied from /samples at build via npm script)
  next.config.ts (rewrites /api → API_INTERNAL_URL, security headers, output: "standalone")
  vitest.config.ts, playwright.config.ts, eslint.config.mjs, .prettierrc
```

## 7. Quality gates
TS strict, `noUncheckedIndexedAccess`; ESLint (next/core-web-vitals, react/no-danger error, jsx-a11y); Prettier; vitest; build; Lighthouse is not gated (manual note in README).

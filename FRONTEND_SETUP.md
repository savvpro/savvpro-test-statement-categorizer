# Statement Categorizer — React + Vite frontend

This folder is a complete React + Vite UI for the Statement Categorizer assessment. It includes CSV/TSV upload, transaction summary cards, searchable/filterable transaction table, Needs Review indicators, category editing, loading states, and API error handling. It does not use a hosted AI service to categorize transactions; categorization is performed by the backend.

## Run it on Windows

1. Copy the `frontend` folder into your existing `statement-categorizer` project, replacing the empty frontend files.
2. Open PowerShell in the `frontend` folder.
3. Install dependencies and start Vite:

```powershell
npm install
npm run dev
```

4. Start the FastAPI backend in a second terminal using the existing backend instructions. The UI expects it to be available at `http://localhost:8000` when no `VITE_API_BASE_URL` is set.
5. Open the Vite URL shown in the terminal, usually `http://localhost:5173`.

For a backend hosted at another origin, create `.env` from `.env.example` and set `VITE_API_BASE_URL=http://localhost:8000`, then restart Vite.

## API integration notes

The upload helper tries `POST /api/statements/upload`, `POST /api/statements`, `POST /statements/upload`, and `POST /statements`, sending a multipart form field named `file`. The response should contain a transaction array either directly or under `transactions`, `results`, `data`, or `items`. Each transaction can use common aliases for id/date/description/amount/category. Category editing tries `PATCH /api/statements/transactions/{id}` and `PATCH /api/transactions/{id}` with JSON `{ "category": "..." }`.

Because the supplied archive's Python files could not be extracted in this environment, these routes are best-effort compatibility candidates rather than a verified match to your backend. If your FastAPI routes differ, update the endpoint paths in `src/lib/api.js` to match `backend/app/routers/statements.py`. The UI will show a clear error rather than pretending the request succeeded.

## Production build

```powershell
npm run build
npm run preview
```

## Privacy and safety

- No third-party AI API is called from the browser.
- The browser uploads the statement only to the configured backend origin.
- Use synthetic/fake statements for assessment testing; do not commit real financial statements, secrets, or `.env` files.
- Amounts are formatted as USD in this starter UI. Change the formatter in `src/components/Stats.jsx` and `src/components/TransactionTable.jsx` if the assessment specifies another currency.

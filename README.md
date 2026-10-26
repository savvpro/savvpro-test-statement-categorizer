# simplke

simplke sorts a freelance designer’s business statement before tax time.

Upload a CSV. simplke reads each row, gives it a category, and sends unsure rows to **Needs review**. You can fix rows and export a new CSV.

All demo data is fake. No keys or real bank statements are included.

## Run the web app

```bash
pnpm install
pnpm dev:static
```

Open the local URL shown in the terminal. The demo statement loads first. To use another file, click **Import statement**.

CSV needs these columns:

- date
- description or merchant
- amount
- optional type: Debit or Credit

These commands run the checks:

```bash
pnpm check
pnpm test
pnpm build:static
python3 -m unittest discover -s backend -p 'test_*.py'
```

Amounts are shown as **PKR** in the app. The original CSV values are kept unchanged in the export. No exchange-rate conversion is guessed.

## Run the Python API

The rule engine is in `backend/categorizer.py`. It uses Python’s standard library only.

```bash
python3 -m backend.server
curl -X POST http://127.0.0.1:8787/api/categorize \
  -H 'Content-Type: text/csv' \
  --data-binary @fixtures/demo_statement.csv
```

## Main files

- `client/src/pages/Home.tsx` — upload, review, totals, and export.
- `client/src/lib/csv.ts` — CSV reading and export.
- `client/src/lib/categorizer.ts` — browser rules.
- `backend/categorizer.py` — Python rules.
- `backend/test_categorizer.py` — Python tests.
- `fixtures/demo_statement.csv` — fake demo data.
- `DESIGN.md` — use case and brain rules.
- `AI_USAGE.md` — AI help and usage evidence.

# Statement Categorizer

A CSV statement review app for freelance designers. The Python API parses
transactions and applies explicit, deterministic rules; the React interface
shows the results, highlights uncertain rows, and lets the user adjust
categories and mark rows reviewed.

## Requirements

- Python 3.10 or newer
- Node.js 20 or newer and npm

## Install

From the repository root, create and activate a Python virtual environment,
then install the backend dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks virtual-environment activation, use
`.venv\Scripts\python.exe -m pip install -r requirements.txt` and run the
backend with `.venv\Scripts\python.exe -m uvicorn app.main:app --reload`.

Install frontend dependencies:

```powershell
cd frontend
npm install
```

## Configure and run

Start the backend from the repository root:

```powershell
python -m uvicorn app.main:app --reload
```

The API listens at `http://127.0.0.1:8000`. Interactive API documentation is
available at `http://127.0.0.1:8000/docs`.

In a second terminal, start the frontend:

```powershell
cd frontend
Copy-Item .env.example .env.local
npm run dev
```

Open the local URL printed by Vite, typically `http://localhost:5173`.
`VITE_API_URL=/api` is the default. During development, Vite forwards `/api`
requests to `http://127.0.0.1:8000` and removes the `/api` prefix before
forwarding them to FastAPI's `/categorize` endpoint.

To change the frontend API URL, edit `frontend/.env.local`. A relative URL
prefix is proxied to `http://127.0.0.1:8000`. An absolute URL (for example,
`https://api.example.com`) is called directly by the browser; that API must
allow the frontend origin through CORS. The included FastAPI app does not
configure CORS middleware. Restart Vite after changing environment variables.
Do not put secrets in `VITE_*` variables; Vite exposes them to browser code.

## CSV format and API

Upload a `.csv` file through the page or send it as multipart form data in the
`file` field to `POST /categorize`. A statement must have date and description
columns plus either an amount column or debit/credit columns. Headers are
case-insensitive and normalized; supported names include `date`,
`transaction date`, `posted date`, `posting date`, `description`,
`transaction description`, `transaction details`, `details`, `memo`,
`merchant`, `narrative`, `amount`, `transaction amount`, `debit`,
`debit amount`, `withdrawal(s)`, `credit`, `credit amount`, and `deposit(s)`.

Dates supported are `YYYY-MM-DD`, `YYYY/MM/DD`, `MM/DD/YYYY`, `MM/DD/YY`,
`DD-Mon-YYYY`, and `DD Mon YYYY`. Amounts accept common currency symbols,
parenthesized negatives, and common comma/dot decimal separators. For an
`amount` column, the sign is retained: use negative amounts for outflows and
positive amounts for inflows. Debit values are made negative and credit values
positive. When debit and credit columns are both present, each row must fill
exactly one.

The response contains normalized transactions, category, transaction type,
review status and reason, invalid rows with CSV row numbers and field errors,
signed totals by category, and total data rows. Invalid transaction rows are
reported and omitted from categorized transactions; a structurally unusable
CSV (for example, missing required headers) receives HTTP 400.

## Tests and production build

From the repository root, run the backend tests:

```powershell
python -m pytest -q
```

From `frontend/`, type-check and create the production build:

```powershell
npm run build
```

The frontend does not currently have a separate automated test suite. To
preview the build locally, run `npm run preview` from `frontend/`.

## Troubleshooting

- **Backend cannot start / missing module:** activate the virtual environment
  and run `python -m pip install -r requirements.txt`.
- **Frontend cannot find the API:** start FastAPI on port `8000`, use the
  default `VITE_API_URL=/api`, and restart Vite after editing `.env.local`.
- **Direct API URL blocked by the browser:** configure CORS on the API for the
  frontend origin; the included backend currently has no CORS middleware.
- **CSV rejected:** check that the header row has recognizable date,
  description, and amount (or debit/credit) headers. Correct row-level date,
  description, and amount errors shown in the results.
- **Transaction marked Needs Review:** the deterministic rules did not
  confidently match its description, or a refund's original merchant category
  could not be identified. Review and assign its category in the table.

## Assessment submission

Fork `savvpro/savvpro-test-statement-categorizer`, clone your fork, and create
the assessment branch (replace the placeholder with your GitHub username):

```bash
git checkout -b candidate-<your-github-username>
```

After testing, commit and push the branch:

```bash
git add .
git commit -m "feat: complete statement-categorizer assessment"
git push origin candidate-<your-github-username>
```

Open a pull request from your fork's `candidate-<your-github-username>` branch
to `savvpro/savvpro-test-statement-categorizer:main` with the title
`feat: complete statement-categorizer assessment`.

See [TASK.md](./TASK.md) for the full assessment requirements. The categorizer
uses no AI model for transaction decisions. Use fake statement data only; do
not commit real personal details, bank statements, credentials, or tokens.

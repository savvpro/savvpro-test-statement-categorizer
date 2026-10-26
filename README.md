# Studio Ledger — Statement Categorizer

Studio Ledger categorizes freelance designers' business transactions from a CSV bank statement. It uses transparent, deterministic Python rules rather than a large language model, and sends uncertain rows to **Needs review**.

## Run locally

### Backend

From the repository root:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`.

### Frontend

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. You can use **Try the sample statement** without preparing a file. Real uploads must be UTF-8 CSV files with `Date`, `Description`, and `Amount` columns.

## Test

```bash
cd backend
pytest
```

The frontend build can be checked with `npm run build` from `frontend`.

See [DESIGN.md](DESIGN.md) for the use case and decision rules, and [AI_USAGE.md](AI_USAGE.md) for development-tool usage.

## SaaS demo

The app now includes a multi-page authenticated workspace:

- `/login` — demo sign-in
- `/app` — overview dashboard
- `/app/transactions` — filter, correct, and export transactions
- `/app/rules` — inspect the categorization rules fetched from the API
- `/app/settings` — workspace profile

Use the seeded demo credentials:

```text
Email: demo@studioledger.com
Password: demo123
```

The frontend fetches workspace, dashboard, rules, login, and upload data from the FastAPI endpoints. The API uses fake seeded data and an in-memory demo session; no real financial data or credentials are used.

---

# Assessment submission guide

**Repository:** https://github.com/savvpro/savvpro-test-statement-categorizer

---

## Step 1: Fork the Repository

1. Go to the repository: https://github.com/savvpro/savvpro-test-statement-categorizer
2. Click the **Fork** button in the top-right corner.
3. This will create a copy of the repository in your GitHub account.

---

## Step 2: Clone Your Fork

1. Open your forked repository in your GitHub account.
2. Click the green **Code** button and copy the URL.
3. Run the following commands:

```bash
git clone https://github.com/your-username/savvpro-test-statement-categorizer.git
cd savvpro-test-statement-categorizer
```

---

## Step 3: Read the Task

Open and read **TASK.md** carefully before writing any code.

- TASK.md URL: https://github.com/savvpro/savvpro-test-statement-categorizer/blob/main/TASK.md

---

## Step 4: Create a New Branch

Branch pattern: `candidate-<your-github-username>`

```bash
git checkout -b candidate-<your-github-username>
```

**Example:**
```bash
git checkout -b candidate-johndoe
```

---

## Step 5: Complete the Task

Build the full application on your branch.

---

## Step 6: Push Your Branch

```bash
git add .
git commit -m "feat: complete statement-categorizer assessment"
git push origin candidate-<your-github-username>
```

---

## Step 7: Create a Pull Request

1. Go to your **forked** repository on GitHub (`https://github.com/your-username/savvpro-test-statement-categorizer`).
2. Click **Compare & pull request** (GitHub will show this banner after you push your branch).
3. Ensure the following settings in the PR form:
   - **Base repository:** `savvpro/savvpro-test-statement-categorizer` ← the original repo
   - **Base branch:** `main`
   - **Head repository:** `your-username/savvpro-test-statement-categorizer` ← your fork
   - **Compare branch:** `candidate-<your-github-username>`
4. Use the title: `feat: complete statement-categorizer assessment`
5. Submit the pull request.

> 💡 **Tip:** If you don't see the banner, go to the original repo (`savvpro/savvpro-test-statement-categorizer`), click the **Pull requests** tab, then click **New pull request** → **compare across forks**.

---

> ⚠️ **Important:** No submissions will be accepted after the deadline.

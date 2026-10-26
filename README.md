# Step-by-Step Guide: How to Fork, Clone, and Submit Your Assessment

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
 
---

# Statement Categorizer — Application Guide

## Use Case

A freelance designer preparing bank and credit card transactions for tax time. The app categorizes business expenses, separates transfers and refunds, and flags uncertain transactions for review.

## Tech Stack

- Backend: Python and FastAPI
- Frontend: React and Vite
- Categorization: Custom deterministic Python rules
- Storage: In-memory
- Testing: pytest, ESLint, Vite

## Features

- Upload CSV statements
- Automatically categorize transactions
- Flag uncertain rows as Needs Review
- Detect duplicates and allow overrides
- Correct categories and reuse merchant corrections
- View spending summaries by category and currency
- Search and filter transactions
- Export categorized results as CSV

## Run Locally

### Backend

From the repository root:

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r backend\requirements.txt
    cd backend
    python -m uvicorn app.main:app --reload --port 8000

Backend API documentation: http://localhost:8000/docs

### Frontend

Open a second terminal in the repository root:

    cd frontend
    npm ci
    npm run dev

Open http://localhost:5173

## Sample Data

Upload `data/sample_statement.csv` to test categorization, duplicates, refunds, transfers, multiple currencies and invalid rows.

## Tests

Backend:

    cd backend
    python -m pytest -q

Frontend:

    cd frontend
    npm run lint
    npm run build

## Limitations

Transactions and corrections are stored in memory and are lost when the backend restarts. Currency totals are reported separately without conversion. Ambiguous transactions require manual review.

See DESIGN.md and AI_USAGE.md for implementation details.

# SAVV PRO SOLUTIONS — Statement Categorizer for Freelancers

A full-stack, local web application designed for freelancers (designers, software engineers, independent contractors) who need to quickly parse, categorize, and review bank and credit card transactions for tax preparation.

Powered by a **100% deterministic Python categorization brain** — zero external AI models, zero API keys, and zero network calls required for transaction classification.

---

## Table of Contents
1. [Features](#features)
2. [Prerequisites](#prerequisites)
3. [Quick Start & Installation](#quick-start--installation)
   - [Backend Setup](#backend-setup)
   - [Frontend Setup](#frontend-setup)
4. [Running the Application](#running-the-application)
5. [CSV Format & Sample Data](#csv-format--sample-data)
6. [API Endpoints](#api-endpoints)
7. [Running Tests](#running-tests)
8. [Tax & Financial Integrity Rules](#tax--financial-integrity-rules)
9. [Known Limitations](#known-limitations)
10. [Submission Guide](#submission-guide)

---

## 1. Features

- **Automated CSV Ingestion**: Handles bank statements with either signed `Amount` or split `Debit` / `Credit` columns.
- **Deterministic Python Engine**: Transparent, regex- and keyword-driven classification covering 9 distinct categories:
  - `Software`
  - `Travel`
  - `Meals`
  - `Office Supplies`
  - `Income`
  - `Refund`
  - `Transfer`
  - `Other Business Expense`
  - `Needs Review`
- **Transparent Audit Trail**: Every transaction row includes an explanation and rule tag detailing why it was classified.
- **Financial Integrity**:
  - **Transfers are excluded** from both income and business expense totals.
  - **Refunds are treated as contra-expenses** (offsetting deductible costs, never inflating gross revenue).
  - **Ambiguous multi-category vendors** (e.g., Amazon, Target) and blank descriptions automatically trigger `Needs Review`.
- **Interactive Manual Corrections**: Instant inline category dropdowns update totals and recalculate summaries in real-time.
- **Spending Visualizer**: Category progress bars highlight deductible spending distribution.
- **Interactive Filters**: Instant search by merchant or date, status filtering (`Needs Review`, `Categorized`, `Manual`), and category selection.

---

## 2. Prerequisites

- **Python**: Version 3.10+ (tested on Python 3.13)
- **Node.js**: Version 18+ (tested on Node.js v20)
- **Git**

---

## 3. Quick Start & Installation

### Backend Setup

1. Open your terminal and navigate to the `backend` folder:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Frontend Setup

1. In a separate terminal tab, navigate to the `frontend` folder:
   ```bash
   cd frontend
   ```

2. Install npm packages:
   ```bash
   npm install
   ```

---

## 4. Running the Application

### 1. Start the Backend API (Port 8000)

From the `backend` directory (with virtual environment activated):
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API health check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- Interactive OpenAPI Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 2. Start the Frontend Client (Port 5173)

From the `frontend` directory:
```bash
npm run dev
```
Open your browser and navigate to: **[http://localhost:5173](http://localhost:5173)**.

---

## 5. CSV Format & Sample Data

The application supports standard CSV files with headers matching common bank exports.

### Option A: Standard 3-Column Format (`Date`, `Description`, `Amount`)
Expenses are negative values (e.g. `-54.99`), and inflows (client income, refunds) are positive values.

```csv
Date,Description,Amount
2026-03-01,STRIPE PAYOUT CLIENT INVOICE 1042,3200.00
2026-03-02,ADOBE CREATIVE CLOUD,-54.99
2026-03-03,UBER *TRIP TO CLIENT OFFICE,-28.45
2026-03-04,STARBUCKS #1042 SEATTLE,-7.25
2026-03-05,TRANSFER TO SAVINGS,-1000.00
2026-03-06,AMAZON WEB SERVICES AWS.AMAZON.COM,-142.10
2026-03-07,STAPLES #0822 PRINTER INK & PAPER,-89.60
2026-03-08,USPS POSTAGE TRACKING,-14.20
2026-03-09,REFUND FROM AMAZON WEB SERVICES,35.00
2026-03-10,UPWORK ESCROW MILESTONE 2,1450.00
2026-03-11,AMAZON.COM*8B3120 RETAIL,-65.40
```

### Option B: 4-Column Credit Card Format (`Date`, `Description`, `Debit`, `Credit`)

```csv
Date,Description,Debit,Credit
2026-03-01,ADOBE CREATIVE CLOUD,54.99,
2026-03-02,UBER TRIP TO AIRPORT,34.20,
2026-03-03,AIRLINE TICKET REFUND,,120.00
2026-03-04,BEST BUY MONITOR MOUNT,84.99,
2026-03-05,TRANSFER TO SAVINGS,500.00,
2026-03-06,PAYPAL DEPOSIT CONSULTING FEE,,2400.00
```

> **Instant Demo**: In the web UI, you can click **"Load Freelancer Sample"** or **"Load Credit Card Sample"** to instantly test the engine with pre-built mock statements.

---

## 6. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check and server status. |
| `GET` | `/api/statements/sample` | Download sample CSV (`standard` or `credit_card`). |
| `POST` | `/api/statements/upload` | Upload and process statement CSV; returns categorized rows and financial summary. |
| `GET` | `/api/statements/current` | Retrieve currently active statement and recalculated metrics. |
| `PATCH` | `/api/transactions/{id}` | Update the category of a transaction; recalculates and returns updated summary. |

---

## 7. Running Tests

The test suite covers parser validation, the categorization brain, edge cases, financial calculations, and REST API endpoints.

From the `backend` directory (with virtual environment activated):
```bash
pytest -v
```

To run frontend build checks:
```bash
cd frontend
npm run build
```

---

## 8. Tax & Financial Integrity Rules

1. **Transfers (`TRANSFER TO SAVINGS`, etc.)**:
   - Internal movements between bank accounts are neither taxable business revenue nor deductible business expenses. They are tracked as **Transfers (Neutral)** and excluded from gross revenue and expense totals.
2. **Refunds (`REFUND FROM...`)**:
   - Money returned from vendors offsets deductible expenses. A refund is never classified as income. The dashboard displays `Net Deductible Expenses = Gross Expenses - Refunds`.
3. **Ambiguous Retailers (`AMAZON`, `TARGET`)**:
   - Freelancers often purchase both personal items and legitimate business equipment at big-box merchants. Rather than hazarding an incorrect tax deduction, the engine assigns `Needs Review` for confirmation.
4. **Duplicates Preserved**:
   - Bank statements legitimately contain identical amounts and merchants on the same day (e.g. multiple coffees or identical subscriptions). Every row receives a distinct unique UUID (`tx_...`) so no transaction is accidentally dropped.

---

## 9. Known Limitations

- **In-Memory Session Persistence**: Statement data is maintained in server memory. Restarting the FastAPI service clears the uploaded statement. In a multi-tenant production environment, PostgreSQL or SQLite with session cookies would be integrated.
- **Statement Header Variations**: While common aliases (`Date`, `Description`, `Payee`, `Merchant`, `Amount`, `Debit`, `Credit`) are supported, statements with non-standard proprietary layouts may require column mapping.
- **Multi-Currency**: Transactions are standardized to USD float values; multi-currency conversions are not currently supported.

---

## 10. Submission Guide

To submit your assessment branch:

1. Stage all changes:
   ```bash
   git add .
   ```
2. Commit your work:
   ```bash
   git commit -m "feat: complete statement-categorizer assessment"
   ```
3. Push to your candidate branch on GitHub:
   ```bash
   git push origin candidate-ZuhaNaveed
   ```
4. Open a Pull Request from `candidate-ZuhaNaveed` to `main` at `https://github.com/savvpro/savvpro-test-statement-categorizer`.

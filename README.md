# Freelancer Expense Statement Categorizer

## Overview
A full-stack application that categorizes freelancer/business expense transactions from CSV statements using rule-based Python logic.

## Features
- CSV statement upload
- Rule-based transaction categorization
- Confidence score
- Needs Review handling
- Manual category correction
- Category totals
- React frontend
- FastAPI backend

## Tech Stack
Frontend:
- React
- Vite

Backend:
- Python
- FastAPI
- Pandas

Testing:
- Pytest

## Categories
- Software
- Cloud Services
- Travel
- Food
- Office Supplies
- Internet & Phone
- Transfer / Not Expense
- Refund
- Needs Review

## Running the Backend

cd backend

venv\Scripts\activate

pip install -r requirements.txt

uvicorn main:app --reload

Backend:
http://127.0.0.1:8000

API Docs:
http://127.0.0.1:8000/docs

## Running the Frontend

cd frontend

npm install

npm run dev

Frontend:
http://localhost:5173

## Input CSV Format

date,description,amount
2026-10-01,ADOBE CREATIVE CLOUD,-5000
2026-10-02,UBER TRIP,-850

## Categorization Approach

The categorization engine uses deterministic Python rules.

For example:
- ADOBE → Software
- AWS → Cloud Services
- UBER → Travel
- PTCL → Internet & Phone

Transactions that do not match a known rule are assigned to:

Needs Review

No LLM is used to make categorization decisions.

## Tests

Run:

cd backend

python -m pytest

## Limitations

- Currently supports CSV input
- Uses keyword-based categorization
- Unknown merchants require manual review
- Rules can be extended for additional merchants/categories
# Statement Categorizer

A full-stack application that reads bank/credit card statements (CSV) and uses a deterministic, rule-based "brain" to categorize transactions for a small e-commerce seller. 

Ambiguous transactions are safely flagged as **Needs Review** rather than guessed, allowing the user to review and correct them.

## Features
- **Rule-Based Brain:** Custom Python regex engine categorizes transactions without using LLMs. It strictly follows a money-flow priority (Refunds > Transfers > Income > Expenses).
- **Interactive Review UI:** Users can manually correct categories via dropdowns.
- **Live Totals:** Category totals dynamically update when corrections are made.
- **Needs Review Filter & Counter:** Quickly isolate uncertain transactions and see exactly how many need fixing.
- **Export to CSV:** Download the final, corrected statement with one click.
- **Robust Error Handling:** Clear UI errors for malformed CSVs (missing columns, bad dates, invalid amounts).

## Project Structure
```text
.
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routes (/upload, /rows/{id})
│   │   ├── brain/        # Rule engine (refunds, transfers, merchants)
│   │   │   ├── models.py
│   │   │   ├── normalize.py
│   │   │   ├── engine.py
│   │   │   └── rules/    # Modular categorization rules
│   │   ├── models/       # Pydantic schemas
│   │   ├── parsers/      # CSV parsing logic
│   │   ├── store/        # In-memory storage for rows
│   │   └── main.py       # FastAPI entrypoint
│   ├── tests/            # Pytest test suite (brain, parser, API)
│   ├── pytest.ini
│   └── requirements.txt  # Python dependencies
├── frontend/
│   ├── app/              # Next.js App Router
│   │   ├── globals.css   # UI design
│   │   ├── layout.tsx
│   │   └── page.tsx      # Main upload, review, and totals UI
│   ├── lib/
│   │   └── api.ts        # Frontend fetch helpers
│   ├── next.config.js
│   ├── package.json
│   └── tsconfig.json
├── sample_data/
│   └── sample_statement.csv # Fake data for testing
├── docs/                 # AI usage screenshots
├── DESIGN.md             # Architecture and Brain logic
└── AI_USAGE.md           # AI tool documentation
How to Run Locally
1. Start the Backend (Python)
Open a terminal and run:

bash
cd backend
python -m venv .venv

# Activate the virtual environment
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

# Install dependencies and run the server
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
(API docs are automatically available at http://localhost:8000/docs)

2. Start the Frontend (Next.js)
Open a new terminal window and run:

bash
cd frontend
npm install
npm run dev
Open http://localhost:3000 in your browser.

3. Test the App
Upload the sample_statement.csv file found in the sample_data/ folder to see the brain categorize the transactions in real-time.

4. Run Backend Tests
To verify the rule-engine and API endpoints:

bash
cd backend
pytest -v
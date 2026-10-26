# Statement Categorizer - Setup & Run Guide

A production-ready statement categorizer for freelancers and agencies. Upload bank/credit card statements and automatically categorize transactions using rule-based logic.

## Project Overview

This application categorizes freelancer/agency transactions into:
- **Software & Tools** - Subscriptions and cloud services
- **Travel & Transport** - Rides, flights, fuel
- **Office & Supplies** - Stationery, printing, furniture
- **Client Income** - Payments from clients
- **Expense Refund** - Refunds and reversals
- **Needs Review** - Unclear transactions requiring manual review

## Architecture

- **Backend:** FastAPI (Python) with rule-based categorization engine
- **Frontend:** Next.js (React + TypeScript)
- **Categorization:** Pure Python logic (no AI models)

## Project Structure

```
savvpro-test-statement-categorizer/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── brain.py             # Rule-based categorization engine
│   ├── requirements.txt     # Python dependencies
│   ├── pytest.ini           # Test configuration
│   ├── tests/
│   │   ├── test_brain.py    # Unit tests for brain
│   │   └── test_api.py      # API integration tests
│   └── sample_data/
│       └── freelancer_statement.csv  # Sample CSV
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── index.tsx    # Main page
│   │   │   └── _app.tsx     # App wrapper
│   │   └── styles/          # CSS modules
│   ├── package.json
│   └── tsconfig.json
├── DESIGN.md                # Design decisions
├── AI_USAGE.md              # AI tool usage report
└── README.md                # This file
```

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- npm or yarn

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
```

3. Activate virtual environment:
```bash
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Run the API server:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

### Frontend Setup

1. Open a new terminal and navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create environment file:
```bash
copy .env.local.example .env.local
```

4. Run the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Running Tests

### Backend Tests

```bash
cd backend
pytest
```

Run tests with coverage:
```bash
pytest --cov=. --cov-report=html
```

View coverage report:
```bash
# Windows
start htmlcov/index.html

# macOS
open htmlcov/index.html
```

## Testing with Sample Data

A sample CSV file is provided at `backend/sample_data/freelancer_statement.csv`

### CSV Format

Your CSV must have these columns:
- `date` - Transaction date (any format)
- `description` - Transaction description
- `amount` - Numeric value (positive = income, negative = expense)

Example:
```csv
date,description,amount
2024-01-15,ADOBE CREATIVE CLOUD,-49.99
2024-01-16,UPWORK PAYMENT,2500.00
2024-01-17,UBER TRIP,-25.50
```

## API Endpoints

### Health Check
```
GET /
GET /api/health
```

### Upload Statement
```
POST /api/upload
Content-Type: multipart/form-data

file: CSV file
```

Response:
```json
{
  "transactions": [
    {
      "date": "2024-01-15",
      "description": "ADOBE CREATIVE CLOUD",
      "amount": -49.99,
      "category": "Software & Tools",
      "confidence": "High"
    }
  ],
  "summary": {
    "Software & Tools": 5,
    "Travel & Transport": 3,
    "Client Income": 2,
    "Needs Review": 1
  },
  "total_transactions": 11
}
```

## Features

### Frontend
- Drag-and-drop CSV upload
- Real-time categorization
- Category summary with counts
- Manual category editing
- Dynamic summary updates
- Color-coded categories and confidence levels
- Responsive design

### Backend
- CSV parsing with pandas
- Rule-based categorization
- Confidence scoring
- Error handling
- CORS support
- Unit and integration tests
- Type hints throughout

## Production Deployment

### Backend (FastAPI)

1. Set environment variables:
```bash
export PORT=8000
export HOST=0.0.0.0
```

2. Run with Uvicorn:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Or use Gunicorn with Uvicorn workers:
```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Frontend (Next.js)

1. Build the production bundle:
```bash
npm run build
```

2. Start production server:
```bash
npm start
```

3. Set environment variable:
```bash
NEXT_PUBLIC_API_URL=https://your-api-domain.com
```

## Development Notes

### Code Style
- Python: PEP 8 compliant
- TypeScript: ESLint + Next.js config
- Type hints used throughout

### Security
- No credentials in code
- .gitignore configured
- CORS properly configured
- Input validation on uploads

## Troubleshooting

### Backend not starting
- Check Python version: `python --version`
- Verify virtual environment is activated
- Check port 8000 is available

### Frontend not connecting to API
- Verify backend is running on port 8000
- Check `.env.local` has correct API URL
- Check browser console for CORS errors

### CSV upload fails
- Verify CSV has required columns (date, description, amount)
- Check CSV encoding (UTF-8 recommended)
- Ensure amount column is numeric

## Additional Documentation

- [DESIGN.md](./DESIGN.md) - Design decisions and categorization logic
- [AI_USAGE.md](./AI_USAGE.md) - AI tools usage report and token statistics

## Contributing

This is an assessment project. For the original task, see [TASK.md](./TASK.md)

## License

This project is for assessment purposes.

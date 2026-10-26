# Backend - Statement Categorizer API

FastAPI-based REST API for transaction categorization.

## Quick Start

```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run the server
python main.py
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_brain.py -v
```

## Project Structure

```
backend/
├── main.py              # FastAPI app and endpoints
├── brain.py             # Categorization engine
├── run.py               # Development server script
├── requirements.txt     # Dependencies
├── pytest.ini          # Test configuration
├── tests/              # Test files
│   ├── test_brain.py   # Brain logic tests
│   └── test_api.py     # API integration tests
└── sample_data/        # Sample CSV files
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=http://localhost:3000
```

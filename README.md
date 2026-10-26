# Freelancer Statement Categorizer

This application helps freelance or user developers sort their business bank statements for tax purposes. It uses a Python (Django) backend for processing and a Next.js as frontend for the user interface.

## Prerequisites
- Python 3.12
- Django
- Next.js

## How to Run the Backend (Django)
1. Navigate to the backend directory: `cd backend`
2. Create and activate a virtual environment:
   - Windows: `python -m venv venv` and `.\venv\Scripts\activate`
   - Linux/Mac: `python3 -m venv venv` and `source venv/bin/activate`
3. Install dependencies: `pip install django djangorestframework django-cors-headers`
4. Run the server: `python manage.py runserver`
   (The API will run on http://127.0.0.1:8000)

## How to Run the Frontend (Next.js)
1. Open a new terminal and navigate to the frontend directory: `cd frontend`
2. Install dependencies: `npm install`
3. Run the development server: `npm run dev`
4. Open http://localhost:3000 in your browser.

## Usage
Upload a standard CSV bank statement (Date, Description, Amount). The backend will automatically categorize known freelance expenses (like AWS, GitHub, Upwork) and flag unknown transactions for manual review.
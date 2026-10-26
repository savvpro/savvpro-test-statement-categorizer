#!/bin/bash
# Setup script for Statement Categorizer (macOS/Linux)

set -e

echo "==============================================="
echo "Statement Categorizer - Setup Script"
echo "==============================================="
echo ""

# Check Python
echo "[1/5] Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.9+ from https://www.python.org/"
    exit 1
fi
python3 --version
echo ""

# Check Node.js
echo "[2/5] Checking Node.js installation..."
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is not installed"
    echo "Please install Node.js 18+ from https://nodejs.org/"
    exit 1
fi
node --version
echo ""

# Setup Backend
echo "[3/5] Setting up Backend..."
cd backend
echo "Creating virtual environment..."
python3 -m venv venv
echo "Activating virtual environment..."
source venv/bin/activate
echo "Installing Python dependencies..."
pip install -r requirements.txt
echo "Backend setup complete!"
cd ..
echo ""

# Setup Frontend
echo "[4/5] Setting up Frontend..."
cd frontend
echo "Installing Node.js dependencies..."
npm install
echo "Copying environment file..."
if [ ! -f .env.local ]; then
    cp .env.local.example .env.local
    echo "Created .env.local file"
fi
echo "Frontend setup complete!"
cd ..
echo ""

# Done
echo "[5/5] Setup Complete!"
echo ""
echo "==============================================="
echo "Next Steps:"
echo "==============================================="
echo ""
echo "1. Start Backend (in one terminal):"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   python main.py"
echo ""
echo "2. Start Frontend (in another terminal):"
echo "   cd frontend"
echo "   npm run dev"
echo ""
echo "3. Open http://localhost:3000 in your browser"
echo ""
echo "==============================================="

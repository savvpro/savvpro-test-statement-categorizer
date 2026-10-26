@echo off
REM Setup script for Statement Categorizer (Windows)

echo ===============================================
echo Statement Categorizer - Setup Script
echo ===============================================
echo.

REM Check Python
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://www.python.org/
    exit /b 1
)
python --version
echo.

REM Check Node.js
echo [2/5] Checking Node.js installation...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js 18+ from https://nodejs.org/
    exit /b 1
)
node --version
echo.

REM Setup Backend
echo [3/5] Setting up Backend...
cd backend
echo Creating virtual environment...
python -m venv venv
echo Activating virtual environment...
call venv\Scripts\activate
echo Installing Python dependencies...
pip install -r requirements.txt
echo Backend setup complete!
cd ..
echo.

REM Setup Frontend
echo [4/5] Setting up Frontend...
cd frontend
echo Installing Node.js dependencies...
call npm install
echo Copying environment file...
if not exist .env.local (
    copy .env.local.example .env.local
    echo Created .env.local file
)
echo Frontend setup complete!
cd ..
echo.

REM Done
echo [5/5] Setup Complete!
echo.
echo ===============================================
echo Next Steps:
echo ===============================================
echo.
echo 1. Start Backend (in one terminal):
echo    cd backend
echo    venv\Scripts\activate
echo    python main.py
echo.
echo 2. Start Frontend (in another terminal):
echo    cd frontend
echo    npm run dev
echo.
echo 3. Open http://localhost:3000 in your browser
echo.
echo ===============================================
pause

@echo off
echo ========================================================
echo   Starting TaxSort Statement Categorizer...
echo ========================================================

echo [1/2] Launching Python FastAPI Backend on port 8000...
start "TaxSort Backend API" cmd /k "cd backend && py run.py"

timeout /t 2 /nobreak >nul

echo [2/2] Launching React Frontend on port 5173...
start "TaxSort Frontend" cmd /k "cd frontend && npm run dev"

timeout /t 2 /nobreak >nul

echo Opening browser at http://localhost:5173...
start http://localhost:5173

echo ========================================================
echo   TaxSort is running!
echo   Backend:  http://localhost:8000/docs
echo   Frontend: http://localhost:5173
echo ========================================================
pause

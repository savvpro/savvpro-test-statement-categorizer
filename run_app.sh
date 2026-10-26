#!/usr/bin/env bash
echo "Starting TaxSort Statement Categorizer..."

# Launch backend
cd backend && python3 run.py &
BACKEND_PID=$!

# Launch frontend
cd ../frontend && npm run dev &
FRONTEND_PID=$!

echo "TaxSort is running!"
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5173"

trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
wait

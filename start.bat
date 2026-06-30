@echo off
REM Quick start script for KubGU Assistant Backend
REM Usage: start.bat

echo 🚀 KubGU Asistente - Iniciando Backend
echo =======================================
echo.

REM Disable semantic search to avoid initialization crashes on some systems
set DISABLE_SEMANTIC_SEARCH=1

REM Go to backend directory
cd backend

echo Starting FastAPI server on http://localhost:8000
echo Frontend will be at: http://localhost:8000/frontend/
echo.
echo Press Ctrl+C to stop
echo.

python main.py
pause

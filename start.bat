@echo off
title SecureBank RAG Launcher
cd /d "%~dp0"

echo ===================================================
echo   Starting SecureBank RAG (Backend + Frontend)
echo ===================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found at .venv!
    echo Please create it first: python -m venv .venv
    pause
    exit /b 1
)

echo [1/2] Starting FastAPI Backend on http://localhost:8000 ...
start "SecureBank Backend (FastAPI)" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

echo [2/2] Starting Streamlit Frontend on http://localhost:8501 ...
start "SecureBank Frontend (Streamlit)" cmd /k ".venv\Scripts\python.exe -m streamlit run streamlit_app.py --server.port 8501"

echo.
echo ===================================================
echo   Services are running!
echo   Frontend: http://localhost:8501
echo   Backend:  http://localhost:8000 (API Docs: /docs)
echo ===================================================
echo.
timeout /t 3 >nul
start http://localhost:8501
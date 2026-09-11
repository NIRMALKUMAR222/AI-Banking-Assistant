@echo off
title Stop SecureBank RAG
echo Stopping all SecureBank Backend and Frontend processes...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8501" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
echo Done. Ports 8000 and 8501 freed.
pause
@echo off
REM ONGC IntelliAssist Backend Startup Script
REM This script automatically handles port conflicts and starts the backend

echo ============================================
echo ONGC IntelliAssist Backend Startup
echo ============================================
echo.

cd /d "%~dp0"

REM Check if venv exists
if not exist "venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found at venv\Scripts\python.exe
    echo Please run: python -m venv venv
    pause
    exit /b 1
)

REM Start backend with port conflict resolution
venv\Scripts\python.exe start_server.py --port 8000

pause

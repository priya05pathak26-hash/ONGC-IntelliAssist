# ONGC IntelliAssist Backend Startup Script for PowerShell
# This script automatically handles port conflicts and starts the backend

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "ONGC IntelliAssist Backend Startup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Change to script directory
Set-Location $PSScriptRoot

# Check if venv exists
if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "ERROR: Virtual environment not found at venv\Scripts\python.exe" -ForegroundColor Red
    Write-Host "Please run: python -m venv venv" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Start backend with port conflict resolution
& .\venv\Scripts\python.exe start_server.py --port 8000

Read-Host "Press Enter to exit"

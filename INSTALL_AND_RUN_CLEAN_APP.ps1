$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force

if (-not (Test-Path ".env")) {
    Write-Host "ERROR: Paste your .env file into this folder before running." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
& ".\.venv\Scripts\python.exe" -m pip install -r ".\backend\requirements.txt"
& ".\VERIFY_LEDGERFLOW_V202.ps1"
& ".\.venv\Scripts\python.exe" ".\run_app.py"

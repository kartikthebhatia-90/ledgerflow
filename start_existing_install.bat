@echo off
cd /d %~dp0
if not exist .venv\Scripts\python.exe (
  echo Run setup_and_run.bat first.
  pause
  exit /b 1
)
start "" http://127.0.0.1:8000
.venv\Scripts\python.exe run_app.py

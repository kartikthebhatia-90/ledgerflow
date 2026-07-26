@echo off
setlocal
cd /d %~dp0

where py >nul 2>nul
if %errorlevel%==0 (
  set PY=py
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Python 3.11 or newer is required.
    pause
    exit /b 1
  )
  set PY=python
)

if not exist .venv %PY% -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt

if not exist frontend\dist\index.html (
  where npm >nul 2>nul
  if errorlevel 1 (
    echo The prebuilt frontend is missing and Node.js 22+ is not installed.
    pause
    exit /b 1
  )
  pushd frontend
  call npm install
  call npm run build
  popd
)

if not exist .env copy .env.example .env >nul
python run_app.py
pause

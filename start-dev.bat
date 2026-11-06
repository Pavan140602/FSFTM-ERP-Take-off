@echo off
REM Starts FSFTM ERP Take-off: backend on :8000 and frontend on :5173.
REM First-time setup: see SETUP_NEW_PC.md
cd /d "%~dp0"

if not exist ".venv\Scripts\openconstructionerp.exe" (
  echo Backend is not installed yet. Follow steps 3 and 4 in SETUP_NEW_PC.md first.
  pause
  exit /b 1
)
if not exist "frontend\node_modules" (
  echo Frontend is not installed yet. Run:  cd frontend  then  npm ci
  pause
  exit /b 1
)

start "ERP backend :8000" cmd /k ".venv\Scripts\openconstructionerp.exe serve --port 8000"
start "ERP frontend :5173" cmd /k "cd /d frontend && npm run dev"

echo.
echo Starting... wait about 20 seconds, then open http://localhost:5173
timeout /t 20 >nul
start "" http://localhost:5173

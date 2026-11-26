@echo off
REM Starts FSFTM ERP Take-off in FAST mode: one backend process on :8000 that
REM also serves the pre-built frontend (frontend\dist). No Vite dev server, so
REM it uses about 0.7 GB less memory and React runs in its fast production mode.
REM
REM Use this for day-to-day takeoff work. Use start-dev.bat only while changing
REM the code. After pulling new code, run build-frontend.bat once.
cd /d "%~dp0"

if not exist ".venv\Scripts\openconstructionerp.exe" (
  echo Backend is not installed yet. Follow steps 3 and 4 in SETUP_NEW_PC.md first.
  pause
  exit /b 1
)
REM Rebuild automatically when the code changed since the last build
REM (e.g. after "git pull"); the build remembers its version in dist\.build-rev.
set "NEEDBUILD="
if not exist "frontend\dist\index.html" set "NEEDBUILD=1"
for /f %%i in ('git rev-parse HEAD 2^>nul') do set "HEADREV=%%i"
set "BUILTREV="
if exist "frontend\dist\.build-rev" set /p BUILTREV=<"frontend\dist\.build-rev"
if defined HEADREV if not "%HEADREV%"=="%BUILTREV%" set "NEEDBUILD=1"
if defined NEEDBUILD (
  echo The code changed since the last build ^(or it was never built^).
  echo Building the frontend now - this takes a few minutes...
  call "%~dp0build-frontend.bat" nopause
  if not exist "frontend\dist\index.html" (
    echo Build failed - see the messages above.
    pause
    exit /b 1
  )
)

start "ERP (fast mode) :8000" cmd /k ".venv\Scripts\openconstructionerp.exe serve --port 8000"

echo.
echo Starting... wait about 15 seconds, then open http://localhost:8000
timeout /t 15 >nul
start "" http://localhost:8000

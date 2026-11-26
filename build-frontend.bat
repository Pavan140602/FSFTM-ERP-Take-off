@echo off
REM Builds the production frontend into frontend\dist for start-fast.bat.
REM Run it again after editing frontend code locally (start-fast.bat rebuilds
REM by itself after git pull). Skips the full type check (~12 GB RAM; CI does it).
REM
REM Safe: it builds into frontend\dist-new first and only replaces
REM frontend\dist when the build succeeded, so a failed build (for example out
REM of memory) never breaks the working app.
cd /d "%~dp0frontend"
if not exist "node_modules" (
  echo Frontend packages are missing. Run:  cd frontend  then  npm ci
  if not "%1"=="nopause" pause
  exit /b 1
)
echo Building the frontend (a few minutes). Close other apps if memory is low...
if exist "dist-new" rmdir /s /q "dist-new"
set OE_LEAN_BUILD=1
node --max-old-space-size=8192 node_modules\vite\bin\vite.js build --outDir dist-new --emptyOutDir
if errorlevel 1 goto failed
if not exist "dist-new\index.html" goto failed

REM Swap the new build in.
if exist "dist" rmdir /s /q "dist"
ren "dist-new" "dist"
REM Keep the tracked placeholder, and remember which code version this is
REM (start-fast.bat rebuilds automatically when the code changes).
git -C "%~dp0." checkout -- frontend/dist/.placeholder >nul 2>&1
git -C "%~dp0." rev-parse HEAD > "%~dp0frontend\dist\.build-rev" 2>nul
echo.
echo Done. Start the app with start-fast.bat and open http://localhost:8000
if not "%1"=="nopause" pause
exit /b 0

:failed
if exist "dist-new" rmdir /s /q "dist-new"
echo.
echo Frontend build FAILED - the previous build (if any) is unchanged.
echo If it says "out of memory", close Chrome tabs, VS Code and other apps and run it again.
if not "%1"=="nopause" pause
exit /b 1

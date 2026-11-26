@echo off
REM Starts FSFTM ERP Take-off for the TEAM on the same local network (office
REM Wi-Fi / LAN). This PC is the server; teammates open http://<this-PC-IP>:8000
REM in their browser - they install nothing.
REM
REM Differences from start-fast.bat:
REM   * listens on the network (0.0.0.0), not only on this PC;
REM   * uses this PC's own random login secret instead of the public default
REM     one, so nobody on the network can fake a login;
REM   * opens Windows Firewall for port 8000 on PRIVATE networks only.
REM Only use it on a trusted network (office). Never forward port 8000 on the
REM router to the internet.
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\openconstructionerp.exe" (
  echo Backend is not installed yet. Follow steps 3 and 4 in SETUP_NEW_PC.md first.
  pause
  exit /b 1
)

REM -- Build the frontend when the code changed (same check as start-fast.bat).
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

REM -- This PC's own login secret (created once, kept outside the project/git).
set "SECRETDIR=%USERPROFILE%\.openestimate"
set "SECRETFILE=%SECRETDIR%\team-jwt-secret.txt"
if not exist "%SECRETDIR%" mkdir "%SECRETDIR%"
if not exist "%SECRETFILE%" (
  powershell -NoProfile -Command "$b = New-Object byte[] 48; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b); [Convert]::ToBase64String($b) | Set-Content -NoNewline -Encoding ascii '%SECRETFILE%'"
)
set /p JWT_SECRET=<"%SECRETFILE%"
if not defined JWT_SECRET (
  echo Could not create the login secret in %SECRETFILE%.
  pause
  exit /b 1
)

REM -- Windows Firewall: allow port 8000 on private networks (needs admin once).
netsh advfirewall firewall show rule name="FSFTM ERP Takeoff 8000" >nul 2>&1
if errorlevel 1 (
  netsh advfirewall firewall add rule name="FSFTM ERP Takeoff 8000" dir=in action=allow protocol=TCP localport=8000 profile=private >nul 2>&1
  if errorlevel 1 (
    echo.
    echo NOTE: Could not open the firewall automatically ^(needs administrator^).
    echo       Right-click start-team.bat ^> "Run as administrator" once, or
    echo       teammates may not be able to connect.
  )
)

REM -- Warn when Windows treats this network as Public (firewall stays closed).
for /f "usebackq delims=" %%n in (`powershell -NoProfile -Command "Get-NetConnectionProfile | Where-Object { $_.NetworkCategory -eq 'Public' -and $_.InterfaceAlias -notmatch 'VPN|wt0|Surfshark|Tailscale' } | ForEach-Object { $_.Name }"`) do (
  echo.
  echo WARNING: Windows treats the network "%%n" as PUBLIC, so teammates are blocked.
  echo          Settings ^> Network ^& internet ^> Ethernet / Wi-Fi ^> Network profile type ^> Private
  echo          ^(only do this on your trusted office network^), then run start-team.bat again.
)

REM -- Show the address teammates should open.
echo.
echo ================================================================
echo  Teammates on the same network open one of these in their browser:
for /f "usebackq delims=" %%a in (`powershell -NoProfile -Command "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' -and $_.PrefixOrigin -ne 'WellKnown' } | ForEach-Object { '   http://' + $_.IPAddress + ':8000   (' + $_.InterfaceAlias + ')' }"`) do echo %%a
echo  Use the Ethernet / Wi-Fi one - not VPN addresses.
echo  This PC itself: http://localhost:8000
echo  Keep this PC on and this window open while the team works.
echo ================================================================
echo.

start "ERP (team mode) :8000" cmd /k ".venv\Scripts\openconstructionerp.exe serve --host 0.0.0.0 --port 8000"
timeout /t 15 >nul
start "" http://localhost:8000
endlocal

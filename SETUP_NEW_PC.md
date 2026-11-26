# Setting up FSFTM ERP Take-off on another Windows PC

Follow these steps once per PC. After that, run `start-dev.bat` to start the app.

## 1. Install the tools (one time)

| Tool | Version | Download |
|---|---|---|
| Git | any recent | https://git-scm.com/download/win |
| Python | **3.12 or newer** (the main PC uses 3.14) | https://www.python.org/downloads/ (tick **"Add python.exe to PATH"**) |
| Node.js | **24 LTS** (22 or newer works) | https://nodejs.org/ |

Check them in a new PowerShell window:

```powershell
git --version
python --version
node --version
```

## 2. Download the code

```powershell
cd $HOME\Downloads
git clone https://github.com/Pavan140602/FSFTM-ERP-Take-off.git
cd FSFTM-ERP-Take-off
```

## 3. Install the backend (Python)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".\backend[server]"
```

This takes several minutes. It also installs the built-in database, so you
don't need to install PostgreSQL separately.

## 4. Install the frontend (Node)

```powershell
cd frontend
npm ci
cd ..
```

## 5. Settings file (`backend/.env`)

`.env` files are **not** stored on GitHub because they contain passwords.
To use email sending, copy `backend\.env` from the main PC to the same place
on this PC. The app still runs without this file; it just won't send email.

## 6. Start the app

Double-click **`start-dev.bat`** in the project folder, or run it from PowerShell:

```powershell
.\start-dev.bat
```

It opens two windows (backend on port 8000, frontend on port 5173).
Then open **http://localhost:5173** in your browser.

## Getting the latest code later

```powershell
cd $HOME\Downloads\FSFTM-ERP-Take-off
git pull
.\.venv\Scripts\python.exe -m pip install -e ".\backend[server]"
cd frontend; npm ci; cd ..
```

Re-run the two install commands only when `git pull` changed
`backend/pyproject.toml` or `frontend/package-lock.json`. Running them anyway
does no harm.

## Fast mode for everyday takeoff work (recommended)

`start-dev.bat` runs the **development** setup: a Vite dev server (about
0.7 GB of RAM) plus React in its slow debugging mode. That is meant for
changing the code, not for doing takeoffs.

For daily work use **fast mode** instead:

1. Build the frontend once: double-click **`build-frontend.bat`** (a few minutes).
2. Start the app: double-click **`start-fast.bat`**, then open
   **http://localhost:8000** (not 5173).

One backend process serves everything, React runs in production mode (much
smoother on big drawing sets, no double renders), and about 0.7 GB of memory
is freed. VS Code is not needed to run it.

`start-fast.bat` rebuilds by itself when the code version changed (after
`git pull`, or on a fresh clone, where the build is never stored in git), so
after pulling just start it - the first start takes a few minutes longer.
Run `build-frontend.bat` by hand only after editing code locally without
committing. Do not run `start-dev.bat` and `start-fast.bat` at the same time.

**Keeping the PC responsive (16 GB RAM):** close the browser tabs and apps
you are not using while taking off - Chrome, VS Code and other Electron apps
(ChatGPT, Cliq, ...) each hold 0.2-2 GB. Keep big drawing sets in single-page
view, close PDF tabs you no longer need, and turn split view off when you are
not comparing. If you regularly work with 70+ page sets, 32 GB of RAM is the
upgrade that helps most.

## Sharing with the team on the office network

One PC runs the app; everyone else on the same network uses it in their
browser and installs nothing. All projects, drawings and markups live on that
one PC, so everyone sees the same data.

On the **server PC** (the one with the code):

1. Make Windows treat the office network as **Private** (only your trusted
   office network): Settings > Network & internet > Ethernet (or Wi-Fi) >
   Network profile type > **Private**.
2. The first time, right-click **`start-team.bat`** > **Run as administrator**
   (it opens port 8000 in Windows Firewall for private networks). After that a
   normal double-click is enough.
3. The window shows the address to share, for example
   `http://192.168.1.189:8000 (Ethernet)`. Use the Ethernet / Wi-Fi address,
   not a VPN one.
4. Keep that PC switched on (and not sleeping) and the window open while the
   team works. Use `start-team.bat` *instead of* `start-fast.bat`, not both.

On **each teammate's PC**: open that address in Chrome or Edge, sign in (or
register; an admin then activates the new account in the user settings).

Notes:

- `start-team.bat` uses a random login secret stored on the server PC in
  `%USERPROFILE%\.openestimate\team-jwt-secret.txt` (not in git). Do not share
  that file. Deleting it signs everyone out and makes a new one.
- If the server PC's address changes after a restart, ask IT for a fixed
  address (DHCP reservation) so the link stays the same.
- PDF rendering happens in each person's browser, so the server PC mostly
  serves files and saves markups; 16 GB is enough for a small team.
- Never forward port 8000 on the router to the internet. For access from
  outside the office use a VPN.

## Default settings

A fresh browser opens in **English (US)**, **imperial units**, **US dollars**
and the **dark theme**. Each person can still change these (language in the
header, theme toggle, Settings > Regional). A browser that already used the
app keeps its saved choices; to get the defaults back, open the browser
console (F12) on http://localhost:5173 and run
`localStorage.removeItem('oe_theme'); localStorage.removeItem('oe_preferences'); localStorage.removeItem('i18nextLng'); location.reload()`.

## Check your changes before pushing (same checks as GitHub CI)

Run these from the project folder. Each should finish with no errors.

```powershell
# Frontend: lint, then the PDF Measurements tests
cd frontend
npx eslint src/modules/pdf-takeoff src/features/takeoff
npx vitest run src/modules/pdf-takeoff src/features/takeoff
cd ..

# Backend: install the dev tools once, then lint, format check and tests
.\.venv\Scripts\python.exe -m pip install -e ".\backend[dev]"
cd backend
..\.venv\Scripts\ruff.exe check app/modules/takeoff tests/unit
..\.venv\Scripts\ruff.exe format --check app/modules/takeoff tests/unit
..\.venv\Scripts\python.exe -m pytest tests/unit -k takeoff -q
cd ..
```

The full frontend build (`npm run build` in `frontend`) also type-checks
everything; it needs about 12 GB of free RAM.

## What is NOT copied by GitHub

- **Your projects, drawings and takeoff data.** These are stored in the
  database folder `C:\Users\<you>\.openestimate\`, not in the code. A new PC
  starts with an empty database, so you need to sign up or log in again there.
  To bring the data across, stop the app on both PCs and copy that whole
  folder over.
- Some take-off settings are saved in the browser (localStorage) and stay
  on each PC's browser.
- `node_modules` and `.venv` are created by steps 3 and 4.

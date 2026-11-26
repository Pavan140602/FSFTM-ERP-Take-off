# Setting up FSFTM ERP Take-off on another Windows PC

Follow these steps once per PC. After that, start the app as in step 6.

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

Open the project folder in VS Code and start two terminals:

```powershell
# Terminal 1 - backend on port 8000
.\.venv\Scripts\openconstructionerp.exe serve --port 8000
```

```powershell
# Terminal 2 - frontend on port 5173
cd frontend
npm run dev
```

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

**Keeping the PC responsive (16 GB RAM):** close the browser tabs and apps
you are not using while taking off - Chrome, VS Code and other Electron apps
(ChatGPT, Cliq, ...) each hold 0.2-2 GB. Keep big drawing sets in single-page
view, close PDF tabs you no longer need, and turn split view off when you are
not comparing. If you regularly work with 70+ page sets, 32 GB of RAM is the
upgrade that helps most.

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

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

## What is NOT copied by GitHub

- **Your projects, drawings and takeoff data.** These are stored in the
  database folder `C:\Users\<you>\.openestimate\`, not in the code. A new PC
  starts with an empty database, so you need to sign up or log in again there.
  To bring the data across, stop the app on both PCs and copy that whole
  folder over.
- Some take-off settings are saved in the browser (localStorage) and stay
  on each PC's browser.
- `node_modules` and `.venv` are created by steps 3 and 4.

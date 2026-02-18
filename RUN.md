# How to Run CrucibAI

---

## Your local URLs

| What        | URL |
|------------|-----|
| **App (open this)** | **http://localhost:3000** |
| Backend API        | http://localhost:8000    |
| API health check   | http://localhost:8000/api/health |

Start backend + frontend first (see below), then open **http://localhost:3000** in your browser.

---

## One command (Windows)

From the repo root in PowerShell:

```powershell
.\run-dev.ps1
```

This starts the backend in a new window and the frontend in the current terminal. Open **http://localhost:3000** when the frontend compiles.

---

## Quick start (two terminals)

1. **Backend (API)** — in a terminal:
   ```powershell
   cd backend
   python -m uvicorn server:app --host 127.0.0.1 --port 8000
   ```
   Requires: MongoDB running (`MONGO_URL` in `backend/.env`), and `DB_NAME` set.

2. **Frontend** — in another terminal:
   ```powershell
   cd frontend
   npm start
   ```
   Opens at **http://localhost:3000**.

3. **Open in browser:** http://localhost:3000

---

## If something isn’t working

- **“localhost refused to connect”**  
  - **Open the full URL:** **http://localhost:3000** (frontend) or **http://localhost:8000** (backend). Do not use `http://localhost` alone (nothing runs on port 80).  
  - Make sure you started both the backend and frontend (two terminals), or run **`.\run-dev.ps1`** from the repo root (PowerShell).

- **“Something is already running on port 3000”**  
  - A dev server is probably already running. Open **http://localhost:3000**.  
  - To restart: close the other terminal or stop the process using port 3000, then run `npm start` again in `frontend`.

- **“Port 8000 already in use”**  
  - Backend may already be running. Try **http://localhost:8000/api/health**.  
  - To use another port:  
    `python -m uvicorn server:app --host 127.0.0.1 --port 8001`  
    Then in `frontend/.env` set:  
    `REACT_APP_BACKEND_URL=http://localhost:8001`

- **Frontend fails with `ajv` or ESLint / "defaultMeta" / html-webpack-plugin errors**  
  - Postinstall patches disable the ESLint webpack plugin in `react-scripts`.  
  - If you still see the error: **re-run the patch and clear cache**, then start again:
    ```powershell
    cd frontend
    node scripts/patch-ajv-formats.js
    rmdir /s /q node_modules\.cache 2>nul
    npm start
    ```
  - Recommended: **Node 18 or 20 LTS** (see `frontend/.nvmrc`).

- **"Backend unavailable" in the app footer**  
  - Backend must be running at the URL in `REACT_APP_BACKEND_URL` (default `http://localhost:8000`).  
  - Click **Retry** in the footer to re-check, or restart the backend and refresh.  
  - See **BACKEND_FRONTEND_CONNECTION.md** for full connection analysis and endpoint map.

- **Backend won’t start (e.g. MONGO_URL)**  
  - Copy `backend/.env.example` to `backend/.env` and set at least:
    - `MONGO_URL=mongodb://localhost:27017` (or your MongoDB URL)
    - `DB_NAME=crucibai`

# Run CrucibAI locally

## Quick start (two terminals)

1. **Terminal 1 – backend** (must run from repo so script finds backend folder)
   ```powershell
   cd c:\Users\benxp\CrucibAI\NEWREUCIB
   .\start-local.ps1
   ```
   Or from backend folder (ensures .env is loaded):
   ```powershell
   cd c:\Users\benxp\CrucibAI\NEWREUCIB\backend
   python run_local.py
   ```
   Wait until you see: `Uvicorn running on http://0.0.0.0:8000`.

2. **Terminal 2 – frontend**
   ```powershell
   cd c:\Users\benxp\CrucibAI\NEWREUCIB
   .\start-frontend.ps1
   ```
   Or: `cd frontend` then `npm run start` or `yarn start`.  
   Open **http://localhost:3000** when it’s ready.

3. **Browser** – use **http://localhost:3000** only.

## If something fails

- **"Google sign-in is not configured"**  
  Backend didn’t load `.env`. Start the backend from the `backend` folder (so `backend\.env` is next to the process).

- **"Cannot reach server" / blank after Google sign-in**  
  Backend must be running on port 8000. In a new terminal run:
  ```powershell
  cd c:\Users\benxp\CrucibAI\NEWREUCIB\backend
  python -m uvicorn server:app --reload --host 0.0.0.0 --port 8000
  ```
  Then try again at http://localhost:3000.

- **"localhost refused to connect" after Google login**  
  You’re being sent to the right place only if the app runs on **port 3000**.  
  Start the frontend from the `frontend` folder and use **http://localhost:3000**.

- **Google OAuth error / redirect_uri_mismatch**  
  In [Google Cloud Console](https://console.cloud.google.com/apis/credentials) → your OAuth 2.0 Client → **Authorized redirect URIs**, add:
  ```text
  http://localhost:8000/api/auth/google/callback
  ```
  (Use your backend URL and port; no trailing slash.)

- **MongoDB**  
  Backend expects MongoDB at `mongodb://localhost:27017`. Start MongoDB locally or set `MONGO_URL` in `backend\.env`.

## Ports

| Service  | URL                     |
|----------|-------------------------|
| Frontend | http://localhost:3000   |
| Backend  | http://localhost:8000   |

Config: `backend\.env` has `FRONTEND_URL=http://localhost:3000` and `CORS_ORIGINS=http://localhost:3000`; `frontend\.env` has `PORT=3000` and `REACT_APP_BACKEND_URL=http://localhost:8000`.

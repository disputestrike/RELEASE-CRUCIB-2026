# Backend only. Railway/Render: prefer Dockerfile; if using Procfile, python3 + uvicorn required.
web: cd backend && python3 -m uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}

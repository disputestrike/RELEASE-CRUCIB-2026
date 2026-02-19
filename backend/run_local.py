#!/usr/bin/env python3
"""Run backend from backend directory so .env is always found. Use: python run_local.py"""
import os
import sys
from pathlib import Path

def main():
    backend_dir = Path(__file__).resolve().parent
    os.chdir(backend_dir)
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    from dotenv import load_dotenv
    load_dotenv(backend_dir / ".env", override=True)

    print("Backend .env loaded from:", backend_dir / ".env")
    print("FRONTEND_URL:", os.environ.get("FRONTEND_URL", "(not set)"))
    print("CORS_ORIGINS:", os.environ.get("CORS_ORIGINS", "(not set)"))
    print("Starting uvicorn on http://0.0.0.0:8000 ...")

    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()

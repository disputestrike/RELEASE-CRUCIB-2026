from pathlib import Path
import os

# In production (Docker): backend/ is at /app/backend/, so __file__ = /app/backend/config.py
# ROOT_DIR = /app/backend, STATIC_DIR = /app/backend/static (where frontend build is copied)
ROOT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = ROOT_DIR.parent / "workspaces"
if not WORKSPACE_ROOT.exists():
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)


from pathlib import Path
import os

ROOT_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = ROOT_DIR / "workspaces"
if not WORKSPACE_ROOT.exists():
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)


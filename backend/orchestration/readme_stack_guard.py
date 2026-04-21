"""
Post-process generated README.md so run instructions match the actual workspace.

Some model runs paste Django-style boilerplate (manage.py runserver, migrate,
createsuperuser) into README even when the artifact tree is Vite + FastAPI-style.
We detect the real stack from files on disk and, when there is a mismatch,
rewrite the README with a correct \"Run\" section and strip obvious Django
command lines.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_DJANGO_BOILERPLATE = re.compile(
    r"\bmanage\.py\b|\brunserver\b|\bcreatesuperuser\b|\bmakemigrations\b|\bmigrate\b",
    re.IGNORECASE,
)


def infer_workspace_stack(root: Path) -> str:
    """Best-effort stack label from files present under workspace root."""
    root = root.resolve()
    if (root / "manage.py").is_file():
        return "django"
    pkg = root / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError, TypeError):
            data = {}
        deps = {
            **(data.get("dependencies") or {}),
            **(data.get("devDependencies") or {}),
        }
        scripts = data.get("scripts") or {}
        if "vite" in deps or any("vite" in str(v).lower() for v in scripts.values()):
            return "vite"
        if "react-scripts" in deps:
            return "cra"
    if (root / "backend" / "main.py").is_file() or (root / "server.py").is_file():
        return "fastapi"
    return "unknown"


def _run_section(root: Path, stack: str) -> str:
    lines = [
        "## Run",
        "",
        "_This section was aligned to files present in this workspace (CrucibAI export guard)._",
        "",
    ]
    if stack == "vite":
        lines += [
            "**Frontend (Vite):**",
            "",
            "```bash",
            "npm install",
            "npm run dev",
            "```",
            "",
        ]
        if (root / "backend" / "main.py").is_file():
            lines += [
                "**Backend (example FastAPI layout under `backend/`):**",
                "",
                "```bash",
                "cd backend",
                "pip install -r requirements.txt   # if requirements.txt exists",
                "uvicorn main:app --reload --port 8000   # adjust if your app object differs",
                "```",
                "",
            ]
        elif (root / "server.py").is_file():
            lines += [
                "**Python API:** this tree may use root `server.py` as the entry; use the "
                "imports and comments in that file, or run with `uvicorn` as documented there.",
                "",
            ]
    elif stack == "django":
        lines += [
            "```bash",
            "python manage.py migrate",
            "python manage.py runserver",
            "```",
            "",
        ]
    elif stack == "fastapi":
        lines += [
            "```bash",
            "pip install -r requirements.txt   # when present",
            "uvicorn main:app --reload   # adjust module:app to your entry file",
            "```",
            "",
        ]
    else:
        lines += [
            "Inspect `package.json` scripts and any Python entry under `backend/` or `server.py`.",
            "",
        ]
    return "\n".join(lines)


def _strip_django_command_lines(text: str) -> str:
    out: list[str] = []
    for line in text.splitlines():
        low = line.lower()
        if re.match(r"^\s*python\s+manage\.py\s+", line, re.IGNORECASE):
            continue
        if "manage.py" in low and any(
            k in low
            for k in ("runserver", "migrate", "createsuperuser", "makemigrations")
        ):
            continue
        if re.match(r"^\s*django-admin\s+", line, re.IGNORECASE):
            continue
        out.append(line)
    return "\n".join(out).strip()


def sanitize_readme_for_workspace(root: Path) -> bool:
    """
    If README looks like Django runbook but the tree is not Django, fix it.
    Returns True if README.md was rewritten.
    """
    readme = root / "README.md"
    if not readme.is_file():
        return False
    try:
        if readme.stat().st_size > 500_000:
            return False
        text = readme.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False

    stack = infer_workspace_stack(root)
    if stack == "django":
        return False
    if not _DJANGO_BOILERPLATE.search(text):
        return False

    body = _strip_django_command_lines(text)
    banner = (
        "<!-- crucibai-readme-guard: removed Django-style commands that did not match "
        "this workspace's detected stack. -->\n\n"
    )
    new_text = banner + _run_section(root, stack) + "\n---\n\n" + body
    try:
        readme.write_text(new_text, encoding="utf-8")
        return True
    except OSError as e:
        logger.warning("readme_stack_guard: could not write README: %s", e)
        return False

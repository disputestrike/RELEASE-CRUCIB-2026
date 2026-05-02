"""Import Doctor.

Deterministic validation for user-supplied code before CrucibAI continues a
build from ZIP/Git/paste content. This module does not execute imported code;
it reconstructs enough project facts to decide whether the workspace can enter
the normal build/preview/BIV pipeline.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any, Dict, Mapping

from .build_integrity_validator import _walk_text_files, validate_workspace_integrity


def _read_json(files: Mapping[str, str], path: str) -> Dict[str, Any]:
    try:
        return json.loads(files.get(path, "") or "{}")
    except json.JSONDecodeError:
        return {"__invalid_json__": True}


def detect_package_manager(files: Mapping[str, str]) -> str:
    if "pnpm-lock.yaml" in files:
        return "pnpm"
    if "yarn.lock" in files:
        return "yarn"
    if "package-lock.json" in files:
        return "npm"
    if "requirements.txt" in files or "pyproject.toml" in files:
        return "python"
    return "unknown"


def detect_framework(files: Mapping[str, str]) -> str:
    pkg = _read_json(files, "package.json")
    deps = {
        **(pkg.get("dependencies") or {}),
        **(pkg.get("devDependencies") or {}),
    } if isinstance(pkg, dict) else {}
    paths = "\n".join(files).lower()
    dep_names = {str(k).lower() for k in deps}
    if "expo" in dep_names or "app.json" in files or "eas.json" in files:
        return "expo_react_native"
    if "next" in dep_names or "app/page.tsx" in files or "pages/_app.tsx" in files:
        return "nextjs"
    if "vite" in dep_names or "vite.config.ts" in files or "vite.config.js" in files:
        if "react" in dep_names:
            return "react_vite"
        return "vite"
    if "react" in dep_names or "src/App.jsx".lower() in paths or "src/App.tsx".lower() in paths:
        return "react"
    if "fastapi" in "\n".join(files.values()).lower() or "requirements.txt" in files:
        return "fastapi_or_python"
    return "unknown"


def detect_entrypoints(files: Mapping[str, str]) -> Dict[str, bool]:
    return {
        "package_json": "package.json" in files,
        "html_root": "index.html" in files or "client/index.html" in files,
        "react_main": any(p in files for p in ("src/main.jsx", "src/main.tsx", "client/src/main.jsx", "client/src/main.tsx")),
        "react_app": any(p in files for p in ("src/App.jsx", "src/App.tsx", "client/src/App.jsx", "client/src/App.tsx")),
        "expo_app": "App.tsx" in files or "App.jsx" in files or "expo-mobile/App.tsx" in files,
        "python_app": any(p in files for p in ("main.py", "app/main.py", "backend/main.py", "backend/app/main.py")),
    }


def validate_zip_archive(zip_path: str, *, max_files: int = 5000, max_uncompressed_bytes: int = 200_000_000) -> Dict[str, Any]:
    path = Path(zip_path)
    issues = []
    if not path.exists() or not path.is_file():
        return {"passed": False, "issues": ["ZIP file does not exist."], "file_count": 0, "total_uncompressed_bytes": 0}
    try:
        with zipfile.ZipFile(path) as zf:
            infos = zf.infolist()
            total = sum(max(0, info.file_size) for info in infos)
            for info in infos:
                name = info.filename.replace("\\", "/")
                if name.startswith("/") or name.startswith("../") or "/../" in name:
                    issues.append(f"Unsafe ZIP path: {info.filename}")
                    break
            if len(infos) > max_files:
                issues.append(f"ZIP has too many entries: {len(infos)} > {max_files}")
            if total > max_uncompressed_bytes:
                issues.append(f"ZIP is too large after extraction: {total} bytes")
            return {
                "passed": not issues,
                "issues": issues,
                "file_count": len(infos),
                "total_uncompressed_bytes": total,
                "sample_files": [info.filename for info in infos[:20]],
            }
    except zipfile.BadZipFile:
        return {"passed": False, "issues": ["Invalid ZIP file."], "file_count": 0, "total_uncompressed_bytes": 0}


def validate_imported_workspace(workspace_path: str, *, goal: str = "") -> Dict[str, Any]:
    files = _walk_text_files(workspace_path, max_files=1000)
    issues = []
    if not files:
        issues.append("Imported workspace has no readable source/config files.")

    package_manager = detect_package_manager(files)
    framework = detect_framework(files)
    entrypoints = detect_entrypoints(files)
    pkg = _read_json(files, "package.json")
    scripts = pkg.get("scripts") if isinstance(pkg, dict) else {}

    if framework == "unknown":
        issues.append("Could not detect framework from imported workspace.")
    if package_manager == "unknown" and "package.json" in files:
        issues.append("package.json exists but no lockfile/package manager signal was found.")
    if "package.json" in files and not (isinstance(scripts, dict) and (scripts.get("build") or scripts.get("dev") or scripts.get("start"))):
        issues.append("package.json lacks build/dev/start scripts.")
    if framework in {"react_vite", "react", "nextjs"} and not (entrypoints["react_main"] or entrypoints["react_app"]):
        issues.append("Frontend import lacks a React entry/root component.")
    if framework == "expo_react_native" and not entrypoints["expo_app"]:
        issues.append("Expo import lacks App.tsx/App.jsx entry.")

    repair_suggestions = []
    if "package.json" in files and package_manager in {"npm", "unknown"}:
        repair_suggestions.append("Run npm install, then npm run build or npm run dev.")
    elif package_manager == "pnpm":
        repair_suggestions.append("Run pnpm install --frozen-lockfile, then pnpm build.")
    elif package_manager == "yarn":
        repair_suggestions.append("Run yarn install --frozen-lockfile, then yarn build.")
    if framework == "unknown":
        repair_suggestions.append("Ask import repair agents to identify stack and create a FILE_CONTRACT_MAP.md.")

    biv_result = validate_workspace_integrity(workspace_path, goal=goal, phase="structure")
    return {
        "passed": not issues and not biv_result.get("hard_block"),
        "issues": issues,
        "framework": framework,
        "package_manager": package_manager,
        "entrypoints": entrypoints,
        "repair_suggestions": repair_suggestions,
        "biv_result": {
            "passed": biv_result.get("passed"),
            "score": biv_result.get("score"),
            "profile": biv_result.get("profile"),
            "issues": biv_result.get("issues", [])[:20],
            "retry_targets": biv_result.get("retry_targets", []),
        },
    }

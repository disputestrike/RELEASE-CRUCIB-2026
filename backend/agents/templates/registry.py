"""
Template Registry for CrucibAI multi-language code generation.

Maps (language, framework) identifiers to template provider callables.
Each provider is a function of type (goal: str, project_name: str) -> Dict[str, str]
that returns a mapping of filename -> complete file content.
"""

import re
from typing import Callable, Dict, List, Optional

from backend.agents.templates.python_fastapi import generate_python_fastapi
from backend.agents.templates.node_express import generate_node_express
from backend.agents.templates.react_vite import generate_react_vite
from backend.agents.templates.python_cli import generate_python_cli
from backend.agents.templates.cpp_cmake import generate_cpp_cmake
from backend.agents.templates.go_gin import generate_go_gin
from backend.agents.templates.rust_axum import generate_rust_axum

# ---------------------------------------------------------------------------
# Type alias
# ---------------------------------------------------------------------------
TemplateProvider = Callable[[str, str], Dict[str, str]]

# ---------------------------------------------------------------------------
# Language/framework hint maps used by select_template
# ---------------------------------------------------------------------------
LANGUAGE_HINTS: Dict[str, List[str]] = {
    "python": ["python", "django", "flask", "fastapi", "pip", "pyproject"],
    "javascript": ["javascript", "node.js", "nodejs", "node", "express", "npm"],
    "typescript": ["typescript", "react", "vite", "angular", "vue", "next.js", "nextjs"],
    "go": ["go ", "golang", " go.", " go/", "gin", "golang"],
    "rust": ["rust", "cargo", "rustc", "axum", "tokio"],
    "cpp": ["c++", "cpp", "cmake", "gcc", "clang", "g++"],
}

FRAMEWORK_HINTS: Dict[str, List[str]] = {
    "fastapi": ["fastapi"],
    "express": ["express"],
    "react+vite": ["react", "vite", "react+vite"],
    "gin": ["gin"],
    "axum": ["axum"],
    "cmake": ["cmake", "c++", "cpp"],
    "cli": ["cli", "command line", "command-line", "console tool", "script"],
}

# ---------------------------------------------------------------------------
# Template Registry
# ---------------------------------------------------------------------------
TEMPLATE_REGISTRY: Dict[str, Dict] = {
    "python_fastapi": {
        "id": "python_fastapi",
        "language": "python",
        "framework": "fastapi",
        "confidence": 0.95,
        "build_command": "pip install -r backend/requirements.txt",
        "run_command": "uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload",
        "files": generate_python_fastapi,
        "required_files": [
            "backend/main.py",
            "backend/models.py",
            "backend/auth.py",
            "backend/requirements.txt",
        ],
        "validator": "python",
    },
    "react_vite": {
        "id": "react_vite",
        "language": "typescript",
        "framework": "react+vite",
        "confidence": 0.90,
        "build_command": "npm install && npm run build",
        "run_command": "npm run dev",
        "files": generate_react_vite,
        "required_files": [
            "package.json",
            "vite.config.js",
            "index.html",
            "src/main.jsx",
            "src/App.jsx",
        ],
        "validator": "node",
    },
    "node_express": {
        "id": "node_express",
        "language": "javascript",
        "framework": "express",
        "confidence": 0.80,
        "build_command": "cd backend && npm install",
        "run_command": "cd backend && node server.js",
        "files": generate_node_express,
        "required_files": [
            "backend/server.js",
            "backend/routes/api.js",
            "backend/package.json",
        ],
        "validator": "node",
    },
    "python_cli": {
        "id": "python_cli",
        "language": "python",
        "framework": "cli",
        "confidence": 0.85,
        "build_command": "pip install -r requirements.txt && pip install -e .",
        "run_command": f"{{cli_command}}",
        "files": generate_python_cli,
        "required_files": [
            "cli/main.py",
            "cli/utils.py",
            "cli/models.py",
            "requirements.txt",
            "pyproject.toml",
        ],
        "validator": "python",
    },
    "go_gin": {
        "id": "go_gin",
        "language": "go",
        "framework": "gin",
        "confidence": 0.50,
        "build_command": "go mod tidy && go build -o bin/server .",
        "run_command": "./bin/server",
        "files": generate_go_gin,
        "required_files": [
            "main.go",
            "handlers/handlers.go",
            "models/models.go",
            "go.mod",
        ],
        "validator": "go",
    },
    "rust_axum": {
        "id": "rust_axum",
        "language": "rust",
        "framework": "axum",
        "confidence": 0.40,
        "build_command": "cargo build --release",
        "run_command": "cargo run --release",
        "files": generate_rust_axum,
        "required_files": [
            "Cargo.toml",
            "src/main.rs",
            "src/handlers.rs",
            "src/models.rs",
        ],
        "validator": "rust",
    },
    "cpp_cmake": {
        "id": "cpp_cmake",
        "language": "cpp",
        "framework": "cmake",
        "confidence": 0.45,
        "build_command": "mkdir -p build && cd build && cmake .. && make",
        "run_command": "./build/calculator_app",
        "files": generate_cpp_cmake,
        "required_files": [
            "CMakeLists.txt",
            "src/main.cpp",
            "src/calculator.cpp",
            "include/calculator.h",
        ],
        "validator": "cpp",
    },
}


def list_templates() -> List[Dict]:
    """Return a list of all registered template metadata dicts."""
    return [
        {
            "id": entry["id"],
            "language": entry["language"],
            "framework": entry["framework"],
            "confidence": entry["confidence"],
        }
        for entry in TEMPLATE_REGISTRY.values()
    ]


def _extract_language(goal: str) -> Optional[str]:
    """Best-effort language extraction from the goal text."""
    goal_lower = goal.lower()
    best_lang: Optional[str] = None
    best_count = 0
    for lang, hints in LANGUAGE_HINTS.items():
        count = sum(1 for hint in hints if hint in goal_lower)
        if count > best_count:
            best_count = count
            best_lang = lang
    return best_lang


def _extract_framework(goal: str) -> Optional[str]:
    """Best-effort framework extraction from the goal text."""
    goal_lower = goal.lower()
    best_fw: Optional[str] = None
    best_count = 0
    for fw, hints in FRAMEWORK_HINTS.items():
        count = sum(1 for hint in hints if hint in goal_lower)
        if count > best_count:
            best_count = count
            best_fw = fw
    return best_fw


def select_template(
    goal: str,
    explicit_language: Optional[str] = None,
    explicit_framework: Optional[str] = None,
) -> Dict:
    """
    Select the best-matching template entry from the registry.

    Resolution order:
    1. If *explicit_language* and *explicit_framework* are given, match exactly.
    2. If only one is given, use it plus hint extraction for the other.
    3. Parse the *goal* for language/framework hints.
    4. Default to ``python_fastapi`` if nothing matches.

    Returns the full template registry dict (with ``files`` callable).
    Raises ``ValueError`` if no match is found.
    """
    # ---- explicit overrides -------------------------------------------------
    if explicit_language or explicit_framework:
        lang = (explicit_language or "").lower()
        fw = (explicit_framework or "").lower()
        if lang and fw:
            # Try exact match on both
            for entry in TEMPLATE_REGISTRY.values():
                if entry["language"] == lang and entry["framework"] == fw:
                    return entry
            raise ValueError(
                f"No template found for language={lang!r}, framework={fw!r}. "
                f"Available: {[e['id'] for e in TEMPLATE_REGISTRY.values()]}"
            )
        # One of them is None — fill in the other
        detected_lang = lang or _extract_language(goal) or "python"
        detected_fw = fw or _extract_framework(goal) or "fastapi"
        for entry in TEMPLATE_REGISTRY.values():
            if entry["language"] == detected_lang and entry["framework"] == detected_fw:
                return entry
        # Loosen to language-only match
        if lang:
            for entry in TEMPLATE_REGISTRY.values():
                if entry["language"] == lang:
                    return entry
        if fw:
            for entry in TEMPLATE_REGISTRY.values():
                if entry["framework"] == fw:
                    return entry

    # ---- hint-based selection -----------------------------------------------
    detected_language = _extract_language(goal)
    detected_framework = _extract_framework(goal)

    # If both detected, try combined match
    if detected_language and detected_framework:
        for entry in TEMPLATE_REGISTRY.values():
            if (
                entry["language"] == detected_language
                and entry["framework"] == detected_framework
            ):
                return entry

    # Language-only match
    if detected_language:
        for entry in TEMPLATE_REGISTRY.values():
            if entry["language"] == detected_language:
                return entry

    # Framework-only match
    if detected_framework:
        for entry in TEMPLATE_REGISTRY.values():
            if entry["framework"] == detected_framework:
                return entry

    # ---- default ------------------------------------------------------------
    return TEMPLATE_REGISTRY["python_fastapi"]

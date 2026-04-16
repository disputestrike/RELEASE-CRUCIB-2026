from __future__ import annotations

import ast
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _is_scanned_source(path: Path) -> bool:
    rel = path.relative_to(BACKEND_ROOT).as_posix()
    if not rel.endswith(".py"):
        return False
    if "/tests/" in f"/{rel}" or rel.startswith("tests/"):
        return False
    if "/__pycache__/" in f"/{rel}" or "/.pytest_cache" in f"/{rel}":
        return False
    if path.name.startswith("test_"):
        return False
    if path.name.endswith(".backup_20260302_173607"):
        return False
    return True


_LEGACY_EXECUTOR_PARTS = {
    "legacy_a": "auto",
    "legacy_b": "runner",
    "legacy_c": "dag",
    "legacy_d": "engine",
    "legacy_e": "agent",
    "legacy_f": "orchestrator",
}


def _legacy_name(*parts: str) -> str:
    return "_".join(_LEGACY_EXECUTOR_PARTS[p] for p in parts)


def _legacy_path(*segments: str) -> str:
    return "/".join(segments)


ALLOWED_PATTERN_FILES = {
    "agent.run": {
        "services/runtime/runtime_engine.py",
    },
    "execute_tool": {
        "services/runtime/runtime_engine.py",
        "tool_executor.py",
    },
}

DELETED_FILES = {
    _legacy_path("orchestration", _legacy_name("legacy_c", "legacy_d") + ".py"),
    _legacy_path("orchestration", _legacy_name("legacy_a", "legacy_b") + ".py"),
    _legacy_path("orchestration", _legacy_name("legacy_e", "legacy_f") + ".py"),
    _legacy_name("legacy_e", "legacy_f") + ".py",
}

FORBIDDEN_IMPORT_TARGETS = {
    ".".join(["orchestration", _legacy_name("legacy_c", "legacy_d")]),
    ".".join(["orchestration", _legacy_name("legacy_a", "legacy_b")]),
    ".".join(["orchestration", _legacy_name("legacy_e", "legacy_f")]),
    _legacy_name("legacy_e", "legacy_f"),
}

FORBIDDEN_SYMBOLS = {
    "build_" + _legacy_name("legacy_c", "legacy_d") + "_from_plan",
    "_".join(["run", "job", "to", "completion"]),
    "run_" + _legacy_name("legacy_a", "legacy_b"),
    "_".join(["is", "runtime", "active"]),
    "execute_workflow",
}


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        return f"{func.value.id}.{func.attr}"
    return None


def test_backend_has_no_forbidden_execution_references():
    violations: list[str] = []

    for rel in DELETED_FILES:
        if (BACKEND_ROOT / rel).exists():
            violations.append(f"{rel}: deleted legacy module still exists")

    for path in BACKEND_ROOT.rglob("*.py"):
        if not _is_scanned_source(path):
            continue

        rel = path.relative_to(BACKEND_ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(text, filename=rel)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in FORBIDDEN_IMPORT_TARGETS:
                        violations.append(
                            f"{rel}:{getattr(node, 'lineno', '?')}: forbidden import {alias.name}"
                        )
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module in FORBIDDEN_IMPORT_TARGETS:
                    violations.append(
                        f"{rel}:{getattr(node, 'lineno', '?')}: forbidden from-import {module}"
                    )
                for alias in node.names:
                    if alias.name in FORBIDDEN_SYMBOLS:
                        violations.append(
                            f"{rel}:{getattr(node, 'lineno', '?')}: forbidden import symbol {alias.name}"
                        )
            if not isinstance(node, ast.Call):
                continue
            name = _call_name(node)
            if not name:
                continue
            if name not in ALLOWED_PATTERN_FILES:
                continue
            if rel in ALLOWED_PATTERN_FILES[name]:
                continue
            violations.append(f"{rel}:{getattr(node, 'lineno', '?')}: forbidden call {name}")

            if name in FORBIDDEN_SYMBOLS:
                violations.append(f"{rel}:{getattr(node, 'lineno', '?')}: forbidden symbol call {name}")

        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in FORBIDDEN_SYMBOLS:
                violations.append(f"{rel}:{getattr(node, 'lineno', '?')}: forbidden symbol {node.id}")

    assert not violations, "\n".join(violations)


def test_global_execution_authority_is_centralized():
    required_imports = {
        "tool_executor.py",
        "agents/base_agent.py",
        "services/llm_service.py",
        "services/runtime/runtime_engine.py",
    }

    missing: list[str] = []
    for rel in required_imports:
        text = (BACKEND_ROOT / rel).read_text(encoding="utf-8", errors="replace")
        if "require_runtime_authority" not in text:
            missing.append(rel)

    assert not missing, f"Missing centralized authority import/use: {missing}"
"""Architecture guardrails for runtime/workspace/journal ownership.

This script is a merge gate. It fails fast when core ownership boundaries
drift away from the intended single-path architecture.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable, List


BACKEND_ROOT = Path(__file__).resolve().parents[1]

ALLOWED_RUN_TASK_LOOP_CALLERS = {
    Path("services/runtime/runtime_engine.py"),
    Path("services/brain_layer.py"),
}

ALLOWED_WORKSPACE_ROOT_DEFINERS = {
    Path("project_state.py"),
    Path("server.py"),
}

EXPECTED_WORKSPACE_ROOT_IMPORTERS = {
    Path("services/runtime/runtime_engine.py"),
    Path("services/runtime/task_store.py"),
    Path("services/runtime/virtual_fs.py"),
    Path("services/runtime/memory_graph.py"),
    Path("services/session_journal.py"),
    Path("orchestration/runtime_state.py"),
    Path("tool_executor.py"),
}

ALLOWED_APPEND_ENTRY_CALLERS = {
    Path("tool_executor.py"),
}

ALLOWED_SURFACES = {"build", "inspect", "deploy", "repair", "what-if"}


def _iter_py_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*.py"):
        rel = path.relative_to(root)
        if rel.parts and rel.parts[0] == "tests":
            continue
        if "__pycache__" in rel.parts:
            continue
        yield path


def _find_calls(pattern: str, rel_path: Path, text: str) -> List[str]:
    violations: List[str] = []
    for match in re.finditer(pattern, text):
        line = text.count("\n", 0, match.start()) + 1
        violations.append(f"{rel_path.as_posix()}:{line}")
    return violations


def verify_runtime_entry_guards(root: Path | None = None) -> List[str]:
    backend_root = root or BACKEND_ROOT
    violations: List[str] = []
    for path in _iter_py_files(backend_root):
        rel = path.relative_to(backend_root)
        text = path.read_text(encoding="utf-8", errors="ignore")

        run_task_loop_calls = _find_calls(r"\.run_task_loop\(", rel, text)
        if run_task_loop_calls and rel not in ALLOWED_RUN_TASK_LOOP_CALLERS:
            violations.append(
                "Forbidden run_task_loop call outside runtime boundary: "
                + ", ".join(run_task_loop_calls)
            )

        direct_tool_calls = _find_calls(r"tool_executor\.execute\(", rel, text)
        if direct_tool_calls and rel != Path("services/runtime/runtime_engine.py"):
            violations.append(
                "Forbidden direct tool execution outside runtime_engine: "
                + ", ".join(direct_tool_calls)
            )
    return violations


def verify_workspace_authority(root: Path | None = None) -> List[str]:
    backend_root = root or BACKEND_ROOT
    violations: List[str] = []
    for path in _iter_py_files(backend_root):
        rel = path.relative_to(backend_root)
        text = path.read_text(encoding="utf-8", errors="ignore")
        defs = _find_calls(r"^WORKSPACE_ROOT\s*=", rel, text)
        if defs and rel not in ALLOWED_WORKSPACE_ROOT_DEFINERS:
            violations.append(
                "Unexpected WORKSPACE_ROOT definition outside authority modules: "
                + ", ".join(defs)
            )

    for rel in EXPECTED_WORKSPACE_ROOT_IMPORTERS:
        file_path = backend_root / rel
        if not file_path.is_file():
            violations.append(f"Expected workspace authority file missing: {rel.as_posix()}")
            continue
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        if "from project_state import WORKSPACE_ROOT" not in text:
            violations.append(
                f"Missing project_state WORKSPACE_ROOT import in {rel.as_posix()}"
            )
    return violations


def verify_journal_authority(root: Path | None = None) -> List[str]:
    backend_root = root or BACKEND_ROOT
    violations: List[str] = []
    journal_literal_users: List[str] = []

    for path in _iter_py_files(backend_root):
        rel = path.relative_to(backend_root)
        text = path.read_text(encoding="utf-8", errors="ignore")

        literal_hits = _find_calls(r"session_journal\.jsonl", rel, text)
        if rel == Path("scripts/verify_architecture_guardrails.py"):
            literal_hits = []
        journal_literal_users.extend(literal_hits)

        append_calls = _find_calls(r"append_entry\(", rel, text)
        if append_calls and rel not in ALLOWED_APPEND_ENTRY_CALLERS and rel != Path("services/session_journal.py"):
            violations.append(
                "Unexpected session journal append caller: " + ", ".join(append_calls)
            )

    if any(not hit.startswith("services/session_journal.py:") for hit in journal_literal_users):
        violations.append(
            "session_journal.jsonl literal must only exist in services/session_journal.py"
        )

    return violations


def verify_surface_lock() -> List[str]:
    # Import late to keep this script pure-static until this point.
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))
    from services.skills.skill_registry import list_skills

    violations: List[str] = []
    for skill in list_skills():
        if not skill.surface:
            violations.append(f"Skill missing surface: {skill.name}")
            continue
        if skill.surface not in ALLOWED_SURFACES:
            violations.append(
                f"Skill has unsupported surface '{skill.surface}': {skill.name}"
            )
    return violations


def run_all_guardrails(root: Path | None = None) -> List[str]:
    return (
        verify_runtime_entry_guards(root)
        + verify_workspace_authority(root)
        + verify_journal_authority(root)
        + verify_surface_lock()
    )


def main() -> int:
    violations = run_all_guardrails()
    if violations:
        print("ARCHITECTURE GUARDRAILS: FAILED")
        for v in violations:
            print(f" - {v}")
        return 1
    print("ARCHITECTURE GUARDRAILS: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

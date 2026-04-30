"""
runtime_validator.py — Wires per-language runtime validators into the build pipeline.

This is the bridge between the template system and the executor.
After code generation, call validate_generated_workspace() to:
1. Detect the stack from workspace files
2. Run the appropriate validator
3. Return structured results with repair hints
"""

import os
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def detect_workspace_language(workspace_path: str) -> str:
    """Detect the primary language of a workspace from its files."""
    if not workspace_path or not os.path.isdir(workspace_path):
        return "unknown"

    # Check for Python backend
    for candidate in ["backend/main.py", "server.py", "main.py", "app.py"]:
        if os.path.isfile(os.path.join(workspace_path, candidate)):
            return "python"

    # Check for Node.js
    if os.path.isfile(os.path.join(workspace_path, "package.json")):
        return "javascript"

    # Check for C++
    if os.path.isfile(os.path.join(workspace_path, "CMakeLists.txt")):
        return "cpp"

    # Check for Go
    if os.path.isfile(os.path.join(workspace_path, "go.mod")):
        return "go"

    # Check for Rust
    if os.path.isfile(os.path.join(workspace_path, "Cargo.toml")):
        return "rust"

    return "unknown"


async def validate_generated_workspace(
    workspace_path: str,
    goal: str = "",
    stack_id: str = None,
) -> Dict[str, Any]:
    """
    Validate a generated workspace by detecting its stack and running
    the appropriate validator.

    Returns:
        {
            "passed": bool,
            "language": str,
            "stage_results": {...},
            "repair_hints": [...],
            "confidence": float,
        }
    """
    if not workspace_path or not os.path.isdir(workspace_path):
        return {
            "passed": False,
            "language": "unknown",
            "stage_results": {},
            "repair_hints": ["workspace_not_found"],
            "confidence": 0.0,
            "error": "Workspace not accessible",
        }

    # Detect language
    language = "unknown"
    confidence = 0.0

    # Try to use stack_id if provided
    if stack_id:
        try:
            from backend.agents.templates import list_templates

            templates = list_templates()
            for t in templates:
                if t.get("id") == stack_id:
                    language = t.get("language", "unknown")
                    confidence = t.get("confidence", 0.0)
                    break
        except Exception:
            pass

    # Fall back to file detection
    if language == "unknown":
        language = detect_workspace_language(workspace_path)

    # Map to validator language
    lang_map = {
        "python": "python",
        "javascript": "javascript",
        "typescript": "typescript",
        "cpp": "cpp",
        "go": "go",
        "rust": "rust",
    }
    validator_lang = lang_map.get(language, language)

    if validator_lang == "unknown":
        return {
            "passed": True,  # Can't validate unknown, don't block
            "language": "unknown",
            "stage_results": {},
            "repair_hints": [],
            "confidence": 0.0,
            "warning": "Unknown language, skipping validation",
        }

    # Get validator and run
    try:
        from backend.agents.validators import get_validator

        validator = get_validator(validator_lang, workspace_path, timeout=60)
        results = validator.validate_all()

        all_hints: List[str] = []
        any_failed = False
        stage_summary: Dict[str, Any] = {}

        for stage_name, result in results.items():
            stage_summary[stage_name] = {
                "success": result.success,
                "errors": result.errors[:5],
                "warnings": result.warnings[:3],
                "duration_ms": result.duration_ms,
                "files_checked": result.files_checked,
            }
            if result.errors:
                any_failed = True
            if result.repair_hints:
                all_hints.extend(result.repair_hints)

        return {
            "passed": not any_failed,
            "language": language,
            "stage_results": stage_summary,
            "repair_hints": list(set(all_hints))[:20],
            "confidence": confidence,
        }
    except Exception as e:
        logger.error("Runtime validation failed: %s", e)
        return {
            "passed": False,
            "language": language,
            "stage_results": {},
            "repair_hints": [f"validation_error:{str(e)[:100]}"],
            "confidence": confidence,
            "error": str(e),
        }

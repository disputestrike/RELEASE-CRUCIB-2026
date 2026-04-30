"""
runtime_validator.py — Wires per-language runtime validators into the build pipeline.

This is the bridge between the template system and the executor.
After code generation, call validate_generated_workspace() to:
1. Detect the stack from workspace files
2. Run the appropriate validator (syntax → build → runtime → integration)
3. Return structured results with repair hints
4. Include stack confidence score and tier
5. Include build gate decision for the UI

This module makes validation results ACTIONABLE:
- repair_hints feed directly into the repair loop
- confidence score feeds into the confidence tracking system
- gate decision tells the UI whether to warn/block
"""

import os
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


# ── Data classes used by the executor ──────────────────────────────────

@dataclass
class ValidationResult:
    """Structured result from the 4-stage runtime validator.

    Attributes:
        success:     True if all 4 stages passed.
        stage:       Name of the deepest stage reached (syntax / build / runtime / integration).
        errors:      List of error strings from failed stages.
        warnings:    List of warning strings from passing stages.
        details:     Arbitrary dict with timing, stage breakdowns, etc.
        repair_hints: Actionable hints for the repair loop.
    """
    success: bool = False
    stage: str = "none"
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    repair_hints: List[str] = field(default_factory=list)


class RuntimeValidator:
    """Executor-facing wrapper around the per-language validator pipeline.

    The executor instantiates this class and calls ``validate()``.
    Internally it delegates to :func:`validate_generated_workspace`.
    """

    async def validate(
        self,
        files: Optional[Dict[str, str]] = None,
        stack: Optional[str] = None,
        workspace_path: Optional[str] = None,
    ) -> ValidationResult:
        """Run 4-stage validation and return a :class:`ValidationResult`."""
        t0 = time.monotonic()

        if not workspace_path:
            return ValidationResult(
                success=False,
                stage="none",
                errors=["No workspace_path provided"],
                details={"total_duration_ms": 0},
            )

        # Delegate to the functional validator
        result = await validate_generated_workspace(
            workspace_path=workspace_path,
            stack_id=stack,
        )

        duration_ms = int((time.monotonic() - t0) * 1000)
        stage_results = result.get("stage_results", {})

        # Determine deepest stage
        stage_order = ["syntax", "build", "runtime", "integration"]
        deepest = "none"
        for s in stage_order:
            sr = stage_results.get(s, {})
            if sr.get("success", False):
                deepest = s
            else:
                break

        # Collect errors and warnings
        errors: List[str] = []
        warnings: List[str] = []
        for sname, sr in stage_results.items():
            if sr.get("errors"):
                errors.extend([f"[{sname}] {e}" for e in sr["errors"]])
            if sr.get("warnings"):
                warnings.extend([f"[{sname}] {w}" for w in sr["warnings"]])

        return ValidationResult(
            success=result.get("passed", False),
            stage=deepest,
            errors=errors,
            warnings=warnings,
            details={
                "total_duration_ms": duration_ms,
                "stage_results": stage_results,
                "confidence": result.get("confidence", 0.0),
                "confidence_tier": result.get("confidence_tier", "untested"),
                "validation_depth": result.get("validation_depth", "none"),
                "gate": result.get("gate", {}),
                "stages_passed": result.get("stages_passed", 0),
                "stages_total": result.get("stages_total", 4),
            },
            repair_hints=result.get("repair_hints", []),
        )


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


def detect_stack_id(workspace_path: str) -> Optional[str]:
    """Detect the most likely stack_id from workspace files."""
    if not workspace_path or not os.path.isdir(workspace_path):
        return None

    has_package_json = os.path.isfile(os.path.join(workspace_path, "package.json"))
    has_backend_main_py = os.path.isfile(os.path.join(workspace_path, "backend/main.py"))
    has_backend_server_js = os.path.isfile(os.path.join(workspace_path, "backend/server.js"))
    has_cmake = os.path.isfile(os.path.join(workspace_path, "CMakeLists.txt"))
    has_go_mod = os.path.isfile(os.path.join(workspace_path, "go.mod"))
    has_cargo = os.path.isfile(os.path.join(workspace_path, "Cargo.toml"))
    has_requirements = os.path.isfile(os.path.join(workspace_path, "backend/requirements.txt"))

    if has_backend_main_py and has_requirements:
        return "python_fastapi"
    elif has_backend_server_js and has_package_json:
        return "node_express"
    elif has_package_json and not has_backend_server_js and not has_backend_main_py:
        return "react_vite"
    elif has_cmake:
        return "cpp_cmake"
    elif has_go_mod:
        return "go_gin"
    elif has_cargo:
        return "rust_axum"

    return None


async def validate_generated_workspace(
    workspace_path: str,
    goal: str = "",
    stack_id: str = None,
) -> Dict[str, Any]:
    """
    Validate a generated workspace by detecting its stack and running
    the appropriate validator through ALL four stages:
      1. syntax — compile / parse each file
      2. build  — install deps, compile / bundle
      3. runtime — start server, health-check /health
      4. integration — test detected endpoints

    Returns:
        {
            "passed": bool,
            "language": str,
            "stack_id": str or None,
            "stage_results": {
                "syntax": {"success": bool, "errors": [...], ...},
                "build":  {"success": bool, "errors": [...], ...},
                "runtime": {"success": bool, "errors": [...], ...},
                "integration": {"success": bool, "errors": [...], ...},
            },
            "repair_hints": [...],
            "confidence": float,
            "confidence_tier": str,
            "gate": {
                "allowed": bool,
                "warning": str or None,
                "requires_acknowledgment": bool,
            },
            "validation_depth": str,  # "syntax_only", "build", "runtime", "full"
        }
    """
    if not workspace_path or not os.path.isdir(workspace_path):
        return {
            "passed": False,
            "language": "unknown",
            "stack_id": None,
            "stage_results": {},
            "repair_hints": ["workspace_not_found"],
            "confidence": 0.0,
            "confidence_tier": "untested",
            "gate": {"allowed": False, "warning": "Workspace not accessible", "requires_acknowledgment": False},
            "validation_depth": "none",
            "error": "Workspace not accessible",
        }

    # Detect stack
    detected_stack = stack_id or detect_stack_id(workspace_path)
    language = "unknown"
    confidence = 0.0
    confidence_tier = "untested"

    # Get confidence from stack confidence system
    try:
        from backend.stack_confidence import get_confidence_system
        cs = get_confidence_system()
        if detected_stack:
            sc = cs.get_confidence(detected_stack)
            confidence = sc.confidence
            confidence_tier = sc.tier
            language = sc.language
    except Exception:
        pass

    # Fall back to template registry for language/confidence
    if language == "unknown" and detected_stack:
        try:
            from backend.agents.templates import list_templates
            templates = list_templates()
            for t in templates:
                if t.get("id") == detected_stack:
                    language = t.get("language", "unknown")
                    confidence = confidence or t.get("confidence", 0.0)
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
            "stack_id": detected_stack,
            "stage_results": {},
            "repair_hints": [],
            "confidence": 0.0,
            "confidence_tier": "untested",
            "gate": {"allowed": True, "warning": None, "requires_acknowledgment": False},
            "validation_depth": "none",
            "warning": "Unknown language, skipping validation",
        }

    # Get build gate decision
    gate = {"allowed": True, "warning": None, "requires_acknowledgment": False}
    if detected_stack:
        try:
            from backend.stack_confidence import get_confidence_system
            gate = get_confidence_system().get_build_gate(detected_stack)
        except Exception:
            pass

    # Run validator
    try:
        from backend.agents.validators import get_validator

        validator = get_validator(validator_lang, workspace_path, timeout=60)
        results = validator.validate_all()

        all_hints: List[str] = []
        any_failed = False
        stage_summary: Dict[str, Any] = {}
        stages_passed = 0
        total_stages = 4

        for stage_name, result in results.items():
            stage_summary[stage_name] = {
                "success": result.success,
                "errors": result.errors[:5],
                "warnings": result.warnings[:3],
                "duration_ms": result.duration_ms,
                "files_checked": result.files_checked,
                "command_used": result.command_used[:200] if result.command_used else "",
                "can_auto_repair": result.can_auto_repair,
                "repair_hints": result.repair_hints[:10],
            }
            if result.errors:
                any_failed = True
            else:
                stages_passed += 1
            if result.repair_hints:
                all_hints.extend(result.repair_hints)

        # Determine validation depth
        if stages_passed >= 4:
            validation_depth = "full"
        elif stages_passed >= 3:
            validation_depth = "runtime"
        elif stages_passed >= 2:
            validation_depth = "build"
        elif stages_passed >= 1:
            validation_depth = "syntax_only"
        else:
            validation_depth = "none"

        return {
            "passed": not any_failed,
            "language": language,
            "stack_id": detected_stack,
            "stage_results": stage_summary,
            "repair_hints": list(set(all_hints))[:20],
            "confidence": confidence,
            "confidence_tier": confidence_tier,
            "gate": gate,
            "validation_depth": validation_depth,
            "stages_passed": stages_passed,
            "stages_total": total_stages,
        }
    except Exception as e:
        logger.error("Runtime validation failed: %s", e)
        return {
            "passed": False,
            "language": language,
            "stack_id": detected_stack,
            "stage_results": {},
            "repair_hints": [f"validation_error:{str(e)[:100]}"],
            "confidence": confidence,
            "confidence_tier": confidence_tier,
            "gate": gate,
            "validation_depth": "none",
            "error": str(e),
        }

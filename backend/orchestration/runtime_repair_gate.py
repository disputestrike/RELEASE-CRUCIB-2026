"""
runtime_repair_gate.py — Real repair loop that actually fixes code.

This is NOT a stub. This module:
  1. Receives validation errors from RuntimeValidator
  2. Classifies errors by type (syntax, import, dependency, runtime)
  3. Routes to the correct repair agent
  4. Applies the repair (patch, not full rewrite)
  5. Re-validates the repaired code
  6. Loops up to max_attempts

CRITICAL RULE: No agent may return success unless validation passes after repair.

The flow:
    validate(files) → fail?
      → classify errors
      → route to repair agent
      → agent returns patched files
      → re-validate
      → if pass: return success
      → if fail: loop (up to max_attempts)
      → if all attempts exhausted: HARD FAIL
"""

import asyncio
import json
import logging
import os
import re
import tempfile
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default max repair cycles
DEFAULT_MAX_REPAIR_CYCLES = 3

# Environment override
MAX_REPAIR_CYCLES = int(os.environ.get("CRUCIBAI_MAX_REPAIR_CYCLES", str(DEFAULT_MAX_REPAIR_CYCLES)))


@dataclass
class RepairResult:
    """Definitive repair result — no ambiguity."""
    success: bool
    files: Dict[str, str] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    cycles_used: int = 0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RepairHint:
    """Classified repair hint from validation errors."""
    error_type: str  # syntax, import, dependency, runtime, json, config
    file_path: str
    error_message: str
    original_error: str = ""
    suggested_fix: str = ""


# ── Error Classification ────────────────────────────────────────────────────

# Patterns for classifying error types
_ERROR_PATTERNS = {
    "syntax": [
        r"SyntaxError",
        r"syntax error",
        r"unexpected (?:token|indent|EOF)",
        r"invalid syntax",
        r"Parse error",
        r"Expected.*but got",
        r"malformed",
    ],
    "import": [
        r"ModuleNotFoundError",
        r"No module named",
        r"ImportError",
        r"Cannot find module",
        r"unresolved import",
    ],
    "dependency": [
        r"npm (?:ERR!|error)",
        r"ECONNECTIONREFUSED",
        r"ETARGET",
        r"peer dep",
        r"missing package",
        r"package\.json.*not found",
        r"go:.*module.*not found",
        r"cargo:.*could not find",
        r"Could not resolve dependency",
        r"could not resolve",
    ],
    "runtime": [
        r"Traceback \(most recent",
        r"Error:.*at.*process\.",
        r"ReferenceError",
        r"TypeError",
        r"AttributeError",
        r"KeyError",
        r"ValueError",
        r"IndexError",
        r"ZeroDivisionError",
        r"segfault",
        r"panic:",
        r"fatal error",
    ],
    "json": [
        r"JSONDecodeError",
        r"JSON parse error",
        r"JSON decode",
        r"Unexpected token.*JSON",
        r"Expected.*JSON",
        r"invalid json",
    ],
    "config": [
        r"config.*not found",
        r"missing.*config",
        r".env.*not found",
        r"ENOENT.*config",
    ],
}


def classify_errors(validation_errors: List[str]) -> List[RepairHint]:
    """
    Classify validation errors into repair hint types.

    Args:
        validation_errors: List of error strings from ValidationResult.errors

    Returns:
        List of RepairHint objects classified by error type
    """
    hints = []

    for error_msg in validation_errors:
        error_lower = error_msg.lower()

        # Try to extract file path from error
        file_path = _extract_file_path(error_msg)

        # Classify by pattern matching
        matched_type = "runtime"  # Default: most errors are runtime

        for error_type, patterns in _ERROR_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, error_msg, re.IGNORECASE):
                    matched_type = error_type
                    break
            if matched_type != "runtime":
                break

        # Special multi-line traceback parsing
        original_error = error_msg
        if "Traceback" in error_msg:
            # Extract the actual error line from Python tracebacks
            lines = error_msg.strip().split("\n")
            for line in reversed(lines):
                if ":" in line and not line.strip().startswith(("File", "During", "The above")):
                    original_error = line.strip()
                    break

        hints.append(RepairHint(
            error_type=matched_type,
            file_path=file_path,
            error_message=error_msg[:500],
            original_error=original_error,
        ))

    logger.info(
        "classify_errors: %d errors → %s",
        len(hints),
        {h.error_type: sum(1 for hh in hints if hh.error_type == h.error_type) for h in hints},
    )

    return hints


def _extract_file_path(error_msg: str) -> str:
    """Extract a file path from an error message."""
    # Pattern: File "path/to/file.py", line N
    match = re.search(r'File "([^"]+)"', error_msg)
    if match:
        return match.group(1)

    # Pattern: at path/to/file.js:line:col
    match = re.search(r'at (?:.+ )?([^:\s]+\.(?:py|js|ts|jsx|tsx|go|rs|cpp|c|h))', error_msg)
    if match:
        return match.group(1)

    # Pattern: path/to/file.py:line:
    match = re.search(r'([\w/.\-]+\.(?:py|js|ts|jsx|tsx|go|rs|cpp|c|h)):\d+', error_msg)
    if match:
        return match.group(1)

    return "unknown"


# ── Repair Agents ───────────────────────────────────────────────────────────

class BaseRepairAgent:
    """Base class for repair agents."""

    name: str = "base_repair"

    async def repair(
        self,
        files: Dict[str, str],
        hints: List[RepairHint],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Attempt to repair files based on error hints.

        Returns:
            {
                "success": bool,
                "files_changed": Dict[str, str],  # Only changed files
                "errors": List[str],
            }
        """
        raise NotImplementedError


class SyntaxRepairAgent(BaseRepairAgent):
    """Fixes syntax errors — indentation, missing colons, brackets."""

    name = "syntax_repair"

    async def repair(
        self,
        files: Dict[str, str],
        hints: List[RepairHint],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        files_changed = {}
        errors = []

        syntax_hints = [h for h in hints if h.error_type == "syntax"]

        for hint in syntax_hints:
            path = hint.file_path
            if path == "unknown" or path not in files:
                # Try to find the file by extension
                for fpath in files.keys():
                    if fpath.endswith(".py") and "syntax" in hint.error_message.lower():
                        path = fpath
                        break

            if path not in files:
                continue

            content = files[path]

            if path.endswith(".py"):
                repaired = self._repair_python_syntax(content, hint)
                if repaired != content:
                    files_changed[path] = repaired
                    logger.info("SyntaxRepairAgent: fixed %s", path)
            elif path.endswith((".js", ".jsx", ".ts", ".tsx")):
                repaired = self._repair_js_syntax(content, hint)
                if repaired != content:
                    files_changed[path] = repaired
                    logger.info("SyntaxRepairAgent: fixed %s", path)

        return {
            "success": len(files_changed) > 0,
            "files_changed": files_changed,
            "errors": errors,
        }

    def _repair_python_syntax(self, content: str, hint: RepairHint) -> str:
        """Attempt common Python syntax fixes."""
        lines = content.split("\n")
        fixed_lines = list(lines)

        # Fix missing colons after def/class/if/for/while/try/else/finally/with/except
        colon_keywords = [r"^\s*(def |class |if |elif |else |for |while |try|finally |with |except )"]
        for i, line in enumerate(fixed_lines):
            for pattern in colon_keywords:
                if re.match(pattern, line) and not line.rstrip().endswith(":"):
                    if not line.rstrip().endswith("\\"):
                        fixed_lines[i] = line.rstrip() + ":"
                        logger.debug("Fixed missing colon on line %d", i + 1)

        # Fix inconsistent indentation (common issue)
        try:
            fixed_content = "\n".join(fixed_lines)
            import ast
            ast.parse(fixed_content)
            return fixed_content  # If it parses now, return it
        except SyntaxError:
            pass  # Our fix didn't work, return original

        return content

    def _repair_js_syntax(self, content: str, hint: RepairHint) -> str:
        """Attempt common JS/TS syntax fixes."""
        # Fix missing closing brackets/parens
        open_braces = content.count("{") - content.count("}")
        open_parens = content.count("(") - content.count(")")
        open_brackets = content.count("[") - content.count("]")

        fixed = content
        if open_braces > 0:
            fixed += "\n" * open_braces + "}" * open_braces
        if open_parens > 0:
            fixed += ")" * open_parens
        if open_brackets > 0:
            fixed += "]" * open_brackets

        return fixed if fixed != content else content


class ImportRepairAgent(BaseRepairAgent):
    """Fixes import/module errors — adds missing imports, adjusts paths."""

    name = "import_repair"

    async def repair(
        self,
        files: Dict[str, str],
        hints: List[RepairHint],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        files_changed = {}
        errors = []
        import_hints = [h for h in hints if h.error_type == "import"]

        for hint in import_hints:
            path = hint.file_path
            if path not in files:
                for fpath in files.keys():
                    if fpath.endswith((".py", ".js", ".ts")):
                        path = fpath
                        break

            if path not in files:
                continue

            content = files[path]

            # Extract missing module name
            module_match = re.search(r"No module named '([^']+)'", hint.error_message)
            if not module_match:
                module_match = re.search(r"Cannot find module '([^']+)'", hint.error_message)
            if not module_match:
                module_match = re.search(r"ModuleNotFoundError: No module named '([^']+)'", hint.error_message)

            if module_match:
                module_name = module_match.group(1)
                logger.info("ImportRepairAgent: adding missing module '%s' to %s", module_name, path)

                if path.endswith(".py"):
                    # Add try/except import with fallback
                    import_line = f"try:\n    import {module_name}\nexcept ImportError:\n    pass\n"
                    # Insert after existing imports
                    lines = content.split("\n")
                    insert_idx = 0
                    for i, line in enumerate(lines):
                        if line.startswith("import ") or line.startswith("from "):
                            insert_idx = i + 1
                        elif line.strip() == "" and insert_idx > 0:
                            insert_idx = i + 1
                            break

                    lines.insert(insert_idx, import_line)
                    files_changed[path] = "\n".join(lines)

                elif path.endswith((".js", ".ts")):
                    # Add try/require with fallback
                    import_line = f"\n// Auto-added by ImportRepairAgent\ntry {{ const {module_name.replace('.', '_')} = require('{module_name}'); }} catch(e) {{}}\n"
                    files_changed[path] = content + import_line

        return {
            "success": len(files_changed) > 0,
            "files_changed": files_changed,
            "errors": errors,
        }


class DependencyRepairAgent(BaseRepairAgent):
    """Fixes dependency issues — updates package.json, requirements.txt, go.mod."""

    name = "dependency_repair"

    async def repair(
        self,
        files: Dict[str, str],
        hints: List[RepairHint],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        files_changed = {}
        errors = []
        dep_hints = [h for h in hints if h.error_type == "dependency"]

        if not dep_hints:
            return {"success": False, "files_changed": {}, "errors": []}

        # Collect missing packages from errors
        missing_packages = set()
        for hint in dep_hints:
            # Extract package name from npm errors
            pkg_match = re.search(r"'([^']+)' not found", hint.error_message)
            if pkg_match:
                missing_packages.add(pkg_match.group(1))

            pkg_match = re.search(r"Cannot find module '([^']+)'", hint.error_message)
            if pkg_match:
                missing_packages.add(pkg_match.group(1))

            # npm dependency resolution errors
            pkg_match = re.search(r"Could not resolve dependency:\s*(\S+)", hint.error_message)
            if pkg_match:
                pkg_name = pkg_match.group(1).split("@")[0].split("/")[-1]
                missing_packages.add(pkg_name)

            pkg_match = re.search(r"npm ERR!\s+(?:missing|Could not find)\s+(\S+)", hint.error_message)
            if pkg_match:
                pkg_name = pkg_match.group(1).split("@")[0].split("/")[-1]
                missing_packages.add(pkg_name)

            # Python packages
            py_match = re.search(r"No module named '([^']+)'", hint.error_message)
            if py_match:
                missing_packages.add(py_match.group(1))

        if not missing_packages:
            return {"success": False, "files_changed": {}, "errors": []}

        # Fix requirements.txt
        for path, content in files.items():
            if "requirements" in path.lower() and path.endswith(".txt"):
                lines = content.strip().split("\n") if content.strip() else []
                added = False
                for pkg in missing_packages:
                    pkg_line = pkg.split(".")[-1]  # Use last component
                    # Convert common import aliases to package names
                    alias_map = {
                        "fastapi": "fastapi",
                        "uvicorn": "uvicorn",
                        "pydantic": "pydantic",
                        "sqlalchemy": "sqlalchemy",
                        "requests": "requests",
                        "httpx": "httpx",
                        "aiohttp": "aiohttp",
                        "react": "react",
                        "express": "express",
                    }
                    pkg_name = alias_map.get(pkg_line, pkg_line)
                    if pkg_name not in "\n".join(lines):
                        lines.append(f"{pkg_name}>=0.1.0")
                        added = True
                        logger.info("DependencyRepairAgent: added %s to %s", pkg_name, path)

                if added:
                    files_changed[path] = "\n".join(lines) + "\n"

        # Fix package.json
        for path, content in files.items():
            if path.lower().endswith("package.json"):
                try:
                    pkg = json.loads(content) if isinstance(content, str) else content
                    deps = pkg.get("dependencies", {})

                    for pkg_name in missing_packages:
                        simple_name = pkg_name.split("/")[-1].split("@")[0]
                        if simple_name not in deps:
                            deps[simple_name] = "^1.0.0"
                            logger.info("DependencyRepairAgent: added %s to %s", simple_name, path)

                    pkg["dependencies"] = deps
                    files_changed[path] = json.dumps(pkg, indent=2)
                except (json.JSONDecodeError, TypeError) as e:
                    errors.append(f"Could not parse package.json: {e}")

        return {
            "success": len(files_changed) > 0,
            "files_changed": files_changed,
            "errors": errors,
        }


class JsonRepairAgent(BaseRepairAgent):
    """Fixes JSON parsing errors — malformed JSON in config files."""

    name = "json_repair"

    async def repair(
        self,
        files: Dict[str, str],
        hints: List[RepairHint],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        files_changed = {}
        errors = []
        json_hints = [h for h in hints if h.error_type == "json"]

        if not json_hints:
            return {"success": False, "files_changed": {}, "errors": []}

        # Find and fix JSON files
        for path, content in files.items():
            if not path.endswith((".json", ".json5")):
                continue

            if isinstance(content, dict):
                # Already a dict — re-serialize
                files_changed[path] = json.dumps(content, indent=2)
                continue

            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                logger.info("JsonRepairAgent: fixing %s: %s", path, e)

                # Common fixes
                fixed = content

                # Fix trailing commas
                fixed = re.sub(r',\s*([}\]])', r'\1', fixed)

                # Fix single quotes → double quotes
                fixed = fixed.replace("'", '"')

                # Fix unquoted keys
                fixed = re.sub(r'(\w+)\s*:', r'"\1":', fixed)

                # Try parsing again
                try:
                    json.loads(fixed)
                    files_changed[path] = fixed
                    logger.info("JsonRepairAgent: fixed %s", path)
                except json.JSONDecodeError:
                    errors.append(f"Could not fix JSON in {path}: {e}")

        return {
            "success": len(files_changed) > 0,
            "files_changed": files_changed,
            "errors": errors,
        }


class LLMCodeRepairAgent(BaseRepairAgent):
    """
    Last-resort repair agent that uses LLM to fix code.

    Only used when all deterministic repair agents fail.
    Sends the error context to the LLM and asks for a fix.
    """

    name = "llm_repair"

    async def repair(
        self,
        files: Dict[str, str],
        hints: List[RepairHint],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        files_changed = {}
        errors = []

        # Try to use CodeRepairAgent from the existing codebase
        try:
            from backend.agents.code_repair_agent import CodeRepairAgent

            # Collect affected file paths
            affected_files = set()
            for hint in hints:
                if hint.file_path and hint.file_path != "unknown":
                    affected_files.add(hint.file_path)

            # Filter to files that actually exist in our file set
            target_files = [f for f in affected_files if f in files]

            if not target_files:
                # Try to fix first file that looks like source code
                for fpath in files.keys():
                    if fpath.endswith((".py", ".js", ".ts", ".jsx", ".tsx")):
                        target_files.append(fpath)
                        break

            if not target_files:
                return {"success": False, "files_changed": {}, "errors": ["No target files for LLM repair"]}

            # Build error context
            error_context = "\n".join(h.error_message for h in hints)

            # Write files to temp dir for CodeRepairAgent
            temp_dir = tempfile.mkdtemp(prefix="crucib_repair_")
            try:
                for fpath, content in files.items():
                    full = os.path.join(temp_dir, fpath)
                    os.makedirs(os.path.dirname(full), exist_ok=True)
                    with open(full, "w") as f:
                        f.write(str(content))

                repaired_files = await CodeRepairAgent.repair_workspace_files(
                    temp_dir,
                    target_files,
                    verification_issues=[h.error_message for h in hints],
                    llm_repair=None,  # Use default LLM callback
                )

                # Read back repaired files
                for rpath in repaired_files:
                    full = os.path.join(temp_dir, rpath)
                    if os.path.exists(full):
                        with open(full) as f:
                            files_changed[rpath] = f.read()
                        logger.info("LLMCodeRepairAgent: repaired %s", rpath)

            finally:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)

        except ImportError:
            errors.append("CodeRepairAgent not available — skipping LLM repair")
            logger.warning("LLMCodeRepairAgent: CodeRepairAgent not importable")
        except Exception as e:
            errors.append(f"LLM repair failed: {str(e)[:200]}")
            logger.error("LLMCodeRepairAgent: failed: %s", e)

        return {
            "success": len(files_changed) > 0,
            "files_changed": files_changed,
            "errors": errors,
        }


# ── Repair Agent Routing ────────────────────────────────────────────────────

_REPAIR_AGENTS: List[BaseRepairAgent] = [
    SyntaxRepairAgent(),
    ImportRepairAgent(),
    DependencyRepairAgent(),
    JsonRepairAgent(),
    LLMCodeRepairAgent(),
]


def select_repair_agent(hints: List[RepairHint]) -> BaseRepairAgent:
    """
    Select the best repair agent for the given error hints.

    Strategy:
      1. If ALL hints are one type, use that type's agent
      2. If mixed types, use the most common type's agent
      3. If no clear match, use LLM repair (last resort)
    """
    if not hints:
        return LLMCodeRepairAgent()

    # Count error types
    type_counts: Dict[str, int] = {}
    for hint in hints:
        type_counts[hint.error_type] = type_counts.get(hint.error_type, 0) + 1

    # Sort by count descending
    sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
    primary_type = sorted_types[0][0]

    # Map to repair agent
    agent_map = {
        "syntax": SyntaxRepairAgent,
        "import": ImportRepairAgent,
        "dependency": DependencyRepairAgent,
        "json": JsonRepairAgent,
    }

    agent_class = agent_map.get(primary_type)
    if agent_class:
        for agent in _REPAIR_AGENTS:
            if isinstance(agent, agent_class):
                return agent

    # Fallback: LLM repair
    return LLMCodeRepairAgent()


def apply_patch(original_files: Dict[str, str], patch: Dict[str, str]) -> Dict[str, str]:
    """
    Apply a patch (changed files) to the original file set.

    Returns a NEW dict with patched files merged in.
    """
    merged = dict(original_files)
    merged.update(patch)
    return merged


# ── Main Repair Loop ────────────────────────────────────────────────────────

async def repair_until_valid(
    files: Dict[str, str],
    stack: Dict[str, Any],
    validation_result: Any,  # ValidationResult from RuntimeValidator
    workspace_path: str = "",
    max_attempts: int = MAX_REPAIR_CYCLES,
    validator: Any = None,  # RuntimeValidator instance
) -> RepairResult:
    """
    Main repair loop: validate → classify → repair → revalidate → repeat.

    CRITICAL RULE: No agent may return success unless validation passes.

    Args:
        files: Current file set {path: content}
        stack: Stack dict from select_stack()
        validation_result: ValidationResult that failed
        workspace_path: Path to workspace on disk
        max_attempts: Maximum repair cycles (default from env)
        validator: RuntimeValidator instance (created if None)

    Returns:
        RepairResult with definitive success/failure
    """
    if validator is None:
        from .runtime_validator import RuntimeValidator
        validator = RuntimeValidator()

    current_files = dict(files)
    last_errors = list(validation_result.errors)
    last_hints = classify_errors(last_errors)

    logger.info(
        "[REPAIR LOOP] starting with %d errors, max_attempts=%d, hints=%s",
        len(last_errors),
        max_attempts,
        [h.error_type for h in last_hints],
    )

    for cycle in range(max_attempts):
        logger.info("[REPAIR CYCLE %d/%d]", cycle + 1, max_attempts)

        # Step 1: Classify current errors
        if cycle == 0:
            hints = last_hints
        else:
            hints = classify_errors(last_errors)

        if not hints:
            logger.warning("[REPAIR] No hints to classify — breaking")
            break

        # Step 2: Select repair agent
        agent = select_repair_agent(hints)
        logger.info("[REPAIR] Selected agent: %s for %d hints", agent.name, len(hints))

        # Step 3: Attempt repair
        try:
            repair_result = await agent.repair(
                files=current_files,
                hints=hints,
                context={"stack": stack, "workspace_path": workspace_path},
            )
        except Exception as e:
            logger.error("[REPAIR] Agent %s raised exception: %s", agent.name, e)
            repair_result = {"success": False, "files_changed": {}, "errors": [str(e)]}

        if not repair_result.get("files_changed"):
            logger.warning("[REPAIR] Agent %s returned no file changes", agent.name)

            # If this was a deterministic agent and it failed, try LLM as last resort
            if not isinstance(agent, LLMCodeRepairAgent) and cycle < max_attempts - 1:
                logger.info("[REPAIR] Escalating to LLM repair agent")
                try:
                    llm_agent = LLMCodeRepairAgent()
                    repair_result = await llm_agent.repair(
                        files=current_files,
                        hints=hints,
                        context={"stack": stack, "workspace_path": workspace_path},
                    )
                except Exception as e2:
                    logger.error("[REPAIR] LLM repair also failed: %s", e2)
                    repair_result = {"success": False, "files_changed": {}, "errors": [str(e2)]}

        if not repair_result.get("files_changed"):
            logger.warning("[REPAIR CYCLE %d] No files changed — cannot repair further", cycle + 1)
            # Try all remaining agents for any error type
            changed = False
            for alt_agent in _REPAIR_AGENTS:
                if isinstance(alt_agent, type(agent)):
                    continue
                try:
                    alt_result = await alt_agent.repair(
                        files=current_files,
                        hints=hints,
                        context={"stack": stack, "workspace_path": workspace_path},
                    )
                    if alt_result.get("files_changed"):
                        repair_result = alt_result
                        changed = True
                        logger.info("[REPAIR] Fallback agent %s produced changes", alt_agent.name)
                        break
                except Exception:
                    continue

            if not changed:
                break

        # Step 4: Apply patch
        current_files = apply_patch(current_files, repair_result["files_changed"])
        logger.info(
            "[REPAIR] Applied %d file changes",
            len(repair_result["files_changed"]),
        )

        # Step 5: Re-validate — THIS IS MANDATORY
        revalidation = await validator.validate(
            files=current_files,
            stack=stack,
            workspace_path=workspace_path,
        )

        if revalidation.success:
            logger.info(
                "[REPAIR SUCCESS] Validation passed after %d cycles", cycle + 1
            )
            return RepairResult(
                success=True,
                files=current_files,
                errors=[],
                cycles_used=cycle + 1,
                details={
                    "agent_used": agent.name,
                    "files_changed": list(repair_result["files_changed"].keys()),
                    "final_validation": {
                        "stage": revalidation.stage,
                        "warnings": revalidation.warnings,
                    },
                },
            )

        # Validation still fails — continue loop
        last_errors = revalidation.errors
        logger.warning(
            "[REPAIR CYCLE %d] Revalidation failed: %s",
            cycle + 1,
            [e[:100] for e in last_errors[:3]],
        )

    # ALL attempts exhausted — HARD FAIL
    logger.error(
        "[REPAIR HARD FAIL] %d cycles exhausted, %d errors remaining",
        max_attempts,
        len(last_errors),
    )

    return RepairResult(
        success=False,
        files=current_files,
        errors=last_errors,
        cycles_used=max_attempts,
        details={
            "last_hints": [h.error_type for h in last_hints],
            "agents_tried": [agent.name for agent in _REPAIR_AGENTS],
        },
    )

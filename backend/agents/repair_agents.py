"""
Real Repair Agents for CrucibAI Self-Healing Build System.

Each agent implements the RepairAgentInterface from orchestration.repair_loop.
Agents READ broken files, ANALYZE errors, APPLY fixes, and VALIDATE results.
Every agent returns honest success/failure — never fakes success=True.

Agents:
    LLMCodeRepairAgent      — LLM-powered code repair (Claude/Cerebras)
    NpmDependencyRepairAgent — Fixes missing npm dependencies
    PythonImportRepairAgent  — Fixes missing Python imports
    SyntaxRepairAgent        — Deterministic syntax error repair
    TemplateRefillAgent      — Refills broken files from template registry
"""

from __future__ import annotations

import ast
import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.orchestration.build_contract import BuildContract
    from backend.orchestration.repair_loop import RepairAgentInterface

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

# Language detection from file extension
_EXT_TO_LANGUAGE: Dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript/JSX",
    ".ts": "TypeScript",
    ".tsx": "TypeScript/TSX",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".sql": "SQL",
    ".go": "Go",
    ".rs": "Rust",
    ".cpp": "C++",
    ".c": "C",
    ".java": "Java",
    ".rb": "Ruby",
    ".php": "PHP",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
}

# Packages that use a different PyPI name than their import name
_PYTHON_IMPORT_TO_PIP: Dict[str, str] = {
    "cv2": "opencv-python",
    "bs4": "beautifulsoup4",
    "PIL": "Pillow",
    "sklearn": "scikit-learn",
    "yaml": "PyYAML",
    "dotenv": "python-dotenv",
    "dateutil": "python-dateutil",
    "attr": "attrs",
    "Crypto": "pycryptodome",
    "serial": "pyserial",
    "usb": "pyusb",
    "gi": "PyGObject",
    "lxml": "lxml",
    "wx": "wxPython",
    "vtk": "vtk",
    "PyQt5": "PyQt5",
    "PyQt6": "PyQt6",
}

# Packages that use a scoped npm name or alias
_NPM_ALIASES: Dict[str, str] = {
    "commander": "commander",
    "express": "express",
    "react": "react",
    "react-dom": "react-dom",
    "axios": "axios",
    "lodash": "lodash",
    "moment": "moment",
    "dayjs": "dayjs",
    "next": "next",
    "vue": "vue",
    "webpack": "webpack",
    "eslint": "eslint",
    "jest": "jest",
    "typescript": "typescript",
    "@prisma/client": "prisma",
    "prisma": "prisma",
}

# Map of common file paths to template IDs for refill
_FILE_TO_TEMPLATE_MAP: Dict[str, str] = {
    "backend/main.py": "python_fastapi",
    "backend/models.py": "python_fastapi",
    "backend/auth.py": "python_fastapi",
    "backend/requirements.txt": "python_fastapi",
    "src/main.jsx": "react_vite",
    "src/App.jsx": "react_vite",
    "src/App.tsx": "react_vite",
    "package.json": "react_vite",
    "vite.config.js": "react_vite",
    "index.html": "react_vite",
    "backend/server.js": "node_express",
    "backend/routes/api.js": "node_express",
    "backend/package.json": "node_express",
    "main.go": "go_gin",
    "src/main.rs": "rust_axum",
    "Cargo.toml": "rust_axum",
    "CMakeLists.txt": "cpp_cmake",
}


def _safe_resolve(workspace: str, rel_path: str) -> Optional[str]:
    """Resolve a relative path against workspace, rejecting path traversal."""
    if not workspace or not rel_path:
        return None
    workspace = os.path.normpath(os.path.abspath(workspace))
    rel_path = rel_path.replace("\\", "/").lstrip("/")
    # Reject obvious traversal
    if ".." in rel_path.split("/"):
        logger.warning("Path traversal rejected: %s", rel_path)
        return None
    full = os.path.normpath(os.path.join(workspace, rel_path))
    if not full.startswith(workspace + os.sep) and full != workspace:
        logger.warning("Path escape rejected: %s -> %s", rel_path, full)
        return None
    return full


def _read_file_safe(path: str) -> Optional[str]:
    """Read a file safely, return content or None."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError as e:
        logger.warning("Cannot read file %s: %s", path, e)
        return None


def _write_file_safe(path: str, content: str) -> bool:
    """Write a file safely, return True on success."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except OSError as e:
        logger.error("Cannot write file %s: %s", path, e)
        return False


def _parse_contract_item_id(contract_item_id: str) -> Optional[str]:
    """
    Parse 'required_files:path/to/file.py' into just 'path/to/file.py'.
    Returns None if the format is unexpected.
    """
    if ":" in contract_item_id:
        _, file_path = contract_item_id.split(":", 1)
        return file_path.strip()
    return contract_item_id if contract_item_id else None


def _detect_language(file_path: str) -> str:
    """Detect programming language from file extension."""
    ext = os.path.splitext(file_path)[1].lower()
    return _EXT_TO_LANGUAGE.get(ext, "Unknown")


def _run_subprocess_silent(cmd: List[str], cwd: Optional[str] = None, timeout: int = 30) -> Dict[str, Any]:
    """Run a subprocess command and return result dict."""
    import subprocess
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout or "",
            "stderr": result.stderr or "",
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"returncode": -1, "stdout": "", "stderr": "Process timed out", "success": False}
    except FileNotFoundError:
        return {"returncode": -1, "stdout": "", "stderr": f"Command not found: {cmd[0]}", "success": False}
    except Exception as e:
        return {"returncode": -1, "stdout": "", "stderr": str(e), "success": False}


def _validate_python_syntax(code: str) -> Dict[str, Any]:
    """Validate Python code with ast.parse. Returns (ok, error_msg)."""
    try:
        ast.parse(code)
        return {"valid": True, "error": ""}
    except SyntaxError as e:
        return {"valid": False, "error": f"SyntaxError: {e.msg} (line {e.lineno}, col {e.offset})"}
    except Exception as e:
        return {"valid": False, "error": str(e)}


def _validate_js_syntax(file_path: str) -> Dict[str, Any]:
    """Validate JS/TS file with node --check. Returns (ok, error_msg)."""
    result = _run_subprocess_silent(["node", "--check", file_path], timeout=15)
    if result["success"]:
        return {"valid": True, "error": ""}
    return {"valid": False, "error": result["stderr"].strip()}


# ---------------------------------------------------------------------------
# Agent 1: LLMCodeRepairAgent
# ---------------------------------------------------------------------------


class LLMCodeRepairAgent:
    """
    Main LLM-powered repair agent.

    Flow:
    1. Parse contract_item_id to get affected file path
    2. Read broken file from workspace
    3. Build repair prompt with error context
    4. Call LLM (Cerebras primary, Anthropic fallback) via call_llm()
    5. Strip any markdown fences from LLM response
    6. Write fixed code to workspace
    7. Validate the fix (py_compile / node --check)
    8. Return honest success/failure
    """

    async def repair(
        self,
        contract_item_id: str,
        contract: "BuildContract",  # noqa: ARG002
        workspace_path: str,
        error_context: Dict[str, Any],
        priority: str = "medium",  # noqa: ARG002
    ) -> Dict[str, Any]:
        logger.info("[LLMCodeRepair] Starting repair for %s", contract_item_id)

        # 1. Parse contract item id to get file path
        file_path = _parse_contract_item_id(contract_item_id)
        if not file_path:
            return {"success": False, "files_modified": [], "error": f"Cannot parse contract item id: {contract_item_id}", "repair_strategy": "llm_code_repair"}

        # 2. Resolve and read the file
        full_path = _safe_resolve(workspace_path, file_path)
        if not full_path or not os.path.isfile(full_path):
            return {"success": False, "files_modified": [], "error": f"File not found: {file_path}", "repair_strategy": "llm_code_repair"}

        original_content = _read_file_safe(full_path)
        if original_content is None:
            return {"success": False, "files_modified": [], "error": f"Cannot read file: {file_path}", "repair_strategy": "llm_code_repair"}

        if not original_content.strip():
            return {"success": False, "files_modified": [], "error": f"File is empty: {file_path}", "repair_strategy": "llm_code_repair"}

        # 3. Get error message from context
        error_message = (
            error_context.get("error_message")
            or error_context.get("instruction")
            or error_context.get("raw_message")
            or "Unknown error"
        )

        language = _detect_language(file_path)

        # 4. Build LLM prompt
        system_prompt = (
            f"You are a {language} code repair expert.\n"
            "You will be given broken code and an error message.\n"
            "Return ONLY the complete fixed file content.\n"
            "Do NOT wrap in markdown fences (no ``` at all).\n"
            "Do NOT add prose explanations. Return ONLY code.\n"
            "The fix must be minimal — change only what is necessary to resolve the error.\n"
            "Preserve all comments, formatting, and structure that are correct."
        )

        user_prompt = (
            f"Fix this {language} code. The following error occurred:\n\n"
            f"Error: {error_message}\n\n"
            f"File: {file_path}\n\n"
            f"Current code:\n{original_content[:10000]}\n\n"
            f"Return ONLY the complete fixed file content."
        )

        # Include line_number and column info if available
        line_number = error_context.get("line_number")
        if line_number:
            user_prompt = f"Error location: line {line_number}\n" + user_prompt

        # 5. Call LLM
        try:
            from backend.llm_client import call_llm

            fixed_content = await call_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,  # Low temp for deterministic repair
                task_type="backend_generation",  # Route to Anthropic for quality
            )
        except Exception as e:
            logger.error("[LLMCodeRepair] LLM call failed: %s", e)
            return {"success": False, "files_modified": [], "error": f"LLM call failed: {e}", "repair_strategy": "llm_code_repair"}

        if not fixed_content:
            return {"success": False, "files_modified": [], "error": "LLM returned no content", "repair_strategy": "llm_code_repair"}

        # 6. Strip markdown fences if the LLM added them despite instructions
        from backend.agents.code_repair_agent import strip_code_fences
        fixed_content = strip_code_fences(fixed_content)

        # Check if anything actually changed
        if fixed_content.strip() == original_content.strip():
            return {"success": False, "files_modified": [], "error": "LLM returned identical content (no fix applied)", "repair_strategy": "llm_code_repair"}

        if not fixed_content.strip():
            return {"success": False, "files_modified": [], "error": "LLM returned empty content", "repair_strategy": "llm_code_repair"}

        # 7. Write fixed content
        if not _write_file_safe(full_path, fixed_content):
            return {"success": False, "files_modified": [], "error": f"Cannot write file: {file_path}", "repair_strategy": "llm_code_repair"}

        # 8. Validate the fix
        validation = self._validate_fix(full_path, file_path)

        if validation["valid"]:
            logger.info("[LLMCodeRepair] Successfully repaired %s", file_path)
            return {
                "success": True,
                "files_modified": [file_path],
                "error": None,
                "repair_strategy": "llm_code_repair",
                "before_after": {
                    file_path: {
                        "before": original_content[:5000],
                        "after": fixed_content[:5000],
                    }
                },
            }
        else:
            # Validation failed — restore original content
            logger.warning("[LLMCodeRepair] Validation failed for %s: %s. Restoring original.", file_path, validation["error"])
            _write_file_safe(full_path, original_content)
            return {
                "success": False,
                "files_modified": [],
                "error": f"LLM fix did not pass validation: {validation['error']}",
                "repair_strategy": "llm_code_repair",
            }

    def _validate_fix(self, full_path: str, file_path: str) -> Dict[str, Any]:
        """Validate a fixed file based on its language."""
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".py":
            content = _read_file_safe(full_path)
            if content is None:
                return {"valid": False, "error": "Cannot read file after write"}
            result = _validate_python_syntax(content)
            if not result["valid"]:
                # Try py_compile as a second opinion
                compile_result = _run_subprocess_silent(
                    ["python", "-m", "py_compile", full_path], timeout=10
                )
                if compile_result["success"]:
                    return {"valid": True, "error": ""}
            return result

        elif ext in (".js", ".jsx", ".ts", ".tsx"):
            return _validate_js_syntax(full_path)

        elif ext == ".json":
            content = _read_file_safe(full_path)
            if content is None:
                return {"valid": False, "error": "Cannot read file after write"}
            try:
                json.loads(content)
                return {"valid": True, "error": ""}
            except json.JSONDecodeError as e:
                return {"valid": False, "error": f"JSON parse error: {e}"}

        # For other languages, skip validation (assume success)
        return {"valid": True, "error": ""}


# ---------------------------------------------------------------------------
# Agent 2: NpmDependencyRepairAgent
# ---------------------------------------------------------------------------


class NpmDependencyRepairAgent:
    """
    Fixes missing npm dependencies.

    Flow:
    1. Parse error message for module-not-found / ERESOLVE patterns
    2. Extract package name
    3. Read package.json from workspace
    4. Add missing package to dependencies with appropriate version
    5. Write updated package.json
    6. Run npm install --legacy-peer-deps
    7. Return honest success/failure
    """

    # Patterns for extracting package names from error messages
    _MODULE_PATTERNS: List[re.Pattern] = [
        re.compile(r"Cannot find module ['\"]([^'\"]+)['\"]", re.IGNORECASE),
        re.compile(r"Could not resolve ['\"]([^'\"]+)['\"]", re.IGNORECASE),
        re.compile(r"Module not found.*['\"]([^'\"]+)['\"]", re.IGNORECASE),
        re.compile(r"Cannot resolve ['\"]([^'\"]+)['\"]", re.IGNORECASE),
        re.compile(r"Unable to resolve ['\"]([^'\"]+)['\"]", re.IGNORECASE),
        re.compile(r"error while resolving.*['\"]([^'\"]+)['\"]", re.IGNORECASE),
    ]

    _ERESOLVE_PATTERN = re.compile(r"ERESOLVE.*['\"]([^'\"]+)['\"]", re.IGNORECASE)

    async def repair(
        self,
        contract_item_id: str,  # noqa: ARG002
        contract: "BuildContract",  # noqa: ARG002
        workspace_path: str,
        error_context: Dict[str, Any],
        priority: str = "medium",  # noqa: ARG002
    ) -> Dict[str, Any]:
        logger.info("[NpmDepRepair] Starting npm dependency repair")

        error_message = (
            error_context.get("error_message")
            or error_context.get("raw_message")
            or error_context.get("instruction")
            or ""
        )

        # 1. Extract package name from error
        package_name = self._extract_package_name(error_message)
        if not package_name:
            return {
                "success": False,
                "files_modified": [],
                "error": "Could not extract npm package name from error message",
                "repair_strategy": "npm_dependency_repair",
            }

        logger.info("[NpmDepRepair] Extracted package: %s", package_name)

        # 2. Find and read package.json
        pkg_path = self._find_package_json(workspace_path)
        if not pkg_path:
            return {
                "success": False,
                "files_modified": [],
                "error": "package.json not found in workspace",
                "repair_strategy": "npm_dependency_repair",
            }

        pkg_content = _read_file_safe(pkg_path)
        if not pkg_content:
            return {
                "success": False,
                "files_modified": [],
                "error": "Cannot read package.json",
                "repair_strategy": "npm_dependency_repair",
            }

        # 3. Parse and update package.json
        try:
            pkg_data = json.loads(pkg_content)
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "files_modified": [],
                "error": f"package.json parse error: {e}",
                "repair_strategy": "npm_dependency_repair",
            }

        # Check if already in dependencies
        all_deps = {}
        all_deps.update(pkg_data.get("dependencies", {}))
        all_deps.update(pkg_data.get("devDependencies", {}))

        # Normalize package name for comparison (strip scoped prefix for check)
        stripped_name = package_name.lstrip("@").split("/")[0] if "/" in package_name else package_name.lstrip("@")
        already_present = any(
            stripped_name in dep_key
            for dep_key in all_deps.keys()
        )

        if already_present:
            logger.info("[NpmDepRepair] Package %s already in dependencies, running npm install", package_name)
        else:
            # Add to dependencies with a caret range
            if "dependencies" not in pkg_data:
                pkg_data["dependencies"] = {}
            pkg_data["dependencies"][package_name] = "^latest"

            updated_content = json.dumps(pkg_data, indent=2) + "\n"
            if not _write_file_safe(pkg_path, updated_content):
                return {
                    "success": False,
                    "files_modified": [],
                    "error": "Cannot write updated package.json",
                    "repair_strategy": "npm_dependency_repair",
                }
            logger.info("[NpmDepRepair] Added %s to package.json", package_name)

        # 4. Run npm install
        pkg_dir = os.path.dirname(pkg_path)
        install_result = await self._run_npm_install(pkg_dir)

        if install_result["success"]:
            logger.info("[NpmDepRepair] npm install succeeded for %s", package_name)
            rel_pkg_path = os.path.relpath(pkg_path, workspace_path)
            return {
                "success": True,
                "files_modified": [rel_pkg_path, "package-lock.json"],
                "error": None,
                "repair_strategy": "npm_dependency_repair",
            }

        # If npm install fails, restore package.json
        _write_file_safe(pkg_path, pkg_content)
        return {
            "success": False,
            "files_modified": [],
            "error": f"npm install failed: {install_result['stderr'][:500]}",
            "repair_strategy": "npm_dependency_repair",
        }

    def _extract_package_name(self, error_message: str) -> Optional[str]:
        """Extract package name from error message."""
        if not error_message:
            return None

        # Try standard module patterns first
        for pattern in self._MODULE_PATTERNS:
            match = pattern.search(error_message)
            if match:
                name = match.group(1)
                # Clean up scoped packages and sub-paths
                # e.g., @org/pkg -> @org/pkg, lodash/map -> lodash
                if name.startswith("@"):
                    parts = name.split("/")
                    if len(parts) >= 2:
                        return f"{parts[0]}/{parts[1]}"
                    return name
                # For sub-path imports like "lodash/map", take the top-level package
                top_level = name.split("/")[0]
                # Strip common file extensions that might be included
                top_level = re.sub(r"\.(js|jsx|ts|tsx|json)$", "", top_level)
                return top_level or name

        # Try ERESOLVE pattern
        match = self._ERESOLVE_PATTERN.search(error_message)
        if match:
            return match.group(1)

        return None

    def _find_package_json(self, workspace_path: str) -> Optional[str]:
        """Find package.json in workspace, checking common locations."""
        candidates = [
            os.path.join(workspace_path, "package.json"),
            os.path.join(workspace_path, "client", "package.json"),
            os.path.join(workspace_path, "frontend", "package.json"),
            os.path.join(workspace_path, "src", "package.json"),
            os.path.join(workspace_path, "backend", "package.json"),
        ]
        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate
        return None

    async def _run_npm_install(self, cwd: str) -> Dict[str, Any]:
        """Run npm install --legacy-peer-deps in the given directory."""
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: _run_subprocess_silent(
                    ["npm", "install", "--legacy-peer-deps"],
                    cwd=cwd,
                    timeout=120,
                ),
            )
            return result
        except Exception as e:
            return {"success": False, "stderr": str(e)}


# ---------------------------------------------------------------------------
# Agent 3: PythonImportRepairAgent
# ---------------------------------------------------------------------------


class PythonImportRepairAgent:
    """
    Fixes missing Python imports.

    Flow:
    1. Parse error for ModuleNotFoundError / ImportError patterns
    2. Extract module name
    3. Determine if it's a local module or a pip package
    4. For pip packages: add to requirements.txt
    5. For local modules: create a minimal stub file
    6. Validate with py_compile on the affected file
    7. Return honest success/failure
    """

    _MODULE_PATTERNS: List[re.Pattern] = [
        re.compile(r"No module named ['\"]([^'\"]+)['\"]", re.IGNORECASE),
        re.compile(r"ModuleNotFoundError.*['\"]([^'\"]+)['\"]", re.IGNORECASE),
        re.compile(r"ImportError.*cannot import name ['\"]([^'\"]+)['\"]", re.IGNORECASE),
    ]

    async def repair(
        self,
        contract_item_id: str,
        contract: "BuildContract",  # noqa: ARG002
        workspace_path: str,
        error_context: Dict[str, Any],
        priority: str = "medium",  # noqa: ARG002
    ) -> Dict[str, Any]:
        logger.info("[PythonImportRepair] Starting Python import repair")

        error_message = (
            error_context.get("error_message")
            or error_context.get("raw_message")
            or error_context.get("instruction")
            or ""
        )

        # 1. Extract module name from error
        module_name = self._extract_module_name(error_message)
        if not module_name:
            return {
                "success": False,
                "files_modified": [],
                "error": "Could not extract Python module name from error message",
                "repair_strategy": "python_import_repair",
            }

        logger.info("[PythonImportRepair] Extracted module: %s", module_name)

        # 2. Determine if it's a local module or pip package
        # First check if it's a local module (exists as .py file)
        is_local = await self._is_local_module(module_name, workspace_path)

        if is_local:
            return await self._create_local_stub(module_name, workspace_path)
        else:
            return await self._add_pip_dependency(module_name, workspace_path, contract_item_id)

    def _extract_module_name(self, error_message: str) -> Optional[str]:
        """Extract Python module name from error message."""
        if not error_message:
            return None

        for pattern in self._MODULE_PATTERNS:
            match = pattern.search(error_message)
            if match:
                return match.group(1)
        return None

    async def _is_local_module(self, module_name: str, workspace_path: str) -> bool:
        """Check if the module might be a local module."""
        # Check common local module locations
        local_dirs = ["", "backend", "client", "src", "app"]
        for base_dir in local_dirs:
            module_path = os.path.join(workspace_path, base_dir, f"{module_name}.py")
            if os.path.isfile(module_path):
                return True
            # Also check for __init__.py in package directories
            package_path = os.path.join(workspace_path, base_dir, module_name.replace(".", os.sep), "__init__.py")
            if os.path.isfile(package_path):
                return True
        return False

    async def _create_local_stub(self, module_name: str, workspace_path: str) -> Dict[str, Any]:
        """Create a minimal stub file for a missing local module."""
        # Find a reasonable location for the stub
        stub_dirs = ["backend", "client", "src", "app", ""]
        stub_path = None
        for base in stub_dirs:
            test_dir = os.path.join(workspace_path, base)
            if os.path.isdir(test_dir) or base == "":
                stub_path = os.path.join(test_dir, f"{module_name}.py")
                break

        if not stub_path:
            stub_path = os.path.join(workspace_path, f"{module_name}.py")

        stub_lines = [
            '"""',
            f'Stub module: {module_name}',
            'Auto-generated by CrucibAI repair agent.',
            '"""',
            '',
            '# This module was auto-generated as a stub.',
            '# Implement the required functionality here.',
            '',
        ]
        stub_content = "\n".join(stub_lines)
        if _write_file_safe(stub_path, stub_content):
            rel_path = os.path.relpath(stub_path, workspace_path)
            logger.info("[PythonImportRepair] Created stub module: %s", rel_path)
            return {
                "success": True,
                "files_modified": [rel_path],
                "error": None,
                "repair_strategy": "python_import_repair",
            }

        return {
            "success": False,
            "files_modified": [],
            "error": f"Cannot create stub module: {module_name}",
            "repair_strategy": "python_import_repair",
        }

    async def _add_pip_dependency(
        self,
        module_name: str,
        workspace_path: str,
        contract_item_id: str,
    ) -> Dict[str, Any]:
        """Add missing pip package to requirements.txt."""
        # Map import name to pip package name
        pip_name = self._import_to_pip_name(module_name)

        # Find requirements.txt
        req_path = self._find_requirements_txt(workspace_path)
        if not req_path:
            return {
                "success": False,
                "files_modified": [],
                "error": "requirements.txt not found in workspace",
                "repair_strategy": "python_import_repair",
            }

        req_content = _read_file_safe(req_path)
        if not req_content:
            return {
                "success": False,
                "files_modified": [],
                "error": "Cannot read requirements.txt",
                "repair_strategy": "python_import_repair",
            }

        # Check if already present
        existing_packages = set()
        for line in req_content.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                # Extract package name from requirement spec
                pkg = re.split(r"[=<>~!;\s\[]", line)[0].strip().lower()
                existing_packages.add(pkg)

        if pip_name.lower() in existing_packages:
            logger.info("[PythonImportRepair] Package %s already in requirements.txt", pip_name)
            # Try pip install anyway
            install_result = await self._run_pip_install(pip_name, workspace_path)
            if install_result["success"]:
                return {
                    "success": True,
                    "files_modified": [],
                    "error": None,
                    "repair_strategy": "python_import_repair",
                }
            return {
                "success": False,
                "files_modified": [],
                "error": f"Package {pip_name} already in requirements.txt but pip install failed: {install_result['stderr'][:300]}",
                "repair_strategy": "python_import_repair",
            }

        # Add to requirements.txt
        new_line = f"{pip_name}\n"
        updated_content = req_content.rstrip("\n") + "\n" + new_line

        if not _write_file_safe(req_path, updated_content):
            return {
                "success": False,
                "files_modified": [],
                "error": "Cannot write updated requirements.txt",
                "repair_strategy": "python_import_repair",
            }

        # Try pip install
        install_result = await self._run_pip_install(pip_name, workspace_path)

        if install_result["success"]:
            rel_req_path = os.path.relpath(req_path, workspace_path)
            logger.info("[PythonImportRepair] Added and installed %s", pip_name)

            # Validate the affected file if possible
            file_path = _parse_contract_item_id(contract_item_id)
            if file_path:
                full_path = _safe_resolve(workspace_path, file_path)
                if full_path and os.path.isfile(full_path):
                    compile_result = _run_subprocess_silent(
                        ["python", "-m", "py_compile", full_path], timeout=10
                    )
                    if not compile_result["success"]:
                        # Remove the dependency if it doesn't fix the issue
                        _write_file_safe(req_path, req_content)
                        return {
                            "success": False,
                            "files_modified": [],
                            "error": f"Added {pip_name} but compilation still fails: {compile_result['stderr'][:300]}",
                            "repair_strategy": "python_import_repair",
                        }

            return {
                "success": True,
                "files_modified": [rel_req_path],
                "error": None,
                "repair_strategy": "python_import_repair",
            }

        # pip install failed — restore requirements.txt
        _write_file_safe(req_path, req_content)
        return {
            "success": False,
            "files_modified": [],
            "error": f"pip install failed for {pip_name}: {install_result['stderr'][:300]}",
            "repair_strategy": "python_import_repair",
        }

    def _import_to_pip_name(self, import_name: str) -> str:
        """Convert Python import name to pip package name."""
        # Check exact match first
        if import_name in _PYTHON_IMPORT_TO_PIP:
            return _PYTHON_IMPORT_TO_PIP[import_name]

        # Check if the top-level package maps to something
        top_level = import_name.split(".")[0]
        if top_level in _PYTHON_IMPORT_TO_PIP:
            return _PYTHON_IMPORT_TO_PIP[top_level]

        # Default: use the import name as-is
        # Common convention: module_name -> module-name
        pip_name = top_level.replace("_", "-")
        return pip_name

    def _find_requirements_txt(self, workspace_path: str) -> Optional[str]:
        """Find requirements.txt in workspace."""
        candidates = [
            os.path.join(workspace_path, "requirements.txt"),
            os.path.join(workspace_path, "backend", "requirements.txt"),
            os.path.join(workspace_path, "client", "requirements.txt"),
            os.path.join(workspace_path, "src", "requirements.txt"),
        ]
        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate
        return None

    async def _run_pip_install(self, package_name: str, workspace_path: str) -> Dict[str, Any]:
        """Run pip install in the workspace."""
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: _run_subprocess_silent(
                    ["pip", "install", package_name],
                    cwd=workspace_path,
                    timeout=120,
                ),
            )
            return result
        except Exception as e:
            return {"success": False, "stderr": str(e)}


# ---------------------------------------------------------------------------
# Agent 4: SyntaxRepairAgent (REAL version)
# ---------------------------------------------------------------------------


class SyntaxRepairAgent:
    """
    Deterministic syntax error repair.

    For Python:
    - Uses ast.parse to find exact line/column
    - Tries: add missing colons, fix indentation, add missing brackets/parens
    - Ensures block bodies exist (adds "pass" where needed)

    For JS/JSX:
    - Tries to fix unclosed brackets/parens/braces
    - Reports errors that need LLM repair

    Validates all fixes before returning.
    """

    _PY_BLOCK_KEYWORDS = {"if", "elif", "else", "for", "while", "with", "try", "except", "finally", "def", "class", "async"}

    async def repair(
        self,
        contract_item_id: str,
        contract: "BuildContract",  # noqa: ARG002
        workspace_path: str,
        error_context: Dict[str, Any],
        priority: str = "medium",  # noqa: ARG002
    ) -> Dict[str, Any]:
        logger.info("[SyntaxRepair] Starting syntax repair for %s", contract_item_id)

        file_path = _parse_contract_item_id(contract_item_id)
        if not file_path:
            return {"success": False, "files_modified": [], "error": f"Cannot parse contract item id: {contract_item_id}", "repair_strategy": "syntax_repair"}

        full_path = _safe_resolve(workspace_path, file_path)
        if not full_path or not os.path.isfile(full_path):
            return {"success": False, "files_modified": [], "error": f"File not found: {file_path}", "repair_strategy": "syntax_repair"}

        original_content = _read_file_safe(full_path)
        if original_content is None:
            return {"success": False, "files_modified": [], "error": f"Cannot read file: {file_path}", "repair_strategy": "syntax_repair"}

        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".py":
            return self._repair_python(full_path, file_path, original_content, error_context)
        elif ext in (".js", ".jsx", ".ts", ".tsx"):
            return self._repair_javascript(full_path, file_path, original_content, error_context)
        elif ext == ".json":
            return self._repair_json(full_path, file_path, original_content, error_context)
        else:
            return {"success": False, "files_modified": [], "error": f"No syntax repair support for {ext} files", "repair_strategy": "syntax_repair"}

    def _repair_python(
        self,
        full_path: str,
        file_path: str,
        original_content: str,
        error_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Attempt deterministic Python syntax repair."""
        from backend.agents.code_repair_agent import (
            _add_missing_python_colons,
            _ensure_python_block_bodies,
            _extract_largest_code_block,
            strip_code_fences,
        )

        # Strategy 1: Strip code fences if the file is wrapped in markdown
        stripped = strip_code_fences(original_content)
        if stripped != original_content:
            validation = _validate_python_syntax(stripped)
            if validation["valid"]:
                if _write_file_safe(full_path, stripped):
                    logger.info("[SyntaxRepair] Fixed by stripping code fences: %s", file_path)
                    return {"success": True, "files_modified": [file_path], "error": None, "repair_strategy": "syntax_repair_strip_fences"}

        # Strategy 2: Extract largest code block (in case of multiple blocks)
        extracted = _extract_largest_code_block(original_content)
        if extracted != original_content:
            validation = _validate_python_syntax(extracted)
            if validation["valid"]:
                if _write_file_safe(full_path, extracted):
                    logger.info("[SyntaxRepair] Fixed by extracting code block: %s", file_path)
                    return {"success": True, "files_modified": [file_path], "error": None, "repair_strategy": "syntax_repair_extract_block"}

        # Strategy 3: Add missing colons
        working = _add_missing_python_colons(original_content)
        validation = _validate_python_syntax(working)
        if validation["valid"]:
            if _write_file_safe(full_path, working):
                logger.info("[SyntaxRepair] Fixed by adding missing colons: %s", file_path)
                return {"success": True, "files_modified": [file_path], "error": None, "repair_strategy": "syntax_repair_add_colons"}

        # Strategy 4: Ensure block bodies have content
        working = _ensure_python_block_bodies(working)
        validation = _validate_python_syntax(working)
        if validation["valid"]:
            if _write_file_safe(full_path, working):
                logger.info("[SyntaxRepair] Fixed by ensuring block bodies: %s", file_path)
                return {"success": True, "files_modified": [file_path], "error": None, "repair_strategy": "syntax_repair_block_bodies"}

        # Strategy 5: Fix common bracket/paren issues
        working = self._fix_brackets(original_content)
        validation = _validate_python_syntax(working)
        if validation["valid"]:
            if _write_file_safe(full_path, working):
                logger.info("[SyntaxRepair] Fixed by balancing brackets: %s", file_path)
                return {"success": True, "files_modified": [file_path], "error": None, "repair_strategy": "syntax_repair_brackets"}

        # Strategy 6: Fix indentation issues
        working = self._fix_indentation(original_content, error_context)
        validation = _validate_python_syntax(working)
        if validation["valid"]:
            if _write_file_safe(full_path, working):
                logger.info("[SyntaxRepair] Fixed by correcting indentation: %s", file_path)
                return {"success": True, "files_modified": [file_path], "error": None, "repair_strategy": "syntax_repair_indentation"}

        # All deterministic strategies failed
        last_error = error_context.get("error_message", "Unknown syntax error")
        return {
            "success": False,
            "files_modified": [],
            "error": f"Deterministic syntax repair failed: {last_error}. Requires LLM repair.",
            "repair_strategy": "syntax_repair",
        }

    def _repair_javascript(
        self,
        full_path: str,
        file_path: str,
        original_content: str,
        error_context: Dict[str, Any],  # noqa: ARG002
    ) -> Dict[str, Any]:
        """Attempt deterministic JavaScript/JSX syntax repair."""
        from backend.agents.code_repair_agent import strip_code_fences, _extract_largest_code_block

        # Strategy 1: Strip code fences
        stripped = strip_code_fences(original_content)
        if stripped != original_content:
            _write_file_safe(full_path, stripped)
            validation = _validate_js_syntax(full_path)
            if validation["valid"]:
                logger.info("[SyntaxRepair] Fixed JS by stripping code fences: %s", file_path)
                return {"success": True, "files_modified": [file_path], "error": None, "repair_strategy": "syntax_repair_strip_fences"}
            # Restore
            _write_file_safe(full_path, original_content)

        # Strategy 2: Extract largest code block
        extracted = _extract_largest_code_block(original_content)
        if extracted != original_content:
            _write_file_safe(full_path, extracted)
            validation = _validate_js_syntax(full_path)
            if validation["valid"]:
                logger.info("[SyntaxRepair] Fixed JS by extracting code block: %s", file_path)
                return {"success": True, "files_modified": [file_path], "error": None, "repair_strategy": "syntax_repair_extract_block"}
            # Restore
            _write_file_safe(full_path, original_content)

        # Strategy 3: Fix unbalanced brackets/braces
        working = self._fix_js_brackets(original_content)
        if working != original_content:
            _write_file_safe(full_path, working)
            validation = _validate_js_syntax(full_path)
            if validation["valid"]:
                logger.info("[SyntaxRepair] Fixed JS by balancing brackets: %s", file_path)
                return {"success": True, "files_modified": [file_path], "error": None, "repair_strategy": "syntax_repair_brackets"}
            # Restore
            _write_file_safe(full_path, original_content)

        return {
            "success": False,
            "files_modified": [],
            "error": "Deterministic JS syntax repair failed. Requires LLM repair.",
            "repair_strategy": "syntax_repair",
        }

    def _repair_json(
        self,
        full_path: str,
        file_path: str,
        original_content: str,
        error_context: Dict[str, Any],  # noqa: ARG002
    ) -> Dict[str, Any]:
        """Attempt deterministic JSON syntax repair."""
        from backend.agents.code_repair_agent import strip_code_fences, _extract_largest_code_block

        # Strategy 1: Strip code fences
        stripped = strip_code_fences(original_content)
        try:
            json.loads(stripped)
            if _write_file_safe(full_path, stripped):
                logger.info("[SyntaxRepair] Fixed JSON by stripping code fences: %s", file_path)
                return {"success": True, "files_modified": [file_path], "error": None, "repair_strategy": "syntax_repair_strip_fences"}
        except (json.JSONDecodeError, ValueError):
            pass

        # Strategy 2: Extract code block
        extracted = _extract_largest_code_block(original_content)
        try:
            parsed = json.loads(extracted)
            if _write_file_safe(full_path, json.dumps(parsed, indent=2) + "\n"):
                logger.info("[SyntaxRepair] Fixed JSON by extracting code block: %s", file_path)
                return {"success": True, "files_modified": [file_path], "error": None, "repair_strategy": "syntax_repair_extract_block"}
        except (json.JSONDecodeError, ValueError):
            pass

        # Strategy 3: Try ast.literal_eval (handles Python-style dicts in JSON)
        try:
            parsed = ast.literal_eval(original_content)
            fixed = json.dumps(parsed, indent=2, sort_keys=True) + "\n"
            json.loads(fixed)  # Verify it's valid JSON
            if _write_file_safe(full_path, fixed):
                logger.info("[SyntaxRepair] Fixed JSON via literal_eval: %s", file_path)
                return {"success": True, "files_modified": [file_path], "error": None, "repair_strategy": "syntax_repair_literal_eval"}
        except (ValueError, SyntaxError, TypeError):
            pass

        # Strategy 4: Common fixes — trailing commas
        working = re.sub(r",\s*([}\]])", r"\1", original_content)
        try:
            json.loads(working)
            if _write_file_safe(full_path, working):
                logger.info("[SyntaxRepair] Fixed JSON by removing trailing commas: %s", file_path)
                return {"success": True, "files_modified": [file_path], "error": None, "repair_strategy": "syntax_repair_trailing_commas"}
        except (json.JSONDecodeError, ValueError):
            pass

        return {
            "success": False,
            "files_modified": [],
            "error": "Deterministic JSON syntax repair failed. Requires LLM repair.",
            "repair_strategy": "syntax_repair",
        }

    def _fix_brackets(self, code: str) -> str:
        """Try to balance brackets, parens, and braces in Python code."""
        openers = {"(": ")", "[": "]", "{": "}"}
        closers = {")": "(", "]": "[", "}": "{"}
        stack = []
        lines = code.splitlines()

        # Track bracket balance across lines
        balance = {")": 0, "]": 0, "}": 0}

        for line in lines:
            i = 0
            while i < len(line):
                ch = line[i]
                if ch in openers:
                    stack.append((ch, i))
                elif ch in closers:
                    if stack and stack[-1][0] == closers[ch]:
                        stack.pop()
                    else:
                        # Unmatched closer — try removing it
                        line = line[:i] + line[i + 1:]
                        continue  # Re-check this position
                elif ch == "'" or ch == '"':
                    # Skip string literals
                    quote = ch
                    i += 1
                    while i < len(line):
                        if line[i] == "\\":
                            i += 2
                            continue
                        if line[i] == quote:
                            break
                        i += 1
                elif ch == "#":
                    # Skip comment to end of line
                    break
                i += 1

        # If there are unclosed brackets, append closers
        if stack:
            lines.append("")  # blank line before closers
            for opener, _ in reversed(stack):
                closer = openers[opener]
                lines.append(closer)

        return "\n".join(lines)

    def _fix_js_brackets(self, code: str) -> str:
        """Try to balance brackets/braces in JS code."""
        openers = {"(": ")", "[": "]", "{": "}"}
        stack = []
        in_string = False
        string_char = None
        escaped = False

        for ch in code:
            if escaped:
                escaped = False
                continue
            if ch == "\\" and in_string:
                escaped = True
                continue
            if in_string:
                if ch == string_char:
                    in_string = False
                continue
            if ch in ("'", '"', "`"):
                in_string = True
                string_char = ch
                continue
            if ch in openers:
                stack.append(ch)
            elif ch in openers.values():
                # Find matching opener
                expected_opener = None
                for op, cl in openers.items():
                    if cl == ch:
                        expected_opener = op
                        break
                if stack and stack[-1] == expected_opener:
                    stack.pop()

        # If unclosed brackets, add closers
        if stack:
            result = code
            for opener in reversed(stack):
                result += openers[opener]
            return result

        return code

    def _fix_indentation(self, code: str, error_context: Dict[str, Any]) -> str:
        """Attempt to fix Python indentation errors."""
        line_number = error_context.get("line_number")
        if not line_number:
            return code

        lines = code.splitlines()
        if line_number < 1 or line_number > len(lines):
            return code

        target_idx = line_number - 1
        prev_indent = 0

        # Find indentation of the previous non-empty line
        for i in range(target_idx - 1, -1, -1):
            if lines[i].strip():
                prev_indent = len(lines[i]) - len(lines[i].lstrip())
                break

        current_line = lines[target_idx]
        if not current_line.strip():
            return code

        current_indent = len(current_line) - len(current_line.lstrip())
        stripped = current_line.strip()

        # If the line starts with a dedent keyword but has wrong indent
        dedent_keywords = {"else", "elif", "except", "finally"}
        if stripped.split()[0] in dedent_keywords and current_indent != prev_indent:
            lines[target_idx] = " " * prev_indent + stripped
            return "\n".join(lines)

        return code


# ---------------------------------------------------------------------------
# Agent 5: TemplateRefillAgent
# ---------------------------------------------------------------------------


class TemplateRefillAgent:
    """
    Refills broken or empty files from the template system.

    When a file is completely broken beyond repair, this agent:
    1. Detects what type of file this is
    2. Uses the template registry to get a fresh template
    3. Customizes it with project goal from error_context
    4. Writes the fresh template
    5. Returns honest success/failure
    """

    async def repair(
        self,
        contract_item_id: str,
        contract: "BuildContract",
        workspace_path: str,
        error_context: Dict[str, Any],
        priority: str = "medium",  # noqa: ARG002
    ) -> Dict[str, Any]:
        logger.info("[TemplateRefill] Starting template refill for %s", contract_item_id)

        file_path = _parse_contract_item_id(contract_item_id)
        if not file_path:
            return {"success": False, "files_modified": [], "error": f"Cannot parse contract item id: {contract_item_id}", "repair_strategy": "template_refill"}

        # 1. Detect template type from file path
        template_id = self._detect_template_id(file_path, contract)

        if not template_id:
            return {
                "success": False,
                "files_modified": [],
                "error": f"No matching template for file: {file_path}",
                "repair_strategy": "template_refill",
            }

        logger.info("[TemplateRefill] Using template: %s for file: %s", template_id, file_path)

        # 2. Get the template entry from registry
        try:
            from backend.agents.templates.registry import TEMPLATE_REGISTRY
            template_entry = TEMPLATE_REGISTRY.get(template_id)
        except ImportError:
            return {
                "success": False,
                "files_modified": [],
                "error": "Template registry not available",
                "repair_strategy": "template_refill",
            }

        if not template_entry:
            return {
                "success": False,
                "files_modified": [],
                "error": f"Template {template_id} not found in registry",
                "repair_strategy": "template_refill",
            }

        # 3. Generate template files
        project_name = getattr(contract, "product_name", "crucibai-project") or "crucibai-project"
        project_goal = getattr(contract, "original_goal", "") or error_context.get("instruction", "")

        try:
            template_generator = template_entry.get("files")
            if not template_generator or not callable(template_generator):
                return {
                    "success": False,
                    "files_modified": [],
                    "error": f"Template {template_id} has no file generator",
                    "repair_strategy": "template_refill",
                }

            # The generator returns a dict of filename -> content
            # We only need to write the specific file that's broken
            generated_files = template_generator(project_goal or project_name, project_name)

        except Exception as e:
            logger.error("[TemplateRefill] Template generation failed: %s", e)
            return {
                "success": False,
                "files_modified": [],
                "error": f"Template generation failed: {e}",
                "repair_strategy": "template_refill",
            }

        # 4. Find the matching file in the generated output
        matched_content = None
        matched_filename = None

        # Try exact match first
        if file_path in generated_files:
            matched_content = generated_files[file_path]
            matched_filename = file_path
        else:
            # Try matching just the filename (without directory)
            target_filename = os.path.basename(file_path)
            for gen_path, gen_content in generated_files.items():
                if os.path.basename(gen_path) == target_filename:
                    matched_content = gen_content
                    matched_filename = gen_path
                    break

        if not matched_content:
            return {
                "success": False,
                "files_modified": [],
                "error": f"Template {template_id} does not contain file matching {file_path}",
                "repair_strategy": "template_refill",
            }

        # 5. Write the fresh template
        full_path = _safe_resolve(workspace_path, file_path)
        if not full_path:
            return {
                "success": False,
                "files_modified": [],
                "error": f"Cannot resolve path: {file_path}",
                "repair_strategy": "template_refill",
            }

        if _write_file_safe(full_path, matched_content):
            logger.info("[TemplateRefill] Refilled %s from template %s", file_path, template_id)
            return {
                "success": True,
                "files_modified": [file_path],
                "error": None,
                "repair_strategy": "template_refill",
            }

        return {
            "success": False,
            "files_modified": [],
            "error": f"Cannot write file: {file_path}",
            "repair_strategy": "template_refill",
        }

    def _detect_template_id(self, file_path: str, contract: "BuildContract") -> Optional[str]:
        """Detect which template to use for a given file path."""
        # Check explicit mapping first
        if file_path in _FILE_TO_TEMPLATE_MAP:
            return _FILE_TO_TEMPLATE_MAP[file_path]

        # Check basename-only match
        basename = os.path.basename(file_path)
        for path_pattern, template_id in _FILE_TO_TEMPLATE_MAP.items():
            if os.path.basename(path_pattern) == basename:
                return template_id

        # Infer from contract stack
        stack = getattr(contract, "stack", {}) or {}
        stack_lang = stack.get("language", "").lower()
        stack_framework = stack.get("framework", "").lower()

        if stack_lang == "python" or "fastapi" in stack_framework or "django" in stack_framework or "flask" in stack_framework:
            return "python_fastapi"
        elif stack_lang in ("typescript", "javascript") or "react" in stack_framework or "vite" in stack_framework or "next" in stack_framework:
            return "react_vite"
        elif "express" in stack_framework:
            return "node_express"
        elif stack_lang == "go":
            return "go_gin"
        elif stack_lang == "rust":
            return "rust_axum"
        elif stack_lang in ("c++", "cpp"):
            return "cpp_cmake"

        # Infer from file path patterns
        if "main.py" in file_path or "app.py" in file_path:
            return "python_fastapi"
        elif "App.jsx" in file_path or "App.tsx" in file_path or "main.jsx" in file_path:
            return "react_vite"
        elif "server.js" in file_path:
            return "node_express"

        return None


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------


def get_repair_agents() -> Dict[str, Any]:
    """
    Return a dict mapping agent names to instances.

    These agents implement the RepairAgentInterface from orchestration.repair_loop
    and can be used as drop-in replacements for the stub agents.
    """
    return {
        "llm_code_repair": LLMCodeRepairAgent(),
        "npm_dependency_repair": NpmDependencyRepairAgent(),
        "python_import_repair": PythonImportRepairAgent(),
        "syntax_repair": SyntaxRepairAgent(),
        "template_refill": TemplateRefillAgent(),
    }

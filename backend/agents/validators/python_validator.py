"""
Python Runtime Validator.

Stages:
  1. validate_syntax()  — py_compile every .py file
  2. validate_build()   — pip install -r requirements.txt, then import main
  3. validate_runtime() — start uvicorn, health-check /health, kill
  4. validate_integration() — test detected endpoints from main.py decorators
"""

import json
import logging
import os
import re
import subprocess
import time
from typing import Dict, List, Optional

from .base import BaseValidator, ValidationResult

logger = logging.getLogger(__name__)


class PythonValidator(BaseValidator):

    def __init__(self, workspace_path: str, timeout_seconds: int = 60):
        super().__init__(workspace_path, timeout_seconds)
        self._language = "python"

    # ------------------------------------------------------------------
    # 1. SYNTAX
    # ------------------------------------------------------------------

    def validate_syntax(self) -> ValidationResult:
        """
        Run ``python -m py_compile <file>`` for every .py file in the
        workspace.  Collect all errors and structured repair hints.
        """
        start = time.monotonic()

        valid, err = self.ensure_workspace()
        if not valid:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False,
                language="python",
                validator_type="syntax",
                errors=[err],
                warnings=[],
                files_checked=0,
                duration_ms=elapsed,
                command_used="",
                can_auto_repair=False,
                repair_hints=["workspace_missing_or_empty"],
            )

        py_files = self.find_files(self.workspace_path, [".py"])
        if not py_files:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=True,
                language="python",
                validator_type="syntax",
                errors=[],
                warnings=["No .py files found in workspace"],
                files_checked=0,
                duration_ms=elapsed,
                command_used="",
                can_auto_repair=False,
                repair_hints=[],
            )

        errors: List[str] = []
        warnings: List[str] = []
        all_hints: List[str] = []
        files_ok = 0
        cmd_parts: List[str] = []

        for filepath in py_files:
            rel = os.path.relpath(filepath, self.workspace_path)
            cmd = f"python -m py_compile {rel}"
            cmd_parts.append(cmd)
            stdout, stderr, rc, _ = self.run_command(cmd)

            if rc == 0:
                files_ok += 1
            else:
                # py_compile writes errors to stderr in the form:
                #   File "<path>", line N
                #     <code>
                # SyntaxError: <message>
                short_msg = stderr.strip().splitlines()[-1] if stderr.strip() else "unknown error"
                errors.append(f"{rel}: {short_msg}")
                all_hints.extend(self.parse_repair_hints(stderr, "python"))

        elapsed = int((time.monotonic() - start) * 1000)
        return ValidationResult(
            success=len(errors) == 0,
            language="python",
            validator_type="syntax",
            errors=errors,
            warnings=warnings,
            files_checked=len(py_files),
            duration_ms=elapsed,
            command_used="; ".join(cmd_parts[:5]) + ("..." if len(cmd_parts) > 5 else ""),
            can_auto_repair=len(all_hints) > 0,
            repair_hints=all_hints,
        )

    # ------------------------------------------------------------------
    # 2. BUILD
    # ------------------------------------------------------------------

    def validate_build(self) -> ValidationResult:
        """
        1. pip install -r requirements.txt  (if present)
        2. python -c "import main"           (verify imports resolve)

        Uses the system Python; sets PYTHONPATH so workspace modules are found.
        """
        start = time.monotonic()

        valid, err = self.ensure_workspace()
        if not valid:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False,
                language="python",
                validator_type="build",
                errors=[err],
                warnings=[],
                files_checked=0,
                duration_ms=elapsed,
                can_auto_repair=False,
                repair_hints=["workspace_missing_or_empty"],
            )

        errors: List[str] = []
        warnings: List[str] = []
        all_hints: List[str] = []
        build_output = ""
        cmd_used = ""
        files_checked = 0

        # --- Step A: install requirements ---
        req_file = os.path.join(self.workspace_path, "requirements.txt")
        if os.path.isfile(req_file):
            cmd = "pip install -r requirements.txt --quiet 2>&1"
            cmd_used = cmd
            stdout, stderr, rc, _ = self.run_command(cmd, timeout=120)
            build_output += stdout + "\n" + stderr
            if rc != 0:
                errors.append(f"pip install failed (rc={rc}): {stderr[:500]}")
                all_hints.extend(self.parse_repair_hints(stderr, "python"))
            else:
                logger.info("[python] pip install succeeded")
        else:
            warnings.append("No requirements.txt found — skipping dependency install")

        # --- Step B: import check ---
        main_py = os.path.join(self.workspace_path, "main.py")
        app_py = os.path.join(self.workspace_path, "app.py")
        target = None
        for candidate in [main_py, app_py]:
            if os.path.isfile(candidate):
                target = candidate
                break

        if target:
            module_name = os.path.splitext(os.path.basename(target))[0]
            import_cmd = f'python -c "import sys; sys.path.insert(0, \\"{self.workspace_path}\\"); import {module_name}; print(\\"OK\\")"'
            cmd_used += " && " + import_cmd if cmd_used else import_cmd
            stdout, stderr, rc, _ = self.run_command(
                import_cmd,
                env={"PYTHONPATH": self.workspace_path},
            )
            build_output += stdout + "\n" + stderr
            files_checked = 1
            if rc != 0:
                errors.append(f"import {module_name} failed: {stderr[:500]}")
                all_hints.extend(self.parse_repair_hints(stderr, "python"))
            else:
                logger.info("[python] import %s OK", module_name)
        else:
            warnings.append("No main.py or app.py found — skipping import check")

        elapsed = int((time.monotonic() - start) * 1000)
        return ValidationResult(
            success=len(errors) == 0,
            language="python",
            validator_type="build",
            errors=errors,
            warnings=warnings,
            files_checked=files_checked,
            duration_ms=elapsed,
            build_output=build_output[:10_000],
            command_used=cmd_used,
            can_auto_repair=len(all_hints) > 0,
            repair_hints=all_hints,
        )

    # ------------------------------------------------------------------
    # 3. RUNTIME
    # ------------------------------------------------------------------

    def validate_runtime(self, port: int = None) -> ValidationResult:
        """
        Start uvicorn in the background, wait for it to be ready,
        curl the /health endpoint, verify JSON ``{"status": "ok"}``,
        then kill the server.
        """
        start = time.monotonic()

        valid, err = self.ensure_workspace()
        if not valid:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False,
                language="python",
                validator_type="runtime",
                errors=[err],
                warnings=[],
                files_checked=0,
                duration_ms=elapsed,
                can_auto_repair=False,
                repair_hints=["workspace_missing_or_empty"],
            )

        _port = port or 8000
        errors: List[str] = []
        warnings: List[str] = []
        all_hints: List[str] = []

        # Determine how to start the server
        start_cmd = self._detect_start_command()
        if not start_cmd:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False,
                language="python",
                validator_type="runtime",
                errors=["Cannot detect how to start the Python server"],
                warnings=[
                    "Expected: main.py with uvicorn/app factory, or "
                    "an ASGI app callable 'app' in main.py"
                ],
                files_checked=0,
                duration_ms=elapsed,
                command_used="",
                can_auto_repair=False,
                repair_hints=["python_no_server_entrypoint"],
            )

        # Build the full command with uvicorn
        full_cmd = f"uvicorn {start_cmd} --host 0.0.0.0 --port {_port}"
        logger.info("[python] runtime: starting server with %r", full_cmd)

        proc: Optional[subprocess.Popen] = None
        try:
            proc = self.run_background(
                full_cmd,
                env={"PYTHONPATH": self.workspace_path},
            )

            # Wait for server to be ready (poll /health up to 10 s)
            health_url = f"http://localhost:{_port}/health"
            health_ok = False
            health_body = ""

            for attempt in range(20):
                time.sleep(0.5)
                stdout, stderr, rc, _ = self.run_command(
                    f'curl -s --max-time 3 "{health_url}"',
                    timeout=5,
                )
                if rc == 0 and stdout:
                    health_ok = True
                    health_body = stdout.strip()
                    break
                # Check if process crashed early
                if proc.poll() is not None:
                    _, crash_err, _, _ = proc.communicate(timeout=2)
                    errors.append(f"Server crashed on startup: {crash_err[:500]}")
                    all_hints.extend(self.parse_repair_hints(crash_err or "", "python"))
                    break

            if not errors:
                if not health_ok:
                    errors.append(
                        f"Server did not respond at {health_url} within 10 s"
                    )
                    all_hints.append("python_server_timeout:health_check_failed")
                else:
                    # Validate JSON response
                    try:
                        data = json.loads(health_body)
                        if data.get("status") != "ok":
                            errors.append(
                                f"Health check returned unexpected status: {data}"
                            )
                            all_hints.append(
                                "python_health_response_unexpected:"
                                + json.dumps(data)[:80]
                            )
                        else:
                            logger.info("[python] runtime health-check PASSED")
                    except json.JSONDecodeError:
                        errors.append(
                            f"Health endpoint did not return JSON: {health_body[:200]}"
                        )
                        all_hints.append("python_health_not_json")

        except Exception as exc:
            errors.append(f"Runtime validation failed: {exc}")
            all_hints.append(f"python_runtime_exception:{str(exc)[:60]}")
        finally:
            self.kill_background(proc)

        elapsed = int((time.monotonic() - start) * 1000)
        return ValidationResult(
            success=len(errors) == 0,
            language="python",
            validator_type="runtime",
            errors=errors,
            warnings=warnings,
            files_checked=1,
            duration_ms=elapsed,
            command_used=full_cmd,
            build_output="",
            can_auto_repair=len(all_hints) > 0,
            repair_hints=all_hints,
        )

    # ------------------------------------------------------------------
    # 4. INTEGRATION
    # ------------------------------------------------------------------

    def validate_integration(self, port: int = None) -> ValidationResult:
        """
        After starting the server, detect endpoints from FastAPI / Flask
        route decorators in main.py, then curl each and verify 200.
        """
        start = time.monotonic()

        valid, err = self.ensure_workspace()
        if not valid:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False,
                language="python",
                validator_type="integration",
                errors=[err],
                warnings=[],
                files_checked=0,
                duration_ms=elapsed,
                can_auto_repair=False,
                repair_hints=["workspace_missing_or_empty"],
            )

        _port = port or 8000
        errors: List[str] = []
        warnings: List[str] = []
        all_hints: List[str] = []
        endpoints = self._detect_endpoints()

        if not endpoints:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=True,
                language="python",
                validator_type="integration",
                errors=[],
                warnings=["No endpoints detected in main.py"],
                files_checked=0,
                duration_ms=elapsed,
                command_used="",
                can_auto_repair=False,
                repair_hints=[],
            )

        # Start server
        start_cmd = self._detect_start_command()
        if not start_cmd:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False,
                language="python",
                validator_type="integration",
                errors=["Cannot detect server entrypoint"],
                warnings=[],
                files_checked=0,
                duration_ms=elapsed,
                can_auto_repair=False,
                repair_hints=["python_no_server_entrypoint"],
            )

        full_cmd = f"uvicorn {start_cmd} --host 0.0.0.0 --port {_port}"
        proc: Optional[subprocess.Popen] = None
        try:
            proc = self.run_background(
                full_cmd,
                env={"PYTHONPATH": self.workspace_path},
            )

            # Wait for server
            time.sleep(3)

            # Check if process crashed
            if proc.poll() is not None:
                _, crash_err, _, _ = proc.communicate(timeout=2)
                errors.append(f"Server crashed: {crash_err[:300]}")
                all_hints.extend(self.parse_repair_hints(crash_err or "", "python"))
                elapsed = int((time.monotonic() - start) * 1000)
                return ValidationResult(
                    success=False,
                    language="python",
                    validator_type="integration",
                    errors=errors,
                    warnings=warnings,
                    files_checked=0,
                    duration_ms=elapsed,
                    command_used=full_cmd,
                    can_auto_repair=len(all_hints) > 0,
                    repair_hints=all_hints,
                )

            # Test each endpoint
            for ep in endpoints:
                url = f"http://localhost:{_port}{ep}"
                stdout, stderr, rc, _ = self.run_command(
                    f'curl -s -o /dev/null -w "%{{http_code}}" --max-time 5 "{url}"',
                    timeout=10,
                )
                status_code = stdout.strip()
                if rc != 0 or status_code.startswith("0"):
                    errors.append(f"Endpoint {ep}: no response (curl rc={rc})")
                    all_hints.append(f"python_endpoint_unreachable:{ep}")
                elif status_code not in ("200", "201", "204"):
                    warnings.append(f"Endpoint {ep}: HTTP {status_code} (expected 2xx)")
                else:
                    logger.info("[python] integration endpoint %s -> %s", ep, status_code)

        except Exception as exc:
            errors.append(f"Integration test failed: {exc}")
            all_hints.append(f"python_integration_exception:{str(exc)[:60]}")
        finally:
            self.kill_background(proc)

        elapsed = int((time.monotonic() - start) * 1000)
        return ValidationResult(
            success=len(errors) == 0,
            language="python",
            validator_type="integration",
            errors=errors,
            warnings=warnings,
            files_checked=len(endpoints),
            duration_ms=elapsed,
            command_used=full_cmd,
            can_auto_repair=len(all_hints) > 0,
            repair_hints=all_hints,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _detect_start_command(self) -> Optional[str]:
        """
        Detect how to start the server.

        Looks for:
          - main.py with an ``app`` or ``application`` variable (ASGI)
          - main.py that calls uvicorn.run() directly
        Returns the module:callable string for uvicorn CLI, or None.
        """
        main_py = os.path.join(self.workspace_path, "main.py")
        app_py = os.path.join(self.workspace_path, "app.py")
        for candidate in [main_py, app_py]:
            if not os.path.isfile(candidate):
                continue
            with open(candidate, "r", errors="replace") as f:
                content = f.read()
            module = os.path.splitext(os.path.basename(candidate))[0]

            # FastAPI: app = FastAPI(...)
            if re.search(r"^(app|application)\s*=\s*FastAPI", content, re.MULTILINE):
                return f"{module}:app"
            # Flask: app = Flask(...)
            if re.search(r"^(app|application)\s*=\s*Flask", content, re.MULTILINE):
                return f"{module}:app"
            # Generic ASGI app variable
            if re.search(r"^(app|application)\s*=", content, re.MULTILINE):
                return f"{module}:app"
        return None

    def _detect_endpoints(self) -> List[str]:
        """
        Scan main.py (and app.py) for route decorators.

        Detects:
          - FastAPI: @app.get("/path"), @app.post("/path"), @router.get(...)
          - Flask:   @app.route("/path")
        """
        endpoints: List[str] = []
        seen: set = set()

        for fname in ["main.py", "app.py"]:
            fpath = os.path.join(self.workspace_path, fname)
            if not os.path.isfile(fpath):
                continue
            with open(fpath, "r", errors="replace") as f:
                content = f.read()

            # FastAPI-style: @app.get("/path") or @app.post("/path")
            for m in re.finditer(
                r"@(?:app|router)\.(?:get|post|put|delete|patch)\(\s*[\"']([^\"']+)[\"']",
                content,
            ):
                ep = m.group(1)
                if ep not in seen:
                    seen.add(ep)
                    endpoints.append(ep)

            # Flask-style: @app.route("/path")
            for m in re.finditer(r"@app\.route\(\s*[\"']([^\"']+)[\"']", content):
                ep = m.group(1)
                if ep not in seen:
                    seen.add(ep)
                    endpoints.append(ep)

        return endpoints

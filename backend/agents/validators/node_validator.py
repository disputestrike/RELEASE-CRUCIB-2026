"""
Node.js Runtime Validator.

Stages:
  1. validate_syntax()  — node --check on every .js file
  2. validate_build()   — npm install, npm run build
  3. validate_runtime() — start server, health-check /health, kill
  4. validate_integration() — test detected routes
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


class NodeValidator(BaseValidator):

    def __init__(self, workspace_path: str, timeout_seconds: int = 60):
        super().__init__(workspace_path, timeout_seconds)
        self._language = "javascript"

    # ------------------------------------------------------------------
    # 1. SYNTAX
    # ------------------------------------------------------------------

    def validate_syntax(self) -> ValidationResult:
        """
        Run ``node --check <file>`` for every .js file.
        Also run ``node --check <file>`` for .mjs files.
        """
        start = time.monotonic()

        valid, err = self.ensure_workspace()
        if not valid:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="javascript", validator_type="syntax",
                errors=[err], warnings=[], files_checked=0, duration_ms=elapsed,
                can_auto_repair=False, repair_hints=["workspace_missing_or_empty"],
            )

        js_files = self.find_files(self.workspace_path, [".js", ".mjs"])
        if not js_files:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=True, language="javascript", validator_type="syntax",
                errors=[], warnings=["No .js files found"], files_checked=0,
                duration_ms=elapsed, can_auto_repair=False, repair_hints=[],
            )

        errors: List[str] = []
        warnings: List[str] = []
        all_hints: List[str] = []
        files_ok = 0
        cmd_parts: List[str] = []

        # Exclude node_modules and common non-source directories
        skip_dirs = {"node_modules", ".next", "dist", "build", "coverage"}

        for filepath in js_files:
            # Skip vendored / build artifacts
            if any(part in filepath for part in skip_dirs):
                continue

            rel = os.path.relpath(filepath, self.workspace_path)
            cmd = f"node --check {rel}"
            cmd_parts.append(cmd)
            stdout, stderr, rc, _ = self.run_command(cmd)

            if rc == 0:
                files_ok += 1
            else:
                short_msg = stderr.strip().splitlines()[-1] if stderr.strip() else "unknown error"
                errors.append(f"{rel}: {short_msg}")
                all_hints.extend(self.parse_repair_hints(stderr, "javascript"))

        elapsed = int((time.monotonic() - start) * 1000)
        return ValidationResult(
            success=len(errors) == 0,
            language="javascript",
            validator_type="syntax",
            errors=errors,
            warnings=warnings,
            files_checked=files_ok,
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
        1. npm install --legacy-peer-deps  (if package.json exists)
        2. npm run build                   (if build script defined)
        """
        start = time.monotonic()

        valid, err = self.ensure_workspace()
        if not valid:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="javascript", validator_type="build",
                errors=[err], warnings=[], files_checked=0, duration_ms=elapsed,
                can_auto_repair=False, repair_hints=["workspace_missing_or_empty"],
            )

        errors: List[str] = []
        warnings: List[str] = []
        all_hints: List[str] = []
        build_output = ""
        cmd_used = ""

        # Check for package.json
        pkg_path = os.path.join(self.workspace_path, "package.json")
        if not os.path.isfile(pkg_path):
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="javascript", validator_type="build",
                errors=["No package.json found"], warnings=[],
                files_checked=0, duration_ms=elapsed,
                can_auto_repair=True,
                repair_hints=["node_missing_package_json"],
            )

        # --- Step A: npm install ---
        install_cmd = "npm install --legacy-peer-deps 2>&1"
        cmd_used = install_cmd
        stdout, stderr, rc, _ = self.run_command(install_cmd, timeout=120)
        build_output += stdout + "\n" + stderr
        combined = stdout + stderr
        if rc != 0:
            errors.append(f"npm install failed (rc={rc}): {stderr[:500]}")
            all_hints.extend(self.parse_repair_hints(stderr, "javascript"))
        else:
            logger.info("[node] npm install succeeded")

        # --- Step B: npm run build ---
        # Read package.json to check for build script
        try:
            with open(pkg_path, "r", errors="replace") as f:
                pkg = json.load(f)
            has_build = bool(pkg.get("scripts", {}).get("build"))
        except (json.JSONDecodeError, OSError):
            has_build = False

        if has_build:
            build_cmd = "npm run build 2>&1"
            cmd_used += " && " + build_cmd
            stdout, stderr, rc, _ = self.run_command(build_cmd, timeout=120)
            build_output += "\n--- BUILD ---\n" + stdout + "\n" + stderr
            if rc != 0:
                errors.append(f"npm run build failed (rc={rc}): {stderr[:500]}")
                all_hints.extend(self.parse_repair_hints(stderr, "javascript"))
            else:
                logger.info("[node] npm run build succeeded")
        else:
            warnings.append("No 'build' script in package.json — skipping build step")

        elapsed = int((time.monotonic() - start) * 1000)
        return ValidationResult(
            success=len(errors) == 0,
            language="javascript",
            validator_type="build",
            errors=errors,
            warnings=warnings,
            files_checked=1 if has_build else 0,
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
        Start the Node.js server (npm run dev || node server.js),
        wait up to 10 seconds, curl /health, kill server.
        """
        start = time.monotonic()

        valid, err = self.ensure_workspace()
        if not valid:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="javascript", validator_type="runtime",
                errors=[err], warnings=[], files_checked=0, duration_ms=elapsed,
                can_auto_repair=False, repair_hints=["workspace_missing_or_empty"],
            )

        _port = port or 3000
        errors: List[str] = []
        warnings: List[str] = []
        all_hints: List[str] = []

        # Detect start command
        start_cmd = self._detect_start_command(_port)
        if not start_cmd:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="javascript", validator_type="runtime",
                errors=["Cannot detect Node.js server start command"],
                warnings=["Expected: npm run dev, node server.js, or node index.js"],
                files_checked=0, duration_ms=elapsed,
                can_auto_repair=False,
                repair_hints=["node_no_server_entrypoint"],
            )

        proc: Optional[subprocess.Popen] = None
        try:
            proc = self.run_background(start_cmd)

            # Poll /health
            health_url = f"http://localhost:{_port}/health"
            health_ok = False
            health_body = ""

            for attempt in range(20):
                time.sleep(0.5)
                stdout, stderr, rc, _ = self.run_command(
                    f'curl -s --max-time 3 "{health_url}"', timeout=5
                )
                if rc == 0 and stdout:
                    health_ok = True
                    health_body = stdout.strip()
                    break
                if proc.poll() is not None:
                    _, crash_err, _, _ = proc.communicate(timeout=2)
                    errors.append(f"Server crashed: {crash_err[:500]}")
                    all_hints.extend(self.parse_repair_hints(crash_err or "", "javascript"))
                    break

            if not errors:
                if not health_ok:
                    errors.append(f"Server did not respond at {health_url} within 10 s")
                    all_hints.append("node_server_timeout:health_check_failed")
                else:
                    try:
                        data = json.loads(health_body)
                        if data.get("status") != "ok":
                            errors.append(f"Unexpected health response: {data}")
                            all_hints.append(f"node_health_unexpected:{json.dumps(data)[:80]}")
                        else:
                            logger.info("[node] runtime health-check PASSED")
                    except json.JSONDecodeError:
                        # Non-JSON health is acceptable for Node (some frameworks return text)
                        if health_body:
                            logger.info("[node] runtime health responded (non-JSON): %s", health_body[:100])
                        else:
                            errors.append("Health endpoint returned empty response")
                            all_hints.append("node_health_empty_response")

        except Exception as exc:
            errors.append(f"Runtime validation failed: {exc}")
            all_hints.append(f"node_runtime_exception:{str(exc)[:60]}")
        finally:
            self.kill_background(proc)

        elapsed = int((time.monotonic() - start) * 1000)
        return ValidationResult(
            success=len(errors) == 0,
            language="javascript",
            validator_type="runtime",
            errors=errors,
            warnings=warnings,
            files_checked=1,
            duration_ms=elapsed,
            command_used=start_cmd,
            can_auto_repair=len(all_hints) > 0,
            repair_hints=all_hints,
        )

    # ------------------------------------------------------------------
    # 4. INTEGRATION
    # ------------------------------------------------------------------

    def validate_integration(self, port: int = None) -> ValidationResult:
        """
        Start server, test all detected routes from Express / route files.
        """
        start = time.monotonic()

        valid, err = self.ensure_workspace()
        if not valid:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="javascript", validator_type="integration",
                errors=[err], warnings=[], files_checked=0, duration_ms=elapsed,
                can_auto_repair=False, repair_hints=["workspace_missing_or_empty"],
            )

        _port = port or 3000
        errors: List[str] = []
        warnings: List[str] = []
        all_hints: List[str] = []
        endpoints = self._detect_endpoints()

        if not endpoints:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=True, language="javascript", validator_type="integration",
                errors=[], warnings=["No endpoints detected"], files_checked=0,
                duration_ms=elapsed, can_auto_repair=False, repair_hints=[],
            )

        start_cmd = self._detect_start_command(_port)
        if not start_cmd:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="javascript", validator_type="integration",
                errors=["Cannot detect server start command"], warnings=[],
                files_checked=0, duration_ms=elapsed, can_auto_repair=False,
                repair_hints=["node_no_server_entrypoint"],
            )

        proc: Optional[subprocess.Popen] = None
        try:
            proc = self.run_background(start_cmd)
            time.sleep(3)

            if proc.poll() is not None:
                _, crash_err, _, _ = proc.communicate(timeout=2)
                errors.append(f"Server crashed: {crash_err[:300]}")
                all_hints.extend(self.parse_repair_hints(crash_err or "", "javascript"))
            else:
                for ep in endpoints:
                    url = f"http://localhost:{_port}{ep}"
                    stdout, stderr, rc, _ = self.run_command(
                        f'curl -s -o /dev/null -w "%{{http_code}}" --max-time 5 "{url}"',
                        timeout=10,
                    )
                    status_code = stdout.strip()
                    if rc != 0 or status_code.startswith("0"):
                        errors.append(f"Endpoint {ep}: no response")
                        all_hints.append(f"node_endpoint_unreachable:{ep}")
                    elif status_code not in ("200", "201", "204", "301", "302"):
                        warnings.append(f"Endpoint {ep}: HTTP {status_code}")
                    else:
                        logger.info("[node] integration %s -> %s", ep, status_code)

        except Exception as exc:
            errors.append(f"Integration test failed: {exc}")
            all_hints.append(f"node_integration_exception:{str(exc)[:60]}")
        finally:
            self.kill_background(proc)

        elapsed = int((time.monotonic() - start) * 1000)
        return ValidationResult(
            success=len(errors) == 0,
            language="javascript",
            validator_type="integration",
            errors=errors,
            warnings=warnings,
            files_checked=len(endpoints),
            duration_ms=elapsed,
            command_used=start_cmd,
            can_auto_repair=len(all_hints) > 0,
            repair_hints=all_hints,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _detect_start_command(self, port: int) -> Optional[str]:
        """Detect how to start the Node.js server."""
        pkg_path = os.path.join(self.workspace_path, "package.json")
        if not os.path.isfile(pkg_path):
            # Fallback: try common entry points
            for entry in ["server.js", "index.js", "app.js", "main.js"]:
                if os.path.isfile(os.path.join(self.workspace_path, entry)):
                    return f"PORT={port} node {entry}"
            return None

        try:
            with open(pkg_path, "r", errors="replace") as f:
                pkg = json.load(f)
            scripts = pkg.get("scripts", {})
        except (json.JSONDecodeError, OSError):
            return None

        # Prefer dev script, then start, then serve
        for script_name in ["dev", "start", "serve"]:
            if script_name in scripts:
                return f"PORT={port} npm run {script_name}"

        # Fallback to entry files
        for entry in ["server.js", "index.js", "app.js", "main.js"]:
            if os.path.isfile(os.path.join(self.workspace_path, entry)):
                return f"PORT={port} node {entry}"

        return None

    def _detect_endpoints(self) -> List[str]:
        """
        Scan JavaScript source files for route definitions.

        Detects:
          - Express: app.get('/path', ...), router.get('/path', ...)
          - app.post('/path', ...), etc.
        """
        endpoints: List[str] = []
        seen: set = set()
        skip_dirs = {"node_modules", ".next", "dist", "build", "coverage"}

        js_files = self.find_files(self.workspace_path, [".js", ".mjs"])
        for fpath in js_files:
            if any(part in fpath for part in skip_dirs):
                continue
            try:
                with open(fpath, "r", errors="replace") as f:
                    content = f.read()
            except OSError:
                continue

            # Express-style: app.get("/path", ...) or router.get("/path", ...)
            for m in re.finditer(
                r"(?:app|router)\.(?:get|post|put|delete|patch)\(\s*[\"']([^\"']+)[\"']",
                content,
            ):
                ep = m.group(1)
                if ep not in seen and not ep.startswith("*"):  # skip wildcard middleware
                    seen.add(ep)
                    endpoints.append(ep)

        return endpoints

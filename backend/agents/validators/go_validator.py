"""
Go Runtime Validator.

Stages:
  1. validate_syntax()  — go vet ./...
  2. validate_build()   — go build ./...
  3. validate_runtime() — start binary in background, health-check, kill
  4. validate_integration() — test detected endpoints
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


class GoValidator(BaseValidator):

    def __init__(self, workspace_path: str, timeout_seconds: int = 60):
        super().__init__(workspace_path, timeout_seconds)
        self._language = "go"

    # ------------------------------------------------------------------
    # 1. SYNTAX
    # ------------------------------------------------------------------

    def validate_syntax(self) -> ValidationResult:
        """
        Run ``go vet ./...`` which performs static analysis beyond
        simple parsing — catches suspicious code, unused variables,
        incorrect printf formats, etc.
        """
        start = time.monotonic()

        valid, err = self.ensure_workspace()
        if not valid:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="go", validator_type="syntax",
                errors=[err], warnings=[], files_checked=0, duration_ms=elapsed,
                can_auto_repair=False, repair_hints=["workspace_missing_or_empty"],
            )

        go_files = self.find_files(self.workspace_path, [".go"])
        # Exclude vendor directory
        go_files = [f for f in go_files if "/vendor/" not in f]

        if not go_files:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=True, language="go", validator_type="syntax",
                errors=[], warnings=["No .go files found"], files_checked=0,
                duration_ms=elapsed, can_auto_repair=False, repair_hints=[],
            )

        # Check for go.mod
        go_mod = os.path.join(self.workspace_path, "go.mod")
        if not os.path.isfile(go_mod):
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="go", validator_type="syntax",
                errors=["No go.mod found"], warnings=[],
                files_checked=len(go_files), duration_ms=elapsed,
                can_auto_repair=True,
                repair_hints=["go_missing_gomod:run_go_mod_init"],
            )

        errors: List[str] = []
        warnings: List[str] = []
        all_hints: List[str] = []

        cmd = "go vet ./... 2>&1"
        stdout, stderr, rc, _ = self.run_command(cmd, timeout=90)
        combined = stdout + stderr

        if rc != 0:
            # Parse go vet output
            # Format: file.go:line:col: message
            error_lines = []
            for line in combined.strip().splitlines():
                if ".go:" in line:
                    error_lines.append(line.strip())

            if error_lines:
                unique = list(dict.fromkeys(error_lines))[:30]
                errors.extend(unique)
            else:
                errors.append(f"go vet failed (rc={rc}): {combined[:500]}")

            all_hints.extend(self.parse_repair_hints(combined, "go"))
        else:
            if combined.strip():
                # go vet succeeded but produced warnings
                warnings.append(combined.strip()[:500])
            logger.info("[go] go vet PASSED (%d files)", len(go_files))

        elapsed = int((time.monotonic() - start) * 1000)
        return ValidationResult(
            success=len(errors) == 0,
            language="go",
            validator_type="syntax",
            errors=errors,
            warnings=warnings,
            files_checked=len(go_files),
            duration_ms=elapsed,
            command_used=cmd,
            can_auto_repair=len(all_hints) > 0,
            repair_hints=all_hints,
        )

    # ------------------------------------------------------------------
    # 2. BUILD
    # ------------------------------------------------------------------

    def validate_build(self) -> ValidationResult:
        """
        Run ``go build ./...`` to compile all packages.
        """
        start = time.monotonic()

        valid, err = self.ensure_workspace()
        if not valid:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="go", validator_type="build",
                errors=[err], warnings=[], files_checked=0, duration_ms=elapsed,
                can_auto_repair=False, repair_hints=["workspace_missing_or_empty"],
            )

        go_mod = os.path.join(self.workspace_path, "go.mod")
        if not os.path.isfile(go_mod):
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="go", validator_type="build",
                errors=["No go.mod found"], warnings=[],
                files_checked=0, duration_ms=elapsed,
                can_auto_repair=True,
                repair_hints=["go_missing_gomod:run_go_mod_init"],
            )

        errors: List[str] = []
        warnings: List[str] = []
        all_hints: List[str] = []

        # --- Step A: go mod download ---
        stdout, stderr, rc, _ = self.run_command("go mod download 2>&1", timeout=90)
        if rc != 0:
            # Non-fatal: go build will handle missing deps
            warnings.append(f"go mod download had issues: {stderr[:300]}")
        else:
            logger.info("[go] go mod download succeeded")

        # --- Step B: go build ---
        cmd = "go build ./... 2>&1"
        stdout, stderr, rc, _ = self.run_command(cmd, timeout=120)
        combined = stdout + stderr

        if rc != 0:
            error_lines = []
            for line in combined.strip().splitlines():
                if ".go:" in line:
                    error_lines.append(line.strip())
            if error_lines:
                unique = list(dict.fromkeys(error_lines))[:30]
                errors.extend(unique)
            else:
                errors.append(f"go build failed (rc={rc}): {combined[:500]}")
            all_hints.extend(self.parse_repair_hints(combined, "go"))
        else:
            logger.info("[go] go build PASSED")

        elapsed = int((time.monotonic() - start) * 1000)
        return ValidationResult(
            success=len(errors) == 0,
            language="go",
            validator_type="build",
            errors=errors,
            warnings=warnings,
            files_checked=len(self.find_files(self.workspace_path, [".go"])),
            duration_ms=elapsed,
            build_output=combined[:10_000],
            command_used=cmd,
            can_auto_repair=len(all_hints) > 0,
            repair_hints=all_hints,
        )

    # ------------------------------------------------------------------
    # 3. RUNTIME
    # ------------------------------------------------------------------

    def validate_runtime(self, port: int = None) -> ValidationResult:
        """
        Build and start the Go binary in background, health-check /health, kill.
        """
        start = time.monotonic()

        valid, err = self.ensure_workspace()
        if not valid:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="go", validator_type="runtime",
                errors=[err], warnings=[], files_checked=0, duration_ms=elapsed,
                can_auto_repair=False, repair_hints=["workspace_missing_or_empty"],
            )

        _port = port or 8080
        errors: List[str] = []
        warnings: List[str] = []
        all_hints: List[str] = []

        # Detect if this is a server (main package)
        is_server = self._detect_server_code()
        if not is_server:
            # Just run it and check exit code
            cmd = "go run . 2>&1"
            stdout, stderr, rc, elapsed = self.run_command(cmd, timeout=10)
            total_elapsed = int((time.monotonic() - start) * 1000)
            if rc == 0 or (rc == -1 and (stdout or stderr)):
                # Success or timeout with output (might be CLI tool)
                if rc == -1:
                    warnings.append("Binary timed out (might be waiting for input)")
            elif rc != 0:
                errors.append(f"go run failed (rc={rc}): {stderr[:500]}")
                all_hints.extend(self.parse_repair_hints(stderr, "go"))

            return ValidationResult(
                success=len(errors) == 0,
                language="go",
                validator_type="runtime",
                errors=errors,
                warnings=warnings,
                files_checked=1,
                duration_ms=total_elapsed,
                command_used=cmd,
                build_output=(stdout + "\n" + stderr)[:5_000],
                can_auto_repair=len(all_hints) > 0,
                repair_hints=all_hints,
            )

        # It's a server — build first, then start
        build_cmd = "go build -o /tmp/crucib_go_app . 2>&1"
        stdout, stderr, rc, _ = self.run_command(build_cmd, timeout=120)
        if rc != 0:
            errors.append(f"go build failed: {stderr[:500]}")
            all_hints.extend(self.parse_repair_hints(stderr, "go"))
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="go", validator_type="runtime",
                errors=errors, warnings=[], files_checked=1,
                duration_ms=elapsed, command_used=build_cmd,
                can_auto_repair=len(all_hints) > 0, repair_hints=all_hints,
            )

        # Start the binary
        proc: Optional[subprocess.Popen] = None
        try:
            proc = self.run_background("/tmp/crucib_go_app")

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
                    all_hints.extend(self.parse_repair_hints(crash_err or "", "go"))
                    break

            if not errors:
                if not health_ok:
                    errors.append(f"Server did not respond at {health_url} within 10 s")
                    all_hints.append("go_server_timeout:health_check_failed")
                else:
                    try:
                        data = json.loads(health_body)
                        if data.get("status") == "ok":
                            logger.info("[go] runtime health-check PASSED")
                        else:
                            errors.append(f"Unexpected health response: {data}")
                    except json.JSONDecodeError:
                        if health_body:
                            logger.info("[go] health responded (non-JSON)")
                        else:
                            errors.append("Health endpoint returned empty response")

        except Exception as exc:
            errors.append(f"Runtime validation failed: {exc}")
            all_hints.append(f"go_runtime_exception:{str(exc)[:60]}")
        finally:
            self.kill_background(proc)
            # Clean up temp binary
            try:
                os.remove("/tmp/crucib_go_app")
            except OSError:
                pass

        elapsed = int((time.monotonic() - start) * 1000)
        return ValidationResult(
            success=len(errors) == 0,
            language="go",
            validator_type="runtime",
            errors=errors,
            warnings=warnings,
            files_checked=1,
            duration_ms=elapsed,
            command_used=build_cmd,
            can_auto_repair=len(all_hints) > 0,
            repair_hints=all_hints,
        )

    # ------------------------------------------------------------------
    # 4. INTEGRATION
    # ------------------------------------------------------------------

    def validate_integration(self, port: int = None) -> ValidationResult:
        """
        Start server, test detected endpoints from Go route handlers.
        """
        start = time.monotonic()

        valid, err = self.ensure_workspace()
        if not valid:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="go", validator_type="integration",
                errors=[err], warnings=[], files_checked=0, duration_ms=elapsed,
                can_auto_repair=False, repair_hints=["workspace_missing_or_empty"],
            )

        _port = port or 8080
        errors: List[str] = []
        warnings: List[str] = []
        all_hints: List[str] = []
        endpoints = self._detect_endpoints()

        if not endpoints:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=True, language="go", validator_type="integration",
                errors=[], warnings=["No endpoints detected"], files_checked=0,
                duration_ms=elapsed, can_auto_repair=False, repair_hints=[],
            )

        # Build
        build_cmd = "go build -o /tmp/crucib_go_app . 2>&1"
        stdout, stderr, rc, _ = self.run_command(build_cmd, timeout=120)
        if rc != 0:
            errors.append(f"go build failed: {stderr[:500]}")
            all_hints.extend(self.parse_repair_hints(stderr, "go"))
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="go", validator_type="integration",
                errors=errors, warnings=[], files_checked=0,
                duration_ms=elapsed, command_used=build_cmd,
                can_auto_repair=len(all_hints) > 0, repair_hints=all_hints,
            )

        proc: Optional[subprocess.Popen] = None
        try:
            proc = self.run_background("/tmp/crucib_go_app")
            time.sleep(3)

            if proc.poll() is not None:
                _, crash_err, _, _ = proc.communicate(timeout=2)
                errors.append(f"Server crashed: {crash_err[:300]}")
                all_hints.extend(self.parse_repair_hints(crash_err or "", "go"))
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
                        all_hints.append(f"go_endpoint_unreachable:{ep}")
                    elif status_code not in ("200", "201", "204"):
                        warnings.append(f"Endpoint {ep}: HTTP {status_code}")
                    else:
                        logger.info("[go] integration %s -> %s", ep, status_code)

        except Exception as exc:
            errors.append(f"Integration test failed: {exc}")
            all_hints.append(f"go_integration_exception:{str(exc)[:60]}")
        finally:
            self.kill_background(proc)
            try:
                os.remove("/tmp/crucib_go_app")
            except OSError:
                pass

        elapsed = int((time.monotonic() - start) * 1000)
        return ValidationResult(
            success=len(errors) == 0,
            language="go",
            validator_type="integration",
            errors=errors,
            warnings=warnings,
            files_checked=len(endpoints),
            duration_ms=elapsed,
            command_used=build_cmd,
            can_auto_repair=len(all_hints) > 0,
            repair_hints=all_hints,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _detect_server_code(self) -> bool:
        """
        Check if Go source contains HTTP server code.
        """
        server_indicators = [
            "http.ListenAndServe(", "http.ListenAndServeTLS(",
            "http.Server{", "http.NewServeMux()",
            "gin.Default()", "gin.New()",
            "echo.New()", "fiber.New()",
            "chi.NewRouter()",
            "gorilla/mux", "labstack/echo",
        ]
        for filepath in self.find_files(self.workspace_path, [".go"]):
            if "/vendor/" in filepath:
                continue
            try:
                with open(filepath, "r", errors="replace") as f:
                    content = f.read()
                for indicator in server_indicators:
                    if indicator in content:
                        return True
            except OSError:
                continue
        return False

    def _detect_endpoints(self) -> List[str]:
        """
        Scan Go source for route handler registrations.

        Detects:
          - net/http: http.HandleFunc("/path", ...)
          - gorilla/mux: r.HandleFunc("/path", ...)
          - gin: r.GET("/path", ...), r.POST("/path", ...)
          - echo: e.GET("/path", ...), e.POST("/path", ...)
          - chi: r.Get("/path", ...), r.Post("/path", ...)
        """
        endpoints: List[str] = []
        seen: set = set()

        go_files = self.find_files(self.workspace_path, [".go"])
        for fpath in go_files:
            if "/vendor/" in filepath if 'filepath' in dir() else "/vendor/" in fpath:
                continue
            try:
                with open(fpath, "r", errors="replace") as f:
                    content = f.read()
            except OSError:
                continue

            # net/http.HandleFunc
            for m in re.finditer(r'HandleFunc\(\s*"([^"]+)"', content):
                ep = m.group(1)
                if ep not in seen:
                    seen.add(ep)
                    endpoints.append(ep)

            # gorilla/mux HandleFunc
            for m in re.finditer(r'\w+\.HandleFunc\(\s*"([^"]+)"', content):
                ep = m.group(1)
                if ep not in seen:
                    seen.add(ep)
                    endpoints.append(ep)

            # gin: r.GET("/path", ...)
            for m in re.finditer(r'\w+\.(?:GET|POST|PUT|DELETE|PATCH)\(\s*"([^"]+)"', content):
                ep = m.group(1)
                if ep not in seen:
                    seen.add(ep)
                    endpoints.append(ep)

            # echo: e.Get("/path", ...)
            for m in re.finditer(r'\w+\.(?:Get|Post|Put|Delete|Patch)\(\s*"([^"]+)"', content):
                ep = m.group(1)
                if ep not in seen:
                    seen.add(ep)
                    endpoints.append(ep)

            # chi: r.Get("/path", ...)
            for m in re.finditer(r'\w+\.(?:Get|Post|Put|Delete|Patch|Route)\(\s*"([^"]+)"', content):
                ep = m.group(1)
                if ep not in seen:
                    seen.add(ep)
                    endpoints.append(ep)

        return endpoints

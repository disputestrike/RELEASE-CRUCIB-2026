"""
Rust Runtime Validator.

Stages:
  1. validate_syntax()  — cargo check
  2. validate_build()   — cargo build
  3. validate_runtime() — cargo run briefly, check exit code
  4. validate_integration() — start server, test endpoints
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


class RustValidator(BaseValidator):

    def __init__(self, workspace_path: str, timeout_seconds: int = 60):
        super().__init__(workspace_path, timeout_seconds)
        self._language = "rust"

    # ------------------------------------------------------------------
    # 1. SYNTAX
    # ------------------------------------------------------------------

    def validate_syntax(self) -> ValidationResult:
        """
        Run ``cargo check`` which type-checks the entire crate without
        producing an artifact.  This catches syntax errors, type mismatches,
        unused imports, and many other issues.
        """
        start = time.monotonic()

        valid, err = self.ensure_workspace()
        if not valid:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="rust", validator_type="syntax",
                errors=[err], warnings=[], files_checked=0, duration_ms=elapsed,
                can_auto_repair=False, repair_hints=["workspace_missing_or_empty"],
            )

        rs_files = self.find_files(self.workspace_path, [".rs"])
        if not rs_files:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=True, language="rust", validator_type="syntax",
                errors=[], warnings=["No .rs files found"], files_checked=0,
                duration_ms=elapsed, can_auto_repair=False, repair_hints=[],
            )

        # Check for Cargo.toml
        cargo_toml = os.path.join(self.workspace_path, "Cargo.toml")
        if not os.path.isfile(cargo_toml):
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="rust", validator_type="syntax",
                errors=["No Cargo.toml found"], warnings=[],
                files_checked=len(rs_files), duration_ms=elapsed,
                can_auto_repair=True,
                repair_hints=["rust_missing_cargo_toml:run_cargo_init"],
            )

        errors: List[str] = []
        warnings: List[str] = []
        all_hints: List[str] = []

        cmd = "cargo check 2>&1"
        stdout, stderr, rc, _ = self.run_command(cmd, timeout=120)
        combined = stdout + stderr

        if rc != 0:
            # Parse Rust compiler errors
            # Format: --> file.rs:line:col
            #         error[E0425]: message
            error_lines = []
            for line in combined.strip().splitlines():
                if "error" in line.lower() and (".rs:" in line or "-->" in line):
                    error_lines.append(line.strip())

            if error_lines:
                # Deduplicate and limit
                unique = list(dict.fromkeys(error_lines))[:30]
                errors.extend(unique)
            else:
                errors.append(f"cargo check failed (rc={rc}): {combined[:500]}")

            all_hints.extend(self.parse_repair_hints(combined, "rust"))
        else:
            # Collect warnings from cargo check output
            warn_lines = []
            for line in combined.strip().splitlines():
                if "warning" in line.lower() and ".rs:" in line:
                    warn_lines.append(line.strip())
            if warn_lines:
                warnings.extend(warn_lines[:10])
            logger.info("[rust] cargo check PASSED (%d files)", len(rs_files))

        elapsed = int((time.monotonic() - start) * 1000)
        return ValidationResult(
            success=len(errors) == 0,
            language="rust",
            validator_type="syntax",
            errors=errors,
            warnings=warnings,
            files_checked=len(rs_files),
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
        Run ``cargo build`` to compile the crate in debug mode.
        """
        start = time.monotonic()

        valid, err = self.ensure_workspace()
        if not valid:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="rust", validator_type="build",
                errors=[err], warnings=[], files_checked=0, duration_ms=elapsed,
                can_auto_repair=False, repair_hints=["workspace_missing_or_empty"],
            )

        cargo_toml = os.path.join(self.workspace_path, "Cargo.toml")
        if not os.path.isfile(cargo_toml):
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="rust", validator_type="build",
                errors=["No Cargo.toml found"], warnings=[],
                files_checked=0, duration_ms=elapsed,
                can_auto_repair=True,
                repair_hints=["rust_missing_cargo_toml:run_cargo_init"],
            )

        errors: List[str] = []
        warnings: List[str] = []
        all_hints: List[str] = []

        cmd = "cargo build 2>&1"
        stdout, stderr, rc, _ = self.run_command(cmd, timeout=180)
        combined = stdout + stderr

        if rc != 0:
            error_lines = []
            for line in combined.strip().splitlines():
                if "error" in line.lower() and (".rs:" in line or "-->" in line):
                    error_lines.append(line.strip())
            if error_lines:
                unique = list(dict.fromkeys(error_lines))[:30]
                errors.extend(unique)
            else:
                errors.append(f"cargo build failed (rc={rc}): {combined[:500]}")
            all_hints.extend(self.parse_repair_hints(combined, "rust"))
        else:
            logger.info("[rust] cargo build PASSED")

        elapsed = int((time.monotonic() - start) * 1000)
        return ValidationResult(
            success=len(errors) == 0,
            language="rust",
            validator_type="build",
            errors=errors,
            warnings=warnings,
            files_checked=len(self.find_files(self.workspace_path, [".rs"])),
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
        Run ``cargo run`` briefly.  If the binary exits 0, great.
        If it times out (server process), also acceptable if it produced
        output.  If it crashes, report the error.
        """
        start = time.monotonic()

        valid, err = self.ensure_workspace()
        if not valid:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="rust", validator_type="runtime",
                errors=[err], warnings=[], files_checked=0, duration_ms=elapsed,
                can_auto_repair=False, repair_hints=["workspace_missing_or_empty"],
            )

        _port = port or 8080
        errors: List[str] = []
        warnings: List[str] = []
        all_hints: List[str] = []

        # Check if this is a server (look for HTTP-related deps or code)
        is_server = self._detect_server_code()

        if is_server:
            # Build first, then start binary in background
            cmd = "cargo build 2>&1"
            stdout, stderr, rc, _ = self.run_command(cmd, timeout=180)
            if rc != 0:
                errors.append(f"cargo build failed: {stderr[:500]}")
                all_hints.extend(self.parse_repair_hints(stderr, "rust"))
                elapsed = int((time.monotonic() - start) * 1000)
                return ValidationResult(
                    success=False, language="rust", validator_type="runtime",
                    errors=errors, warnings=[], files_checked=1,
                    duration_ms=elapsed, command_used=cmd,
                    can_auto_repair=len(all_hints) > 0, repair_hints=all_hints,
                )

            # Find the binary
            binary = self._find_binary()
            if not binary:
                errors.append("Built successfully but cannot find binary")
                elapsed = int((time.monotonic() - start) * 1000)
                return ValidationResult(
                    success=False, language="rust", validator_type="runtime",
                    errors=errors, warnings=[], files_checked=1,
                    duration_ms=elapsed, can_auto_repair=False, repair_hints=[],
                )

            proc: Optional[subprocess.Popen] = None
            try:
                proc = self.run_background(binary)

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
                        all_hints.extend(self.parse_repair_hints(crash_err or "", "rust"))
                        break

                if not errors:
                    if not health_ok:
                        errors.append(f"Server did not respond at {health_url} within 10 s")
                        all_hints.append("rust_server_timeout:health_check_failed")
                    else:
                        try:
                            data = json.loads(health_body)
                            if data.get("status") == "ok":
                                logger.info("[rust] runtime health-check PASSED")
                            else:
                                errors.append(f"Unexpected health response: {data}")
                        except json.JSONDecodeError:
                            if health_body:
                                logger.info("[rust] health responded (non-JSON)")
                            else:
                                errors.append("Health endpoint returned empty response")

            except Exception as exc:
                errors.append(f"Runtime validation failed: {exc}")
                all_hints.append(f"rust_runtime_exception:{str(exc)[:60]}")
            finally:
                self.kill_background(proc)
        else:
            # Just run briefly and check exit code
            cmd = "cargo run 2>&1"
            stdout, stderr, rc, elapsed = self.run_command(cmd, timeout=15)

            if rc == 0:
                logger.info("[rust] cargo run exited cleanly")
            elif rc == -1:
                # Timeout — might be a CLI waiting for input
                if stdout or stderr:
                    warnings.append("Binary timed out (might be waiting for input)")
                    all_hints.append("rust_binary_timeout:may_wait_for_input")
                else:
                    errors.append("Binary timed out with no output")
                    all_hints.append("rust_binary_timeout:no_output")
            else:
                errors.append(f"cargo run failed (rc={rc}): {stderr[:500]}")
                all_hints.extend(self.parse_repair_hints(stderr, "rust"))

        elapsed = int((time.monotonic() - start) * 1000)
        return ValidationResult(
            success=len(errors) == 0,
            language="rust",
            validator_type="runtime",
            errors=errors,
            warnings=warnings,
            files_checked=1,
            duration_ms=elapsed,
            command_used="cargo run" if not is_server else "cargo build",
            can_auto_repair=len(all_hints) > 0,
            repair_hints=all_hints,
        )

    # ------------------------------------------------------------------
    # 4. INTEGRATION
    # ------------------------------------------------------------------

    def validate_integration(self, port: int = None) -> ValidationResult:
        """
        For Rust HTTP servers: start, test endpoints, kill.
        """
        start = time.monotonic()

        valid, err = self.ensure_workspace()
        if not valid:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="rust", validator_type="integration",
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
                success=True, language="rust", validator_type="integration",
                errors=[], warnings=["No endpoints detected"], files_checked=0,
                duration_ms=elapsed, can_auto_repair=False, repair_hints=[],
            )

        # Build
        cmd = "cargo build 2>&1"
        stdout, stderr, rc, _ = self.run_command(cmd, timeout=180)
        if rc != 0:
            errors.append(f"cargo build failed: {stderr[:500]}")
            all_hints.extend(self.parse_repair_hints(stderr, "rust"))
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="rust", validator_type="integration",
                errors=errors, warnings=[], files_checked=0,
                duration_ms=elapsed, command_used=cmd,
                can_auto_repair=len(all_hints) > 0, repair_hints=all_hints,
            )

        binary = self._find_binary()
        if not binary:
            errors.append("Cannot find built binary")
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="rust", validator_type="integration",
                errors=errors, warnings=[], files_checked=0,
                duration_ms=elapsed, can_auto_repair=False, repair_hints=[],
            )

        proc: Optional[subprocess.Popen] = None
        try:
            proc = self.run_background(binary)
            time.sleep(3)

            if proc.poll() is not None:
                _, crash_err, _, _ = proc.communicate(timeout=2)
                errors.append(f"Server crashed: {crash_err[:300]}")
                all_hints.extend(self.parse_repair_hints(crash_err or "", "rust"))
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
                        all_hints.append(f"rust_endpoint_unreachable:{ep}")
                    elif status_code not in ("200", "201", "204"):
                        warnings.append(f"Endpoint {ep}: HTTP {status_code}")
                    else:
                        logger.info("[rust] integration %s -> %s", ep, status_code)

        except Exception as exc:
            errors.append(f"Integration test failed: {exc}")
            all_hints.append(f"rust_integration_exception:{str(exc)[:60]}")
        finally:
            self.kill_background(proc)

        elapsed = int((time.monotonic() - start) * 1000)
        return ValidationResult(
            success=len(errors) == 0,
            language="rust",
            validator_type="integration",
            errors=errors,
            warnings=warnings,
            files_checked=len(endpoints),
            duration_ms=elapsed,
            command_used=cmd,
            can_auto_repair=len(all_hints) > 0,
            repair_hints=all_hints,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _detect_server_code(self) -> bool:
        """
        Check if Rust source is an HTTP server by looking at Cargo.toml
        dependencies and source code patterns.
        """
        # Check Cargo.toml for web frameworks
        cargo_toml = os.path.join(self.workspace_path, "Cargo.toml")
        if os.path.isfile(cargo_toml):
            try:
                with open(cargo_toml, "r", errors="replace") as f:
                    content = f.read()
                server_crates = [
                    "actix-web", "axum", "rocket", "warp", "tower",
                    "hyper", "tokio", "tide", "rouille", "salvo",
                    "thruster", "nickel",
                ]
                for crate_name in server_crates:
                    if crate_name in content:
                        return True
            except OSError:
                pass

        # Check source code for HTTP patterns
        server_indicators = [
            ".listen(", "HttpServer::new(", "rocket::ignite(",
            "warp::serve(", "axum::", "route!(", "TcpListener",
        ]
        for filepath in self.find_files(self.workspace_path, [".rs"]):
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
        Scan Rust source for route definitions.

        Detects:
          - axum: .route("/path", ...)
          - actix-web: .route("/path", ...), .resource("/path")
          - rocket: #[get("/path")], #[post("/path")]
          - warp: .path("path")
          - tide: .at("/path", ...)
        """
        endpoints: List[str] = []
        seen: set = set()

        rs_files = self.find_files(self.workspace_path, [".rs"])
        for fpath in rs_files:
            try:
                with open(fpath, "r", errors="replace") as f:
                    content = f.read()
            except OSError:
                continue

            # axum / actix-web: .route("/path", ...)
            for m in re.finditer(r'\.route\(\s*"([^"]+)"', content):
                ep = m.group(1)
                if ep not in seen:
                    seen.add(ep)
                    endpoints.append(ep)

            # actix-web: .resource("/path")
            for m in re.finditer(r'\.resource\(\s*"([^"]+)"', content):
                ep = m.group(1)
                if ep not in seen:
                    seen.add(ep)
                    endpoints.append(ep)

            # actix-web: .path("/path")
            for m in re.finditer(r'\.path\(\s*"([^"]+)"', content):
                ep = m.group(1)
                if ep not in seen:
                    seen.add(ep)
                    endpoints.append(ep)

            # rocket: #[get("/path")], #[post("/path")]
            for m in re.finditer(r'#\[ (?:get|post|put|delete|patch) \(\s*"([^"]+)"', content):
                ep = m.group(1)
                if ep not in seen:
                    seen.add(ep)
                    endpoints.append(ep)

            # tide: .at("/path", ...)
            for m in re.finditer(r'\.at\(\s*"([^"]+)"', content):
                ep = m.group(1)
                if ep not in seen:
                    seen.add(ep)
                    endpoints.append(ep)

            # warp: .path("segment")
            for m in re.finditer(r'\.path\(\s*"([^"]+)"', content):
                ep = "/" + m.group(1)
                if ep not in seen:
                    seen.add(ep)
                    endpoints.append(ep)

        return endpoints

    def _find_binary(self) -> Optional[str]:
        """Find the compiled binary in target/debug/."""
        # Read Cargo.toml to get the package name
        cargo_toml = os.path.join(self.workspace_path, "Cargo.toml")
        if os.path.isfile(cargo_toml):
            try:
                with open(cargo_toml, "r", errors="replace") as f:
                    content = f.read()
                m = re.search(r'name\s*=\s*"([^"]+)"', content)
                if m:
                    pkg_name = m.group(1)
                    binary = os.path.join(
                        self.workspace_path, "target", "debug", pkg_name
                    )
                    if os.path.isfile(binary):
                        return binary
            except OSError:
                pass

        # Fallback: look for any executable in target/debug
        debug_dir = os.path.join(self.workspace_path, "target", "debug")
        if os.path.isdir(debug_dir):
            for f in os.listdir(debug_dir):
                fpath = os.path.join(debug_dir, f)
                if os.path.isfile(fpath) and os.access(fpath, os.X_OK):
                    # Skip .d, .rlib, .rmeta files
                    if not f.endswith((".d", ".rlib", ".rmeta", ".so")):
                        return fpath

        return None

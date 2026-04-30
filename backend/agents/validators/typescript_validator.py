"""
TypeScript Runtime Validator.

Stages:
  1. validate_syntax()  — npx tsc --noEmit
  2. validate_build()   — npm install + npm run build (which runs tsc)
  3. validate_runtime() — start server, health-check, kill
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


class TypeScriptValidator(BaseValidator):

    def __init__(self, workspace_path: str, timeout_seconds: int = 60):
        super().__init__(workspace_path, timeout_seconds)
        self._language = "typescript"

    # ------------------------------------------------------------------
    # 1. SYNTAX
    # ------------------------------------------------------------------

    def validate_syntax(self) -> ValidationResult:
        """
        Run ``npx tsc --noEmit`` in the workspace directory.

        This type-checks all .ts/.tsx files without emitting output.
        If no tsconfig.json exists, creates a minimal one temporarily.
        """
        start = time.monotonic()

        valid, err = self.ensure_workspace()
        if not valid:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="typescript", validator_type="syntax",
                errors=[err], warnings=[], files_checked=0, duration_ms=elapsed,
                can_auto_repair=False, repair_hints=["workspace_missing_or_empty"],
            )

        ts_files = self.find_files(self.workspace_path, [".ts", ".tsx"])
        # Filter out node_modules etc.
        skip_dirs = {"node_modules", ".next", "dist", "build", "coverage"}
        ts_files = [f for f in ts_files if not any(part in f for part in skip_dirs)]

        if not ts_files:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=True, language="typescript", validator_type="syntax",
                errors=[], warnings=["No .ts/.tsx files found"], files_checked=0,
                duration_ms=elapsed, can_auto_repair=False, repair_hints=[],
            )

        # Check for tsconfig.json
        tsconfig_path = os.path.join(self.workspace_path, "tsconfig.json")
        if not os.path.isfile(tsconfig_path):
            # Create a minimal tsconfig for type-checking
            logger.warning("[typescript] No tsconfig.json — creating minimal one")
            minimal_tsconfig = json.dumps({
                "compilerOptions": {
                    "target": "ES2020",
                    "module": "commonjs",
                    "esModuleInterop": True,
                    "skipLibCheck": True,
                    "strict": False,
                    "noEmit": True,
                    "resolveJsonModule": True,
                    "jsx": "react",
                },
                "include": ["**/*.ts", "**/*.tsx"],
                "exclude": ["node_modules", "dist", "build"],
            }, indent=2)
            wrote_tsconfig = False
            try:
                with open(tsconfig_path, "w") as f:
                    f.write(minimal_tsconfig)
                wrote_tsconfig = True
            except OSError as e:
                errors = [f"Cannot create tsconfig.json: {e}"]
                elapsed = int((time.monotonic() - start) * 1000)
                return ValidationResult(
                    success=False, language="typescript", validator_type="syntax",
                    errors=errors, warnings=[], files_checked=len(ts_files),
                    duration_ms=elapsed, can_auto_repair=False,
                    repair_hints=["typescript_missing_tsconfig"],
                )

        errors: List[str] = []
        warnings: List[str] = []
        all_hints: List[str] = []

        cmd = "npx tsc --noEmit 2>&1"
        stdout, stderr, rc, _ = self.run_command(cmd, timeout=90)
        combined = stdout + stderr

        # Clean up temporary tsconfig if we wrote one
        if wrote_tsconfig:
            try:
                os.remove(tsconfig_path)
            except OSError:
                pass

        if rc != 0:
            # Parse TypeScript errors
            # Format: file.ts(line,col): error TSXXXX: message
            error_lines = []
            for line in combined.strip().splitlines():
                if "error TS" in line:
                    error_lines.append(line.strip())

            if error_lines:
                # Deduplicate and limit
                unique_errors = list(dict.fromkeys(error_lines))[:20]
                errors.extend(unique_errors)
            else:
                errors.append(f"tsc failed (rc={rc}): {combined[:500]}")

            all_hints.extend(self.parse_repair_hints(combined, "typescript"))
        else:
            logger.info("[typescript] tsc --noEmit PASSED (%d files)", len(ts_files))

        elapsed = int((time.monotonic() - start) * 1000)
        return ValidationResult(
            success=len(errors) == 0,
            language="typescript",
            validator_type="syntax",
            errors=errors,
            warnings=warnings,
            files_checked=len(ts_files),
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
        1. npm install --legacy-peer-deps
        2. npm run build
        """
        start = time.monotonic()

        valid, err = self.ensure_workspace()
        if not valid:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="typescript", validator_type="build",
                errors=[err], warnings=[], files_checked=0, duration_ms=elapsed,
                can_auto_repair=False, repair_hints=["workspace_missing_or_empty"],
            )

        errors: List[str] = []
        warnings: List[str] = []
        all_hints: List[str] = []
        build_output = ""
        cmd_used = ""

        pkg_path = os.path.join(self.workspace_path, "package.json")
        if not os.path.isfile(pkg_path):
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="typescript", validator_type="build",
                errors=["No package.json found"], warnings=[],
                files_checked=0, duration_ms=elapsed,
                can_auto_repair=True,
                repair_hints=["typescript_missing_package_json"],
            )

        # --- Step A: npm install ---
        install_cmd = "npm install --legacy-peer-deps 2>&1"
        cmd_used = install_cmd
        stdout, stderr, rc, _ = self.run_command(install_cmd, timeout=120)
        build_output += stdout + "\n" + stderr
        if rc != 0:
            errors.append(f"npm install failed (rc={rc}): {stderr[:500]}")
            all_hints.extend(self.parse_repair_hints(stderr, "typescript"))
        else:
            logger.info("[typescript] npm install succeeded")

        # --- Step B: npm run build ---
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
                all_hints.extend(self.parse_repair_hints(stderr, "typescript"))
            else:
                logger.info("[typescript] npm run build succeeded")
        else:
            warnings.append("No 'build' script in package.json — skipping build step")

        elapsed = int((time.monotonic() - start) * 1000)
        return ValidationResult(
            success=len(errors) == 0,
            language="typescript",
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
        Start the TypeScript server, health-check /health, kill.
        Supports: npm run dev, npm run start, ts-node, next dev.
        """
        start = time.monotonic()

        valid, err = self.ensure_workspace()
        if not valid:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="typescript", validator_type="runtime",
                errors=[err], warnings=[], files_checked=0, duration_ms=elapsed,
                can_auto_repair=False, repair_hints=["workspace_missing_or_empty"],
            )

        _port = port or 3000
        errors: List[str] = []
        warnings: List[str] = []
        all_hints: List[str] = []

        start_cmd = self._detect_start_command(_port)
        if not start_cmd:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="typescript", validator_type="runtime",
                errors=["Cannot detect TypeScript server start command"],
                warnings=["Expected: npm run dev, npm run start, or next dev"],
                files_checked=0, duration_ms=elapsed,
                can_auto_repair=False,
                repair_hints=["typescript_no_server_entrypoint"],
            )

        proc: Optional[subprocess.Popen] = None
        try:
            proc = self.run_background(start_cmd)

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
                    all_hints.extend(self.parse_repair_hints(crash_err or "", "typescript"))
                    break

            if not errors:
                if not health_ok:
                    errors.append(f"Server did not respond at {health_url} within 10 s")
                    all_hints.append("typescript_server_timeout:health_check_failed")
                else:
                    try:
                        data = json.loads(health_body)
                        if data.get("status") != "ok":
                            errors.append(f"Unexpected health response: {data}")
                        else:
                            logger.info("[typescript] runtime health-check PASSED")
                    except json.JSONDecodeError:
                        # Accept non-JSON responses for some frameworks
                        if health_body:
                            logger.info("[typescript] health responded (non-JSON)")
                        else:
                            errors.append("Health endpoint returned empty response")

        except Exception as exc:
            errors.append(f"Runtime validation failed: {exc}")
            all_hints.append(f"typescript_runtime_exception:{str(exc)[:60]}")
        finally:
            self.kill_background(proc)

        elapsed = int((time.monotonic() - start) * 1000)
        return ValidationResult(
            success=len(errors) == 0,
            language="typescript",
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
        Start server, test detected routes from Express/NestJS/Next.js route files.
        """
        start = time.monotonic()

        valid, err = self.ensure_workspace()
        if not valid:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="typescript", validator_type="integration",
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
                success=True, language="typescript", validator_type="integration",
                errors=[], warnings=["No endpoints detected"], files_checked=0,
                duration_ms=elapsed, can_auto_repair=False, repair_hints=[],
            )

        start_cmd = self._detect_start_command(_port)
        if not start_cmd:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="typescript", validator_type="integration",
                errors=["Cannot detect server start command"], warnings=[],
                files_checked=0, duration_ms=elapsed, can_auto_repair=False,
                repair_hints=["typescript_no_server_entrypoint"],
            )

        proc: Optional[subprocess.Popen] = None
        try:
            proc = self.run_background(start_cmd)
            time.sleep(3)

            if proc.poll() is not None:
                _, crash_err, _, _ = proc.communicate(timeout=2)
                errors.append(f"Server crashed: {crash_err[:300]}")
                all_hints.extend(self.parse_repair_hints(crash_err or "", "typescript"))
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
                        all_hints.append(f"typescript_endpoint_unreachable:{ep}")
                    elif status_code not in ("200", "201", "204", "301", "302"):
                        warnings.append(f"Endpoint {ep}: HTTP {status_code}")
                    else:
                        logger.info("[typescript] integration %s -> %s", ep, status_code)

        except Exception as exc:
            errors.append(f"Integration test failed: {exc}")
            all_hints.append(f"typescript_integration_exception:{str(exc)[:60]}")
        finally:
            self.kill_background(proc)

        elapsed = int((time.monotonic() - start) * 1000)
        return ValidationResult(
            success=len(errors) == 0,
            language="typescript",
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
        """Detect how to start the TypeScript server."""
        pkg_path = os.path.join(self.workspace_path, "package.json")
        if not os.path.isfile(pkg_path):
            # Fallback: try ts-node or node with transpiled output
            for entry in ["server.ts", "index.ts", "app.ts", "main.ts"]:
                if os.path.isfile(os.path.join(self.workspace_path, entry)):
                    return f"PORT={port} npx ts-node {entry}"
            return None

        try:
            with open(pkg_path, "r", errors="replace") as f:
                pkg = json.load(f)
            scripts = pkg.get("scripts", {})
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        except (json.JSONDecodeError, OSError):
            return None

        # Next.js
        if "next" in deps:
            return f"PORT={port} npx next dev"

        # Prefer dev, then start, then serve
        for script_name in ["dev", "start", "serve"]:
            if script_name in scripts:
                return f"PORT={port} npm run {script_name}"

        # Try ts-node
        for entry in ["server.ts", "index.ts", "app.ts", "main.ts"]:
            if os.path.isfile(os.path.join(self.workspace_path, entry)):
                return f"PORT={port} npx ts-node {entry}"

        return None

    def _detect_endpoints(self) -> List[str]:
        """
        Scan TypeScript source files for route definitions.

        Detects:
          - Express: app.get('/path', ...), router.get('/path', ...)
          - NestJS: @Get('/path'), @Post('/path')
          - Next.js app/ directory pages
        """
        endpoints: List[str] = []
        seen: set = set()
        skip_dirs = {"node_modules", ".next", "dist", "build", "coverage"}

        # Check for Next.js app/ or pages/ router
        app_dir = os.path.join(self.workspace_path, "app")
        pages_dir = os.path.join(self.workspace_path, "pages")

        if os.path.isdir(app_dir):
            # Next.js App Router
            for root, _dirs, files in os.walk(app_dir):
                for f in files:
                    if f in ("page.tsx", "page.ts", "page.jsx", "page.js", "route.ts", "route.js"):
                        rel = os.path.relpath(root, app_dir)
                        if rel == ".":
                            ep = "/"
                        else:
                            ep = "/" + rel.replace(os.sep, "/")
                        if ep not in seen:
                            seen.add(ep)
                            endpoints.append(ep)

        if os.path.isdir(pages_dir):
            # Next.js Pages Router
            for root, _dirs, files in os.walk(pages_dir):
                for f in files:
                    if f.endswith((".ts", ".tsx", ".js", ".jsx")):
                        rel = os.path.relpath(root, pages_dir)
                        if rel == ".":
                            ep = "/"
                        else:
                            ep = "/" + rel.replace(os.sep, "/")
                        if ep not in seen:
                            seen.add(ep)
                            endpoints.append(ep)

        # Scan .ts/.tsx files for Express routes
        ts_files = self.find_files(self.workspace_path, [".ts", ".tsx"])
        for fpath in ts_files:
            if any(part in fpath for part in skip_dirs):
                continue
            try:
                with open(fpath, "r", errors="replace") as f:
                    content = f.read()
            except OSError:
                continue

            # Express-style
            for m in re.finditer(
                r"(?:app|router)\.(?:get|post|put|delete|patch)\(\s*[\"']([^\"']+)[\"']",
                content,
            ):
                ep = m.group(1)
                if ep not in seen:
                    seen.add(ep)
                    endpoints.append(ep)

            # NestJS-style decorators
            for m in re.finditer(r"@(?:Get|Post|Put|Delete|Patch)\(\s*[\"']([^\"']+)[\"']", content):
                ep = m.group(1)
                if ep not in seen:
                    seen.add(ep)
                    endpoints.append(ep)

        return endpoints

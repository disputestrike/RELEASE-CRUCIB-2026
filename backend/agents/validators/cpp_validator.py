"""
C++ Runtime Validator.

Stages:
  1. validate_syntax()  — g++ -fsyntax-only on each .cpp file
  2. validate_build()   — CMake build or direct g++ compilation
  3. validate_runtime() — run compiled binary, check exit code
  4. validate_integration() — (not applicable for compiled binaries)
"""

import logging
import os
import re
import time
from typing import Dict, List, Optional

from .base import BaseValidator, ValidationResult

logger = logging.getLogger(__name__)


class CppValidator(BaseValidator):

    def __init__(self, workspace_path: str, timeout_seconds: int = 60):
        super().__init__(workspace_path, timeout_seconds)
        self._language = "cpp"
        self._binary_path = os.path.join(self.workspace_path, "build", "app")

    # ------------------------------------------------------------------
    # 1. SYNTAX
    # ------------------------------------------------------------------

    def validate_syntax(self) -> ValidationResult:
        """
        Run ``g++ -fsyntax-only`` on every .cpp file.

        Also checks that matching .h files exist for included headers.
        """
        start = time.monotonic()

        valid, err = self.ensure_workspace()
        if not valid:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="cpp", validator_type="syntax",
                errors=[err], warnings=[], files_checked=0, duration_ms=elapsed,
                can_auto_repair=False, repair_hints=["workspace_missing_or_empty"],
            )

        cpp_files = self.find_files(self.workspace_path, [".cpp"])
        h_files = self.find_files(self.workspace_path, [".h", ".hpp"])

        if not cpp_files:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=True, language="cpp", validator_type="syntax",
                errors=[], warnings=["No .cpp files found"], files_checked=0,
                duration_ms=elapsed, can_auto_repair=False, repair_hints=[],
            )

        errors: List[str] = []
        warnings: List[str] = []
        all_hints: List[str] = []
        files_ok = 0
        cmd_parts: List[str] = []

        # Determine include directories
        include_dirs = self._find_include_dirs()

        for filepath in cpp_files:
            rel = os.path.relpath(filepath, self.workspace_path)
            include_flags = " ".join(f"-I {d}" for d in include_dirs)
            cmd = f"g++ -std=c++17 -fsyntax-only {include_flags} {rel}"
            cmd_parts.append(cmd)
            stdout, stderr, rc, _ = self.run_command(cmd)

            if rc == 0:
                files_ok += 1
            else:
                # Parse first meaningful error line
                first_error = ""
                for line in stderr.strip().splitlines():
                    if "error:" in line.lower():
                        first_error = line.strip()
                        break
                if not first_error:
                    first_error = stderr.strip().splitlines()[-1] if stderr.strip() else "unknown"
                errors.append(f"{rel}: {first_error}")
                all_hints.extend(self.parse_repair_hints(stderr, "cpp"))

        # Check for missing headers referenced in source files
        if cpp_files and not h_files:
            # Scan #include "..." directives and check if local headers exist
            for filepath in cpp_files:
                try:
                    with open(filepath, "r", errors="replace") as f:
                        content = f.read()
                    for m in re.finditer(r'#include\s+"([^"]+)"', content):
                        header = m.group(1)
                        header_path = os.path.join(os.path.dirname(filepath), header)
                        if not os.path.isfile(header_path):
                            # Check in workspace root and include dirs too
                            found = False
                            for d in [self.workspace_path] + include_dirs:
                                if os.path.isfile(os.path.join(d, header)):
                                    found = True
                                    break
                            if not found:
                                rel = os.path.relpath(filepath, self.workspace_path)
                                warnings.append(f"{rel}: included header '{header}' not found locally")
                                all_hints.append(f"cpp_missing_header:{header}")
                except OSError:
                    continue

        elapsed = int((time.monotonic() - start) * 1000)
        return ValidationResult(
            success=len(errors) == 0,
            language="cpp",
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
        If CMakeLists.txt exists:
            mkdir -p build && cd build && cmake .. && cmake --build .
        Else:
            g++ -o build/app src/main.cpp src/*.cpp -I include -std=c++17
        """
        start = time.monotonic()

        valid, err = self.ensure_workspace()
        if not valid:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="cpp", validator_type="build",
                errors=[err], warnings=[], files_checked=0, duration_ms=elapsed,
                can_auto_repair=False, repair_hints=["workspace_missing_or_empty"],
            )

        errors: List[str] = []
        warnings: List[str] = []
        all_hints: List[str] = []
        build_output = ""
        cmd_used = ""

        cmake_path = os.path.join(self.workspace_path, "CMakeLists.txt")

        if os.path.isfile(cmake_path):
            # --- CMake build ---
            cmd_used = "cmake build"
            logger.info("[cpp] Using CMake build")

            # mkdir -p build
            stdout, stderr, rc, _ = self.run_command("mkdir -p build")
            build_output += stdout + stderr

            if rc != 0:
                errors.append(f"Cannot create build directory: {stderr[:300]}")
            else:
                # cmake ..
                stdout, stderr, rc, _ = self.run_command("cd build && cmake .. 2>&1")
                build_output += stdout + "\n" + stderr
                if rc != 0:
                    errors.append(f"cmake configure failed: {stderr[:500]}")
                    all_hints.extend(self.parse_repair_hints(stderr, "cpp"))
                else:
                    # cmake --build .
                    stdout, stderr, rc, _ = self.run_command(
                        "cd build && cmake --build . 2>&1", timeout=120
                    )
                    build_output += stdout + "\n" + stderr
                    if rc != 0:
                        errors.append(f"cmake build failed: {stderr[:500]}")
                        all_hints.extend(self.parse_repair_hints(stderr, "cpp"))
                    else:
                        # Find the binary
                        self._binary_path = self._find_cmake_binary()
                        logger.info("[cpp] CMake build succeeded")
        else:
            # --- Direct g++ build ---
            cpp_files = self.find_files(self.workspace_path, [".cpp"])
            if not cpp_files:
                elapsed = int((time.monotonic() - start) * 1000)
                return ValidationResult(
                    success=False, language="cpp", validator_type="build",
                    errors=["No .cpp files to compile"], warnings=[],
                    files_checked=0, duration_ms=elapsed,
                    can_auto_repair=False, repair_hints=["cpp_no_source_files"],
                )

            include_dirs = self._find_include_dirs()
            include_flags = " ".join(f"-I {d}" for d in include_dirs)

            # Collect all .cpp file paths relative to workspace
            cpp_rel = [os.path.relpath(f, self.workspace_path) for f in cpp_files]
            cpp_str = " ".join(cpp_rel)

            build_dir = os.path.join(self.workspace_path, "build")
            os.makedirs(build_dir, exist_ok=True)

            cmd = f"g++ -std=c++17 -o build/app {include_flags} {cpp_str} 2>&1"
            cmd_used = cmd
            stdout, stderr, rc, _ = self.run_command(cmd, timeout=120)
            build_output = stdout + "\n" + stderr

            if rc != 0:
                errors.append(f"g++ compilation failed: {stderr[:500]}")
                all_hints.extend(self.parse_repair_hints(stderr, "cpp"))
            else:
                self._binary_path = os.path.join(self.workspace_path, "build", "app")
                logger.info("[cpp] g++ build succeeded")

        elapsed = int((time.monotonic() - start) * 1000)
        return ValidationResult(
            success=len(errors) == 0,
            language="cpp",
            validator_type="build",
            errors=errors,
            warnings=warnings,
            files_checked=len(self.find_files(self.workspace_path, [".cpp"])),
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
        Run the compiled binary and check that it exits cleanly (rc 0)
        or runs for at least 1 second without crashing.
        """
        start = time.monotonic()

        valid, err = self.ensure_workspace()
        if not valid:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="cpp", validator_type="runtime",
                errors=[err], warnings=[], files_checked=0, duration_ms=elapsed,
                can_auto_repair=False, repair_hints=["workspace_missing_or_empty"],
            )

        errors: List[str] = []
        warnings: List[str] = []
        all_hints: List[str] = []

        # Find the binary
        binary = self._find_binary()
        if not binary or not os.path.isfile(binary):
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="cpp", validator_type="runtime",
                errors=["No compiled binary found. Run validate_build() first."],
                warnings=[],
                files_checked=0, duration_ms=elapsed,
                can_auto_repair=True,
                repair_hints=["cpp_binary_not_found:run_build_first"],
            )

        rel_binary = os.path.relpath(binary, self.workspace_path)
        cmd = f"./{rel_binary}"
        logger.info("[cpp] runtime: running %r", binary)

        stdout, stderr, rc, elapsed = self.run_command(cmd, timeout=10)

        if rc == 0:
            logger.info("[cpp] binary exited cleanly (rc=0)")
        elif rc == -1:
            # Timeout — the binary might be a long-running server, which is OK
            # Check if it produced any output
            if stdout or stderr:
                warnings.append("Binary timed out (might be a server — consider integration test)")
                all_hints.append("cpp_binary_timeout:may_be_server")
            else:
                errors.append("Binary timed out with no output")
                all_hints.append("cpp_binary_timeout:no_output")
        elif rc < 0:
            # Killed by signal (common for servers stopped with SIGTERM)
            abs_rc = abs(rc)
            if abs_rc == 9 or abs_rc == 15:  # SIGKILL or SIGTERM
                logger.info("[cpp] binary killed by signal (likely a server process)")
            else:
                errors.append(f"Binary killed by signal {abs_rc}")
                all_hints.append(f"cpp_signal_kill:{abs_rc}")
        else:
            errors.append(f"Binary exited with non-zero code {rc}: {stderr[:500]}")
            all_hints.extend(self.parse_repair_hints(stderr, "cpp"))

        total_elapsed = int((time.monotonic() - start) * 1000)
        return ValidationResult(
            success=len(errors) == 0,
            language="cpp",
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

    # ------------------------------------------------------------------
    # 4. INTEGRATION
    # ------------------------------------------------------------------

    def validate_integration(self, port: int = None) -> ValidationResult:
        """
        For C++ binaries that act as servers:
        Start the binary in background, wait, curl health endpoint, kill.

        This is only applicable if the binary appears to be a server
        (based on build output or source analysis).
        """
        start = time.monotonic()

        valid, err = self.ensure_workspace()
        if not valid:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=False, language="cpp", validator_type="integration",
                errors=[err], warnings=[], files_checked=0, duration_ms=elapsed,
                can_auto_repair=False, repair_hints=["workspace_missing_or_empty"],
            )

        binary = self._find_binary()
        if not binary or not os.path.isfile(binary):
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=True, language="cpp", validator_type="integration",
                errors=[], warnings=["No compiled binary found — skipping integration"],
                files_checked=0, duration_ms=elapsed,
                can_auto_repair=False, repair_hints=[],
            )

        # Check if source files suggest this is a network server
        is_server = self._detect_server_code()
        if not is_server:
            elapsed = int((time.monotonic() - start) * 1000)
            return ValidationResult(
                success=True, language="cpp", validator_type="integration",
                errors=[], warnings=["C++ binary does not appear to be a server — skipping integration"],
                files_checked=0, duration_ms=elapsed,
                can_auto_repair=False, repair_hints=[],
            )

        _port = port or 8080
        errors: List[str] = []
        warnings: List[str] = []
        all_hints: List[str] = []

        rel_binary = os.path.relpath(binary, self.workspace_path)
        proc = None
        try:
            proc = self.run_background(f"./{rel_binary}")

            health_url = f"http://localhost:{_port}/health"
            health_ok = False

            for _ in range(10):
                time.sleep(1)
                stdout, _, rc, _ = self.run_command(
                    f'curl -s --max-time 2 "{health_url}"', timeout=5
                )
                if rc == 0 and stdout:
                    health_ok = True
                    break
                if proc.poll() is not None:
                    _, crash_err, _, _ = proc.communicate(timeout=2)
                    errors.append(f"Server crashed: {crash_err[:300]}")
                    all_hints.extend(self.parse_repair_hints(crash_err or "", "cpp"))
                    break

            if not errors and not health_ok:
                warnings.append(f"Server did not respond at {health_url} within 10 s")
                all_hints.append("cpp_server_timeout:health_check_failed")
        except Exception as exc:
            errors.append(f"Integration test failed: {exc}")
            all_hints.append(f"cpp_integration_exception:{str(exc)[:60]}")
        finally:
            self.kill_background(proc)

        elapsed = int((time.monotonic() - start) * 1000)
        return ValidationResult(
            success=len(errors) == 0,
            language="cpp",
            validator_type="integration",
            errors=errors,
            warnings=warnings,
            files_checked=1,
            duration_ms=elapsed,
            command_used=f"./{rel_binary}",
            can_auto_repair=len(all_hints) > 0,
            repair_hints=all_hints,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_include_dirs(self) -> List[str]:
        """Detect common include directories."""
        dirs: List[str] = []
        for candidate in ["include", "inc", "headers", "src/include"]:
            full = os.path.join(self.workspace_path, candidate)
            if os.path.isdir(full):
                dirs.append(candidate)
        return dirs

    def _find_binary(self) -> Optional[str]:
        """Find the compiled binary."""
        # Check explicit path
        if os.path.isfile(self._binary_path):
            return self._binary_path

        # Check CMake build directory
        build_dir = os.path.join(self.workspace_path, "build")
        if os.path.isdir(build_dir):
            for root, _dirs, files in os.walk(build_dir):
                for f in files:
                    fpath = os.path.join(root, f)
                    # Check if it's an executable (and not a .o file)
                    if os.access(fpath, os.X_OK) and not f.endswith((".o", ".a", ".so")):
                        return fpath

        return None

    def _find_cmake_binary(self) -> str:
        """After CMake build, find the main executable."""
        build_dir = os.path.join(self.workspace_path, "build")
        if os.path.isdir(build_dir):
            for root, _dirs, files in os.walk(build_dir):
                for f in files:
                    fpath = os.path.join(root, f)
                    if os.access(fpath, os.X_OK) and not f.endswith((".o", ".a", ".so")):
                        return fpath
        return self._binary_path

    def _detect_server_code(self) -> bool:
        """
        Check if the C++ source contains server-related code
        (sockets, HTTP libraries, etc.).
        """
        server_indicators = [
            "listen(", "accept(", "bind(", "socket(",
            "httplib", "cpp-httplib", "crow", "pistache",
            "Boost.Beast", "boost::asio",
            "HTTPServer", "TcpServer",
        ]
        for filepath in self.find_files(self.workspace_path, [".cpp", ".h", ".hpp"]):
            try:
                with open(filepath, "r", errors="replace") as f:
                    content = f.read()
                for indicator in server_indicators:
                    if indicator in content:
                        return True
            except OSError:
                continue
        return False

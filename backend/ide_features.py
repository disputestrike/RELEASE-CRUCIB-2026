"""
IDE Features for CrucibAI — debugger, profiler, linter (in-memory stubs).
Enables IDE-style endpoints; real execution can be wired later.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import uuid
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class BreakPoint:
    file_path: str
    line: int
    column: int = 0
    condition: Optional[str] = None
    hit_count: int = 0
    enabled: bool = True
    id: Optional[str] = None

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())[:8]


@dataclass
class StackFrame:
    id: int
    name: str
    file_path: str
    line: int
    column: int = 0
    locals: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LintIssue:
    file_path: str
    line: int
    column: int
    message: str
    severity: str = "info"
    code: Optional[str] = None


@dataclass
class DebugSession:
    session_id: str
    project_id: str
    user_id: str
    status: str = "active"
    breakpoints: List[BreakPoint] = field(default_factory=list)
    current_frame: Optional[StackFrame] = None


class DebuggerManager:
    _sessions: Dict[str, DebugSession] = {}

    async def start_debug_session(self, session_id: str, project_id: str, user_id: str = "") -> DebugSession:
        s = DebugSession(session_id=session_id, project_id=project_id, user_id=user_id)
        self._sessions[session_id] = s
        return s

    async def set_breakpoint(self, session_id: str, bp: BreakPoint, user_id: str = "") -> BreakPoint:
        if session_id not in self._sessions:
            raise ValueError("Session not found")
        session = self._sessions[session_id]
        if session.user_id != user_id:
            raise ValueError("Session not found")
        session.breakpoints.append(bp)
        return bp

    async def remove_breakpoint(self, session_id: str, breakpoint_id: str, user_id: str = "") -> None:
        if session_id in self._sessions and self._sessions[session_id].user_id == user_id:
            self._sessions[session_id].breakpoints = [b for b in self._sessions[session_id].breakpoints if b.id != breakpoint_id]
            return
        raise ValueError("Session not found")


class ProfilerManager:
    _sessions: Dict[str, Dict[str, str]] = {}

    async def start_profiler(self, session_id: str, project_id: str, user_id: str = "") -> Dict[str, Any]:
        self._sessions[session_id] = {"project_id": project_id, "user_id": user_id}
        return {"session_id": session_id, "project_id": project_id, "status": "running"}

    async def stop_profiler(self, session_id: str, user_id: str = "") -> Dict[str, Any]:
        session = self._sessions.get(session_id)
        if not session or session.get("user_id") != user_id:
            raise ValueError("Session not found")
        del self._sessions[session_id]
        return {"session_id": session_id, "status": "stopped", "summary": {}}


class LinterManager:
    async def run_lint(self, project_id: str, file_path: str, code: Optional[str] = None) -> List[LintIssue]:
        """Run real linter: pyflakes for Python, node --check for JS/TS."""
        import subprocess
        import tempfile
        import os
        issues: List[LintIssue] = []
        if not code:
            return issues
        ext = (file_path or "").rsplit(".", 1)[-1].lower()
        try:
            if ext == "py":
                # pyflakes for Python
                import ast
                try:
                    ast.parse(code)
                except SyntaxError as e:
                    issues.append(LintIssue(
                        file_path=file_path or "file.py",
                        line=e.lineno or 1,
                        column=e.offset or 0,
                        message=str(e.msg),
                        severity="error",
                        code="SyntaxError"
                    ))
                    return issues
                # Run pyflakes
                fd, tmp = tempfile.mkstemp(suffix=".py")
                try:
                    with os.fdopen(fd, "w") as f:
                        f.write(code)
                    result = subprocess.run(
                        ["python3", "-m", "pyflakes", tmp],
                        capture_output=True, text=True, timeout=10
                    )
                    output = result.stdout + result.stderr
                    for line in output.splitlines():
                        m = re.match(r".+:(\d+):\d*\s*(.*)", line)
                        if m:
                            issues.append(LintIssue(
                                file_path=file_path or "file.py",
                                line=int(m.group(1)),
                                column=0,
                                message=m.group(2).strip(),
                                severity="warning"
                            ))
                finally:
                    try:
                        os.unlink(tmp)
                    except Exception:
                        pass
            elif ext in ("js", "jsx", "ts", "tsx", "mjs"):
                # node --check for basic JS/TS syntax
                fd, tmp = tempfile.mkstemp(suffix=f".{ext}")
                try:
                    with os.fdopen(fd, "w") as f:
                        f.write(code)
                    result = subprocess.run(
                        ["node", "--check", tmp],
                        capture_output=True, text=True, timeout=10
                    )
                    output = result.stderr or result.stdout
                    for line in output.splitlines():
                        m = re.match(r".+:(\d+).*", line)
                        if m:
                            issues.append(LintIssue(
                                file_path=file_path or f"file.{ext}",
                                line=int(m.group(1)),
                                column=0,
                                message=m.group(2).strip() or line.strip(),
                                severity="error"
                            ))
                        elif "SyntaxError" in line or "error" in line.lower():
                            # Parse line:col from node error format
                            nm = re.search(r":(\d+)", line)
                            issues.append(LintIssue(
                                file_path=file_path or f"file.{ext}",
                                line=int(nm.group(1)) if nm else 1,
                                column=0,
                                message=line.strip(),
                                severity="error"
                            ))
                finally:
                    try:
                        os.unlink(tmp)
                    except Exception:
                        pass
        except subprocess.TimeoutExpired:
            issues.append(LintIssue(file_path=file_path or "file", line=1, column=0, message="Lint timed out", severity="warning"))
        except Exception as e:
            logger.warning("Linter error: %s", e)
        return issues


class NavigationManager:
    async def get_symbols(self, project_id: str, file_path: str) -> List[Dict[str, Any]]:
        return []


debugger_manager = DebuggerManager()
profiler_manager = ProfilerManager()
linter_manager = LinterManager()
navigation_manager = NavigationManager()

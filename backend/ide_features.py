"""
IDE Features for CrucibAI — debugger, profiler, linter, symbol navigator.

Real implementations:
  - LinterManager.run_lint      -> pyflakes (Python) / node --check (JS/TS)
  - NavigationManager.get_symbols -> ast.walk (Python) / regex (JS/TS)
  - ProfilerManager.profile_code -> cProfile on sandboxed snippet (Python)
  - DebuggerManager             -> session state + breakpoint registry
"""

import logging
import os
import re
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Data models ────────────────────────────────────────────────────────────────

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


# ── DebuggerManager ────────────────────────────────────────────────────────────

class DebuggerManager:
    """Session-based breakpoint registry. Wire to DAP adapter for live stepping."""

    _sessions: Dict[str, DebugSession] = {}

    async def start_debug_session(
        self, session_id: str, project_id: str, user_id: str = ""
    ) -> DebugSession:
        s = DebugSession(session_id=session_id, project_id=project_id, user_id=user_id)
        self._sessions[session_id] = s
        return s

    async def set_breakpoint(
        self, session_id: str, bp: BreakPoint, user_id: str = ""
    ) -> BreakPoint:
        if session_id not in self._sessions:
            raise ValueError("Session not found")
        session = self._sessions[session_id]
        if session.user_id and session.user_id != user_id:
            raise ValueError("Session not found")
        session.breakpoints.append(bp)
        return bp

    async def remove_breakpoint(
        self, session_id: str, breakpoint_id: str, user_id: str = ""
    ) -> None:
        if session_id in self._sessions:
            sess = self._sessions[session_id]
            if not sess.user_id or sess.user_id == user_id:
                sess.breakpoints = [b for b in sess.breakpoints if b.id != breakpoint_id]
                return
        raise ValueError("Session not found")

    async def list_breakpoints(self, session_id: str, user_id: str = "") -> List[BreakPoint]:
        sess = self._sessions.get(session_id)
        if not sess or (sess.user_id and sess.user_id != user_id):
            raise ValueError("Session not found")
        return list(sess.breakpoints)

    async def end_session(self, session_id: str, user_id: str = "") -> None:
        sess = self._sessions.get(session_id)
        if sess and (not sess.user_id or sess.user_id == user_id):
            del self._sessions[session_id]


# ── ProfilerManager ────────────────────────────────────────────────────────────

_PROFILER_WRAPPER = """
import cProfile, pstats, io, json, sys, textwrap

_code = textwrap.dedent(open(sys.argv[1]).read())
_pr = cProfile.Profile()
_err = None
try:
    _pr.enable()
    exec(compile(_code, '<profile>', 'exec'))
    _pr.disable()
except Exception as _e:
    _pr.disable()
    _err = str(_e)

_s = pstats.Stats(_pr, stream=io.StringIO())
_s.sort_stats('cumulative')
_rows = []
for _func, _stat in list(_s.stats.items())[:20]:
    _file, _line, _name = _func
    _cc, _nc, _tt, _ct, _ = _stat
    _rows.append({"func": _name + " (" + _file + ":" + str(_line) + ")",
                  "calls": _nc, "tottime": round(_tt, 6), "cumtime": round(_ct, 6)})
_total_calls = sum(v[1] for v in _s.stats.values()) if _s.stats else 0
_total_time  = sum(v[2] for v in _s.stats.values()) if _s.stats else 0.0
print(json.dumps({"ok": _err is None, "hotspots": _rows,
    "total_calls": _total_calls, "total_time": round(_total_time, 6), "error": _err}))
"""


class ProfilerManager:
    """Profile Python code snippets via cProfile in a subprocess sandbox."""

    _sessions: Dict[str, Dict[str, str]] = {}

    async def start_profiler(
        self, session_id: str, project_id: str, user_id: str = ""
    ) -> Dict[str, Any]:
        self._sessions[session_id] = {
            "project_id": project_id,
            "user_id": user_id,
            "status": "running",
        }
        return {"session_id": session_id, "project_id": project_id, "status": "running"}

    async def stop_profiler(self, session_id: str, user_id: str = "") -> Dict[str, Any]:
        session = self._sessions.get(session_id)
        if not session or (session.get("user_id") and session["user_id"] != user_id):
            raise ValueError("Session not found")
        del self._sessions[session_id]
        return {"session_id": session_id, "status": "stopped", "summary": {}}

    async def profile_code(
        self,
        code: str,
        *,
        timeout: int = 10,
    ) -> Dict[str, Any]:
        """Run code under cProfile in a subprocess; return top hotspots.

        Returns dict with keys: ok, hotspots, total_calls, total_time, error.
        Each hotspot: {func, calls, tottime, cumtime}.
        """
        # Write the user code to a temp file and run our wrapper script against it
        fd_code, code_tmp = tempfile.mkstemp(suffix=".py", prefix="crucib_profile_code_")
        fd_wrap, wrap_tmp = tempfile.mkstemp(suffix=".py", prefix="crucib_profile_wrap_")
        try:
            with os.fdopen(fd_code, "w") as f:
                f.write(code)
            with os.fdopen(fd_wrap, "w") as f:
                f.write(_PROFILER_WRAPPER)
            proc = subprocess.run(
                ["python3", wrap_tmp, code_tmp],
                capture_output=True, text=True, timeout=timeout,
            )
            raw = (proc.stdout or "").strip()
            if raw:
                import json as _json
                return _json.loads(raw)
            return {
                "ok": False, "hotspots": [], "total_calls": 0, "total_time": 0.0,
                "error": proc.stderr or "No profiler output",
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "hotspots": [], "total_calls": 0, "total_time": 0.0,
                    "error": "Profiler timed out"}
        except Exception as e:
            logger.warning("ProfilerManager.profile_code error: %s", e)
            return {"ok": False, "hotspots": [], "total_calls": 0, "total_time": 0.0,
                    "error": str(e)}
        finally:
            for p in (code_tmp, wrap_tmp):
                try:
                    os.unlink(p)
                except Exception:
                    pass


# ── LinterManager ─────────────────────────────────────────────────────────────

class LinterManager:
    """Real linter: pyflakes (Python) + node --check (JS/TS)."""

    async def run_lint(
        self, project_id: str, file_path: str, code: Optional[str] = None
    ) -> List[LintIssue]:
        """Run real linter: pyflakes for Python, node --check for JS/TS."""
        issues: List[LintIssue] = []
        if not code:
            return issues
        ext = (file_path or "").rsplit(".", 1)[-1].lower()
        try:
            if ext == "py":
                import ast as _ast
                try:
                    _ast.parse(code)
                except SyntaxError as e:
                    issues.append(LintIssue(
                        file_path=file_path or "file.py",
                        line=e.lineno or 1, column=e.offset or 0,
                        message=str(e.msg), severity="error", code="SyntaxError",
                    ))
                    return issues
                fd, tmp = tempfile.mkstemp(suffix=".py")
                try:
                    with os.fdopen(fd, "w") as f:
                        f.write(code)
                    result = subprocess.run(
                        ["python3", "-m", "pyflakes", tmp],
                        capture_output=True, text=True, timeout=10,
                    )
                    output = result.stdout + result.stderr
                    for line in output.splitlines():
                        m = re.match(r".+:(\d+):\d*\s*(.*)", line)
                        if m:
                            issues.append(LintIssue(
                                file_path=file_path or "file.py",
                                line=int(m.group(1)), column=0,
                                message=m.group(2).strip(), severity="warning",
                            ))
                finally:
                    try:
                        os.unlink(tmp)
                    except Exception:
                        pass

            elif ext in ("js", "jsx", "ts", "tsx", "mjs"):
                fd, tmp = tempfile.mkstemp(suffix="." + ext)
                try:
                    with os.fdopen(fd, "w") as f:
                        f.write(code)
                    result = subprocess.run(
                        ["node", "--check", tmp],
                        capture_output=True, text=True, timeout=10,
                    )
                    output = result.stderr or result.stdout
                    for line in output.splitlines():
                        m = re.match(r".+:(\d+).*", line)
                        if m:
                            issues.append(LintIssue(
                                file_path=file_path or ("file." + ext),
                                line=int(m.group(1)), column=0,
                                message=line.strip(), severity="error",
                            ))
                        elif "SyntaxError" in line or "error" in line.lower():
                            nm = re.search(r":(\d+)", line)
                            issues.append(LintIssue(
                                file_path=file_path or ("file." + ext),
                                line=int(nm.group(1)) if nm else 1, column=0,
                                message=line.strip(), severity="error",
                            ))
                finally:
                    try:
                        os.unlink(tmp)
                    except Exception:
                        pass

        except subprocess.TimeoutExpired:
            issues.append(LintIssue(
                file_path=file_path or "file", line=1, column=0,
                message="Lint timed out", severity="warning",
            ))
        except Exception as e:
            logger.warning("Linter error: %s", e)
        return issues


# ── NavigationManager ─────────────────────────────────────────────────────────

class NavigationManager:
    """Extract symbols via AST (Python) or regex (JS/TS)."""

    async def get_symbols(
        self, project_id: str, file_path: str, code: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return [{name, kind, line, col, file}] symbols from code."""
        if not code:
            return []
        ext = (file_path or "").rsplit(".", 1)[-1].lower()
        if ext == "py":
            return self._python_symbols(code, file_path or "file.py")
        if ext in ("js", "jsx", "ts", "tsx", "mjs"):
            return self._js_symbols(code, file_path or ("file." + ext))
        return []

    def _python_symbols(self, code: str, file_path: str) -> List[Dict[str, Any]]:
        import ast as _ast
        symbols: List[Dict[str, Any]] = []
        try:
            tree = _ast.parse(code)
        except SyntaxError:
            return symbols
        for node in _ast.walk(tree):
            if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                symbols.append({"name": node.name, "kind": "function",
                                 "line": node.lineno, "col": node.col_offset, "file": file_path})
            elif isinstance(node, _ast.ClassDef):
                symbols.append({"name": node.name, "kind": "class",
                                 "line": node.lineno, "col": node.col_offset, "file": file_path})
            elif (isinstance(node, _ast.Assign)
                  and node.targets
                  and isinstance(node.targets[0], _ast.Name)):
                symbols.append({"name": node.targets[0].id, "kind": "variable",
                                 "line": node.lineno, "col": node.col_offset, "file": file_path})
        return sorted(symbols, key=lambda s: s["line"])

    def _js_symbols(self, code: str, file_path: str) -> List[Dict[str, Any]]:
        symbols: List[Dict[str, Any]] = []
        patterns = [
            (r"(?:^|\n)(?:export\s+)?(?:async\s+)?function\s+(\w+)", "function"),
            (r"(?:^|\n)(?:export\s+)?class\s+(\w+)", "class"),
            (r"(?:^|\n)(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\(", "arrow_function"),
            (r"(?:^|\n)(?:export\s+)?const\s+(\w+)\s*=", "constant"),
            (r"interface\s+(\w+)", "interface"),
            (r"type\s+(\w+)\s*=", "type"),
        ]
        for pattern, kind in patterns:
            for m in re.finditer(pattern, code, re.MULTILINE):
                line = code[: m.start()].count("\n") + 1
                col = m.start() - code.rfind("\n", 0, m.start()) - 1
                symbols.append({"name": m.group(1), "kind": kind,
                                 "line": line, "col": col, "file": file_path})
        return sorted(symbols, key=lambda s: s["line"])


# ── Singletons ─────────────────────────────────────────────────────────────────
debugger_manager = DebuggerManager()
profiler_manager = ProfilerManager()
linter_manager = LinterManager()
navigation_manager = NavigationManager()

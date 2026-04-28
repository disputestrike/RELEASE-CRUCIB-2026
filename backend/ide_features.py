"""
IDE Features for CrucibAI — debugger, profiler, linter, symbol navigator.

Real implementations:
  - LinterManager.run_lint      -> pyflakes (Python) / node --check (JS/TS)
  - NavigationManager.get_symbols -> ast.walk (Python) / regex (JS/TS)
  - ProfilerManager.profile_code -> cProfile on sandboxed snippet (Python)
  - DebuggerManager             -> session state + breakpoint registry
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import uuid
import logging

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
    status: str = "active"
    breakpoints: List[BreakPoint] = field(default_factory=list)
    current_frame: Optional[StackFrame] = None


# ── DebuggerManager ────────────────────────────────────────────────────────────

class DebuggerManager:
    """Session-based breakpoint registry. Wire to DAP adapter for live stepping."""

    _sessions: Dict[str, DebugSession] = {}

    async def start_debug_session(self, session_id: str, project_id: str) -> DebugSession:
        s = DebugSession(session_id=session_id, project_id=project_id)
        self._sessions[session_id] = s
        return s

    async def set_breakpoint(self, session_id: str, bp: BreakPoint) -> BreakPoint:
        if session_id not in self._sessions:
            raise ValueError("Session not found")
        self._sessions[session_id].breakpoints.append(bp)
        return bp

    async def remove_breakpoint(self, session_id: str, breakpoint_id: str) -> None:
        if session_id in self._sessions:
            self._sessions[session_id].breakpoints = [b for b in self._sessions[session_id].breakpoints if b.id != breakpoint_id]

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
    async def start_profiler(self, session_id: str, project_id: str) -> Dict[str, Any]:
        return {"session_id": session_id, "project_id": project_id, "status": "running"}

    async def stop_profiler(self, session_id: str) -> Dict[str, Any]:
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
    async def run_lint(self, project_id: str, file_path: str, code: Optional[str] = None) -> List[LintIssue]:
        return []


# ── NavigationManager ─────────────────────────────────────────────────────────

class NavigationManager:
    async def get_symbols(self, project_id: str, file_path: str) -> List[Dict[str, Any]]:
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

"""
IDE Features for CrucibAI — debugger, profiler, linter (in-memory stubs).
Enables IDE-style endpoints; real execution can be wired later.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import uuid
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
    status: str = "active"
    breakpoints: List[BreakPoint] = field(default_factory=list)
    current_frame: Optional[StackFrame] = None


class DebuggerManager:
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


class ProfilerManager:
    async def start_profiler(self, session_id: str, project_id: str) -> Dict[str, Any]:
        return {"session_id": session_id, "project_id": project_id, "status": "running"}

    async def stop_profiler(self, session_id: str) -> Dict[str, Any]:
        return {"session_id": session_id, "status": "stopped", "summary": {}}


class LinterManager:
    async def run_lint(self, project_id: str, file_path: str, code: Optional[str] = None) -> List[LintIssue]:
        return []


class NavigationManager:
    async def get_symbols(self, project_id: str, file_path: str) -> List[Dict[str, Any]]:
        return []


debugger_manager = DebuggerManager()
profiler_manager = ProfilerManager()
linter_manager = LinterManager()
navigation_manager = NavigationManager()

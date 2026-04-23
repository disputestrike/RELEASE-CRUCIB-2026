"""Execution context for enforcing runtime-engine-owned tool execution."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Optional


_runtime_active: ContextVar[bool] = ContextVar("runtime_active", default=False)
_runtime_project_id: ContextVar[Optional[str]] = ContextVar("runtime_project_id", default=None)
_runtime_task_id: ContextVar[Optional[str]] = ContextVar("runtime_task_id", default=None)
_runtime_skill_hint: ContextVar[Optional[str]] = ContextVar("runtime_skill_hint", default=None)


@contextmanager
def runtime_execution_scope(
    *,
    project_id: str,
    task_id: str,
    skill_hint: Optional[str] = None,
):
    tok_active = _runtime_active.set(True)
    tok_project = _runtime_project_id.set(project_id)
    tok_task = _runtime_task_id.set(task_id)
    tok_skill = _runtime_skill_hint.set(skill_hint)
    try:
        yield
    finally:
        _runtime_active.reset(tok_active)
        _runtime_project_id.reset(tok_project)
        _runtime_task_id.reset(tok_task)
        _runtime_skill_hint.reset(tok_skill)


def current_project_id() -> Optional[str]:
    return _runtime_project_id.get()


def current_task_id() -> Optional[str]:
    return _runtime_task_id.get()


def current_skill_hint() -> Optional[str]:
    return _runtime_skill_hint.get()

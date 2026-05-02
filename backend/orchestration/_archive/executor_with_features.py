"""
Backward-compatible alias for the live compatibility executor.

Older tests and scripts imported ``ExecutorWithFeatures`` while the real runtime
evolved elsewhere. Keeping this module as a thin wrapper avoids split-brain
logic while preserving import stability.
"""

from __future__ import annotations

from .executor_wired import WiredExecutor, get_wired_executor


class ExecutorWithFeatures(WiredExecutor):
    """Compatibility subclass with no separate execution path."""


def get_executor_with_features(job_id: str, project_id: str) -> ExecutorWithFeatures:
    return ExecutorWithFeatures(job_id, project_id)


__all__ = [
    "ExecutorWithFeatures",
    "get_executor_with_features",
    "WiredExecutor",
    "get_wired_executor",
]

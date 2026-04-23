"""Virtual filesystem — sandboxed Path management per project + task.

All resolved paths must remain within the sandbox root.
Traversal attempts outside the root raise ValueError.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ...config import WORKSPACE_ROOT


class VirtualFS:
    """Sandboxed filesystem scoped to a single task workspace."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    def resolve(self, relative: str) -> Path:
        """Resolve a relative path within the sandbox.

        Raises:
            ValueError: if the resolved path escapes the sandbox root.
        """
        clean = (relative or "").strip().lstrip("/").lstrip("\\")
        resolved = (self._root / clean).resolve()
        try:
            resolved.relative_to(self._root)
        except ValueError:
            raise ValueError(
                f"Path traversal denied: {relative!r} escapes sandbox root {self._root}"
            )
        return resolved

    def mkdir(self, relative: str) -> Path:
        """Create a directory (and parents) inside the sandbox."""
        p = self.resolve(relative)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def write_text(self, relative: str, content: str, encoding: str = "utf-8") -> Path:
        """Write text to a file inside the sandbox."""
        p = self.resolve(relative)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding=encoding)
        return p

    def read_text(self, relative: str, encoding: str = "utf-8") -> str:
        """Read text from a file inside the sandbox."""
        return self.resolve(relative).read_text(encoding=encoding)

    def exists(self, relative: str) -> bool:
        """Return True if the path exists inside the sandbox."""
        return self.resolve(relative).exists()

    def list_dir(self, relative: str = ".") -> list[str]:
        """List child names of a directory inside the sandbox."""
        p = self.resolve(relative)
        if not p.is_dir():
            return []
        return [child.name for child in p.iterdir()]


def task_workspace(
    project_id: str,
    task_id: str,
    *,
    subdir: Optional[str] = None,
) -> VirtualFS:
    """Return a VirtualFS scoped to a specific project + task."""
    safe_project = (project_id or "default").replace("/", "_").replace("\\", "_")
    safe_task = (task_id or "default").replace("/", "_").replace("\\", "_")
    root = WORKSPACE_ROOT / safe_project / "_tasks" / safe_task
    if subdir:
        root = root / subdir.strip("/\\")
    return VirtualFS(root)

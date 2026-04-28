from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


def _safe_segment(value: str) -> str:
    raw = str(value or "").strip()
    return raw.replace("/", "_").replace("\\", "_").replace("..", "_")


@dataclass(frozen=True)
class WorkspacePaths:
    job_id: Optional[str]
    project_id: Optional[str]
    workspace: Path
    candidates: List[Path]

    @property
    def dist_path(self) -> Path:
        return self.workspace / "dist"

    @property
    def package_path(self) -> Path:
        return self.workspace / "package.json"

    @property
    def preview_url(self) -> Optional[str]:
        return f"/api/preview/{self.job_id}/serve" if self.job_id else None

    @property
    def exists(self) -> bool:
        return any(candidate.exists() and candidate.is_dir() for candidate in self.candidates)


class WorkspaceResolver:
    """Canonical backend workspace path resolver.

    The product has accumulated several workspace layouts. New code should use
    this resolver so job preview, workspace files, manifests, and final gates
    agree on one primary root while still reading known legacy roots.
    """

    def workspace_root(self) -> Path:
        try:
            from backend.config import WORKSPACE_ROOT

            return Path(WORKSPACE_ROOT)
        except Exception:
            return Path("/tmp/workspaces")

    def project_workspace_path(self, project_id: str) -> Path:
        safe = _safe_segment(project_id)
        return self.workspace_root() / "projects" / safe

    def candidates_for(self, primary: Path, job_id: str = "") -> List[Path]:
        configured_root = self.workspace_root().resolve()
        try:
            primary_root = primary.resolve().parent.parent if primary.parent.name == "projects" else primary.resolve().parent
        except Exception:
            primary_root = configured_root
        roots = [configured_root]
        if primary_root != configured_root:
            roots.append(primary_root)
        raw: List[Path] = [primary]
        names = [primary.name]
        if job_id and job_id not in names:
            names.append(job_id)
        for name in names:
            if not name:
                continue
            safe = _safe_segment(name)
            for root in roots:
                raw.extend([root / "projects" / safe, root / safe])
        if job_id:
            raw.append(Path("/tmp/workspaces") / _safe_segment(job_id))

        seen = set()
        out: List[Path] = []
        for path in raw:
            try:
                resolved = path.resolve()
            except Exception:
                continue
            key = str(resolved)
            if key in seen:
                continue
            seen.add(key)
            out.append(resolved)
        return out

    def workspace_for_project(self, project_id: str) -> WorkspacePaths:
        primary = self.project_workspace_path(project_id)
        return WorkspacePaths(
            job_id=None,
            project_id=str(project_id or "").strip() or None,
            workspace=primary,
            candidates=self.candidates_for(primary),
        )

    def workspace_for_job(self, job_id: str, project_id: Optional[str] = None) -> WorkspacePaths:
        clean_job_id = str(job_id or "").strip()
        clean_project_id = str(project_id or "").strip() or clean_job_id
        primary = self.project_workspace_path(clean_project_id)
        candidates = self.candidates_for(primary, clean_job_id)
        workspace = next((p for p in candidates if p.exists() and p.is_dir()), primary)
        return WorkspacePaths(
            job_id=clean_job_id or None,
            project_id=clean_project_id or None,
            workspace=workspace,
            candidates=candidates,
        )


workspace_resolver = WorkspaceResolver()

"""
Workspace manifests and sealing for Auto-Runner jobs.

Writes under <workspace>/META/:
  run_manifest.json   — step ledger summary
  artifact_manifest.json — file tree with sha256
  seal.json           — job completion fingerprint

Full multi-agent merge pipeline lives behind future CRUCIBAI_ASSEMBLY_V2 work;
this module is the mandatory evidence + ZIP source-of-truth hook.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SKIP_ZIP_DIRS = frozenset({"node_modules", ".git", "__pycache__", ".pytest_cache", ".venv", "venv"})


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_artifact_manifest(workspace_root: Path) -> Dict[str, Any]:
    """Walk workspace (excluding heavy/ephemeral dirs) and record path → hash."""
    root = workspace_root.resolve()
    files: List[Dict[str, Any]] = []
    if not root.is_dir():
        return {"root": str(root), "generated_at": datetime.now(timezone.utc).isoformat(), "files": []}

    for dirpath, dirnames, filenames in os.walk(root):
        # prune dirs in-place
        dnames = [d for d in list(dirnames) if d not in SKIP_ZIP_DIRS and not d.startswith(".tmp")]
        dirnames[:] = dnames
        for fn in filenames:
            if fn.startswith(".") and fn not in (".env.example",):
                continue
            p = Path(dirpath) / fn
            try:
                rel = p.resolve().relative_to(root).as_posix()
            except ValueError:
                continue
            if rel.startswith("META/"):
                continue
            try:
                st = p.stat()
                raw = p.read_bytes()
            except OSError:
                continue
            files.append(
                {
                    "path": rel,
                    "sha256": _sha256_bytes(raw),
                    "bytes": st.st_size,
                    "last_writer_agent": "",
                    "contributing_agents": [],
                    "merge_policy": "unspecified",
                }
            )
    files.sort(key=lambda x: x["path"])
    return {
        "root": str(root),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "file_count": len(files),
        "files": files,
    }


def build_run_manifest(job_id: str, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows = []
    for s in sorted(steps, key=lambda x: (x.get("order_index") or 0, x.get("step_key") or "")):
        rows.append(
            {
                "step_id": s.get("id"),
                "step_key": s.get("step_key"),
                "agent_name": s.get("agent_name"),
                "phase": s.get("phase"),
                "status": s.get("status"),
                "order_index": s.get("order_index"),
                "depends_on": s.get("depends_on"),
                "error_message": (s.get("error_message") or "")[:500] if s.get("error_message") else "",
            }
        )
    return {
        "job_id": job_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "step_count": len(rows),
        "steps": rows,
    }


def write_meta(workspace_root: Path, name: str, payload: Dict[str, Any]) -> Path:
    meta = workspace_root.resolve() / "META"
    meta.mkdir(parents=True, exist_ok=True)
    path = meta / name
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


async def seal_completed_job_workspace(
    job_id: str,
    workspace_path: str,
    steps: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Persist manifests after a successful job completion (caller ensures success).
    Returns summary dict or None if skipped.
    """
    ws = (workspace_path or "").strip()
    if not ws:
        return None
    root = Path(ws)
    if not root.is_dir():
        logger.warning("seal: workspace not a directory: %s", ws)
        return None
    try:
        run_m = build_run_manifest(job_id, steps)
        art_m = build_artifact_manifest(root)
        write_meta(root, "run_manifest.json", run_m)
        write_meta(root, "artifact_manifest.json", art_m)
        seal_payload = {
            "job_id": job_id,
            "sealed_at": datetime.now(timezone.utc).isoformat(),
            "artifact_file_count": art_m.get("file_count", 0),
            "step_count": run_m.get("step_count", 0),
            "workspace_root": str(root.resolve()),
        }
        seal_payload["manifest_sha256"] = _sha256_bytes(
            json.dumps(art_m["files"], sort_keys=True).encode("utf-8")
        )
        write_meta(root, "seal.json", seal_payload)
        try:
            from .proof_index import write_meta_proof_index

            await write_meta_proof_index(job_id, root, art_m, steps)
        except Exception as _pi_e:
            logger.warning("proof_index on seal: %s", _pi_e)
        return seal_payload
    except Exception as e:
        logger.exception("seal_completed_job_workspace failed: %s", e)
        return None


def iter_files_for_zip(workspace_root: Path):
    """Yield (arcname, full_path) for zip builder."""
    root = workspace_root.resolve()
    meta = root / "META"
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_ZIP_DIRS and not d.startswith(".tmp")]
        for fn in filenames:
            fp = Path(dirpath) / fn
            if not fp.is_file():
                continue
            try:
                arc = fp.resolve().relative_to(root).as_posix()
            except ValueError:
                continue
            yield arc, fp

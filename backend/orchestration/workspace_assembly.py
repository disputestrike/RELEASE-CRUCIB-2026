"""
Workspace manifests and sealing for Auto-Runner jobs.

Writes under <workspace>/META/:
  run_manifest.json   — step ledger summary
  path_last_writer.json — last ``dag_node_completed`` owner per output path (P2)
  merge_map.json       — optional; assembly V2 last-writer agents (merged into artifact_manifest at seal)
  artifact_manifest.json — file tree with sha256 + optional last_writer fields
  seal.json           — job completion fingerprint

Multi-file merge pipeline is default-on (``CRUCIBAI_ASSEMBLY_V2`` opt-out); legacy path remains in ``legacy_file_tool_writes``;
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


def build_artifact_manifest(
    workspace_root: Path,
    path_owners: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Walk workspace (excluding heavy/ephemeral dirs) and record path → hash.

    When ``path_owners`` is provided (rel path → {step_key, step_id}), fills
    ``last_writer_agent`` / ``last_writer_step_id`` on each manifest row (P2).
    """
    root = workspace_root.resolve()
    files: List[Dict[str, Any]] = []
    owners = path_owners or {}
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
            own = owners.get(rel) or {}
            lw = str(own.get("step_key") or own.get("agent") or "")
            lsid = str(own.get("step_id") or "")
            files.append(
                {
                    "path": rel,
                    "sha256": _sha256_bytes(raw),
                    "bytes": st.st_size,
                    "last_writer_agent": lw,
                    "last_writer_step_id": lsid,
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


def merge_map_owner_overlay(workspace_root: Path) -> Dict[str, Dict[str, Any]]:
    """
    Owners from META/merge_map.json (assembly V2 last-writer merge).
    Used only to fill artifact_manifest rows when dag events did not list a path.
    """
    owners: Dict[str, Dict[str, Any]] = {}
    path = workspace_root / "META" / "merge_map.json"
    if not path.is_file():
        return owners
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return owners
    raw_paths = doc.get("paths")
    if not isinstance(raw_paths, dict):
        return owners
    for rel, row in raw_paths.items():
        if not isinstance(rel, str) or not isinstance(row, dict):
            continue
        rel_norm = rel.strip().replace("\\", "/").lstrip("/")
        if not rel_norm or ".." in rel_norm.split("/"):
            continue
        agent = row.get("last_writer_agent") or row.get("agent")
        if not agent:
            continue
        owners[rel_norm] = {
            "step_key": str(agent),
            "step_id": "",
            "source": "assembly_merge_map",
        }
    return owners


async def compute_path_last_writers_from_events(job_id: str) -> Dict[str, Dict[str, Any]]:
    """
    P2 — Last step that reported each path in ``dag_node_completed.output_files`` wins.
    """
    from .runtime_state import get_job_events

    owners: Dict[str, Dict[str, Any]] = {}
    try:
        events = await get_job_events(job_id, limit=5000)
    except Exception as e:
        logger.warning("path_last_writer: load events failed: %s", e)
        return owners
    for ev in events:
        if (ev.get("event_type") or "") != "dag_node_completed":
            continue
        payload = ev.get("payload_json")
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                continue
        elif not isinstance(payload, dict):
            continue
        sk = str(payload.get("step_key") or "")
        sid = str(ev.get("step_id") or "")
        for fp in payload.get("output_files") or []:
            if not isinstance(fp, str):
                continue
            rel = fp.strip().replace("\\", "/").lstrip("/")
            if not rel or ".." in rel.split("/"):
                continue
            owners[rel] = {"step_key": sk, "step_id": sid}
    return owners


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
        path_owners = await compute_path_last_writers_from_events(job_id)
        merge_overlay = merge_map_owner_overlay(root)
        manifest_owners = dict(merge_overlay)
        manifest_owners.update(path_owners)
        plw_doc = {
            "job_id": job_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "paths": path_owners,
            "path_count": len(path_owners),
        }
        write_meta(root, "path_last_writer.json", plw_doc)
        art_m = build_artifact_manifest(root, path_owners=manifest_owners)
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

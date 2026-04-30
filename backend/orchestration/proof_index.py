"""
P5 — Proof index ↔ artifact manifest.

Builds META/proof_index.json on job seal: each proof_item is linked to workspace paths
that appear in its payload and that exist in artifact_manifest.json.
Also builds reverse index by_path for UI navigation.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Reasonable repo-relative paths (exclude URLs and sentence-like strings)
_REL_PATH_RE = re.compile(r"^([A-Za-z0-9_.\-]+/)+[A-Za-z0-9_.\-]+\.[A-Za-z0-9]{1,12}$")
# Repo root files (server.py, README.md) — used when key is file/path
_SIMPLE_FILE_RE = re.compile(r"^[A-Za-z0-9_.\-]+\.[A-Za-z0-9]{1,12}$")
# Paths embedded in prose / issue lines (e.g. "error in src/App.jsx line 1")
_EMBED_PATH_RE = re.compile(
    r"\b([A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]+)+\.(?:jsx?|tsx?|js|ts|py|json|ya?ml|yml|md|css|scss|html?|sql))\b",
    re.IGNORECASE,
)
_PAYLOAD_PATH_KEYS = frozenset(
    {
        "file",
        "path",
        "rel",
        "rel_path",
        "filepath",
        "target_file",
        "file_path",
        "rel_path",
    }
)


def _norm_rel(p: str) -> str:
    s = (p or "").strip().replace("\\", "/").lstrip("/")
    if ".." in s.split("/"):
        return ""
    return s


def _looks_like_rel_path(s: str) -> bool:
    s = (s or "").strip().replace("\\", "/").lstrip("/")
    if not s or len(s) > 260 or "://" in s or s.startswith("{"):
        return False
    if _REL_PATH_RE.match(s):
        return True
    # Single-segment filenames (e.g. server.py) when they look like code files
    if _SIMPLE_FILE_RE.match(s) and len(s) < 120:
        return True
    return False


def _paths_from_free_text(text: str) -> List[str]:
    if not isinstance(text, str) or not text.strip():
        return []
    if len(text) > 20000:
        text = text[:20000]
    out: List[str] = []
    for m in _EMBED_PATH_RE.finditer(text):
        n = _norm_rel(m.group(1))
        if n:
            out.append(n)
    return list(dict.fromkeys(out))


def extract_path_candidates(payload: Any) -> List[str]:
    """Collect workspace-relative path strings from a proof payload (nested dict/list)."""
    found: Set[str] = set()

    def walk(x: Any) -> None:
        if isinstance(x, dict):
            for k, v in x.items():
                if isinstance(v, str) and v:
                    if k in _PAYLOAD_PATH_KEYS and _looks_like_rel_path(v):
                        n = _norm_rel(v)
                        if n:
                            found.add(n)
                    elif _looks_like_rel_path(v):
                        n = _norm_rel(v)
                        if n:
                            found.add(n)
                    for n in _paths_from_free_text(v):
                        found.add(n)
                else:
                    walk(v)
        elif isinstance(x, list):
            for it in x:
                walk(it)
        elif isinstance(x, str) and x.strip():
            if _looks_like_rel_path(x):
                n = _norm_rel(x)
                if n:
                    found.add(n)
            for n in _paths_from_free_text(x):
                found.add(n)

    walk(payload)
    return sorted(found)


def _manifest_path_set(artifact_manifest: Dict[str, Any]) -> Set[str]:
    files = artifact_manifest.get("files") or []
    return {str(f.get("path") or "") for f in files if f.get("path")}


def resolve_paths_to_manifest(
    candidates: List[str],
    manifest_paths: Set[str],
) -> Tuple[List[str], List[str]]:
    resolved = [p for p in candidates if p in manifest_paths]
    missing = [p for p in candidates if p not in manifest_paths]
    return resolved, missing


def build_proof_index_document(
    job_id: str,
    artifact_manifest: Dict[str, Any],
    proof_items: List[Dict[str, Any]],
    step_key_by_id: Dict[str, str],
) -> Dict[str, Any]:
    manifest_paths = _manifest_path_set(artifact_manifest)
    entries: List[Dict[str, Any]] = []
    by_path: Dict[str, List[Dict[str, str]]] = {}

    for row in proof_items:
        pid = str(row.get("id") or "")
        sid = str(row.get("step_id") or "")
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        candidates = extract_path_candidates(payload)
        resolved, missing = resolve_paths_to_manifest(candidates, manifest_paths)
        entry = {
            "proof_item_id": pid,
            "step_id": sid,
            "step_key": step_key_by_id.get(sid, ""),
            "proof_type": row.get("proof_type") or "",
            "title": (row.get("title") or "")[:500],
            "paths_mentioned_in_payload": candidates,
            "paths_resolved_in_manifest": resolved,
            "paths_missing_from_manifest": missing,
        }
        entries.append(entry)
        for p in resolved:
            by_path.setdefault(p, []).append(
                {
                    "proof_item_id": pid,
                    "title": entry["title"],
                    "proof_type": entry["proof_type"],
                }
            )

    by_proof_item_id: Dict[str, Any] = {}
    for e in entries:
        pid = e.get("proof_item_id") or ""
        if pid:
            by_proof_item_id[pid] = {
                "step_key": e.get("step_key", ""),
                "proof_type": e.get("proof_type", ""),
                "title": e.get("title", ""),
                "paths_resolved_in_manifest": e.get("paths_resolved_in_manifest") or [],
                "paths_missing_from_manifest": e.get("paths_missing_from_manifest")
                or [],
            }

    am_sha = ""
    try:
        raw = json.dumps(
            artifact_manifest.get("files") or [], sort_keys=True, default=str
        )
        import hashlib

        am_sha = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    except Exception:
        pass

    return {
        "version": 1,
        "job_id": job_id,
        "artifact_manifest_sha256": am_sha,
        "proof_item_count": len(entries),
        "entries": entries,
        "by_path": dict(sorted(by_path.items(), key=lambda kv: kv[0])),
        "by_proof_item_id": by_proof_item_id,
    }


async def write_meta_proof_index(
    job_id: str,
    workspace_root: Path,
    artifact_manifest: Dict[str, Any],
    steps: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Persist META/proof_index.json; returns document or None."""
    from backend.proof import proof_service

    step_key_by_id = {
        str(s.get("id") or ""): str(s.get("step_key") or "")
        for s in steps
        if s.get("id")
    }
    try:
        proof_items = await proof_service.fetch_proof_items_raw(job_id)
    except Exception as e:
        logger.warning("proof_index: fetch proof items failed: %s", e)
        proof_items = []

    doc = build_proof_index_document(
        job_id, artifact_manifest, proof_items, step_key_by_id
    )
    try:
        meta = workspace_root.resolve() / "META"
        meta.mkdir(parents=True, exist_ok=True)
        (meta / "proof_index.json").write_text(
            json.dumps(doc, indent=2), encoding="utf-8"
        )
    except OSError as e:
        logger.warning("proof_index: write failed: %s", e)
        return None
    return doc

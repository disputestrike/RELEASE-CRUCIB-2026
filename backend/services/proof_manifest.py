"""Signed proof manifest helpers.

This module provides deterministic canonicalization, HMAC signing, signature
verification, and replay-plan extraction for proof manifests.
"""

from __future__ import annotations

import copy
import hashlib
import hmac
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


SIGNATURE_ALGORITHM = "hmac-sha256"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json_bytes(data: Dict[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _unsigned_manifest(manifest: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(manifest)
    out.pop("signature", None)
    out.pop("signature_algorithm", None)
    out.pop("payload_sha256", None)
    out.pop("signed_at", None)
    return out


def compute_payload_sha256(manifest: Dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json_bytes(_unsigned_manifest(manifest))).hexdigest()


def sign_manifest(manifest: Dict[str, Any], *, secret: str, signed_at: str | None = None) -> Dict[str, Any]:
    if not secret:
        raise ValueError("secret is required")

    out = _unsigned_manifest(manifest)
    out["signed_at"] = signed_at or _utc_now_iso()
    out["signature_algorithm"] = SIGNATURE_ALGORITHM
    out["payload_sha256"] = compute_payload_sha256(out)

    payload_bytes = _canonical_json_bytes(_unsigned_manifest(out))
    out["signature"] = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return out


def verify_manifest(manifest: Dict[str, Any], *, secret: str) -> Dict[str, Any]:
    if not secret:
        return {"ok": False, "reason": "missing_secret"}
    if not isinstance(manifest, dict):
        return {"ok": False, "reason": "invalid_manifest"}

    signature = str(manifest.get("signature") or "").strip()
    algorithm = str(manifest.get("signature_algorithm") or "").strip()
    payload_sha = str(manifest.get("payload_sha256") or "").strip()

    if not signature:
        return {"ok": False, "reason": "missing_signature"}
    if algorithm != SIGNATURE_ALGORITHM:
        return {"ok": False, "reason": "unsupported_algorithm"}

    normalized = _unsigned_manifest(manifest)
    computed_sha = hashlib.sha256(_canonical_json_bytes(normalized)).hexdigest()
    if payload_sha and payload_sha != computed_sha:
        return {"ok": False, "reason": "payload_hash_mismatch", "computed_payload_sha256": computed_sha}

    expected_sig = hmac.new(secret.encode("utf-8"), _canonical_json_bytes(normalized), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected_sig):
        return {"ok": False, "reason": "signature_mismatch", "computed_payload_sha256": computed_sha}

    return {
        "ok": True,
        "reason": "verified",
        "computed_payload_sha256": computed_sha,
        "signed_at": manifest.get("signed_at"),
    }


def build_replay_plan(manifest: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _unsigned_manifest(manifest)
    artifacts = normalized.get("artifacts")
    if not isinstance(artifacts, list):
        artifacts = []

    replay_artifacts = []
    for item in artifacts:
        if not isinstance(item, dict):
            continue
        replay_artifacts.append(
            {
                "path": item.get("path"),
                "sha256": item.get("sha256"),
                "bytes": item.get("bytes"),
            }
        )

    replay_artifacts = sorted(
        replay_artifacts,
        key=lambda row: (str(row.get("path") or ""), str(row.get("sha256") or "")),
    )

    return {
        "manifest_id": normalized.get("manifest_id"),
        "project_id": normalized.get("project_id"),
        "run_id": normalized.get("run_id"),
        "replay_payload_sha256": hashlib.sha256(_canonical_json_bytes(normalized)).hexdigest(),
        "artifacts": replay_artifacts,
        "steps": [
            "fetch_artifacts",
            "validate_sha256",
            "reconstruct_output",
            "compare_expected_vs_actual",
        ],
    }


def hash_file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def collect_artifacts(directory: Path, *, exclude_names: set[str] | None = None) -> list[Dict[str, Any]]:
    root = Path(directory).resolve()
    excludes = set(exclude_names or set())
    rows: list[Dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name in excludes:
            continue
        rel = path.relative_to(root).as_posix()
        rows.append(
            {
                "path": rel,
                "sha256": hash_file_sha256(path),
                "bytes": path.stat().st_size,
            }
        )
    return rows


def build_signed_manifest_for_directory(
    *,
    directory: Path,
    secret: str,
    manifest_id: str,
    project_id: str,
    run_id: str,
    metadata: Dict[str, Any] | None = None,
    exclude_names: set[str] | None = None,
) -> Dict[str, Any]:
    payload = {
        "manifest_id": manifest_id,
        "project_id": project_id,
        "run_id": run_id,
        "generated_at": _utc_now_iso(),
        "artifacts": collect_artifacts(directory, exclude_names=exclude_names),
        "meta": dict(metadata or {}),
    }
    return sign_manifest(payload, secret=secret)

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routes.trust import create_trust_router
from backend.services.proof_manifest import (
    build_replay_plan,
    build_signed_manifest_for_directory,
    sign_manifest,
    verify_manifest,
)


def _sample_manifest() -> dict:
    return {
        "manifest_id": "mf-001",
        "project_id": "proj-123",
        "run_id": "run-abc",
        "artifacts": [
            {"path": "dist/app.js", "sha256": "a" * 64, "bytes": 1280},
            {"path": "dist/index.html", "sha256": "b" * 64, "bytes": 950},
        ],
        "meta": {"benchmark": "product_dominance_v1"},
    }


def test_sign_and_verify_manifest_roundtrip():
    secret = "test-proof-secret"
    signed = sign_manifest(_sample_manifest(), secret=secret)
    result = verify_manifest(signed, secret=secret)
    assert result["ok"] is True
    assert result["reason"] == "verified"


def test_verify_manifest_detects_tampering():
    secret = "test-proof-secret"
    signed = sign_manifest(_sample_manifest(), secret=secret)
    signed["artifacts"][0]["bytes"] = 999999
    result = verify_manifest(signed, secret=secret)
    assert result["ok"] is False
    assert result["reason"] in {"payload_hash_mismatch", "signature_mismatch"}


def test_build_replay_plan_is_deterministic_shape():
    signed = sign_manifest(_sample_manifest(), secret="test-proof-secret")
    replay = build_replay_plan(signed)
    assert replay["manifest_id"] == "mf-001"
    assert replay["project_id"] == "proj-123"
    assert replay["run_id"] == "run-abc"
    assert replay["steps"] == [
        "fetch_artifacts",
        "validate_sha256",
        "reconstruct_output",
        "compare_expected_vs_actual",
    ]
    assert isinstance(replay["replay_payload_sha256"], str)
    assert len(replay["replay_payload_sha256"]) == 64


def test_trust_manifest_endpoints_verify_and_replay(monkeypatch):
    monkeypatch.setenv("CRUCIB_PROOF_HMAC_SECRET", "route-test-secret")
    app = FastAPI()
    app.include_router(create_trust_router(Path(__file__).resolve().parents[1]))
    client = TestClient(app)

    manifest = sign_manifest(_sample_manifest(), secret="route-test-secret")

    verify_resp = client.post("/api/trust/proof-manifest/verify", json={"manifest": manifest})
    assert verify_resp.status_code == 200
    verify_json = verify_resp.json()
    assert verify_json["ok"] is True

    replay_resp = client.post("/api/trust/proof-manifest/replay", json={"manifest": manifest})
    assert replay_resp.status_code == 200
    replay_json = replay_resp.json()
    assert replay_json["verification"]["ok"] is True
    assert replay_json["replay"]["manifest_id"] == "mf-001"


def test_trust_manifest_verify_requires_secret(monkeypatch):
    monkeypatch.delenv("CRUCIB_PROOF_HMAC_SECRET", raising=False)
    app = FastAPI()
    app.include_router(create_trust_router(Path(__file__).resolve().parents[1]))
    client = TestClient(app)

    resp = client.post("/api/trust/proof-manifest/verify", json={"manifest": _sample_manifest()})
    assert resp.status_code == 503


def test_build_signed_manifest_for_directory_collects_artifacts(tmp_path):
    (tmp_path / "summary.json").write_text('{"ok":true}', encoding="utf-8")
    (tmp_path / "BENCHMARK_REPORT.md").write_text("# report\n", encoding="utf-8")

    manifest = build_signed_manifest_for_directory(
        directory=tmp_path,
        secret="dir-secret",
        manifest_id="mf-dir-1",
        project_id="proj-dir",
        run_id="run-dir",
        exclude_names={"proof_manifest.json"},
    )
    verify = verify_manifest(manifest, secret="dir-secret")
    assert verify["ok"] is True
    artifact_paths = {a.get("path") for a in (manifest.get("artifacts") or [])}
    assert "summary.json" in artifact_paths
    assert "BENCHMARK_REPORT.md" in artifact_paths


def test_signer_cli_writes_manifest(tmp_path, monkeypatch):
    (tmp_path / "summary.json").write_text('{"ok":true}', encoding="utf-8")
    (tmp_path / "BENCHMARK_REPORT.md").write_text("# report\n", encoding="utf-8")
    monkeypatch.setenv("CRUCIB_PROOF_HMAC_SECRET", "cli-secret")

    script = Path(__file__).resolve().parents[2] / "scripts" / "sign-proof-manifest.py"
    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "--input-dir",
            str(tmp_path),
            "--project-id",
            "proj-cli",
            "--run-id",
            "run-cli",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    manifest_file = tmp_path / "proof_manifest.json"
    assert manifest_file.is_file()

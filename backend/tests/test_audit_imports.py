"""CF27 — in-process tests for the 6 audit-imported route modules."""
from __future__ import annotations

import io
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


def _client(module_name: str) -> TestClient:
    import importlib
    mod = importlib.import_module(module_name)
    app = FastAPI()
    app.include_router(mod.router)
    return TestClient(app)


# ── cost_hook ───────────────────────────────────────────────────────────
def test_cost_record_turn():
    c = _client("routes.cost_hook")
    r = c.post("/api/cost/turn", json={"run_id": "r1", "model": "claude-sonnet-4-6",
                                       "input_tokens": 1000, "output_tokens": 500})
    assert r.status_code == 200
    data = r.json()
    assert data["usd"] > 0
    assert data["run_id"] == "r1"


def test_cost_totals():
    c = _client("routes.cost_hook")
    c.post("/api/cost/turn", json={"run_id": "r2", "model": "claude-sonnet-4-6",
                                   "input_tokens": 100, "output_tokens": 50})
    assert c.get("/api/cost/totals").status_code == 200


# ── doctor ──────────────────────────────────────────────────────────────
def test_doctor_endpoint():
    c = _client("routes.doctor")
    r = c.get("/api/doctor")
    assert r.status_code == 200
    d = r.json()
    assert d["status"] in {"ok", "degraded"}
    assert any(ch["name"] == "python" for ch in d["checks"])


# ── autofix-pr ──────────────────────────────────────────────────────────
def test_autofix_queue_and_get():
    c = _client("routes.autofix_pr")
    r = c.post("/api/autofix/pr", json={"repo": "acme/x", "branch": "main"})
    assert r.status_code == 200
    job_id = r.json()["job_id"]
    assert c.get(f"/api/autofix/pr/{job_id}").status_code == 200


# ── commit-push-pr ──────────────────────────────────────────────────────
def test_commit_push_pr_queue():
    c = _client("routes.commit_push_pr")
    r = c.post("/api/git/commit-push-pr", json={
        "repo": "acme/x", "branch": "feature/foo",
        "commit_message": "feat: add foo",
    })
    assert r.status_code == 200
    job_id = r.json()["job_id"]
    g = c.get(f"/api/git/commit-push-pr/{job_id}")
    assert g.status_code == 200
    assert g.json()["pr_title"] == "feat: add foo"


# ── voice ──────────────────────────────────────────────────────────────
def test_voice_transcribe_and_keyterms(monkeypatch):
    import importlib

    from backend.deps import get_current_user

    monkeypatch.setenv("CRUCIBAI_VOICE_TEST_MODE", "1")

    mod = importlib.import_module("routes.voice_input")
    app = FastAPI()
    app.include_router(mod.router)
    app.dependency_overrides[get_current_user] = lambda: {"id": "audit-voice"}

    c = TestClient(app)
    audio = io.BytesIO(b"\x00" * 2048)
    r = c.post(
        "/api/voice/transcribe",
        files={"audio": ("clip.wav", audio, "audio/wav")},
        data={"session_id": "s1", "language": "en"},
    )
    assert r.status_code == 200, r.text
    tid = r.json()["transcript_id"]
    assert c.get(f"/api/voice/transcript/{tid}").status_code == 200
    k = c.get("/api/voice/keyterms").json()
    assert "wake" in k and "stop" in k and "run" in k


# ── compact ────────────────────────────────────────────────────────────
def test_compact_tokens_estimate():
    c = _client("routes.compact_command")
    r = c.post("/api/runtime/compact", json={
        "session_id": "s1", "target_tokens": 1000,
        "messages": [{"role": "user", "content": "x" * 7000}],
    })
    assert r.status_code == 200
    d = r.json()
    assert d["tokens_before"] >= 1900
    assert d["tokens_after_target"] <= d["tokens_before"]


# ── mode_transitions (pure service) ─────────────────────────────────────
def test_mode_transitions():
    from services.permissions.mode_transitions import PermissionMode, can_transition, next_mode, describe
    assert can_transition(PermissionMode.DEFAULT, PermissionMode.PLAN)
    assert not can_transition(PermissionMode.DEFAULT, PermissionMode.YOLO)
    assert can_transition(PermissionMode.BYPASS, PermissionMode.YOLO, admin=True)
    assert can_transition(PermissionMode.YOLO, PermissionMode.DEFAULT)  # downshift always allowed
    nxt = next_mode(PermissionMode.DEFAULT, direction="up")
    assert nxt == PermissionMode.ACCEPT_EDITS
    assert isinstance(describe(PermissionMode.YOLO), str)

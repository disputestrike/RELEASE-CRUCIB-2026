"""CF26 — in-process tests for mobile build API route.

Uses the same _app_for pattern as test_phase2_wave2.py to avoid importing
backend.routes.__init__ (which depends on modular_env).
"""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


def _client() -> TestClient:
    import importlib
    mod = importlib.import_module("routes.mobile_build")
    app = FastAPI()
    app.include_router(mod.router)
    return TestClient(app)


def test_queue_ios_build_returns_job_id():
    c = _client()
    r = c.post("/api/mobile/build", json={"platform": "ios", "project_id": "proj-1"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "queued"
    assert data["platform"] == "ios"
    assert data["project_id"] == "proj-1"
    assert data["job_id"]
    assert data["queued_at"]


def test_queue_android_build_returns_job_id():
    c = _client()
    r = c.post("/api/mobile/build", json={"platform": "android", "project_id": "proj-x"})
    assert r.status_code == 200
    assert r.json()["platform"] == "android"


def test_invalid_platform_rejected():
    c = _client()
    r = c.post("/api/mobile/build", json={"platform": "windows", "project_id": "p"})
    assert r.status_code == 422


def test_get_job_and_list():
    c = _client()
    post = c.post("/api/mobile/build", json={"platform": "ios", "project_id": "p2"}).json()
    job_id = post["job_id"]
    g = c.get(f"/api/mobile/build/{job_id}")
    assert g.status_code == 200
    assert g.json()["job_id"] == job_id
    lst = c.get("/api/mobile/jobs")
    assert lst.status_code == 200
    assert lst.json()["count"] >= 1

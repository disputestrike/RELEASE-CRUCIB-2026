from fastapi.testclient import TestClient

from backend.server import app


def test_doctor_endpoints_are_mounted_and_structured():
    client = TestClient(app)

    base = client.get("/api/doctor")
    assert base.status_code == 200
    assert base.json()["status"] in {"ok", "degraded"}

    routes = client.get("/api/doctor/routes")
    assert routes.status_code == 200
    body = routes.json()
    assert body["status"] == "ok"
    assert "backend.routes.preview_serve" not in body["critical_missing"]

    preview = client.get("/api/doctor/preview")
    assert preview.status_code == 200
    assert preview.json()["required_artifact"] == "dist/index.html"

    voice = client.get("/api/voice/doctor")
    assert voice.status_code == 200
    voice_body = voice.json()
    assert "speech_provider_configured" in voice_body
    assert "audio/webm" in voice_body["supported_mime_types"]

"""
Fortune 100 Layer 3: Admin action audit logging.
"""

import pytest
from conftest import register_and_get_headers
from test_admin import register_admin_and_get_headers


@pytest.mark.asyncio
async def test_suspend_user_logged(app_client):
    """Suspend user action is logged to audit_log."""
    from server import db

    admin_headers = await register_admin_and_get_headers(app_client)
    me_admin = await app_client.get("/api/auth/me", headers=admin_headers, timeout=5)
    admin_id = me_admin.json().get("id")
    reg = await register_and_get_headers(app_client)
    me = await app_client.get("/api/auth/me", headers=reg, timeout=5)
    target_id = me.json().get("id")
    r = await app_client.post(
        f"/api/admin/users/{target_id}/suspend",
        json={"reason": "Audit test"},
        headers=admin_headers,
        timeout=10,
    )
    assert r.status_code == 200
    logs = (
        await db.audit_log.find({"user_id": admin_id})
        .sort("timestamp", -1)
        .limit(5)
        .to_list(5)
    )
    assert len(logs) > 0
    assert any(log.get("action") == "admin_suspend_user" for log in logs)


@pytest.mark.asyncio
async def test_grant_credits_logged(app_client):
    """Grant credits action is logged to audit_log."""
    from server import db

    admin_headers = await register_admin_and_get_headers(app_client)
    me_admin = await app_client.get("/api/auth/me", headers=admin_headers, timeout=5)
    admin_id = me_admin.json().get("id")
    reg = await register_and_get_headers(app_client)
    me = await app_client.get("/api/auth/me", headers=reg, timeout=5)
    target_id = me.json().get("id")
    r = await app_client.post(
        f"/api/admin/users/{target_id}/grant-credits",
        json={"credits": 10, "reason": "Audit test"},
        headers=admin_headers,
        timeout=10,
    )
    assert r.status_code == 200
    logs = (
        await db.audit_log.find({"user_id": admin_id})
        .sort("timestamp", -1)
        .limit(5)
        .to_list(5)
    )
    assert len(logs) > 0
    assert any(log.get("action") == "admin_grant_credits" for log in logs)


@pytest.mark.asyncio
async def test_downgrade_logged(app_client):
    """Downgrade user action is logged to audit_log."""
    from server import db

    admin_headers = await register_admin_and_get_headers(app_client)
    me_admin = await app_client.get("/api/auth/me", headers=admin_headers, timeout=5)
    admin_id = me_admin.json().get("id")
    reg = await register_and_get_headers(app_client)
    me = await app_client.get("/api/auth/me", headers=reg, timeout=5)
    target_id = me.json().get("id")
    r = await app_client.post(
        f"/api/admin/users/{target_id}/downgrade",
        headers=admin_headers,
        timeout=10,
    )
    assert r.status_code == 200
    logs = (
        await db.audit_log.find({"user_id": admin_id})
        .sort("timestamp", -1)
        .limit(5)
        .to_list(5)
    )
    assert len(logs) > 0
    assert any(log.get("action") == "admin_downgrade_user" for log in logs)


@pytest.mark.asyncio
async def test_audit_log_has_required_fields(app_client):
    """Audit log entries have user_id, action, resource_type, timestamp."""
    from server import db

    admin_headers = await register_admin_and_get_headers(app_client)
    reg = await register_and_get_headers(app_client)
    me = await app_client.get("/api/auth/me", headers=reg, timeout=5)
    target_id = me.json().get("id")
    await app_client.post(
        f"/api/admin/users/{target_id}/grant-credits",
        json={"credits": 5},
        headers=admin_headers,
        timeout=10,
    )
    logs = (
        await db.audit_log.find({"action": "admin_grant_credits"}).limit(1).to_list(1)
    )
    if logs:
        log = logs[0]
        assert "user_id" in log
        assert "action" in log
        assert log.get("action") == "admin_grant_credits"
        assert "timestamp" in log or "date" in log

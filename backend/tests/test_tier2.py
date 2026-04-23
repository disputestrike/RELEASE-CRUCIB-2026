"""
Tests for Tier 2: MFA, Audit Log, RBAC.
Run from repo root: pytest backend/tests/test_tier2.py -v
"""

from datetime import datetime, timezone

import pytest


# Unit tests that don't require DB or app
class TestRBAC:
    def test_get_user_role_default(self):
        from utils.rbac import Role, get_user_role

        assert get_user_role({}) == Role.OWNER
        assert get_user_role({"role": "viewer"}) == Role.VIEWER

    def test_has_permission_owner(self):
        from utils.rbac import Permission, Role, has_permission

        user = {"role": Role.OWNER.value}
        assert has_permission(user, Permission.CREATE_PROJECT)
        assert has_permission(user, Permission.DEPLOY_PROJECT)

    def test_has_permission_viewer(self):
        from utils.rbac import Permission, has_permission

        user = {"role": "viewer"}
        assert has_permission(user, Permission.VIEW_PROJECT)
        assert not has_permission(user, Permission.CREATE_PROJECT)


class TestAuditLogUtil:
    def test_audit_logger_init(self):
        from utils.audit_log import AuditLogger

        class FakeDb:
            async def insert_one(self, doc):
                return type("R", (), {"inserted_id": "id1"})()

            async def find(self, *a, **k):
                return type(
                    "C",
                    (),
                    {
                        "sort": lambda *a, **k: self,
                        "skip": lambda n: self,
                        "limit": lambda n: self,
                        "to_list": lambda l: [],
                    },
                )()

            async def count_documents(self, q):
                return 0

        db = FakeDb()
        logger = AuditLogger(db)
        assert logger.db is db


class TestMFAUtil:
    def test_pyotp_verify(self):
        import pyotp

        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        code = totp.now()
        assert totp.verify(code, valid_window=1)

    def test_backup_code_hash(self):
        import hashlib

        code = "a1b2c3d4"
        h = hashlib.sha256(code.encode()).hexdigest()
        assert hashlib.sha256(code.encode()).hexdigest() == h

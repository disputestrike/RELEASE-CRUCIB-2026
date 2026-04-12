"""Deterministic post-verify patches."""

import os
import tempfile

from orchestration.fixer import try_deterministic_verification_fix


def test_tenant_guc_hint_appended_to_main():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "backend"))
        main = os.path.join(d, "backend", "main.py")
        with open(main, "w", encoding="utf-8") as f:
            f.write("x = 1\n")
        vr = {"issues": ["Multitenant workspace must reference PostgreSQL set_config"]}
        assert try_deterministic_verification_fix("deploy.build", d, vr) == [
            "backend/main.py"
        ]
        text = open(main, encoding="utf-8").read()
        assert "set_config" in text.lower()
        assert "app.tenant_id" in text


def test_no_op_when_main_already_has_guc():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "backend"))
        main = os.path.join(d, "backend", "main.py")
        with open(main, "w", encoding="utf-8") as f:
            f.write(
                "await conn.execute(\"SELECT set_config('app.tenant_id', $1, true)\", tid)\n"
            )
        vr = {"issues": ["tenant context"]}
        assert try_deterministic_verification_fix("deploy.build", d, vr) == []

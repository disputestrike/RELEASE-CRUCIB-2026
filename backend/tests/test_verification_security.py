import os
import tempfile

from orchestration.multitenancy_rls_sql import migration_002_multitenancy_rls_sql
from orchestration.verification_security import verify_security_workspace
from orchestration.executor import _ensure_stripe_router_mounted, _main_py_sketch


def test_verify_security_finds_tenancy_and_stripe_sql():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "db", "migrations"), exist_ok=True)
        with open(
            os.path.join(d, "db", "migrations", "001.sql"), "w", encoding="utf-8"
        ) as f:
            f.write(
                "CREATE TABLE tenants (id uuid); ALTER TABLE app_items ADD tenant_id uuid;\n"
            )
        with open(
            os.path.join(d, "db", "migrations", "003.sql"), "w", encoding="utf-8"
        ) as f:
            f.write("CREATE TABLE stripe_events_processed (id text primary key);\n")
        os.makedirs(os.path.join(d, "backend"), exist_ok=True)
        with open(os.path.join(d, "backend", "main.py"), "w", encoding="utf-8") as f:
            f.write(
                "from fastapi import FastAPI\nfrom fastapi.middleware.cors import CORSMiddleware\n"
                'app = FastAPI()\napp.add_middleware(CORSMiddleware, allow_origins=["*"])\n'
            )
        with open(os.path.join(d, "package.json"), "w", encoding="utf-8") as f:
            f.write('{"dependencies":{"react":"18"}}\n')
        r = verify_security_workspace(d)
        assert r["passed"]
        titles = " ".join(p["title"] for p in r["proof"])
        assert "tenancy" in titles.lower()
        assert "stripe" in titles.lower() or "idempotency" in titles.lower()


def test_verify_security_detects_rls_in_migration_sql():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "db", "migrations"), exist_ok=True)
        with open(
            os.path.join(d, "db", "migrations", "002_multitenancy_rls.sql"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(migration_002_multitenancy_rls_sql())
        os.makedirs(os.path.join(d, "backend"), exist_ok=True)
        with open(os.path.join(d, "backend", "main.py"), "w", encoding="utf-8") as f:
            f.write("from fastapi import FastAPI\napp = FastAPI()\n")
        with open(os.path.join(d, "package.json"), "w", encoding="utf-8") as f:
            f.write('{"dependencies":{"react":"18"},"engines":{"node":">=18"}}\n')
        r = verify_security_workspace(d)
        assert r["passed"]
        checks = [p.get("payload", {}).get("check") for p in r["proof"]]
        assert "rls_policies_in_migrations" in checks


def test_stripe_router_patch_idempotent():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "backend"), exist_ok=True)
        main = _main_py_sketch(multitenant=False)
        with open(os.path.join(d, "backend", "main.py"), "w", encoding="utf-8") as f:
            f.write(main)
        _ensure_stripe_router_mounted(d)
        _ensure_stripe_router_mounted(d)
        text = open(os.path.join(d, "backend", "main.py"), encoding="utf-8").read()
        assert text.count("CRUCIBAI_STRIPE_ROUTER_MOUNT") == 1
        assert "include_router" in text

#!/usr/bin/env python3
"""Generate evidence that enterprise prompts build real app files instead of prompt-echo scaffolds."""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from orchestration.executor import (  # noqa: E402
    handle_backend_route,
    handle_db_migration,
    handle_delivery_manifest,
    handle_frontend_generate,
)
from orchestration.preview_gate import verify_preview_workspace  # noqa: E402


HELIOS_PROMPT = """
AEGIS OMEGA BUILD — END-TO-END ELITE AUTONOMOUS SYSTEM TEST

Build a production-style multi-tenant enterprise platform named:
Helios Aegis Command

The system must support CRM, quoting, project workflow, AI recommendation,
rules and policy engine, immutable audit/compliance, analytics, background jobs,
integration adapters, deployment manifests, and proof-enforced validation.
Do not scaffold. Build the strongest honest version of the product.
""".strip()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


async def main() -> int:
    proof_dir = ROOT / "proof" / "enterprise_build_fix"
    if proof_dir.exists():
        shutil.rmtree(proof_dir)
    proof_dir.mkdir(parents=True, exist_ok=True)

    os.environ["CRUCIBAI_SKIP_BROWSER_PREVIEW"] = "1"

    with tempfile.TemporaryDirectory(prefix="crucibai-enterprise-") as tmp:
        workspace = Path(tmp)
        job = {"id": "proof-helios-enterprise", "goal": HELIOS_PROMPT}

        frontend = await handle_frontend_generate({"step_key": "frontend.scaffold"}, job, str(workspace))
        backend_models = await handle_backend_route({"step_key": "backend.models"}, job, str(workspace))
        backend_routes = await handle_backend_route({"step_key": "backend.routes"}, job, str(workspace))
        backend_auth = await handle_backend_route({"step_key": "backend.auth"}, job, str(workspace))
        migration = await handle_db_migration({"step_key": "database.migration"}, job, str(workspace))
        seed = await handle_db_migration({"step_key": "database.seed"}, job, str(workspace))
        manifest = await handle_delivery_manifest({"step_key": "implementation.delivery_manifest"}, job, str(workspace))
        preview = await verify_preview_workspace(str(workspace))

        home_page = _read(workspace / "src" / "pages" / "HomePage.jsx")
        app_file = _read(workspace / "src" / "App.jsx")
        main_py = _read(workspace / "backend" / "main.py")
        schema_sql = _read(workspace / "db" / "migrations" / "001_enterprise_command_schema.sql")

        checks = {
            "enterprise_frontend_selected": "src/pages/PolicyPage.jsx" in frontend.get("output_files", []),
            "prompt_not_echoed_to_homepage": "MASTER EXECUTION DIRECTIVE" not in home_page and "You are an elite autonomous engineering" not in home_page,
            "enterprise_routes_present": "/api/policies/{policy_id}/enforce" in main_py and "/api/quotes/{quote_id}/approve" in main_py,
            "human_approval_boundary_present": "Explicit human approval role required" in main_py,
            "enterprise_schema_present": "CREATE TABLE IF NOT EXISTS policy_recommendations" in schema_sql,
            "preview_gate_passed": bool(preview.get("passed")),
            "delivery_manifest_written": "proof/DELIVERY_CLASSIFICATION.md" in manifest.get("output_files", []),
            "enterprise_navigation_present": all(route in app_file for route in ["/quotes", "/projects", "/policy", "/audit", "/analytics"]),
        }

        bundle: Dict[str, Any] = {
            "job": job,
            "results": {
                "frontend": frontend,
                "backend_models": backend_models,
                "backend_routes": backend_routes,
                "backend_auth": backend_auth,
                "migration": migration,
                "seed": seed,
                "manifest": manifest,
                "preview": preview,
            },
            "checks": checks,
            "workspace_snapshot": sorted(
                str(path.relative_to(workspace)).replace("\\", "/")
                for path in workspace.rglob("*")
                if path.is_file()
            ),
        }

        (proof_dir / "proof_bundle.json").write_text(json.dumps(bundle, indent=2, sort_keys=True), encoding="utf-8")
        (proof_dir / "HomePage.jsx").write_text(home_page, encoding="utf-8")
        (proof_dir / "App.jsx").write_text(app_file, encoding="utf-8")
        (proof_dir / "backend_main.py").write_text(main_py, encoding="utf-8")
        (proof_dir / "enterprise_schema.sql").write_text(schema_sql, encoding="utf-8")

        pass_fail_lines = [
            "# Enterprise build fix PASS/FAIL",
            "",
            "| Check | Result |",
            "| --- | --- |",
        ]
        for name, passed in checks.items():
            pass_fail_lines.append(f"| `{name}` | {'PASS' if passed else 'FAIL'} |")
        (proof_dir / "PASS_FAIL.md").write_text("\n".join(pass_fail_lines) + "\n", encoding="utf-8")

        root_cause = """# Root cause

- Enterprise prompts were being sent through the generic frontend/backend agent path first.
- When that path returned weak or empty output, CrucibAI silently downgraded to the generic preview scaffold.
- The generic scaffold rendered a sanitized slice of `job.goal`, which is why the published app showed the Aegis Omega spec instead of a real Helios product.

# Fix

- Enterprise prompt detection now routes directly into the enterprise command build pack before generic agents run.
- The enterprise pack emits a multi-page command center frontend, a tenant-aware FastAPI backend, and enterprise SQL migrations/seeds.
- The generic fallback no longer renders the raw prompt text into the visible app.
"""
        (proof_dir / "ROOT_CAUSE.md").write_text(root_cause, encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

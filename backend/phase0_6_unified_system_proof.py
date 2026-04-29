"""
Unified Phase 0 -> 6 system proof.

Goal:
Prove the project behaves as one integrated software stack, not disconnected phases.

Checks:
- Phase 0: compliance/proof baseline artifacts exist
- Phases 1-6: integrated AGI orchestrator executes end-to-end
- Phase 5: stress pipeline (assembly/runtime/export)
- Phase 6B: deployment proof (provider/config/url/routes/logs/rollback)
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from phase_integration import AGICapabilityOrchestrator
from phase6_multimodal import MediaInput, MediaType
from phase5_stress_test import Phase5StressTest
from phase6_deployment_proof import DeploymentProofRunner


class InMemoryDB:
    """Tiny async db shim compatible with phase modules."""

    def __init__(self):
        self.rows: Dict[str, List[Dict[str, Any]]] = {}

    async def insert_one(self, collection: str, payload: Dict[str, Any]):
        self.rows.setdefault(collection, []).append(payload)
        return {"ok": True}

    async def find(self, collection: str, query: Dict[str, Any]):
        # Simple implementation: return all rows for collection.
        return list(self.rows.get(collection, []))


def phase0_checks(repo_root: Path) -> Dict[str, Any]:
    required = [
        repo_root / "docs" / "PHASE0_COMPLIANCE_AND_PROOF.md",
        repo_root / "docs" / "STRESS_TEST_BUILD_BRIEF.md",
    ]
    existing = [str(p) for p in required if p.exists()]
    return {
        "required_count": len(required),
        "found_count": len(existing),
        "found_paths": existing,
        "passed": len(existing) == len(required),
    }


async def run_integration_1_6() -> Dict[str, Any]:
    db = InMemoryDB()
    orchestrator = AGICapabilityOrchestrator(db)
    await orchestrator.initialize()

    problem = {
        "domain": "software_engineering",
        "description": "Generate a robust tenant-aware SaaS module with validation and API flow",
        "requirements": ["routing", "validation", "db schema", "tests"],
    }
    media = [
        MediaInput(
            media_id="img_arch",
            media_type=MediaType.IMAGE.value,
            source="local://architecture.png",
            format="png",
            metadata={"type": "architecture"},
        ),
        MediaInput(
            media_id="doc_spec",
            media_type=MediaType.DOCUMENT.value,
            source="local://spec.pdf",
            format="pdf",
            metadata={"type": "spec"},
        ),
    ]

    execution = await orchestrator.solve_problem(problem, media)
    phases = execution.get("phases_executed", [])
    expected = {
        "domain_knowledge",
        "reasoning",
        "self_correction",
        "learning",
        "creative_solving",
        "multimodal",
    }
    return {
        "success": bool(execution.get("success")),
        "phases_executed": phases,
        "all_expected_phases_seen": expected.issubset(set(phases)),
        "execution_error": execution.get("error"),
    }


async def main() -> int:
    started = datetime.now(timezone.utc).isoformat()
    backend_dir = Path(__file__).resolve().parent
    repo_root = backend_dir.parent
    proof_dir = backend_dir / "proof-ci"
    proof_dir.mkdir(parents=True, exist_ok=True)

    result: Dict[str, Any] = {
        "started": started,
        "phase0": {},
        "phase1_6_integration": {},
        "phase5": {},
        "phase6b": {},
        "overall_passed": False,
        "ended": None,
    }

    # Phase 0
    result["phase0"] = phase0_checks(repo_root)

    # Phases 1-6 merged execution
    result["phase1_6_integration"] = await run_integration_1_6()

    # Phase 5 unified build/runtime/export
    p5 = Phase5StressTest()
    p5_result = await p5.run()
    result["phase5"] = {
        "exit_code": p5_result.get("exit_code"),
        "status": p5_result.get("status"),
        "assembly_success": p5_result.get("assembly", {}).get("success"),
        "runtime_alive": p5_result.get("assembly", {}).get("runtime_alive"),
        "export_allowed": p5_result.get("export", {}).get("export_allowed") if p5_result.get("export") else None,
    }

    # Phase 6B deployment proof
    p6b = DeploymentProofRunner()
    p6b_result = await p6b.run()
    result["phase6b"] = {
        "status": p6b_result.get("status"),
        "provider_selected": p6b_result.get("provider_selected"),
        "live_url_http_200": p6b_result.get("live_url_http_200"),
        "deployed_route_checks_passed": p6b_result.get("deployed_route_checks_passed"),
        "rollback_supported": p6b_result.get("rollback_failure_handling", {}).get("supported"),
    }

    result["overall_passed"] = all(
        [
            result["phase0"].get("passed"),
            result["phase1_6_integration"].get("success"),
            result["phase1_6_integration"].get("all_expected_phases_seen"),
            result["phase5"].get("exit_code") == 0,
            result["phase6b"].get("status") == "passed",
        ]
    )
    result["ended"] = datetime.now(timezone.utc).isoformat()

    out_path = proof_dir / "phase0_6_unified_system_proof.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(json.dumps(result, indent=2))
    print(f"Proof artifact: {out_path}")
    return 0 if result["overall_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))


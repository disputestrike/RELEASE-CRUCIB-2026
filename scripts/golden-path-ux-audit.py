#!/usr/bin/env python3
"""Audit the launch-critical golden-path UX wiring without requiring host Node."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _contains_all(path: Path, markers: Iterable[str]) -> tuple[bool, list[str]]:
    source = _read(path)
    missing = [marker for marker in markers if marker not in source]
    return not missing, missing


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit CrucibAI golden-path UX contracts.")
    parser.add_argument("--proof-dir", default="proof/golden_path_ux", help="Directory for proof artifacts.")
    args = parser.parse_args()

    proof_dir = ROOT / args.proof_dir
    proof_dir.mkdir(parents=True, exist_ok=True)

    checks = [
        {
            "id": "onboarding_three_outcomes",
            "file": ROOT / "frontend/src/pages/OnboardingPage.jsx",
            "markers": ["Build new app", "Improve existing code", "Automate workflow", "state: card.state"],
            "requirement": "Onboarding presents the three launch paths and carries intent into the app.",
        },
        {
            "id": "dashboard_golden_path",
            "file": ROOT / "frontend/src/pages/Dashboard.jsx",
            "markers": ["GOLDEN_PATH_STEPS", "Build, prove, preview, publish", "openImport", "suggestedPrompt"],
            "requirement": "Dashboard foregrounds the prompt/import -> proof -> publish journey.",
        },
        {
            "id": "engine_room_beta_gating",
            "file": ROOT / "frontend/src/components/Sidebar.jsx",
            "markers": ["beta: true", "sidebar-engine-beta"],
            "requirement": "Incomplete engine-room product surfaces are marked beta instead of launch-ready.",
        },
        {
            "id": "public_status_full_systems",
            "file": ROOT / "frontend/src/pages/Status.jsx",
            "markers": ["Full Systems Gate", "trust/full-systems-summary", "fullSystemsReady"],
            "requirement": "Public status page exposes the full-systems gate as a launch-critical service.",
        },
        {
            "id": "security_terminal_trust",
            "file": ROOT / "frontend/src/pages/Security.jsx",
            "markers": ["Terminal", "audit", "Generated-code sandbox", "Community templates", "full systems"],
            "requirement": "Security page discloses terminal policy and full-systems proof posture.",
        },
        {
            "id": "public_templates_community_trust",
            "file": ROOT / "frontend/src/pages/TemplatesPublic.jsx",
            "markers": ["community/templates", "proof_score", "moderation_status"],
            "requirement": "Public templates surface reads curated community templates with proof and moderation signals.",
        },
        {
            "id": "visual_edit_endpoint",
            "file": ROOT / "backend/server.py",
            "markers": ["/jobs/{job_id}/visual-edit", "snapshot_path", "VisualEditRequest"],
            "requirement": "Visual edit v1 has an owned workspace patch endpoint and undo snapshot.",
        },
        {
            "id": "terminal_audit_endpoint",
            "file": ROOT / "backend/server.py",
            "markers": ["/terminal/audit", "audit_events_for_user", "get_current_user"],
            "requirement": "Terminal actions have an authenticated user-visible audit trail.",
        },
        {
            "id": "trust_full_systems_endpoint",
            "file": ROOT / "backend/routes/trust.py",
            "markers": ["/trust/full-systems-summary", "proof/full_systems/summary.json", "required_failures"],
            "requirement": "Public trust API exposes full-systems proof status without leaking secrets.",
        },
        {
            "id": "community_router_extracted",
            "file": ROOT / "backend/routes/community.py",
            "markers": ["/templates", "/case-studies", "/moderation-policy", "remix_endpoint"],
            "requirement": "Community/templates routes live outside the monolithic server router.",
        },
    ]

    results = []
    for check in checks:
        path = check["file"]
        if not path.exists():
            passed = False
            missing = [str(path)]
        else:
            passed, missing = _contains_all(path, check["markers"])
        results.append({
            "id": check["id"],
            "requirement": check["requirement"],
            "file": str(path.relative_to(ROOT)),
            "passed": passed,
            "missing": missing,
        })

    passed_count = sum(1 for result in results if result["passed"])
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": passed_count == len(results),
        "passed_count": passed_count,
        "total_count": len(results),
        "results": results,
    }

    (proof_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    rows = [
        "# Golden Path UX Audit",
        "",
        f"Generated: {summary['generated_at']}",
        "",
        "| Check | Status | File | Missing |",
        "|---|---|---|---|",
    ]
    for result in results:
        missing = ", ".join(result["missing"]) if result["missing"] else "-"
        rows.append(f"| {result['id']} | {'PASS' if result['passed'] else 'FAIL'} | {result['file']} | {missing} |")
    rows.extend(["", f"Passed: {passed_count}/{len(results)}"])
    (proof_dir / "PASS_FAIL.md").write_text("\n".join(rows), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

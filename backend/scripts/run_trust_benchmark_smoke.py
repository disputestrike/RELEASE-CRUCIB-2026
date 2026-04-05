#!/usr/bin/env python3
"""
Smoke benchmark for trust scoring + roadmap wiring (no DB required).
Run from repo: python backend/scripts/run_trust_benchmark_smoke.py
"""
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT / "backend"))

from orchestration.trust.roadmap_wiring import roadmap_wiring_status  # noqa: E402
from orchestration.trust.trust_scoring import compute_trust_metrics  # noqa: E402


def main() -> int:
    sample_items = [
        {"payload": {"verification_class": "presence"}, "proof_type": "file", "title": "f1"},
        {"payload": {"verification_class": "syntax"}, "proof_type": "compile", "title": "c1"},
        {"payload": {"verification_class": "runtime"}, "proof_type": "api", "title": "a1"},
        {"payload": {"verification_class": "experience", "kind": "preview_screenshot"}, "title": "p1"},
    ]
    metrics = compute_trust_metrics(sample_items, has_screenshot_proof=True, has_live_deploy_url=True)
    out = {
        "benchmark": "trust_smoke_v1",
        "metrics": metrics,
        "roadmap_item_count": len(roadmap_wiring_status()),
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

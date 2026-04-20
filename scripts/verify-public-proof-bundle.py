#!/usr/bin/env python3
"""Verify signed proof manifests under product_dominance_v1."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from services.proof_manifest import verify_manifest  # noqa: E402

BENCH_ROOT = REPO_ROOT / "proof" / "benchmarks" / "product_dominance_v1"


def main() -> int:
    secret = (os.environ.get("CRUCIB_PROOF_HMAC_SECRET") or "").strip()
    if not secret:
        raise RuntimeError("CRUCIB_PROOF_HMAC_SECRET is required for proof verification")

    manifests = sorted(BENCH_ROOT.glob("**/proof_manifest.json"))
    if not manifests:
        print(json.dumps({"ok": True, "verified": 0, "reason": "no_manifests_found"}, indent=2))
        return 0

    verified = 0
    failures = []
    for path in manifests:
        data = json.loads(path.read_text(encoding="utf-8"))
        result = verify_manifest(data, secret=secret)
        if result.get("ok"):
            verified += 1
        else:
            failures.append({
                "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
                "result": result,
            })

    out = {
        "ok": not failures,
        "verified": verified,
        "failed": len(failures),
        "failures": failures,
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

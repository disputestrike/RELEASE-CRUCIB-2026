#!/usr/bin/env python3
"""Wave 3 — Competitor benchmark runner.

Usage
-----
  python scripts/run_competitor_benchmarks.py [--mode=seeded] [--out=DIR]
  python scripts/run_competitor_benchmarks.py --mode=live

Modes
-----
seeded (default)
    Writes a deterministic, seed-based competitor snapshot to
    proof/benchmarks/competitors/{timestamp}.json.
    No network calls, no credentials required.  Safe to run in CI.

live
    Reads COMPETITOR_CREDS env var → path to a YAML file with shape:
        cursor:  {email: ..., password: ...}
        lovable: {email: ..., password: ...}
        bolt:    {email: ..., password: ...}
        replit:  {email: ..., password: ...}
    If the env var is absent, prints an error and exits 2.
    If the file exists, logs "live-mode stub — real runner TBD" and exits 0.
    (Hook — real runner to be implemented when creds are available.)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Repo-root resolution ──────────────────────────────────────────────────────
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent

# ── Axes must match _COMPETITOR_BASELINE in benchmarks_api.py ────────────────
_AXES = [
    "first_preview_target_seconds",
    "repeatability_pass_rate",
    "deploy_targets_supported",
    "mobile_proof_run",
    "migration_mode_supported",
    "inspect_mode_supported",
    "typed_tool_registry",
]

_SEEDED_DATA = {
    "cursor": {
        "first_preview_target_seconds": None,
        "repeatability_pass_rate": None,
        "deploy_targets_supported": [],
        "mobile_proof_run": False,
        "migration_mode_supported": True,
        "inspect_mode_supported": False,
        "typed_tool_registry": True,
        "source": "seeded_public_marketing_claim",
    },
    "lovable": {
        "first_preview_target_seconds": 60,
        "repeatability_pass_rate": None,
        "deploy_targets_supported": ["vercel", "netlify"],
        "mobile_proof_run": False,
        "migration_mode_supported": False,
        "inspect_mode_supported": False,
        "typed_tool_registry": False,
        "source": "seeded_public_marketing_claim",
    },
    "bolt": {
        "first_preview_target_seconds": 60,
        "repeatability_pass_rate": None,
        "deploy_targets_supported": ["netlify"],
        "mobile_proof_run": False,
        "migration_mode_supported": False,
        "inspect_mode_supported": False,
        "typed_tool_registry": False,
        "source": "seeded_public_marketing_claim",
    },
    "replit": {
        "first_preview_target_seconds": None,
        "repeatability_pass_rate": None,
        "deploy_targets_supported": ["replit"],
        "mobile_proof_run": False,
        "migration_mode_supported": False,
        "inspect_mode_supported": False,
        "typed_tool_registry": False,
        "source": "seeded_public_marketing_claim",
    },
}


def run_seeded(out_dir: Path) -> Path:
    """Write a deterministic competitor snapshot to *out_dir*."""
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"{timestamp}.json"

    payload = {
        "version": f"{timestamp}.competitor-seeded.v1",
        "mode": "seeded",
        "axes": _AXES,
        "competitors": _SEEDED_DATA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    print(f"[seeded] wrote {out_path}")
    return out_path


def run_live() -> None:
    """Live-mode stub — credentials hook, no implementation yet."""
    creds_path = os.environ.get("COMPETITOR_CREDS", "").strip()
    if not creds_path:
        print(
            "Live mode needs COMPETITOR_CREDS=path/to/creds.yaml",
            file=sys.stderr,
        )
        sys.exit(2)
    # Creds path provided — real runner TBD.
    print("live-mode stub — real runner TBD")
    sys.exit(0)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CrucibAI competitor benchmark runner"
    )
    parser.add_argument(
        "--mode",
        choices=["seeded", "live"],
        default="seeded",
        help="seeded (default, deterministic) or live (needs COMPETITOR_CREDS)",
    )
    parser.add_argument(
        "--out",
        default=str(_REPO_ROOT / "proof" / "benchmarks" / "competitors"),
        help="Output directory for seeded mode (default: proof/benchmarks/competitors/)",
    )
    args = parser.parse_args()

    if args.mode == "live":
        run_live()
    else:
        run_seeded(Path(args.out))


if __name__ == "__main__":
    main()

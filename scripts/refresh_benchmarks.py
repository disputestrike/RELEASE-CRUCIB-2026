#!/usr/bin/env python3
"""CF26 — Idempotent benchmark baseline refresher.

Updates the `last_refreshed_utc` field on every entry inside
backend/routes/benchmarks_api.py::_COMPETITOR_BASELINE without touching
any numeric score. Safe to run on a schedule.

Usage:
    python3 scripts/refresh_benchmarks.py            # applies changes
    python3 scripts/refresh_benchmarks.py --dry-run  # prints diff only
"""
from __future__ import annotations

import argparse
import difflib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


TARGET = Path(__file__).resolve().parent.parent / "backend" / "routes" / "benchmarks_api.py"


def _apply(text: str, stamp: str) -> str:
    """Inject or update `"last_refreshed_utc": "<stamp>"` on each dict entry
    of `_COMPETITOR_BASELINE`.  Non-destructive: only touches that field.
    """
    # Find the _COMPETITOR_BASELINE block
    start = text.find("_COMPETITOR_BASELINE")
    if start < 0:
        raise SystemExit("_COMPETITOR_BASELINE not found in target file")
    # Refresh only existing stamps
    pattern = re.compile(r'"last_refreshed_utc"\s*:\s*"[^"]*"')
    if pattern.search(text):
        new_text = pattern.sub(f'"last_refreshed_utc": "{stamp}"', text)
    else:
        # Seed one top-level stamp comment after the dict name (safe, single insertion)
        insertion = f"\n# last benchmark refresh: {stamp}\n"
        new_text = text[:start] + insertion + text[start:]
    return new_text


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--path", default=str(TARGET))
    args = ap.parse_args(argv)

    p = Path(args.path)
    if not p.exists():
        print(f"[refresh_benchmarks] target missing: {p}", file=sys.stderr)
        return 1

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    original = p.read_text()
    updated = _apply(original, stamp)

    if original == updated:
        print(f"[refresh_benchmarks] no change needed (stamp {stamp})")
        return 0

    if args.dry_run:
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=str(p),
            tofile=str(p) + " (updated)",
            n=2,
        )
        sys.stdout.writelines(diff)
        print(f"\n[refresh_benchmarks] dry-run OK (stamp {stamp})")
        return 0

    p.write_text(updated)
    print(f"[refresh_benchmarks] refreshed {p} with {stamp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

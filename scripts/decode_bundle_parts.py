#!/usr/bin/env python3
"""
Reassemble a git bundle from chat-split Base64 parts.

One or more text files may contain blocks like:
  ---BEGIN PART 001---
  ...base64...
  ---END PART 001---

Parts are collected from ALL input files, sorted by part number, then decoded.

Usage:
  python scripts/decode_bundle_parts.py [parts1.txt [parts2.txt ...]] OUTPUT.bundle

Example (merge Codex chunks + your saved 001-003):
  python scripts/decode_bundle_parts.py handoff/bundle_parts_001_003.txt handoff/bundle_parts_004_006.txt crucibai-work.bundle

Verify:
  git bundle verify crucibai-work.bundle
"""
from __future__ import annotations

import base64
import re
import sys
from pathlib import Path


def collect_parts(text: str) -> list[tuple[int, str]]:
    found = re.findall(
        r"---BEGIN PART (\d+)---\s*(.*?)\s*---END PART \d+---",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return [(int(n), body) for n, body in found]


def main() -> int:
    argv = sys.argv[1:]
    if len(argv) < 2:
        print(__doc__)
        return 2
    out = Path(argv[-1])
    src_paths = [Path(p) for p in argv[:-1]]

    combined: list[tuple[int, str]] = []
    for p in src_paths:
        if not p.is_file():
            print(f"Missing input file: {p}")
            return 1
        text = p.read_text(encoding="utf-8", errors="replace")
        combined.extend(collect_parts(text))

    if not combined:
        print("No PART blocks found in inputs.")
        return 1

    combined.sort(key=lambda x: x[0])
    nums = [n for n, _ in combined]
    if len(nums) != len(set(nums)):
        print("Warning: duplicate part numbers; later file order wins after sort — check inputs.")

    raw_b64 = "".join(body for _, body in combined)
    raw_b64 = re.sub(r"\s+", "", raw_b64)
    missing = (-len(raw_b64)) % 4
    if missing:
        raw_b64 += "=" * missing
    try:
        data = base64.b64decode(raw_b64, validate=True)
    except Exception as e:
        print("Base64 decode failed:", e)
        print("Often: truncated last part, missing PART 001–003, or copy/paste errors.")
        return 1

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    print(f"Wrote {out.resolve()} ({len(data):,} bytes)")
    print(f"Parts merged (sorted): {nums}")
    if len(data) < 500_000:
        print("Warning: bundle is small; full branch export was ~9–10 MB.")
    head = data[:32]
    if head.startswith(b"# v2 git bundle\n") or head.startswith(b"# v3 git bundle\n"):
        print("Header looks like a git bundle.")
    elif data[:15] == b"# v2 git bundle":
        print("Header looks like a git bundle (partial read).")
    else:
        print("Warning: does not start with '# v2 git bundle' — wrong or incomplete parts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

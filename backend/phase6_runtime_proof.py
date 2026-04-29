"""
Phase 6 runtime proof harness.

Runs a concrete multimodal pass and prints deterministic proof output.

Exit codes:
    0 = runtime proof passed
    1 = runtime proof failed
"""

import asyncio
import json
import sys
from datetime import datetime, timezone

from phase6_multimodal import MediaInput, MediaType, MultiModalUnderstanding


class InMemoryDB:
    """Minimal async DB shim for phase6 runtime proof."""

    def __init__(self):
        self.rows = []

    async def insert_one(self, collection, payload):
        self.rows.append({"collection": collection, "payload": payload})
        return {"ok": True, "collection": collection}


async def main():
    started = datetime.now(timezone.utc).isoformat()
    print("=" * 70)
    print("PHASE 6 - RUNTIME PROOF")
    print("=" * 70)
    print(f"Started: {started}")

    db = InMemoryDB()
    engine = MultiModalUnderstanding(db)

    media_inputs = [
        MediaInput(
            media_id="img_hero",
            media_type=MediaType.IMAGE.value,
            source="local://hero.png",
            format="png",
            metadata={"role": "hero"},
        ),
        MediaInput(
            media_id="audio_call",
            media_type=MediaType.AUDIO.value,
            source="local://call.wav",
            format="wav",
            metadata={"role": "support_call"},
        ),
        MediaInput(
            media_id="doc_policy",
            media_type=MediaType.DOCUMENT.value,
            source="local://policy.pdf",
            format="pdf",
            metadata={"role": "policy"},
        ),
    ]

    result = await engine.process_multimodal_input(media_inputs)

    checks = {
        "inputs_processed_3": result.get("inputs_processed") == 3,
        "vision_present": "vision" in result.get("insights_by_type", {}),
        "audio_present": "audio" in result.get("insights_by_type", {}),
        "document_present": "document" in result.get("insights_by_type", {}),
        "db_inserted": len(db.rows) == 1,
        "synthesis_present": bool(result.get("synthesis")),
    }

    all_passed = all(checks.values())
    print("Checks:", json.dumps(checks, indent=2))
    print(f"DB rows: {len(db.rows)}")
    print("Status:", "PASSED" if all_passed else "FAILED")
    print("=" * 70)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    asyncio.run(main())

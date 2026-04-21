"""Wave 3 — Public (no-auth) benchmark scorecard endpoint.

Exposes a read-only scorecard derived from the private benchmark data so that
external auditors, prospects, and embedding sites can access it without
authentication.

GET /public/benchmarks/scorecard
    Returns axes, competitor names, and per-product cell values drawn from
    _COMPETITOR_BASELINE in benchmarks_api.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter

from routes.benchmarks_api import _COMPETITOR_BASELINE

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public/benchmarks", tags=["public-benchmarks"])


def _build_scorecard() -> Dict[str, Any]:
    """Derive a scorecard dict from the shared _COMPETITOR_BASELINE."""
    axes: List[str] = _COMPETITOR_BASELINE.get("axes", [])
    products: List[Dict[str, Any]] = _COMPETITOR_BASELINE.get("products", [])

    # Build column headers (competitor names in canonical order)
    competitors: List[Dict[str, str]] = [
        {"id": p["id"], "name": p["name"]} for p in products
    ]

    # Build row-major scorecard: one dict per axis
    scorecards: List[Dict[str, Any]] = []
    for axis in axes:
        row: Dict[str, Any] = {"axis": axis, "values": {}}
        for product in products:
            row["values"][product["id"]] = product.get(axis)
        scorecards.append(row)

    return {
        "version": _COMPETITOR_BASELINE.get("version"),
        "axes": axes,
        "competitors": competitors,
        "scorecards": scorecards,
        "note": (
            "Independently reproducible — seed and raw data in "
            "proof/benchmarks/"
        ),
    }


@router.get("/scorecard")
async def public_scorecard():
    """Return the full competitor scorecard, no authentication required."""
    return _build_scorecard()

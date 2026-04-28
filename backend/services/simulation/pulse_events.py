"""Human-readable pulse lines derived from a completed debate + population snapshot.

Deterministic narrative hooks from structured data—not extra LLM calls—to power a live feed UX."""
from __future__ import annotations

from typing import Any, Dict, List

from .models import ScenarioClassification


def _truncate(text: str, limit: int = 220) -> str:
    t = (text or "").strip()
    if len(t) <= limit:
        return t
    return t[: max(1, limit - 1)] + "…"


def _gap_headline(missing: List[Any]) -> str:
    if not missing:
        return ""
    raw = missing[0]
    if isinstance(raw, str):
        return _truncate(raw, 200)
    if isinstance(raw, dict):
        return _truncate(str(raw.get("claim_text") or raw.get("detail") or raw.get("text") or raw.get("issue") or ""), 200)
    return _truncate(str(raw), 200)


def _msg_excerpt(messages: List[Dict[str, Any]], round_no: int) -> str:
    for m in messages:
        try:
            r = int(m.get("round_number") or 0)
        except (TypeError, ValueError):
            r = 0
        if r == round_no:
            c = str(m.get("content") or "").strip()
            if c:
                return c
    return ""


def build_simulation_pulse(
    *,
    classification: ScenarioClassification,
    debate: Dict[str, Any],
    population_model: Dict[str, Any],
    evidence_summary: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Return ordered feed items suitable for replay + REST response."""

    pulses: List[Dict[str, Any]] = []
    messages = list(debate.get("messages") or [])
    avg_b = float(debate.get("average_belief") or 0)
    agr = float(debate.get("agreement") or 0)
    missing = list(evidence_summary.get("missing_evidence") or [])

    ex3 = _msg_excerpt(messages, 3)
    if ex3:
        pulses.append(
            {
                "kind": "arena_cross_pressure",
                "emoji": "⚡",
                "title": "Arena cross-pressure",
                "body": _truncate(ex3, 218),
                "cause": "Round 3 arguments stress-test peer disagreement before beliefs compound.",
            }
        )

    ex6 = _msg_excerpt(messages, 6)
    if ex6:
        pulses.append(
            {
                "kind": "peer_paraphrase_mid",
                "emoji": "🧭",
                "title": "Mid-run peer challenge",
                "body": _truncate(ex6, 218),
                "cause": "Round 6 forces explicit replies to neighboring agents, not parallel monologue.",
            }
        )

    clusters_pop = sorted(
        (population_model.get("clusters") or []),
        key=lambda c: -(float(c.get("share") or 0)),
    )
    if clusters_pop:
        top = clusters_pop[0]
        label = str(top.get("label") or "Leading cohort")
        share = float(top.get("share") or 0)
        pct = round(share * 100)
        pulses.append(
            {
                "kind": "cohort_center_of_mass",
                "emoji": "📈",
                "title": "Cohort center-of-mass",
                "body": f'{label} holds the widest modeled stance band (~{pct}% share of synthetic perspectives).',
                "cause": "Population clustering weighs agent divergence + seeded cohort bias for this domain.",
            }
        )

    gap = _gap_headline(missing)
    if gap:
        pulses.append(
            {
                "kind": "unresolved_lever",
                "emoji": "🔗",
                "title": "Unresolved lever still swings outcomes",
                "body": f'Evidence choke point: "{gap}"',
                "cause": "Marked as disproportionate leverage on calibrated verdict uncertainty.",
            }
        )

    pulses.append(
        {
            "kind": "belief_telemetry",
            "emoji": "📊",
            "title": "Belief telemetry after debate lattice",
            "body": (
                f"Synthetic cohort reference belief ≈ {round(avg_b * 100)}%; "
                f"arena cohesion index ≈ {round(agr * 100)}% "
                "(higher means agents converged)."
            ),
            "cause": "Derived from pairwise belief deltas and round-by-round deltas.",
        }
    )

    stype = str(classification.scenario_type or "").replace("_", " ") or "scenario frame"
    dom = str(classification.domain or "scenario")
    pulses.append(
        {
            "kind": "domain_echo",
            "emoji": "🎯",
            "title": "Domain echo",
            "body": f"Dominant frame: {stype} @ {dom} — pulses are mechanically keyed to this classification.",
            "cause": "Classifier anchors vocabulary so the feed avoids unrelated invented tropes.",
        }
    )

    return pulses[:8]

"""Optional Claude layer: replace template debate utterances with expert-sounding prose.

Falls back to templates when ``ANTHROPIC_API_KEY`` is absent, JSON parse fails,
or ``REALITY_ENGINE_LLM_DEBATE`` is falsy."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List

from .models import ScenarioClassification

_LOGGER = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are rewriting a multi-agent technical debate transcript for simulation transparency.
OUTPUT RULES — reply with VALID JSON ONLY, no markdown fencing:
{"replacements":[{"index":NUMBER,"content":"STRING"}, ...]}

- Use the same cardinality and order implied by INPUT ``instructions[].index`` (preserve index values 0..N-1 exactly once each).
- Each content: 80–520 characters; domain-appropriate jargon for the ROLE implied by drafts; cite gaps/tensions—not hallucinated patient directives.
- Vary wording across indices—do not reuse one sentence verbatim for different agents.
"""


def _json_from_model_text(text: str) -> Dict[str, Any]:
    t = text.strip()
    if "```" in t:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", t)
        if m:
            t = m.group(1).strip()
    return json.loads(t)


async def augment_debate_with_llm_maybe(
    debate: Dict[str, Any],
    *,
    classification: ScenarioClassification,
    evidence_summary: Dict[str, Any],
) -> Dict[str, Any]:
    """Rewrite ``debate[\"messages\"][\"content\"]`` when Claude is reachable."""

    debate.setdefault("debate_engine_mode", "template_skeleton")
    msgs: List[Dict[str, Any]] = list(debate.get("messages") or [])
    if os.getenv("REALITY_ENGINE_LLM_DEBATE", "1").lower() not in {"1", "true", "yes", "on"}:
        debate["debate_engine_mode"] = "template_skeleton"
        debate["debate_augment_reason"] = "REALITY_ENGINE_LLM_DEBATE disabled"
        return debate

    api_key = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if not api_key or not msgs:
        debate.setdefault("debate_augment_reason", "ANTHROPIC_API_KEY not set — template prose retained" if not api_key else "no messages")
        return debate

    indexed = list(enumerate(msgs))
    indexed.sort(key=lambda im: ((im[1].get("round_number") or 0), str(im[1].get("agent_id") or "")))
    max_ut = max(12, min(48, int(os.getenv("CRUCIB_SIM_LLM_DEBATE_MAX_MESSAGES") or "32")))
    capped_tuples = indexed[:max_ut]

    evidence_bits = []
    for ev in (evidence_summary.get("evidence") or [])[:12]:
        c = ev.get("claim") if isinstance(ev, dict) else str(ev)
        if c:
            evidence_bits.append(str(c)[:380])
    miss = evidence_summary.get("missing_evidence") or []
    miss_text = [m if isinstance(m, str) else (m.get("claim_text") or str(m)) for m in miss[:10]]

    briefing = {
        "domain": classification.domain,
        "scenario_type": classification.scenario_type,
        "interpretation_seed": classification.interpretation[:700],
        "evidence_claims_truncated": evidence_bits[:10],
        "missing_evidence": miss_text,
        "instructions": [
            {"index": slot, "draft": str(msgs[oix].get("content") or "")[:420]}
            for slot, (oix, _) in enumerate(capped_tuples)
        ],
    }

    skipped = len(msgs) - len(capped_tuples)
    user_block = json.dumps(briefing, ensure_ascii=False)[:14000]

    try:
        from .....services.llm_service import _call_anthropic_direct        from .....anthropic_models import ANTHROPIC_HAIKU_MODEL
        model = os.getenv("REALITY_ENGINE_DEBATE_MODEL", "").strip() or ANTHROPIC_HAIKU_MODEL
        raw = await _call_anthropic_direct(
            user_block,
            _SYSTEM_PROMPT,
            model=model,
            api_key=api_key,
        )
        data = _json_from_model_text(raw)
        reps = data.get("replacements") or []
        by_idx = {int(r["index"]): str(r.get("content") or "").strip() for r in reps if r.get("index") is not None}
        for slot, (oix, _) in enumerate(capped_tuples):
            new_c = by_idx.get(slot)
            if new_c:
                msgs[oix]["content"] = new_c[:2000]

        debate["debate_engine_mode"] = "llm_augmented_claude"
        debate["debate_augment_reason"] = None
        debate["debate_augment_caps"] = {
            "messages_total": len(msgs),
            "messages_augmented": len(capped_tuples),
            "skipped_tail": skipped,
            "model": model,
        }

        agents_by_id = {a["id"]: a for a in debate.get("agents") or []}
        for aid in list(agents_by_id.keys()):
            agent_msgs = [m for m in msgs if m.get("agent_id") == aid]
            if agent_msgs:
                last_m = max(agent_msgs, key=lambda m: int(m.get("round_number") or 0))
                agents_by_id[aid]["latest_argument"] = last_m.get("content", "")
                agents_by_id[aid]["latest_round"] = last_m.get("round_number")
    except Exception as exc:
        debate["debate_augment_reason"] = f"{type(exc).__name__}: {str(exc)[:400]}"
        _LOGGER.warning("[debate_llm] augment failed; using templates: %s", exc)

    return debate

"""Auto memory consolidator.

Adapted from claude-code-collection/memory/consolidator.py.
Extracts long-term insights from completed sessions using a lightweight LLM
call. Design principles mirror the original:
  • Hard cap of 3 memories per session
  • Auto-extracted memories start at 0.8 confidence
  • Won't overwrite a higher-confidence existing memory
  • Skips short sessions
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

MIN_MESSAGES_TO_CONSOLIDATE = 8
MAX_MEMORIES_PER_SESSION = 3
DEFAULT_CONFIDENCE = 0.8

SYSTEM_PROMPT = """You are a memory consolidation assistant. Analyze the conversation
below and extract insights worth storing as persistent memories for future sessions.

Focus ONLY on:
1. New user preferences or working-style corrections revealed in this session
2. Project decisions or facts made explicit (NOT derivable from code/git)
3. Behavioral feedback given to the AI (what to do or avoid, and why)

Return a JSON object with key "memories" containing a list of objects, each with:
  "name":        short slug, e.g. "user_prefers_concise_responses"
  "type":        "user" | "feedback" | "project"
  "description": one-line description
  "content":     memory body
  "confidence":  float 0.0–1.0 (use ~0.8 for inferred, ~0.9 for explicit)

Return {"memories": []} if nothing new or worth saving.
Do NOT extract code patterns, git history, or ephemeral state.
Keep to AT MOST 3 memories. Quality over quantity."""


@dataclass
class ConsolidatedMemory:
    name: str
    type: str
    description: str
    content: str
    confidence: float
    created: str
    source: str = "consolidator"


def consolidate_session(
    messages: List[Dict[str, Any]],
    *,
    llm_call: Optional[Callable[[str, str], str]] = None,
    save: Optional[Callable[[ConsolidatedMemory], bool]] = None,
    conflict_check: Optional[Callable[[ConsolidatedMemory], Optional[float]]] = None,
    max_turns: int = 40,
) -> List[str]:
    """Run consolidation over a session's messages.

    Args:
        messages: conversation list; each dict has {"role", "content"}.
        llm_call: (system, user) -> JSON text; if None, consolidator is a no-op.
        save: persist callback; if None we just return the dry-run list.
        conflict_check: returns existing_confidence (float) or None.
        max_turns: how many recent turns to send to the LLM.

    Returns:
        names of memories actually saved (or would be saved, on dry-run).
    """
    if len(messages) < MIN_MESSAGES_TO_CONSOLIDATE:
        logger.info("consolidator: skipping (only %d messages)", len(messages))
        return []

    transcript = _format_transcript(messages[-max_turns:])
    if not transcript:
        return []

    if llm_call is None:
        logger.info("consolidator: no llm_call provided, running in dry-mode")
        return []

    try:
        raw = llm_call(SYSTEM_PROMPT, f"Conversation:\n\n{transcript}")
        parsed = json.loads(raw) if isinstance(raw, str) else raw
    except Exception as exc:
        logger.warning("consolidator: LLM parse failed: %s", exc)
        return []

    memories_data = parsed.get("memories") if isinstance(parsed, dict) else None
    if not isinstance(memories_data, list):
        return []

    saved_names: List[str] = []
    today = datetime.now().strftime("%Y-%m-%d")
    for raw_mem in memories_data[:MAX_MEMORIES_PER_SESSION]:
        if not isinstance(raw_mem, dict):
            continue
        required = ("name", "description", "content")
        if not all(k in raw_mem for k in required):
            continue
        mem = ConsolidatedMemory(
            name=str(raw_mem["name"]),
            description=str(raw_mem["description"]),
            type=str(raw_mem.get("type", "user")),
            content=str(raw_mem["content"]),
            confidence=float(raw_mem.get("confidence", DEFAULT_CONFIDENCE)),
            created=today,
        )
        if conflict_check is not None:
            existing = conflict_check(mem)
            if existing is not None and existing >= mem.confidence:
                logger.info("consolidator: skipping %s — existing has %.2f >= %.2f",
                            mem.name, existing, mem.confidence)
                continue
        if save is None or save(mem):
            saved_names.append(mem.name)

    return saved_names


def _format_transcript(messages: List[Dict[str, Any]]) -> str:
    parts: List[str] = []
    for m in messages:
        role = m.get("role", "")
        content = m.get("content", "")
        if isinstance(content, str) and content.strip():
            prefix = "User" if role == "user" else "Assistant"
            snippet = content[:600].replace("\n", " ")
            parts.append(f"{prefix}: {snippet}")
    return "\n".join(parts)

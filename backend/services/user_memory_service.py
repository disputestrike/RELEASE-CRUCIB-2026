"""
user_memory_service.py — Phase 6: User memory & context persistence.

Stores per-user profile (preferred stack, company name, brand color,
build history) in a flat JSON file under the workspace data dir.
Injected into every build prompt so the LLM already knows who it's
building for without the user having to repeat themselves.

Storage: {DATA_DIR}/user_profiles/{user_id}.json
DATA_DIR defaults to /tmp/crucibai_data (overridden by CRUCIBAI_DATA_DIR).

Fields stored:
  user_id           str
  display_name      str
  company_name      str
  brand_color       str    (hex, e.g. "#6366f1")
  preferred_stack   str    ("react_fastapi" | "react_only" | "next_js" | ...)
  font_preference   str    ("Inter" | "system" | ...)
  build_history     list   [{goal, build_type, timestamp, job_id}]   (last 20)
  custom_notes      str    (free-text the user types about their project)
  updated_at        str    ISO timestamp
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DATA_DIR = Path(os.environ.get("CRUCIBAI_DATA_DIR", "/tmp/crucibai_data"))
_PROFILES_DIR = _DATA_DIR / "user_profiles"
_MAX_HISTORY = 20


def _profile_path(user_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in str(user_id))[:64]
    _PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    return _PROFILES_DIR / f"{safe}.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Read / Write ──────────────────────────────────────────────────────────────

def load_user_memory(user_id: str) -> Dict[str, Any]:
    """Load user memory. Returns empty dict if none saved yet."""
    if not user_id:
        return {}
    p = _profile_path(user_id)
    if not p.exists():
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("user_memory: failed to load %s: %s", p, e)
        return {}


def save_user_memory(user_id: str, profile: Dict[str, Any]) -> bool:
    """Persist user memory. Returns True on success."""
    if not user_id:
        return False
    try:
        p = _profile_path(user_id)
        profile["user_id"] = user_id
        profile["updated_at"] = _now_iso()
        with open(p, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.warning("user_memory: failed to save for %s: %s", user_id, e)
        return False


def patch_user_memory(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Merge updates into existing profile and save. Returns merged profile."""
    profile = load_user_memory(user_id)
    # Never overwrite build_history via patch — use record_build_in_memory
    updates.pop("build_history", None)
    updates.pop("user_id", None)
    profile.update(updates)
    save_user_memory(user_id, profile)
    return profile


def record_build_in_memory(
    user_id: str,
    *,
    goal: str,
    build_type: str = "",
    job_id: str = "",
) -> None:
    """Append a completed build to the user's history (capped at MAX_HISTORY)."""
    if not user_id:
        return
    profile = load_user_memory(user_id)
    history: List[Dict[str, Any]] = profile.get("build_history", [])
    history.append({
        "goal": goal[:200],
        "build_type": build_type,
        "job_id": job_id,
        "timestamp": _now_iso(),
    })
    profile["build_history"] = history[-_MAX_HISTORY:]
    # Auto-detect preferred stack from history
    _auto_update_preferred_stack(profile)
    save_user_memory(user_id, profile)


def _auto_update_preferred_stack(profile: Dict[str, Any]) -> None:
    """Infer preferred stack from build history if not explicitly set."""
    if profile.get("preferred_stack"):
        return  # user has set this explicitly — don't override
    history = profile.get("build_history", [])
    if not history:
        return
    stack_votes: Dict[str, int] = {}
    for entry in history:
        bt = (entry.get("build_type") or "").lower()
        goal = (entry.get("goal") or "").lower()
        if "fastapi" in goal or "python" in goal or bt in ("fullstack", "backend"):
            stack_votes["react_fastapi"] = stack_votes.get("react_fastapi", 0) + 1
        elif "next" in goal or "nextjs" in goal or bt == "next_js":
            stack_votes["next_js"] = stack_votes.get("next_js", 0) + 1
        else:
            stack_votes["react_only"] = stack_votes.get("react_only", 0) + 1
    if stack_votes:
        best = max(stack_votes, key=lambda k: stack_votes[k])
        profile["inferred_stack"] = best


# ── Context injection ─────────────────────────────────────────────────────────

def build_memory_context_block(user_id: str) -> str:
    """
    Return a short text block injected into build prompts.
    Empty string if no meaningful profile data exists.
    """
    if not user_id:
        return ""
    profile = load_user_memory(user_id)
    if not profile:
        return ""

    parts: List[str] = []

    company = profile.get("company_name", "").strip()
    if company:
        parts.append(f"Company: {company}")

    name = profile.get("display_name", "").strip()
    if name:
        parts.append(f"User: {name}")

    stack = profile.get("preferred_stack") or profile.get("inferred_stack", "")
    stack_labels = {
        "react_fastapi": "React + FastAPI (Python)",
        "react_only":    "React (frontend only)",
        "next_js":       "Next.js",
        "vue_fastapi":   "Vue + FastAPI",
    }
    if stack:
        parts.append(f"Preferred stack: {stack_labels.get(stack, stack)}")

    brand_color = profile.get("brand_color", "").strip()
    if brand_color:
        parts.append(f"Brand color: {brand_color}")

    font = profile.get("font_preference", "").strip()
    if font and font.lower() != "inter":
        parts.append(f"Font preference: {font}")

    notes = profile.get("custom_notes", "").strip()
    if notes:
        parts.append(f"Project notes: {notes}")

    history = profile.get("build_history", [])
    if len(history) >= 2:
        recent = [h.get("goal", "")[:80] for h in history[-3:] if h.get("goal")]
        if recent:
            parts.append(f"Recent builds: {'; '.join(recent)}")

    if not parts:
        return ""

    lines = "\n".join(f"  - {p}" for p in parts)
    return f"[User context — incorporate naturally if relevant]\n{lines}\n"


def get_profile_summary(user_id: str) -> Dict[str, Any]:
    """Return the profile dict suitable for the API (no internal fields)."""
    profile = load_user_memory(user_id)
    return {
        "company_name":     profile.get("company_name", ""),
        "display_name":     profile.get("display_name", ""),
        "brand_color":      profile.get("brand_color", ""),
        "preferred_stack":  profile.get("preferred_stack", ""),
        "inferred_stack":   profile.get("inferred_stack", ""),
        "font_preference":  profile.get("font_preference", "Inter"),
        "custom_notes":     profile.get("custom_notes", ""),
        "build_count":      len(profile.get("build_history", [])),
        "recent_builds":    profile.get("build_history", [])[-5:],
        "updated_at":       profile.get("updated_at", ""),
    }

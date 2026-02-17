"""
Project state: structured store per project (plan, requirements, stack, artifacts, reports).
All state writers and tool runners read/write this so the pipeline is real and verifiable.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path(__file__).parent / "workspace"

# Schema: state is a flat dict; we use keys like plan, requirements, stack, design_spec, etc.
DEFAULT_STATE: Dict[str, Any] = {
    "plan": [],
    "requirements": {},
    "stack": {},
    "decisions": {},
    "design_spec": {},
    "brand_spec": {},
    "memory_summary": "",
    "artifacts": [],
    "test_results": {},
    "deploy_result": {},
    "security_report": "",
    "ux_report": "",
    "performance_report": "",
    "tool_log": [],
    "images": {},
    "videos": {},
    "vibe_spec": {},
    "voice_requirements": {},
    "aesthetic_report": {},
    "team_preferences": {},
    "feedback_log": [],
    "mood": {},
    "accessibility_vibe": {},
    "performance_vibe": {},
    "creative_ideas": {},
    "design_iterations": [],
    "code_review_report": "",
    "bundle_report": "",
    "lighthouse_report": "",
    "dependency_audit": "",
    "scrape_urls": [],
}


def _state_path(project_id: str) -> Path:
    safe_id = project_id.replace("/", "_").replace("\\", "_")
    root = WORKSPACE_ROOT / safe_id
    root.mkdir(parents=True, exist_ok=True)
    return root / "state.json"


def load_state(project_id: str) -> Dict[str, Any]:
    """Load project state; return default if missing."""
    path = _state_path(project_id)
    if not path.exists():
        return dict(DEFAULT_STATE)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        # Merge with default so new keys exist
        out = dict(DEFAULT_STATE)
        out.update(data)
        return out
    except Exception as e:
        logger.warning("load_state %s: %s", project_id, e)
        return dict(DEFAULT_STATE)


def save_state(project_id: str, state: Dict[str, Any]) -> None:
    """Persist project state."""
    path = _state_path(project_id)
    try:
        path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("save_state %s: %s", project_id, e)


def update_state(project_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Load state, apply updates, save, return new state."""
    state = load_state(project_id)
    state.update(updates)
    save_state(project_id, state)
    return state

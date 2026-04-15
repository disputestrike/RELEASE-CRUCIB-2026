"""
projects.py - Real project route implementations extracted from server.py.
All 34 @projects_router routes plus supporting helpers and orchestration.
"""

import asyncio
import base64
import io
import json
import logging
import mimetypes
import os
import re
import subprocess
import sys
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import jwt
from code_quality import score_generated_code
from deps import (
    JWT_ALGORITHM,
    JWT_SECRET,
    get_audit_logger,
    get_current_user,
    get_current_user_sse,
    get_db,
    get_optional_user,
    require_permission,
)
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pricing_plans import CREDITS_PER_TOKEN, _speed_from_plan
from project_state import WORKSPACE_ROOT, load_state
from pydantic import BaseModel, Field, model_validator
from services.llm_service import (
    _call_llm_with_fallback,
    _effective_api_keys,
    _get_model_chain,
    get_authenticated_or_api_user,
    get_workspace_api_keys,
)

from services.project_preview_service import (
    get_preview_token_service,
    serve_preview_service,
    get_project_dependency_audit_service,
)

try:
    from utils.rbac import Permission, has_permission
except ImportError:
    has_permission = lambda u, p: True
    Permission = None

try:
    from agents.legal_compliance import check_request as legal_check_request
except ImportError:
    legal_check_request = None

from agent_dag import (
    AGENT_DAG,
    build_context_from_previous_agents,
    get_execution_phases,
    get_system_prompt_for_agent,
)
from agent_real_behavior import run_agent_real_behavior
from agent_recursive_learning import AgentMemory, ExecutionStatus
from agent_resilience import AgentError, generate_fallback, get_criticality, get_timeout
from agents.code_repair_agent import CodeRepairAgent, coerce_text_output
from content_policy import screen_user_content
from critic_agent import CriticAgent, TruthModule
from dev_stub_llm import (
    REAL_AGENT_NO_LLM_KEYS_DETAIL,
    chat_llm_available,
    is_real_agent_only,
)
from dev_stub_llm import plan_and_suggestions as _stub_plan_and_suggestions
from dev_stub_llm import (
    stub_build_enabled,
)
from pgvector_memory import pgvector_memory as _pgvector_memory
from real_agent_runner import (
    REAL_AGENT_NAMES,
    persist_agent_output,
    run_real_agent,
    run_real_post_step,
)
from vector_memory import vector_memory as _vector_memory

try:
    from agents.image_generator import generate_images_for_app, parse_image_prompts
    from agents.video_generator import generate_videos_for_app, parse_video_queries
except ImportError:
    generate_images_for_app = parse_image_prompts = None
    generate_videos_for_app = parse_video_queries = None

try:
    from metrics_system import metrics as _metrics
except ImportError:
    _metrics = None

projects_router = APIRouter(prefix="/api", tags=["projects"])
logger = logging.getLogger(__name__)

_build_events: Dict[str, List[Dict[str, Any]]] = {}
_BUILD_EVENTS_MAX = 500
_critic_agent = CriticAgent()
_truth_module = TruthModule()
_agent_memory_instance = None


async def _init_agent_learning():
    global _agent_memory_instance
    if _agent_memory_instance is None:
        db = get_db()
        if db is not None:
            _agent_memory_instance = AgentMemory(db)
    return _agent_memory_instance


MIN_CREDITS_FOR_LLM = 5
FREE_TIER_MAX_PROJECTS = 3
MAX_EXPORTS_LIST = 200
SWARM_TOKEN_MULTIPLIER = 1.5
MAX_PROMPT_LENGTH = 50000
MAX_PROJECT_DESCRIPTION_LENGTH = 10000
MAX_PROJECT_REQUIREMENTS_JSON_LENGTH = 100000

DEPLOY_README = """# Deploy this project
## Vercel: https://vercel.com/new  ## Netlify: https://app.netlify.com/drop
## Railway: https://railway.app/new  Generated with CrucibAI."""

TEMPLATES_GALLERY = [
    {
        "id": "dashboard",
        "name": "Dashboard",
        "description": "Sidebar + stats cards + chart placeholder",
        "prompt": "Create a dashboard with a sidebar, stat cards, and a chart area. React and Tailwind.",
        "tags": ["saas", "analytics"],
        "difficulty": "starter",
    },
    {
        "id": "blog",
        "name": "Blog",
        "description": "Blog layout with posts list and post detail",
        "prompt": "Build a blog with a list of posts and a post detail view. React and Tailwind.",
        "tags": ["cms", "publishing"],
        "difficulty": "starter",
    },
    {
        "id": "saas-shell",
        "name": "SaaS shell",
        "description": "Auth shell with nav and settings",
        "prompt": "Create a SaaS app shell with top nav, user menu, and settings page. React and Tailwind.",
        "tags": ["saas", "auth"],
        "difficulty": "intermediate",
    },
]

BUILD_PHASES = [
    {
        "id": "planning",
        "name": "Planning",
        "agents": ["Planner", "Requirements Clarifier", "Stack Selector"],
    },
    {
        "id": "generating",
        "name": "Generating",
        "agents": [
            "Frontend Generation",
            "Backend Generation",
            "Database Agent",
            "API Integration",
            "Test Generation",
            "Image Generation",
        ],
    },
    {
        "id": "validating",
        "name": "Validating",
        "agents": [
            "Security Checker",
            "Test Executor",
            "UX Auditor",
            "Performance Analyzer",
        ],
    },
    {
        "id": "deployment",
        "name": "Deployment",
        "agents": ["Deployment Agent", "Error Recovery", "Memory Agent"],
    },
    {
        "id": "export_automation",
        "name": "Export & automation",
        "agents": [
            "PDF Export",
            "Excel Export",
            "Markdown Export",
            "Scraping Agent",
            "Automation Agent",
        ],
    },
]

CRUCIBAI_TOP_COMMENT = "// Built with CrucibAI · https://crucibai.com\n"
_BRANDING_BASE_URL = os.environ.get("CRUCIBAI_BRANDING_URL") or (
    os.environ.get("BACKEND_PUBLIC_URL", "http://localhost:8000").rstrip("/")
    + "/branding"
)
CRUCIBAI_FREE_FOOTER_JSX = f'<iframe src="{_BRANDING_BASE_URL}" title="Built with CrucibAI" style={{{{ border: "none", height: "28px", width: "100%", display: "block" }}}} />'
CRUCIBAI_PAID_FOOTER_JSX = '<div className="mt-8 py-3 text-center text-sm text-gray-500 border-t border-gray-200/50"><a href="https://crucibai.com" target="_blank" rel="noopener noreferrer" className="text-gray-500 hover:text-gray-700">Built with CrucibAI</a></div>'


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    description: str = Field("", max_length=MAX_PROJECT_DESCRIPTION_LENGTH)
    project_type: str = Field(..., max_length=100)
    requirements: Dict[str, Any] = Field(default_factory=dict)
    estimated_tokens: Optional[int] = None
    quick_build: Optional[bool] = False

    @model_validator(mode="after")
    def check_requirements_size(self):
        try:
            if (
                len(json.dumps(self.requirements or {}))
                > MAX_PROJECT_REQUIREMENTS_JSON_LENGTH
            ):
                raise ValueError("requirements too large")
        except TypeError:
            pass
        return self


class BuildPlanRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=MAX_PROMPT_LENGTH)
    swarm: Optional[bool] = False
    build_kind: Optional[str] = None


class ProjectImportBody(BaseModel):
    name: Optional[str] = None
    source: str
    files: Optional[List[Dict[str, Any]]] = None
    zip_base64: Optional[str] = None
    git_url: Optional[str] = None


class DeployOneClickBody(BaseModel):
    token: Optional[str] = None


class ProjectPublishSettingsBody(BaseModel):
    custom_domain: Optional[str] = None
    railway_project_url: Optional[str] = None


class ReferenceBuildBody(BaseModel):
    url: Optional[str] = None
    prompt: str


def _user_credits(user: Optional[dict]) -> int:
    if not user:
        return 0
    if user.get("credit_balance") is not None:
        return int(user["credit_balance"])
    return int((user.get("token_balance") or 0) // CREDITS_PER_TOKEN)


def _tokens_to_credits(tokens: int) -> int:
    return max(1, (tokens + CREDITS_PER_TOKEN - 1) // CREDITS_PER_TOKEN)


async def _ensure_credit_balance(user_id: str) -> None:
    db = get_db()
    doc = await db.users.find_one(
        {"id": user_id}, {"credit_balance": 1, "token_balance": 1}
    )
    if not doc or doc.get("credit_balance") is not None:
        return
    cred = (doc.get("token_balance") or 0) // CREDITS_PER_TOKEN
    await db.users.update_one({"id": user_id}, {"$set": {"credit_balance": cred}})


def _quality_verdict(score: float) -> str:
    if score >= 90:
        return "excellent"
    if score >= 75:
        return "good"
    if score >= 60:
        return "acceptable"
    return "needs-improvement"


def _quality_badge(score: float) -> str:
    if score >= 90:
        return "\U0001f3c6"
    if score >= 75:
        return "\u2705"
    if score >= 60:
        return "\u26a0\ufe0f"
    return "\u274c"


def emit_build_event(project_id: str, event_type: str, **kwargs: Any) -> None:
    if project_id not in _build_events:
        _build_events[project_id] = []
    lst = _build_events[project_id]
    ev = {
        "id": len(lst),
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        **kwargs,
    }
    lst.append(ev)
    if len(lst) > _BUILD_EVENTS_MAX:
        _build_events[project_id] = lst[-_BUILD_EVENTS_MAX:]
        for i, e in enumerate(_build_events[project_id]):
            e["id"] = i
    _db = get_db()
    if _db is not None:

        async def _persist():
            try:
                await _db.projects.update_one(
                    {"id": project_id},
                    {
                        "$set": {
                            "build_events": lst[-200:],
                            "build_events_updated_at": datetime.now(
                                timezone.utc
                            ).isoformat(),
                        }
                    },
                )
            except Exception:
                pass

        try:
            asyncio.get_running_loop().create_task(_persist())
        except RuntimeError:
            pass


def _project_workspace_path(project_id: str) -> Path:
    safe_id = project_id.replace("/", "_").replace("\\", "_")
    return WORKSPACE_ROOT / safe_id


def _safe_import_path(path: str) -> str:
    p = (path or "").strip().replace("\\", "/").lstrip("/")
    if ".." in p or p.startswith("/"):
        return ""
    return p[:500]


async def _user_can_access_project_workspace(
    user_id: Optional[str], project_id: str
) -> bool:
    db = get_db()
    if not project_id or not user_id:
        return False
    project = await db.projects.find_one(
        {"id": project_id, "user_id": user_id}, {"id": 1}
    )
    if project:
        return True
    try:
        from db_pg import get_pg_pool

        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT 1 FROM jobs WHERE project_id = $1 AND user_id = $2 LIMIT 1",
                project_id,
                user_id,
            )
        return row is not None
    except Exception:
        return False


def _list_all_workspace_rel_paths(root: Path) -> List[str]:
    files: List[str] = []
    if not root.is_dir():
        return files
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        sp = str(p)
        if "node_modules" in sp or "__pycache__" in sp:
            continue
        try:
            files.append(p.relative_to(root).as_posix())
        except ValueError:
            continue
    files.sort()
    return files


def _paginated_workspace_files_payload(
    paths: List[str], offset: int, limit: int
) -> Dict[str, Any]:
    total = len(paths)
    off = max(0, int(offset))
    lim = max(1, min(int(limit), 1000))
    slice_paths = paths[off : off + lim]
    has_more = off + lim < total
    return {
        "files": slice_paths,
        "total_count": total,
        "offset": off,
        "limit": lim,
        "has_more": has_more,
        "next_offset": off + lim if has_more else None,
    }


def _workspace_file_disk_path(root: Path, path: str) -> Path:
    rel = (path or "").strip().replace("\\", "/").lstrip("/")
    if ".." in rel or not rel:
        raise HTTPException(status_code=400, detail="Invalid path")
    full = (root / rel).resolve()
    try:
        full.relative_to(root.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Path outside workspace")
    if not full.exists() or not full.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return full


def _create_preview_token(project_id: str, user_id: str) -> str:
    payload = {
        "project_id": project_id,
        "user_id": user_id,
        "purpose": "preview",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=2),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _verify_preview_token(token: str) -> tuple:
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    if payload.get("purpose") != "preview":
        raise jwt.InvalidTokenError("Invalid purpose")
    return payload["project_id"], payload["user_id"]


async def _build_project_deploy_zip(project_id: str, user_id: str):
    db = get_db()
    project = await db.projects.find_one({"id": project_id, "user_id": user_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    deploy_files = project.get("deploy_files") or {}
    if not deploy_files:
        raise HTTPException(
            status_code=404, detail="No deploy snapshot for this project."
        )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README-DEPLOY.md", DEPLOY_README)
        for name, content in deploy_files.items():
            safe_name = (name or "").lstrip("/")
            if safe_name:
                zf.writestr(
                    safe_name, content if isinstance(content, str) else str(content)
                )
    buf.seek(0)
    return buf


async def _get_project_deploy_files(project_id: str, user_id: str) -> tuple:
    db = get_db()
    project = await db.projects.find_one({"id": project_id, "user_id": user_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    deploy_files = project.get("deploy_files") or {}
    if not deploy_files:
        raise HTTPException(status_code=404, detail="No deploy snapshot.")
    name = (project.get("name") or "crucibai-app").replace(" ", "-")[:50]
    return deploy_files, name


# ── Orchestration helpers (from server.py) ──


def _token_budget_for_orchestration_agent(agent_name: str, system_msg: str) -> int:
    explicit = {
        "Frontend Generation": 150000,
        "Backend Generation": 120000,
        "Database Agent": 80000,
        "Test Generation": 100000,
        "Deployment Agent": 60000,
    }
    if agent_name in explicit:
        return explicit[agent_name]
    if agent_name.endswith("Tool Agent"):
        return 70000
    prompt_len = len(system_msg or "")
    return max(25000, min(110000, 22000 + prompt_len * 18))


_ORCHESTRATION_AGENTS = [
    (
        agent_name,
        _token_budget_for_orchestration_agent(
            agent_name, get_system_prompt_for_agent(agent_name)
        ),
        get_system_prompt_for_agent(agent_name),
    )
    for phase in get_execution_phases(AGENT_DAG)
    for agent_name in phase
]


async def _run_single_agent_with_context(
    project_id: str,
    user_id: str,
    agent_name: str,
    project_prompt: str,
    previous_outputs: Dict[str, Dict[str, Any]],
    effective: Dict[str, Optional[str]],
    model_chain: list,
    build_kind: Optional[str] = None,
    user_tier: str = "free",
    speed_selector: str = "lite",
    available_credits: int = 0,
    retry_error: Optional[str] = None,
) -> Dict[str, Any]:
    """Run one agent with context from previous agents. Returns {output, tokens_used, status} or raises."""
    if agent_name not in AGENT_DAG:
        return {
            "output": "",
            "tokens_used": 0,
            "status": "skipped",
            "reason": "Unknown agent",
        }
    # Real tool agents: execute real tools (File, Browser, API, Database, Deployment) from DAG context
    if agent_name in REAL_AGENT_NAMES:
        real_result = await run_real_agent(
            agent_name, project_id, user_id, previous_outputs, project_prompt
        )
        if real_result is not None:
            persist_agent_output(project_id, agent_name, real_result)
            try:
                run_agent_real_behavior(
                    agent_name, project_id, real_result, previous_outputs
                )
            except Exception as e:
                logger.warning("run_agent_real_behavior %s: %s", agent_name, e)
            return real_result
    system_msg = get_system_prompt_for_agent(agent_name)
    if (
        agent_name == "Frontend Generation"
        and (build_kind or "").strip().lower() == "mobile"
    ):
        system_msg = "You are Frontend Generation for a mobile app. Output only Expo/React Native code (App.js, use React Native components from 'react-native', no DOM or web-only APIs). No markdown."
    enhanced_message = build_context_from_previous_agents(
        agent_name, previous_outputs, project_prompt
    )
    if retry_error:
        enhanced_message += (
            "\n\n[Previous attempt failed]\n"
            f"{retry_error[:1200]}\n"
            "Return corrected code/config only. Do not repeat the failure."
        )
    response, _ = await _call_llm_with_fallback(
        message=enhanced_message,
        system_message=system_msg,
        session_id=f"orch_{project_id}",
        model_chain=model_chain,
        api_keys=effective,
        user_id=user_id,
        user_tier=user_tier,
        speed_selector=speed_selector,
        available_credits=available_credits,
        agent_name=agent_name,
    )
    tokens_used = max(
        100, min(200000, (len(enhanced_message) + len(response or "")) * 2)
    )
    out = (response or "").strip()
    input_data = _agent_cache_input(agent_name, project_prompt, previous_outputs)
    result: Dict[str, Any] = {
        "output": out,
        "tokens_used": tokens_used,
        "status": "completed",
        "result": out,
        "code": out,
    }

    # Image Generation: LLM returns JSON prompts -> Together.ai generates images
    if (
        agent_name == "Image Generation"
        and generate_images_for_app
        and parse_image_prompts
    ):
        try:
            prompts_dict = parse_image_prompts(out)
            design_desc = (
                enhanced_message[:1000] if enhanced_message else project_prompt[:500]
            )
            images = await generate_images_for_app(
                design_desc, prompts_dict if prompts_dict else None
            )
            out = json.dumps(images) if images else out
            result = {
                "output": out,
                "tokens_used": tokens_used,
                "status": "completed",
                "result": out,
                "code": out,
                "images": images,
            }
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            result = {
                "output": out,
                "tokens_used": tokens_used,
                "status": "completed",
                "result": out,
                "code": out,
            }
    elif (
        agent_name == "Video Generation"
        and generate_videos_for_app
        and parse_video_queries
    ):
        try:
            queries_dict = parse_video_queries(out)
            design_desc = (
                enhanced_message[:1000] if enhanced_message else project_prompt[:500]
            )
            videos = await generate_videos_for_app(
                design_desc, queries_dict if queries_dict else None
            )
            out = json.dumps(videos) if videos else out
            result = {
                "output": out,
                "tokens_used": tokens_used,
                "status": "completed",
                "result": out,
                "code": out,
                "videos": videos,
            }
        except Exception as e:
            logger.warning("Video generation agent failed: %s", e)

    result = await _repair_generated_agent_output(
        agent_name=agent_name,
        result=result,
        model_chain=model_chain,
        effective=effective,
        user_id=user_id,
        user_tier=user_tier,
        speed_selector=speed_selector,
        available_credits=available_credits,
        project_id=project_id,
    )

    result = await run_real_post_step(agent_name, project_id, previous_outputs, result)
    persist_agent_output(project_id, agent_name, result)
    try:
        run_agent_real_behavior(agent_name, project_id, result, previous_outputs)
    except Exception as e:
        logger.warning("run_agent_real_behavior %s: %s", agent_name, e)

    # --- METRICS: Track agent execution ---
    try:
        safe_output = coerce_text_output(
            result.get("output") or result.get("result") or ""
        )
        _metrics.agent_executions_total.labels(
            agent=agent_name,
            status="success" if safe_output and len(safe_output) > 50 else "partial",
        ).inc()
        _metrics.active_agents.dec()
    except Exception:
        pass

    try:
        memory = await _init_agent_learning()
        if memory:
            safe_output = coerce_text_output(
                result.get("output") or result.get("result") or ""
            )
            await memory.record_execution(
                agent_name=agent_name,
                input_data={"prompt": input_data[:500], "project_id": project_id},
                output={"result": safe_output[:500], "tokens": tokens_used},
                status=(
                    ExecutionStatus.SUCCESS
                    if safe_output and len(safe_output) > 50
                    else ExecutionStatus.PARTIAL
                ),
                duration_ms=0,
                metadata={"build_kind": build_kind or "web"},
            )
    except Exception as e:
        logger.debug("Agent learning record failed (non-fatal): %s", e)

    try:
        if _vector_memory.is_available():
            await _vector_memory.store_agent_output(
                project_id=project_id,
                agent_name=agent_name,
                output=coerce_text_output(
                    result.get("output") or result.get("result") or "", limit=2000
                ),
                tokens_used=tokens_used,
            )
    except Exception as e:
        logger.debug("Vector memory store failed (non-fatal): %s", e)

    try:
        if (
            _pgvector_memory
            and getattr(_pgvector_memory, "is_available", lambda: False)()
        ):
            await _pgvector_memory.store_agent_output(
                project_id=project_id,
                agent_name=agent_name,
                output=coerce_text_output(
                    result.get("output") or result.get("result") or "", limit=2000
                ),
                tokens_used=tokens_used,
            )
    except Exception as e:
        logger.debug("PGVector memory store failed (non-fatal): %s", e)

    return result


async def _repair_generated_agent_output(
    *,
    agent_name: str,
    result: Dict[str, Any],
    model_chain: list,
    effective: Dict[str, Optional[str]],
    user_id: str,
    user_tier: str,
    speed_selector: str,
    available_credits: int,
    project_id: str,
) -> Dict[str, Any]:
    raw_output = (
        result.get("output") or result.get("result") or result.get("code") or ""
    )
    if not CodeRepairAgent.requires_validation(agent_name, raw_output):
        safe_text = coerce_text_output(raw_output)
        result["output"] = safe_text
        result["result"] = safe_text
        result["code"] = safe_text
        return result

    async def _llm_repair_callback(
        name: str, language: str, broken: str, error: str
    ) -> str:
        repair_prompt = (
            f"The previous output for agent '{name}' is invalid {language}.\n"
            f"Error: {error}\n\n"
            "Return ONLY corrected code/config. Do not explain. Do not wrap in markdown.\n\n"
            f"{broken[:12000]}"
        )
        repaired, _ = await _call_llm_with_fallback(
            message=repair_prompt,
            system_message=(
                "You are a precise code repair system. Make the smallest fix that produces valid syntax "
                "and preserves intent."
            ),
            session_id=f"repair_{project_id}_{name.lower().replace(' ', '_')}",
            model_chain=model_chain,
            api_keys=effective,
            user_id=user_id,
            user_tier=user_tier,
            speed_selector=speed_selector,
            available_credits=available_credits,
            agent_name=name,
        )
        return repaired or ""

    repaired = await CodeRepairAgent.repair_output(
        agent_name=agent_name,
        output=raw_output,
        error_message="agent_output_validation_failed",
        llm_repair=_llm_repair_callback,
    )
    if not repaired.get("valid"):
        raise AgentError(
            agent_name, f"output_validation_failed: {repaired.get('error')}", "high"
        )

    safe_text = repaired.get("output") or ""
    result["output"] = safe_text
    result["result"] = safe_text
    result["code"] = safe_text
    if repaired.get("repaired"):
        result["repair_metadata"] = {
            "language": repaired.get("language"),
            "strategy": repaired.get("strategy"),
            "status": "repaired",
        }
        logger.warning(
            "agent %s output repaired via %s",
            agent_name,
            repaired.get("strategy") or "unknown_strategy",
        )
    return result


def _agent_cache_input(
    agent_name: str, project_prompt: str, previous_outputs: Dict[str, Dict[str, Any]]
) -> str:
    """Build stable input string for agent cache key (prompt + dependent outputs)."""
    parts = [project_prompt]
    deps = list(AGENT_DAG.get(agent_name, {}).get("depends_on", []))
    for dep in sorted(deps):
        if dep in previous_outputs:
            out = coerce_text_output(
                previous_outputs[dep].get("output")
                or previous_outputs[dep].get("result")
                or "",
                limit=800,
            )
            parts.append(f"{dep}:{out}")
    return "\n".join(parts)


async def _run_single_agent_with_retry(
    project_id: str,
    user_id: str,
    agent_name: str,
    project_prompt: str,
    previous_outputs: Dict[str, Dict[str, Any]],
    effective: Dict[str, Optional[str]],
    model_chain: list,
    max_retries: int = 3,
    build_kind: Optional[str] = None,
    user_tier: str = "free",
    speed_selector: str = "lite",
    available_credits: int = 0,
) -> Dict[str, Any]:
    db = get_db()
    from agent_cache import get as cache_get
    from agent_cache import set as cache_set

    input_data = _agent_cache_input(agent_name, project_prompt, previous_outputs)
    cached = await cache_get(db, agent_name, input_data)
    if (
        cached
        and isinstance(cached, dict)
        and (cached.get("output") or cached.get("result"))
    ):
        return cached
    last_err = None
    for attempt in range(max_retries):
        try:
            r = await _run_single_agent_with_context(
                project_id,
                user_id,
                agent_name,
                project_prompt,
                previous_outputs,
                effective,
                model_chain,
                build_kind=build_kind,
                user_tier=user_tier,
                speed_selector=speed_selector,
                available_credits=available_credits,
                retry_error=str(last_err) if last_err else None,
            )
            if not (r.get("output") or r.get("result")):
                raise AgentError(agent_name, "Empty output", "medium")
            await cache_set(db, agent_name, input_data, r)
            return r
        except Exception as e:
            last_err = e
            logger.warning(
                "agent retry %s attempt %s/%s failed: %s",
                agent_name,
                attempt + 1,
                max_retries,
                str(e)[:300],
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)
    crit = get_criticality(agent_name)
    if crit == "critical":
        completed_at = datetime.now(timezone.utc).isoformat()
        await db.projects.update_one(
            {"id": project_id},
            {"$set": {"status": "failed", "completed_at": completed_at}},
        )
        # Append to build_history for version history UI (item 13)
        proj = await db.projects.find_one({"id": project_id})
        if proj is not None:
            history = list(proj.get("build_history") or [])
            history.insert(
                0,
                {
                    "completed_at": completed_at,
                    "status": "failed",
                    "quality_score": None,
                    "tokens_used": 0,
                },
            )
            await db.projects.update_one(
                {"id": project_id}, {"$set": {"build_history": history[:50]}}
            )
        return {
            "output": "",
            "tokens_used": 0,
            "status": "failed",
            "reason": str(last_err),
            "recoverable": False,
        }
    if crit == "high":
        fallback = generate_fallback(agent_name)
        return {
            "output": fallback,
            "result": fallback,
            "tokens_used": 0,
            "status": "failed_with_fallback",
            "reason": str(last_err),
            "recoverable": True,
        }
    return {
        "output": "",
        "tokens_used": 0,
        "status": "skipped",
        "reason": str(last_err),
        "recoverable": True,
    }


def _inject_media_into_jsx(
    jsx: str, images: Dict[str, str], videos: Dict[str, str]
) -> str:
    """Inject image/video URLs into generated JSX. Replaces placeholders or prepends a media section."""
    if not jsx or (not images and not videos):
        return jsx
    # Replace placeholders if present
    out = jsx
    if images.get("hero"):
        out = out.replace("CRUCIBAI_HERO_IMG", images["hero"]).replace(
            "{{HERO_IMAGE}}", images["hero"]
        )
    if images.get("feature_1"):
        out = out.replace("CRUCIBAI_FEATURE_1_IMG", images["feature_1"]).replace(
            "{{FEATURE_1_IMAGE}}", images["feature_1"]
        )
    if images.get("feature_2"):
        out = out.replace("CRUCIBAI_FEATURE_2_IMG", images["feature_2"]).replace(
            "{{FEATURE_2_IMAGE}}", images["feature_2"]
        )
    if videos.get("hero"):
        out = out.replace("CRUCIBAI_HERO_VIDEO", videos["hero"]).replace(
            "{{HERO_VIDEO}}", videos["hero"]
        )
    if videos.get("feature"):
        out = out.replace("CRUCIBAI_FEATURE_VIDEO", videos["feature"]).replace(
            "{{FEATURE_VIDEO}}", videos["feature"]
        )
    # If no placeholders were used, prepend a media section after "return ("
    if out == jsx and ("CRUCIBAI_" not in jsx and "{{HERO" not in jsx):
        media_parts = []
        if videos.get("hero"):
            media_parts.append(
                f'<section className="relative w-full h-48 md:h-64 overflow-hidden rounded-lg"><video autoPlay muted loop playsInline className="absolute inset-0 w-full h-full object-cover" src="{videos["hero"]}" /></section>'
            )
        img_keys = ["hero", "feature_1", "feature_2"]
        img_urls = [images.get(k) for k in img_keys if images.get(k)]
        if img_urls:
            divs = "".join(
                f'<div><img src="{u}" alt="Media" className="w-full h-32 object-cover rounded-lg" /></div>'
                for u in img_urls
            )
            media_parts.append(
                f'<section className="grid grid-cols-1 md:grid-cols-3 gap-4 py-4">{divs}</section>'
            )
        if media_parts:
            block = "\n      ".join(media_parts)
            idx = out.find("return (")
            if idx != -1:
                insert = idx + len("return (")
                out = (
                    out[:insert]
                    + "\n      "
                    + block
                    + "\n      "
                    + out[insert:].lstrip()
                )
    return out


# CrucibAI attribution: comment at top + footer. Free = iframe (served from our server, not removable). Paid = static div (user may remove).
CRUCIBAI_TOP_COMMENT = "// Built with CrucibAI · https://crucibai.com\n"
# URL for free-tier iframe: badge content is on our server so free users have no way to remove it (only the iframe tag in source).
_BRANDING_BASE_URL = os.environ.get("CRUCIBAI_BRANDING_URL") or (
    os.environ.get("BACKEND_PUBLIC_URL", "http://localhost:8000").rstrip("/")
    + "/branding"
)
# Free: iframe loads badge from our server — permanent, not in their editable content.
CRUCIBAI_FREE_FOOTER_JSX = (
    f'<iframe src="{_BRANDING_BASE_URL}" title="Built with CrucibAI" '
    'style={{ border: "none", height: "28px", width: "100%", display: "block" }} />'
)
# Paid: static div so they can remove it in the editor if they want.
CRUCIBAI_PAID_FOOTER_JSX = (
    '<div className="mt-8 py-3 text-center text-sm text-gray-500 border-t border-gray-200/50">'
    '<a href="https://crucibai.com" target="_blank" rel="noopener noreferrer" className="text-gray-500 hover:text-gray-700">Built with CrucibAI</a>'
    "</div>"
)


def _inject_crucibai_branding(jsx: str, plan: str) -> str:
    """Add CrucibAI attribution. Free: iframe (content on our server — cannot be removed). Paid: static div (user may remove)."""
    if not jsx or not jsx.strip():
        return jsx
    out = jsx
    # 1) Top comment (watermark in code)
    if "crucibai.com" not in out.lower() and "Built with CrucibAI" not in out:
        if out.lstrip().startswith("//") or out.lstrip().startswith("/*"):
            first_newline = out.find("\n")
            if first_newline != -1:
                out = (
                    out[: first_newline + 1]
                    + CRUCIBAI_TOP_COMMENT
                    + out[first_newline + 1 :]
                )
            else:
                out = CRUCIBAI_TOP_COMMENT + out
        else:
            out = CRUCIBAI_TOP_COMMENT + out
    # 2) Footer: free = iframe (permanent); paid = static div (removable)
    is_free = (plan or "free").lower() == "free"
    already_has = (CRUCIBAI_PAID_FOOTER_JSX in out) or (is_free and "/branding" in out)
    if not already_has:
        footer_jsx = CRUCIBAI_FREE_FOOTER_JSX if is_free else CRUCIBAI_PAID_FOOTER_JSX
        idx = out.rfind(");")
        if idx != -1:
            before = out[:idx]
            last_div = before.rfind("</div>")
            if last_div != -1:
                out = (
                    out[:last_div]
                    + "\n      "
                    + footer_jsx
                    + "\n      "
                    + out[last_div:]
                )
    return out


def _infer_build_kind(prompt: str) -> str:
    """Infer build_kind from prompt so we build the right artifact: web, mobile, agent/automation, software, etc."""
    if not prompt:
        return "fullstack"
    p = prompt.lower()
    if any(
        x in p
        for x in (
            "mobile app",
            "react native",
            "flutter",
            "ios app",
            "android app",
            "pwa ",
            "app store",
            "play store",
            "apple store",
            "google play",
            "build me a mobile",
            "mobile application",
        )
    ):
        return "mobile"
    if any(
        x in p
        for x in (
            "build me an agent",
            "automation agent",
            "automation",
            "scheduled task",
            "cron",
            "webhook agent",
            "run_agent",
            "build agent",
        )
    ):
        return "ai_agent"
    if any(
        x in p
        for x in (
            "saas",
            "subscription",
            "multi-tenant",
            "billing",
            "stripe",
            "plans/tiers",
        )
    ):
        return "saas"
    if any(
        x in p
        for x in (
            "slack bot",
            "discord bot",
            "telegram bot",
            "chatbot",
            " webhook bot",
            "bot that",
        )
    ):
        return "bot"
    if any(
        x in p
        for x in ("ai agent", "llm agent", "agent with tools", "autonomous agent")
    ):
        return "ai_agent"
    if any(
        x in p
        for x in (
            "game",
            "2d game",
            "3d game",
            "browser game",
            "mobile game",
            "arcade",
            "player score",
            "level design",
        )
    ):
        return "game"
    if any(
        x in p
        for x in (
            "trading software",
            "trading app",
            "stock trading",
            "crypto trading",
            "forex",
            "order book",
            "positions",
            "p&l",
            "trade execution",
            "portfolio tracker",
        )
    ):
        return "trading"
    if any(
        x in p for x in ("landing page", "landing only", "one-page", "marketing page")
    ):
        return "landing"
    if any(x in p for x in ("website", "build me a website", "build me a web")):
        return "fullstack"
    if any(x in p for x in ("anything", "whatever", "no limit", "any idea", "any app")):
        return "any"
    return "fullstack"


async def run_orchestration_v2(project_id: str, user_id: str):
    """DAG-based orchestration: parallel phases, output chaining, retry, timeout, quality score."""
    # --- METRICS: Track build start ---
    db = get_db()
    try:
        _metrics.build_queue_depth.inc()
    except Exception:
        pass
    project = await db.projects.find_one({"id": project_id})
    if not project:
        return
    req = project.get("requirements") or {}
    prompt = (
        req.get("prompt")
        or req.get("description")
        or project.get("description")
        or "Build a web application"
    )
    if isinstance(prompt, dict):
        prompt = prompt.get("prompt") or str(prompt)
    build_kind = (req.get("build_kind") or "").strip().lower() or _infer_build_kind(
        prompt
    )
    if build_kind not in (
        "fullstack",
        "landing",
        "mobile",
        "saas",
        "bot",
        "ai_agent",
        "game",
        "trading",
        "any",
    ):
        build_kind = "fullstack"
    project_prompt_with_kind = f"[Build kind: {build_kind}]\n{prompt}"
    try:
        from autonomous_domain_agent import initialize_autonomous_domain_agent

        _domain_agent = await initialize_autonomous_domain_agent(db)
        _analysis = await _domain_agent.analyze_requirements(prompt)
        _d = _analysis.get("detected_domain") or "general"
        _best = _analysis.get("best_practices") or []
        _constraints = _analysis.get("applicable_constraints") or []
        _extra = f"\n[Domain: {_d}]"
        if _best:
            _extra += "\nBest practices: " + "; ".join(str(x) for x in _best[:5])
        if _constraints:
            _extra += "\nConstraints: " + str(_constraints[:3])
        project_prompt_with_kind = f"[Build kind: {build_kind}]{_extra}\n{prompt}"
    except Exception as _dom_err:
        logger.debug("Autonomous domain enrichment skipped: %s", _dom_err)
    user_keys = await get_workspace_api_keys({"id": user_id})
    effective = _effective_api_keys(user_keys)

    # Get user tier and derive speed from plan (no client speed_selector)
    user = await db.users.find_one({"id": user_id}, {"plan": 1, "credit_balance": 1})
    user_tier = user.get("plan", "free") if user else "free"
    available_credits = user.get("credit_balance", 0) if user else 0
    speed_selector = _speed_from_plan(user_tier)
    model_chain = _get_model_chain("auto", prompt, effective_keys=effective)
    if not effective.get("anthropic"):
        await db.projects.update_one(
            {"id": project_id},
            {
                "$set": {
                    "status": "failed",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )
        emit_build_event(
            project_id, "build_completed", status="failed", message="No API keys"
        )
        return
    await db.projects.update_one(
        {"id": project_id},
        {"$set": {"status": "running", "current_phase": 0, "progress_percent": 0}},
    )
    phases = get_execution_phases(AGENT_DAG)
    # Item 29: Quick build — run only first 2 phases for preview in ~2 min
    if project.get("quick_build"):
        phases = phases[:2]
        emit_build_event(
            project_id,
            "build_started",
            phases=len(phases),
            message="Quick build started (preview in ~2 min)",
        )
    else:
        emit_build_event(
            project_id,
            "build_started",
            phases=len(phases),
            message="Orchestration started",
        )
    results: Dict[str, Dict[str, Any]] = {}
    total_used = 0
    suggest_retry_phase: Optional[int] = None
    suggest_retry_reason: Optional[str] = None

    # ── GAP 2.5 FIX: Checkpoint recovery — skip completed agents on restart ──
    # Reads agent_status table — if agent already has output, skip and reuse
    try:
        checkpoint_cursor = db.agent_status.find({"project_id": project_id})
        checkpoint_count = 0
        async for row in checkpoint_cursor:
            doc = row.get("doc", {})
            agent_nm = row.get("agent_name") or doc.get("agent_name", "")
            status = doc.get("status", "")
            output = doc.get("output", "")
            if agent_nm and status in ("complete", "failed_with_fallback") and output:
                results[agent_nm] = {
                    "output": output,
                    "result": output,
                    "status": status,
                    "from_checkpoint": True,
                }
                checkpoint_count += 1
        if checkpoint_count > 0:
            logger.info(
                f"Checkpoint recovery: {checkpoint_count} agents reloaded, skipping re-execution"
            )
            emit_build_event(
                project_id,
                "checkpoint_restored",
                count=checkpoint_count,
                message=f"Resuming from checkpoint: {checkpoint_count} agents already complete",
            )
    except Exception as _cp_err:
        logger.debug(f"Checkpoint load skipped: {_cp_err}")

    for phase_idx, agent_names in enumerate(phases):
        emit_build_event(
            project_id,
            "phase_started",
            phase=phase_idx,
            agents=agent_names,
            message=f"Phase {phase_idx + 1}: {', '.join(agent_names)}",
        )
        progress_pct = int((phase_idx + 1) / len(phases) * 100)
        await db.projects.update_one(
            {"id": project_id},
            {
                "$set": {
                    "current_phase": phase_idx,
                    "current_agent": ",".join(agent_names),
                    "progress_percent": progress_pct,
                    "tokens_used": total_used,
                }
            },
        )
        for agent_name in agent_names:
            # Skip agents already completed in a previous run (checkpoint recovery)
            if agent_name in results and results[agent_name].get("from_checkpoint"):
                emit_build_event(
                    project_id,
                    "agent_skipped",
                    agent=agent_name,
                    message=f"{agent_name} skipped (checkpoint)",
                )
                continue
            emit_build_event(
                project_id,
                "agent_started",
                agent=agent_name,
                message=f"{agent_name} started",
            )
            await db.agent_status.update_one(
                {"project_id": project_id, "agent_name": agent_name},
                {
                    "$set": {
                        "project_id": project_id,
                        "agent_name": agent_name,
                        "status": "running",
                        "progress": 0,
                        "tokens_used": 0,
                        "started_at": datetime.now(timezone.utc).isoformat(),
                    }
                },
                upsert=True,
            )
            await db.project_logs.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "project_id": project_id,
                    "agent": agent_name,
                    "message": f"Starting {agent_name}...",
                    "level": "info",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        timeout_sec = max(get_timeout(a) for a in agent_names)

        async def run_one(name: str):
            return await asyncio.wait_for(
                _run_single_agent_with_retry(
                    project_id,
                    user_id,
                    name,
                    project_prompt_with_kind,
                    results,
                    effective,
                    model_chain,
                    build_kind=build_kind,
                    user_tier=user_tier,
                    speed_selector=speed_selector,
                    available_credits=available_credits,
                ),
                timeout=timeout_sec + 30,
            )

        tasks = [run_one(name) for name in agent_names]
        phase_results = await asyncio.gather(*tasks, return_exceptions=True)
        phase_fail_count = 0
        for name, r in zip(agent_names, phase_results):
            if isinstance(r, Exception):
                phase_fail_count += 1
                crit = get_criticality(name)
                fallback = generate_fallback(name)
                if crit == "critical":
                    # Fallback on every critical path (9.5+): use minimal output and continue build
                    results[name] = {
                        "output": fallback,
                        "result": fallback,
                        "status": "failed_with_fallback",
                        "reason": str(r),
                    }
                else:
                    results[name] = {
                        "output": fallback,
                        "result": fallback,
                        "status": "failed_with_fallback",
                    }
            else:
                results[name] = r
                total_used += r.get("tokens_used", 0)
                if (r.get("status") or "").lower() in (
                    "skipped",
                    "failed",
                    "failed_with_fallback",
                ):
                    phase_fail_count += 1
            emit_build_event(
                project_id,
                "agent_completed",
                agent=name,
                tokens=results[name].get("tokens_used", 0),
                status=results[name].get("status", ""),
                message=f"{name} completed",
            )
            out_snippet = coerce_text_output(
                results[name].get("output") or results[name].get("result") or "",
                limit=200,
            )
            await db.agent_status.update_one(
                {"project_id": project_id, "agent_name": name},
                {
                    "$set": {
                        "status": "completed",
                        "progress": 100,
                        "tokens_used": results[name].get("tokens_used", 0),
                    }
                },
            )
            await db.project_logs.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "project_id": project_id,
                    "agent": name,
                    "message": f"{name} completed. Output: {out_snippet}...",
                    "level": "success",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            await db.token_usage.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "project_id": project_id,
                    "user_id": user_id,
                    "agent": name,
                    "tokens": results[name].get("tokens_used", 0),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        # 10/10: suggest phase retry when Quality phase (index 3) has many failures
        if phase_idx == 3 and phase_fail_count >= 2:
            suggest_retry_phase = 1
            suggest_retry_reason = (
                "Quality phase had many failures. Retry code generation?"
            )
        project = await db.projects.find_one({"id": project_id})
        if project and project.get("status") == "failed":
            return
    # Bounded autonomy loop: re-run tests/security once if they failed (self-heal)
    try:
        from autonomy_loop import run_bounded_autonomy_loop

        autonomy_result = run_bounded_autonomy_loop(
            project_id, results, emit_event=emit_build_event
        )
        if autonomy_result.get("iterations"):
            await db.project_logs.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "project_id": project_id,
                    "agent": "AutonomyLoop",
                    "message": f"Self-heal: re-ran tests={autonomy_result.get('ran_tests')}, security={autonomy_result.get('ran_security')}",
                    "level": "info",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
    except Exception as e:
        logger.warning("autonomy loop: %s", e)

    # --- SPECIALIZED AGENT (domain-matched: game, ml, blockchain, etc.) ---
    _spec_key = None
    if build_kind == "game":
        _spec_key = "games"
    elif (
        "ml" in prompt.lower()
        or "machine learning" in prompt.lower()
        or "model" in prompt.lower()
    ):
        _spec_key = "ml"
    elif (
        "blockchain" in prompt.lower()
        or "smart contract" in prompt.lower()
        or "crypto" in prompt.lower()
    ):
        _spec_key = "blockchain"
    elif (
        "iot" in prompt.lower()
        or "firmware" in prompt.lower()
        or "embedded" in prompt.lower()
    ):
        _spec_key = "iot"
    elif (
        "science" in prompt.lower()
        or "math" in prompt.lower()
        or "simulation" in prompt.lower()
    ):
        _spec_key = "science"
    if _spec_key:
        try:
            from specialized_agents_100_percent import SpecializedAgentOrchestrator

            _spec_orch = SpecializedAgentOrchestrator()
            _spec_req = {
                "prompt": prompt,
                "name": project_id[:12],
                "type": "2d_platformer" if _spec_key == "games" else "full",
            }
            _spec_out = await _spec_orch.execute_agent(_spec_key, _spec_req)
            _code = (
                _spec_out.get("game_code")
                or _spec_out.get("firmware_code")
                or _spec_out.get("model_code")
                or _spec_out.get("contract_code")
                or _spec_out.get("solution_code")
                or str(_spec_out)
            )
            results[f"SpecializedAgent-{_spec_key.title()}"] = {
                "output": _code,
                "result": _code,
                "status": _spec_out.get("status", "ok"),
                "tokens_used": 0,
            }
        except Exception as _spec_err:
            logger.debug("Specialized agent (%s) skipped: %s", _spec_key, _spec_err)

    # --- POST-BUILD: CRITIC + TRUTH (anti-hallucination) ---
    critic_review: Optional[Dict[str, Any]] = None
    truth_report: Optional[Dict[str, Any]] = None
    truth_result: Optional[Dict[str, Any]] = None
    emit_build_event(
        project_id,
        "quality_check_started",
        message="Running quality review and truth verification…",
    )
    try:
        emit_build_event(project_id, "critic_started", message="Critic review…")
        critic_review = await _critic_agent.review_build(
            project_id=project_id,
            agent_outputs=results,
            llm_caller=_call_llm_with_fallback,
            model_chain=model_chain,
            api_keys=effective,
        )
        logger.info(
            f"Critic review: score={critic_review.get('overall_score')}, pass_rate={critic_review.get('pass_rate')}%"
        )
        await db.project_logs.insert_one(
            {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "type": "critic_review",
                "data": critic_review,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as _critic_err:
        logger.debug("Critic review failed (non-fatal): %s", _critic_err)
    try:
        emit_build_event(project_id, "truth_started", message="Truth verification…")
        truth_report = await _truth_module.verify_claims(
            agent_outputs=results,
            llm_caller=_call_llm_with_fallback,
            model_chain=model_chain,
            api_keys=effective,
            project_prompt=prompt,
        )
        logger.info(
            "Truth verification: verdict=%s, truth_score=%s",
            truth_report.get("verdict"),
            truth_report.get("truth_score"),
        )
        await db.project_logs.insert_one(
            {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "type": "truth_verification",
                "data": truth_report,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as _truth_err:
        logger.debug("Truth verification failed (non-fatal): %s", _truth_err)

    # --- Optional: standalone truth_check (adversarial code honesty) ---
    try:
        from truth_module import truth_check as truth_check_build

        async def _llm_for_truth(msg: str, sys_msg: str, sid: str, mchain) -> str:
            r, _ = await _call_llm_with_fallback(
                message=msg,
                system_message=sys_msg,
                session_id=sid,
                model_chain=mchain if isinstance(mchain, list) else model_chain,
                api_keys=effective,
            )
            return r or ""

        build_output = {
            k: coerce_text_output(v.get("output") or v.get("result") or "", limit=5000)
            for k, v in list(results.items())[:15]
        }
        truth_result = await truth_check_build(project_id, build_output, _llm_for_truth)
        await db.project_logs.insert_one(
            {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "type": "truth_check_honesty",
                "data": truth_result,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as _tc_err:
        logger.debug("truth_check (honesty) failed (non-fatal): %s", _tc_err)

    critic_score = (critic_review or {}).get("overall_score")
    truth_verdict = (truth_report or {}).get("verdict")
    truth_score = (truth_report or {}).get("truth_score")
    truth_honest_score = (
        (truth_result or {}).get("honest_score") if truth_result else None
    )

    fe = (results.get("Frontend Generation") or {}).get("output") or ""
    be = (results.get("Backend Generation") or {}).get("output") or ""
    db_schema = (results.get("Database Agent") or {}).get("output") or ""
    tests = (results.get("Test Generation") or {}).get("output") or ""
    images = (results.get("Image Generation") or {}).get("images") or {}
    videos = (results.get("Video Generation") or {}).get("videos") or {}
    quality = score_generated_code(
        frontend_code=fe, backend_code=be, database_schema=db_schema, test_code=tests
    )
    deploy_files = {}
    if build_kind == "mobile" and fe:
        # Mobile project: Expo app + native config + store submission pack
        user_doc = await db.users.find_one({"id": user_id}, {"plan": 1})
        user_plan = (user_doc or {}).get("plan") or "free"
        fe_mobile = _inject_crucibai_branding(fe, user_plan)
        deploy_files["App.js"] = fe_mobile
        # Native Config Agent -> app.json, eas.json
        native_out = (results.get("Native Config Agent") or {}).get("output") or ""
        json_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)```", native_out)
        if len(json_blocks) >= 1:
            try:
                deploy_files["app.json"] = json_blocks[0].strip()
            except Exception:
                pass
        if len(json_blocks) >= 2:
            try:
                deploy_files["eas.json"] = json_blocks[1].strip()
            except Exception:
                pass
        if "app.json" not in deploy_files:
            deploy_files["app.json"] = (
                '{"name":"App","slug":"app","version":"1.0.0","ios":{"bundleIdentifier":"com.example.app"},"android":{"package":"com.example.app"}}'
            )
        if "eas.json" not in deploy_files:
            deploy_files["eas.json"] = (
                '{"build":{"preview":{"ios":{},"android":{}},"production":{"ios":{},"android":{}}}}'
            )
        deploy_files["package.json"] = (
            '{"name":"app","version":"1.0.0","main":"node_modules/expo/AppEntry.js","scripts":{"start":"expo start","android":"expo start --android","ios":"expo start --ios"},"dependencies":{"expo":"~50.0.0","react":"18.2.0","react-native":"0.73.0"}}'
        )
        deploy_files["babel.config.js"] = (
            "module.exports = function(api) { api.cache(true); return { presets: ['babel-preset-expo'] }; };"
        )
        # Store Prep Agent -> store-submission/
        store_out = (results.get("Store Prep Agent") or {}).get("output") or ""
        deploy_files["store-submission/STORE_SUBMISSION_GUIDE.md"] = (
            store_out
            or "See Expo EAS Submit docs for Apple App Store and Google Play submission."
        )
        metadata_match = re.search(r"\{[\s\S]*?\"app_name\"[\s\S]*?\}", store_out)
        if metadata_match:
            deploy_files["store-submission/metadata.json"] = metadata_match.group(0)
    else:
        # Web project — always emit a full preview bundle (like Manus): entry + App + styles so Sandpack preview works
        if fe:
            fe = _inject_media_into_jsx(fe, images, videos)
            user_doc = await db.users.find_one({"id": user_id}, {"plan": 1})
            user_plan = (user_doc or {}).get("plan") or "free"
            fe = _inject_crucibai_branding(fe, user_plan)
            deploy_files["src/App.jsx"] = fe
            # Ensure Sandpack has an entry and styles so preview runs (Manus-like minimal runnable set)
            if "src/index.js" not in deploy_files:
                deploy_files["src/index.js"] = """import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles.css';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
"""
            if "src/styles.css" not in deploy_files:
                deploy_files[
                    "src/styles.css"
                ] = """@import url('https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css');
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: Inter, system-ui, sans-serif; }
"""
            # Full build (not minimal): package.json + index.html so export/deploy is a complete project
            if "package.json" not in deploy_files:
                deploy_files["package.json"] = """{
  "name": "crucib-app",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test"
  },
  "browserslist": { "production": [">0.2%", "not dead"], "development": ["last 1 chrome version"] }
}
"""
            if "public/index.html" not in deploy_files:
                deploy_files["public/index.html"] = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="theme-color" content="#000000" />
  <title>App</title>
</head>
<body>
  <noscript>You need to enable JavaScript to run this app.</noscript>
  <div id="root"></div>
</body>
</html>
"""
        if be:
            deploy_files["server.py"] = be
        if db_schema:
            deploy_files["schema.sql"] = db_schema
        if tests:
            deploy_files["tests/test_basic.py"] = tests
    set_payload = {
        "status": "completed",
        "tokens_used": total_used,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "live_url": None,
        "quality_score": quality,
        "orchestration_version": "v2_dag",
        "build_kind": build_kind,
    }
    if critic_score is not None:
        set_payload["critic_score"] = critic_score
    if truth_verdict is not None:
        set_payload["truth_verdict"] = truth_verdict
    if truth_score is not None:
        set_payload["truth_score"] = truth_score
    if truth_honest_score is not None:
        set_payload["truth_honest_score"] = truth_honest_score
    if images:
        set_payload["images"] = images
    if videos:
        set_payload["videos"] = videos
    if deploy_files:
        set_payload["deploy_files"] = deploy_files
    if suggest_retry_phase is not None:
        set_payload["suggest_retry_phase"] = suggest_retry_phase
        set_payload["suggest_retry_reason"] = (
            suggest_retry_reason or "Retry code generation?"
        )
    update_op = {"$set": set_payload}
    if suggest_retry_phase is None:
        update_op["$unset"] = {"suggest_retry_phase": "", "suggest_retry_reason": ""}
    await db.projects.update_one({"id": project_id}, update_op)
    # Version history (item 13): append this build to build_history for UI
    project_after = await db.projects.find_one({"id": project_id})
    if project_after is not None:
        history = list(project_after.get("build_history") or [])
        history.insert(
            0,
            {
                "completed_at": set_payload.get("completed_at"),
                "status": "completed",
                "quality_score": quality,
                "tokens_used": total_used,
            },
        )
        await db.projects.update_one(
            {"id": project_id}, {"$set": {"build_history": history[:50]}}
        )
    emit_build_event(
        project_id,
        "build_completed",
        status="completed",
        tokens=total_used,
        message="Build completed",
        deploy_files=deploy_files,
        quality_score=quality,
        critic_score=critic_score,
        truth_verdict=truth_verdict,
        truth_score=truth_score,
        truth_honest_score=truth_honest_score,
    )
    project = await db.projects.find_one({"id": project_id})
    if project and project.get("tokens_allocated"):
        refund = project["tokens_allocated"] - total_used
        if refund > 0:
            await db.users.update_one(
                {"id": user_id}, {"$inc": {"token_balance": refund}}
            )
            await db.token_ledger.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "tokens": refund,
                    "type": "refund",
                    "description": f"Unused tokens from project {project_id[:8]}",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )


@projects_router.post("/projects")
async def create_project(
    data: ProjectCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    audit_logger = get_audit_logger()
    if Permission is not None and not has_permission(user, Permission.CREATE_PROJECT):
        raise HTTPException(
            status_code=403, detail="Insufficient permission to create projects"
        )
    plan = user.get("plan", "free")
    if plan == "free":
        count = await db.projects.count_documents({"user_id": user["id"]})
        if count >= FREE_TIER_MAX_PROJECTS:
            raise HTTPException(
                status_code=403,
                detail="You've saved 3 projects. Upgrade to Builder to save unlimited projects and get faster builds.",
                headers={"X-Upgrade-Required": "builder"},
            )
    # Landing pages need fewer credits so free/guest (100–700) can build
    project_type_lower = (data.project_type or "").strip().lower()
    default_tokens = 80000 if project_type_lower == "landing" else 675000
    estimated_tokens = data.estimated_tokens or default_tokens
    estimated_credits = _tokens_to_credits(estimated_tokens)
    await _ensure_credit_balance(user["id"])
    cred = _user_credits(user)
    if cred < estimated_credits:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Need {estimated_credits}, have {cred}. Buy more in Credit Center.",
        )

    # Free tier: landing-only unless user has a paid purchase
    if plan == "free":
        has_paid = await db.token_ledger.find_one(
            {"user_id": user["id"], "type": "purchase"}
        )
        if not has_paid and (data.project_type or "").strip().lower() != "landing":
            raise HTTPException(
                status_code=402,
                detail="Free tier is for landing pages only. Set project_type to 'landing' or upgrade/buy credits in Credit Center to create full apps.",
            )

    # Legal / AUP compliance: block prohibited build requests
    prompt = (data.requirements or {}).get("prompt") or data.description or ""
    if isinstance(prompt, dict):
        prompt = prompt.get("prompt") or str(prompt)
    if legal_check_request and prompt:
        compliance = legal_check_request(prompt)
        if not compliance.get("allowed"):
            await db.blocked_requests.insert_one(
                {
                    "user_id": user["id"],
                    "prompt": prompt[:2000],
                    "reason": compliance.get("reason"),
                    "category": compliance.get("category"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "blocked",
                }
            )
            raise HTTPException(
                status_code=400,
                detail=compliance.get("reason")
                or "Request violates Acceptable Use Policy. See /aup for details.",
            )

    project_id = str(uuid.uuid4())
    project = {
        "id": project_id,
        "user_id": user["id"],
        "name": data.name,
        "description": data.description,
        "project_type": data.project_type,
        "requirements": data.requirements,
        "status": "queued",
        "tokens_allocated": estimated_tokens,
        "tokens_used": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "live_url": None,
        "quick_build": getattr(data, "quick_build", False) or False,
    }
    await db.projects.insert_one(project)
    if audit_logger:
        await audit_logger.log(
            user["id"],
            "project_created",
            resource_type="project",
            resource_id=project_id,
            new_value={"name": data.name},
            ip_address=getattr(request.client, "host", None),
        )
    await db.users.update_one(
        {"id": user["id"]}, {"$inc": {"credit_balance": -estimated_credits}}
    )

    background_tasks.add_task(run_orchestration_v2, project_id, user["id"])

    return {"project": {k: v for k, v in project.items() if k != "_id"}}


@projects_router.get("/projects")
async def get_projects(
    user: dict = Depends(get_current_user),
    _: dict = Depends(
        require_permission(Permission.VIEW_PROJECT if Permission else None)
    ),
):
    db = get_db()
    cursor = db.projects.find({"user_id": user["id"]}, {"_id": 0}).sort(
        "created_at", -1
    )
    projects = await cursor.to_list(100)
    return {"projects": projects}


def _safe_import_path(path: str) -> str:
    """Return a safe relative path for import (no .., no absolute)."""
    p = (path or "").strip().replace("\\", "/").lstrip("/")
    if ".." in p or p.startswith("/"):
        return ""
    return p[:500]  # limit length


@projects_router.post("/projects/import")
async def import_project(
    data: ProjectImportBody,
    user: dict = Depends(
        require_permission(Permission.CREATE_PROJECT if Permission else None)
    ),
):
    """Import a project from paste (files), ZIP (base64), or Git URL. Creates project and writes files to workspace."""
    db = get_db()
    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    name = (data.name or "Imported project").strip() or "Imported project"
    project = {
        "id": project_id,
        "user_id": user["id"],
        "name": name,
        "description": "Imported from paste, ZIP, or Git.",
        "project_type": "fullstack",
        "requirements": {"prompt": "", "imported": True},
        "status": "imported",
        "tokens_allocated": 0,
        "tokens_used": 0,
        "created_at": now,
        "completed_at": now,
        "live_url": None,
    }
    await db.projects.insert_one(project)
    root = _project_workspace_path(project_id).resolve()
    root.mkdir(parents=True, exist_ok=True)
    written = 0
    if data.source == "paste" and data.files:
        for item in data.files[:200]:
            path = _safe_import_path(item.get("path") or "")
            if not path:
                continue
            content = item.get("code") or item.get("content") or ""
            if len(content) > 2 * 1024 * 1024:
                continue
            full = (root / path).resolve()
            try:
                full.relative_to(root)
            except ValueError:
                continue
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(
                content[: 2 * 1024 * 1024], encoding="utf-8", errors="replace"
            )
            written += 1
    elif data.source == "zip" and data.zip_base64:
        try:
            raw = base64.b64decode(data.zip_base64, validate=True)
            if len(raw) > 10 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="ZIP too large (max 10MB)")
            with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
                for info in zf.infolist()[:500]:
                    if info.is_dir():
                        continue
                    path = _safe_import_path(info.filename)
                    if not path or "node_modules" in path or "__pycache__" in path:
                        continue
                    full = (root / path).resolve()
                    try:
                        full.relative_to(root)
                    except ValueError:
                        continue
                    full.parent.mkdir(parents=True, exist_ok=True)
                    full.write_bytes(zf.read(info))
                    written += 1
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Invalid ZIP file")
    elif data.source == "git" and data.git_url:
        url = (data.git_url or "").strip()
        if not url.startswith("http"):
            raise HTTPException(status_code=400, detail="Git URL must be HTTPS")
        try:
            import httpx

            if "github.com" in url:
                u = (
                    url.rstrip("/")
                    .replace("https://github.com/", "")
                    .replace(".git", "")
                )
                parts = u.split("/")
                if len(parts) >= 2:
                    archive_url = f"https://github.com/{parts[0]}/{parts[1]}/archive/refs/heads/main.zip"
                else:
                    archive_url = f"https://github.com/{parts[0]}/{parts[1]}/archive/refs/heads/master.zip"
            else:
                raise HTTPException(
                    status_code=400, detail="Only GitHub URLs supported for now"
                )
            async with httpx.AsyncClient() as client:
                r = await client.get(archive_url, timeout=30)
                if r.status_code != 200:
                    r = await client.get(
                        archive_url.replace("/main.zip", "/master.zip"), timeout=30
                    )
                if r.status_code != 200:
                    raise HTTPException(
                        status_code=400, detail="Could not fetch repo archive"
                    )
                raw = r.content
                if len(raw) > 15 * 1024 * 1024:
                    raise HTTPException(
                        status_code=413, detail="Repo archive too large (max 15MB)"
                    )
                with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
                    for info in zf.infolist()[:500]:
                        if info.is_dir():
                            continue
                        parts = info.filename.replace("\\", "/").split("/")
                        name_part = (
                            "/".join(parts[1:]) if len(parts) > 1 else info.filename
                        )
                        path = _safe_import_path(name_part)
                        if not path or "node_modules" in path or "__pycache__" in path:
                            continue
                        full = (root / path).resolve()
                        try:
                            full.relative_to(root)
                        except ValueError:
                            continue
                        full.parent.mkdir(parents=True, exist_ok=True)
                        full.write_bytes(zf.read(info))
                        written += 1
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Git import failed: %s", e)
            raise HTTPException(
                status_code=400, detail=f"Git import failed: {str(e)[:200]}"
            )
    else:
        raise HTTPException(
            status_code=400, detail="Provide source and files, zip_base64, or git_url"
        )
    return {
        "project_id": project_id,
        "project": {k: v for k, v in project.items() if k != "_id"},
        "files_written": written,
    }


@projects_router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    user: dict = Depends(get_current_user),
    _: dict = Depends(
        require_permission(Permission.VIEW_PROJECT if Permission else None)
    ),
):
    db = get_db()
    project = await db.projects.find_one(
        {"id": project_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": project}


@projects_router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    user: dict = Depends(
        require_permission(Permission.DELETE_PROJECT if Permission else None)
    ),
):
    """Delete a project and its related data. Only the project owner can delete."""
    db = get_db()
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.project_logs.delete_many({"project_id": project_id})
    await db.agent_status.delete_many({"project_id": project_id})
    await db.shares.delete_many({"project_id": project_id})
    await db.projects.delete_one({"id": project_id, "user_id": user["id"]})
    if project_id in _build_events:
        del _build_events[project_id]
    try:
        workspace_path = _project_workspace_path(project_id)
        if workspace_path.exists():
            import shutil

            shutil.rmtree(workspace_path, ignore_errors=True)
    except Exception as e:
        logger.warning("Could not remove project workspace dir %s: %s", project_id, e)
    return Response(status_code=204)


@projects_router.get("/projects/{project_id}/state")
async def get_project_state(project_id: str, user: dict = Depends(get_current_user)):
    """Return structured project state (plan, requirements, stack, reports, tool_log) for UI and debugging."""
    db = get_db()
    project = await db.projects.find_one(
        {"id": project_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    state = load_state(project_id)
    # Merge quality score prominently into state so UI can display "App scored X/10"
    quality_score = project.get("quality_score")
    if quality_score and isinstance(quality_score, dict):
        overall = quality_score.get("overall_score", 0)
        breakdown = quality_score.get("breakdown") or {}
        state["quality"] = {
            "overall_score": overall,
            "display": f"{round(overall / 10, 1)}/10",
            "verdict": _quality_verdict(overall),
            "breakdown": breakdown,
            "badge": _quality_badge(overall),
            "deploy_gated": overall < 60,
        }
    elif quality_score is not None:
        state["quality"] = {
            "overall_score": quality_score,
            "display": f"{round(float(quality_score) / 10, 1)}/10",
        }
    return {"state": state}


@projects_router.get("/projects/{project_id}/events")
async def stream_build_events(
    project_id: str,
    last_id: int = Query(0, description="Last event id received"),
    user: dict = Depends(get_current_user_sse),
):
    db = get_db()
    """SSE stream of build events (agent_started, agent_completed, phase_started, build_completed). Wired to orchestration."""
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    async def event_generator():
        seen = last_id
        while True:
            events = _build_events.get(project_id, [])
            for ev in events:
                if ev.get("id", 0) >= seen:
                    yield f"data: {json.dumps(ev)}\n\n"
                    seen = ev.get("id", 0) + 1
            project_doc = await db.projects.find_one(
                {"id": project_id, "user_id": user["id"]}, {"status": 1}
            )
            if project_doc and project_doc.get("status") in ("completed", "failed"):
                yield f"data: {json.dumps({'type': 'stream_end', 'status': project_doc['status']})}\n\n"
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@projects_router.get("/projects/{project_id}/events/snapshot")
async def get_build_events_snapshot(
    project_id: str, user: dict = Depends(get_current_user)
):
    """One-shot fetch of all build events (for UI timeline). Wired to same store as SSE."""
    db = get_db()
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    events = _build_events.get(project_id, [])
    # If in-memory is empty (e.g. after server restart), load persisted events from DB
    if not events and project and project.get("build_events"):
        events = project.get("build_events", [])
        _build_events[project_id] = list(events)  # Restore to cache
    return {"project_id": project_id, "events": events, "count": len(events)}


def _project_workspace_path(project_id: str) -> Path:
    safe_id = project_id.replace("/", "_").replace("\\", "_")
    return WORKSPACE_ROOT / safe_id


async def _user_can_access_project_workspace(
    user_id: Optional[str], project_id: str
) -> bool:
    """Allow workspace I/O if a user-owned project or Auto-Runner job exists."""
    db = get_db()
    if not project_id or not user_id:
        return False
    project = await db.projects.find_one(
        {"id": project_id, "user_id": user_id}, {"id": 1}
    )
    if project:
        return True
    try:
        from db_pg import get_pg_pool

        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT 1 FROM jobs WHERE project_id = $1 AND user_id = $2 LIMIT 1",
                project_id,
                user_id,
            )
        return row is not None
    except Exception:
        return False


async def _resolve_workspace_project_for_job(job_id: str, user: dict) -> str:
    """Orchestrator job → workspace root via project_id; same access rules as project workspace."""
    runtime_state, _, _, _, _ = _get_orchestration()
    from db_pg import get_pg_pool

    pool = await get_pg_pool()
    runtime_state.set_pool(pool)
    from orchestration import runtime_state as orch_rs

    oj = await orch_rs.get_job(job_id)
    if not oj:
        raise HTTPException(status_code=404, detail="Job not found")
    _assert_job_owner_match(oj.get("user_id"), user)
    uid = user.get("id")
    pid = oj.get("project_id")
    if not pid:
        raise HTTPException(status_code=404, detail="Job has no project workspace")
    if not await _user_can_access_project_workspace(uid, pid):
        raise HTTPException(status_code=404, detail="Project not found")
    return str(pid)


async def _resolve_project_workspace_path_for_user(
    project_id: Optional[str], user: dict
) -> Path:
    """Resolve a user-owned project workspace without trusting client-supplied server paths."""
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id required")
    if not await _user_can_access_project_workspace(user.get("id"), project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    root = _project_workspace_path(project_id).resolve()
    workspace_root = WORKSPACE_ROOT.resolve()
    try:
        root.relative_to(workspace_root)
    except ValueError:
        raise HTTPException(status_code=400, detail="Path outside workspace")
    return root


async def _resolve_job_project_id_for_user(
    project_id: Optional[str], user: dict
) -> str:
    """Resolve a job project_id without letting users attach jobs to other workspaces."""
    pid = (project_id or "").strip()
    if not pid:
        return user["id"]
    if pid == user.get("id"):
        return pid
    if not await _user_can_access_project_workspace(user.get("id"), pid):
        raise HTTPException(status_code=404, detail="Project not found")
    return pid


def _list_all_workspace_rel_paths(root: Path) -> List[str]:
    """Sorted posix relative paths for all files under workspace (excludes node_modules / __pycache__)."""
    files: List[str] = []
    if not root.is_dir():
        return files
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        sp = str(p)
        if "node_modules" in sp or "__pycache__" in sp:
            continue
        try:
            rel = p.relative_to(root)
            files.append(rel.as_posix())
        except ValueError:
            continue
    files.sort()
    return files


def _paginated_workspace_files_payload(
    paths: List[str], offset: int, limit: int
) -> Dict[str, Any]:
    total = len(paths)
    off = max(0, int(offset))
    lim = max(1, min(int(limit), 1000))
    slice_paths = paths[off : off + lim]
    has_more = off + lim < total
    next_off = off + lim if has_more else None
    return {
        "files": slice_paths,
        "total_count": total,
        "offset": off,
        "limit": lim,
        "has_more": has_more,
        "next_offset": next_off,
    }


def _workspace_file_disk_path(root: Path, path: str) -> Path:
    rel = (path or "").strip().replace("\\", "/").lstrip("/")
    if ".." in rel or not rel:
        raise HTTPException(status_code=400, detail="Invalid path")
    full = (root / rel).resolve()
    try:
        full.relative_to(root.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Path outside workspace")
    if not full.exists() or not full.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return full


def _create_preview_token(project_id: str, user_id: str) -> str:
    """Short-lived JWT so iframe can load preview without Bearer header."""
    payload = {
        "project_id": project_id,
        "user_id": user_id,
        "purpose": "preview",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=2),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _verify_preview_token(token: str) -> tuple:
    """Returns (project_id, user_id) or raises."""
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    if payload.get("purpose") != "preview":
        raise jwt.InvalidTokenError("Invalid purpose")
    return payload["project_id"], payload["user_id"]


@projects_router.get("/settings/capabilities")
async def get_settings_capabilities(user: dict = Depends(get_current_user)):
    """Returns sandbox (Docker) availability and other capabilities for UI polish."""
    sandbox_available = False
    try:
        proc = await asyncio.to_thread(
            subprocess.run,
            ["docker", "run", "--rm", "hello-world"],
            capture_output=True,
            timeout=10,
        )
        sandbox_available = proc.returncode == 0
    except Exception as e:
        logger.info(
            "Sandbox (Docker) check failed: %s. Runs will use host when Docker unavailable.",
            e,
        )
    return {
        "sandbox_available": sandbox_available,
        "sandbox_default": os.environ.get("RUN_IN_SANDBOX", "1").strip().lower()
        in ("1", "true", "yes"),
    }


@projects_router.get("/projects/{project_id}/preview-token")
async def get_project_preview_token(project_id: str, user: dict = Depends(get_current_user), request: Request = None):
    api_base_url = str(request.base_url).rstrip('/') if request is not None else os.getenv("API_BASE_URL", "http://localhost:8000")
    return await get_preview_token_service(
        project_id=project_id,
        user_id=user.get("id"),
        user_can_access=_user_can_access_project_workspace,
        create_preview_token=_create_preview_token,
        api_base_url=api_base_url,
    )


@projects_router.get("/projects/{project_id}/preview")
@projects_router.get("/projects/{project_id}/preview/{path:path}")
async def serve_project_preview(project_id: str, path: str = "", preview_token: Optional[str] = Query(default=None)):
    return await serve_preview_service(
        project_id=project_id,
        path=path,
        preview_token=preview_token,
        verify_preview_token=_verify_preview_token,
        user_can_access=_user_can_access_project_workspace,
        project_workspace_path=_project_workspace_path,
    )


@projects_router.get("/projects/{project_id}/workspace/files")
async def list_workspace_files(
    project_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=1000),
    user: dict = Depends(get_current_user),
):
    """List files in project workspace (paginated; tree source of truth for clients)."""
    if not await _user_can_access_project_workspace(user.get("id"), project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    root = _project_workspace_path(project_id).resolve()
    if not root.exists():
        return _paginated_workspace_files_payload([], offset, limit)
    paths = _list_all_workspace_rel_paths(root)
    return _paginated_workspace_files_payload(paths, offset, limit)


@projects_router.get("/projects/{project_id}/workspace/file")
async def get_workspace_file_content(
    project_id: str,
    path: str = Query(..., description="Relative file path in workspace"),
    user: dict = Depends(get_current_user),
):
    """Get content of a single file in project workspace (for import/open in Workspace)."""
    if not await _user_can_access_project_workspace(user.get("id"), project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    root = _project_workspace_path(project_id).resolve()
    full = _workspace_file_disk_path(root, path)
    try:
        content = full.read_text(encoding="utf-8", errors="replace")
    except Exception:
        raise HTTPException(status_code=400, detail="File not readable as text")
    rel = str(full.relative_to(root)).replace("\\", "/")
    return {"path": rel, "content": content}


@projects_router.get("/projects/{project_id}/workspace/file/raw")
async def get_workspace_file_raw(
    project_id: str,
    path: str = Query(..., description="Relative file path in workspace"),
    user: dict = Depends(get_current_user),
):
    """Stream file bytes from project workspace (images, binaries, or fallback when text read fails)."""
    if not await _user_can_access_project_workspace(user.get("id"), project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    root = _project_workspace_path(project_id).resolve()
    full = _workspace_file_disk_path(root, path)
    guessed, _ = mimetypes.guess_type(full.name)
    media = guessed or "application/octet-stream"
    return FileResponse(path=str(full), media_type=media, filename=full.name)


@projects_router.get("/projects/{project_id}/dependency-audit")
async def get_project_dependency_audit(
    project_id: str, user: dict = Depends(get_current_user)
):
    """Optional: run npm audit and/or pip-audit in project workspace and return summary (high/critical counts)."""
    db = get_db()
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    root = _project_workspace_path(project_id).resolve()
    if not root.exists():
        return {"npm": None, "pip": None, "message": "No workspace files yet"}
    out = {"npm": None, "pip": None}

    def _run_npm_audit() -> Optional[Dict[str, Any]]:
        pkg = root / "package.json"
        if not pkg.exists():
            return None
        try:
            r = subprocess.run(
                ["npm", "audit", "--json"],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=60,
                env={**os.environ, "CI": "1"},
            )
            if r.stdout:
                data = json.loads(r.stdout)
                meta = data.get("metadata", {}) or {}
                counts = meta.get("vulnerabilities", {}) or {}
                return {
                    "critical": counts.get("critical", 0) or 0,
                    "high": counts.get("high", 0) or 0,
                    "moderate": counts.get("moderate", 0) or 0,
                    "low": counts.get("low", 0) or 0,
                    "info": counts.get("info", 0) or 0,
                    "ok": (counts.get("critical", 0) or 0) == 0
                    and (counts.get("high", 0) or 0) == 0,
                }
            return {"ok": True, "critical": 0, "high": 0}
        except (
            subprocess.TimeoutExpired,
            json.JSONDecodeError,
            FileNotFoundError,
        ) as e:
            return {"error": str(e)[:200]}
        except Exception as e:
            return {"error": str(e)[:200]}

    def _run_pip_audit() -> Optional[Dict[str, Any]]:
        req = root / "requirements.txt"
        if not req.exists():
            return None
        try:
            r = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip_audit",
                    "-r",
                    str(req),
                    "--format",
                    "json",
                    "--require-hashes",
                    "false",
                ],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=90,
            )
            if r.stdout:
                data = json.loads(r.stdout)
                deps = data.get("dependencies", {}) or {}
                total = sum(
                    len((d.get("vulns") or []))
                    for d in deps.values()
                    if isinstance(d, dict)
                )
                return {"critical": total, "high": 0, "ok": total == 0}
            return {"ok": True, "critical": 0, "high": 0}
        except (
            subprocess.TimeoutExpired,
            json.JSONDecodeError,
            FileNotFoundError,
        ) as e:
            return {"error": str(e)[:200]}
        except Exception as e:
            return {"error": str(e)[:200]}

    out["npm"] = await asyncio.to_thread(_run_npm_audit)
    out["pip"] = await asyncio.to_thread(_run_pip_audit)
    return out


async def _build_project_deploy_zip(project_id: str, user_id: str):
    """Build deploy ZIP for a project. Raises HTTPException if not found or no deploy_files."""
    db = get_db()
    project = await db.projects.find_one({"id": project_id, "user_id": user_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    deploy_files = project.get("deploy_files") or {}
    if not deploy_files:
        raise HTTPException(
            status_code=404,
            detail="No deploy snapshot for this project. Open in Workspace and use Deploy there, or re-run the build.",
        )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README-DEPLOY.md", DEPLOY_README)
        for name, content in deploy_files.items():
            safe_name = (name or "").lstrip("/")
            if safe_name:
                zf.writestr(
                    safe_name, content if isinstance(content, str) else str(content)
                )
    buf.seek(0)
    return buf


@projects_router.get("/projects/{project_id}/deploy/files")
async def get_project_deploy_files_json(
    project_id: str, user: dict = Depends(get_current_user)
):
    """Return deploy_files as JSON dict for Sandpack preview auto-wire. Called by Workspace after build_completed."""
    db = get_db()
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    deploy_files = project.get("deploy_files") or {}
    quality_score = project.get("quality_score")
    status = project.get("status", "unknown")
    return {"files": deploy_files, "status": status, "quality_score": quality_score}


@projects_router.get("/projects/{project_id}/deploy/zip")
async def get_project_deploy_zip(
    project_id: str, user: dict = Depends(get_current_user)
):
    """Download deploy ZIP for a completed project (Vercel/Netlify/Railway). Requires project to have deploy_files (stored at completion)."""
    buf = await _build_project_deploy_zip(project_id, user["id"])
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=crucibai-deploy.zip"},
    )


@projects_router.get("/projects/{project_id}/export/deploy")
async def get_project_export_deploy(
    project_id: str, user: dict = Depends(get_current_user)
):
    """Alias for deploy ZIP: same deploy-ready package keyed by project_id (for Deploy UX)."""
    buf = await _build_project_deploy_zip(project_id, user["id"])
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=crucibai-deploy.zip"},
    )


async def _get_project_deploy_files(
    project_id: str, user_id: str
) -> tuple[Dict[str, str], str]:
    """Return (deploy_files dict, project_name) for a project. Raises HTTPException if not found."""
    db = get_db()
    project = await db.projects.find_one({"id": project_id, "user_id": user_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    deploy_files = project.get("deploy_files") or {}
    if not deploy_files:
        raise HTTPException(
            status_code=404,
            detail="No deploy snapshot. Open in Workspace and use Deploy there, or re-run the build.",
        )
    name = (project.get("name") or "crucibai-app").replace(" ", "-")[:50]
    return deploy_files, name


@projects_router.post("/projects/{project_id}/deploy/vercel")
async def one_click_deploy_vercel(
    project_id: str,
    request: Request,
    body: DeployOneClickBody = None,
    user: dict = Depends(
        require_permission(Permission.DEPLOY_PROJECT if Permission else None)
    ),
):
    db = get_db()
    audit_logger = get_audit_logger()
    """One-click deploy to Vercel. Uses token from body, or user's stored deploy_tokens.vercel, or env VERCEL_TOKEN."""
    deploy_files, project_name = await _get_project_deploy_files(project_id, user["id"])
    from validate_deployment import validate_deployment

    validation = validate_deployment("vercel", deploy_files, None)
    if not validation.valid and validation.errors:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Deploy validation failed",
                "errors": validation.errors,
                "warnings": validation.warnings,
            },
        )
    u = await db.users.find_one({"id": user["id"]}, {"deploy_tokens": 1})
    vercel_token = (
        (body.token if body and body.token else None)
        or (u.get("deploy_tokens") or {}).get("vercel")
        or os.environ.get("VERCEL_TOKEN")
    )
    if not vercel_token:
        raise HTTPException(
            status_code=402,
            detail="Add your Vercel token in Settings → Deploy integrations for one-click deploy, or set VERCEL_TOKEN on server.",
        )
    files_payload = []
    for path, content in deploy_files.items():
        safe_path = (path or "").lstrip("/")
        if not safe_path:
            continue
        raw = (
            content
            if isinstance(content, (bytes, bytearray))
            else content.encode("utf-8")
        )
        # Explicit base64 encoding so Vercel handles binary files correctly
        files_payload.append(
            {
                "file": safe_path,
                "data": base64.b64encode(raw).decode("ascii"),
                "encoding": "base64",
            }
        )
    if not files_payload:
        raise HTTPException(status_code=400, detail="No deploy files to upload")
    import httpx

    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            "https://api.vercel.com/v13/deployments",
            headers={
                "Authorization": f"Bearer {vercel_token}",
                "Content-Type": "application/json",
            },
            json={"name": project_name, "files": files_payload, "target": "production"},
        )
    if r.status_code >= 400:
        msg = r.text
        try:
            msg = r.json().get("error", {}).get("message", r.text)
        except Exception as e:
            logger.error(f"Error parsing Vercel error response: {e}")
        raise HTTPException(status_code=502, detail=f"Vercel deploy failed: {msg}")
    data = r.json()
    # Vercel returns url as a hostname only (no scheme) — normalise to https://
    raw_url = data.get("url") or (
        data.get("alias", [""])[0] if data.get("alias") else ""
    )
    if not raw_url and data.get("id"):
        raw_url = f"{data.get('id', '')}.vercel.app"
    live_url = (
        f"https://{raw_url}" if raw_url and not raw_url.startswith("http") else raw_url
    )
    if live_url:
        await db.projects.update_one(
            {"id": project_id, "user_id": user["id"]}, {"$set": {"live_url": live_url}}
        )
        if audit_logger:
            await audit_logger.log(
                user["id"],
                "project_deployed",
                resource_type="project",
                resource_id=project_id,
                new_value={"live_url": live_url},
                ip_address=getattr(request.client, "host", None),
            )
    return {
        "url": live_url,
        "deployment_id": data.get("id"),
        "status": data.get("readyState") or data.get("status"),
    }


@projects_router.post("/projects/{project_id}/deploy/netlify")
async def one_click_deploy_netlify(
    project_id: str,
    request: Request,
    body: Optional[DeployOneClickBody] = None,
    user: dict = Depends(
        require_permission(Permission.DEPLOY_PROJECT if Permission else None)
    ),
):
    db = get_db()
    audit_logger = get_audit_logger()
    """One-click deploy to Netlify. Reuses the same site on subsequent deploys (idempotent).
    Uses token from body, or user's stored deploy_tokens.netlify, or env NETLIFY_TOKEN."""
    deploy_files, _ = await _get_project_deploy_files(project_id, user["id"])
    from validate_deployment import validate_deployment

    validation = validate_deployment("netlify", deploy_files, None)
    if not validation.valid and validation.errors:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Deploy validation failed",
                "errors": validation.errors,
                "warnings": validation.warnings,
            },
        )
    buf = await _build_project_deploy_zip(project_id, user["id"])
    zip_bytes = buf.getvalue()
    u = await db.users.find_one({"id": user["id"]}, {"deploy_tokens": 1})
    netlify_token = (
        (body.token if body and body.token else None)
        or (u.get("deploy_tokens") or {}).get("netlify")
        or os.environ.get("NETLIFY_TOKEN")
    )
    if not netlify_token:
        raise HTTPException(
            status_code=402,
            detail="Add your Netlify token in Settings → Deploy integrations for one-click deploy, or set NETLIFY_TOKEN on server.",
        )
    # Reuse an existing Netlify site for this project to avoid creating a new site every deploy
    existing_project = await db.projects.find_one(
        {"id": project_id, "user_id": user["id"]}, {"netlify_site_id": 1}
    )
    netlify_site_id = (existing_project or {}).get("netlify_site_id")
    import httpx

    async with httpx.AsyncClient(timeout=90.0) as client:
        if netlify_site_id:
            # Redeploy to the existing site
            r = await client.post(
                f"https://api.netlify.com/api/v1/sites/{netlify_site_id}/deploys",
                headers={
                    "Authorization": f"Bearer {netlify_token}",
                    "Content-Type": "application/zip",
                },
                content=zip_bytes,
            )
        else:
            # First deploy: create a new site
            r = await client.post(
                "https://api.netlify.com/api/v1/sites",
                headers={
                    "Authorization": f"Bearer {netlify_token}",
                    "Content-Type": "application/zip",
                },
                content=zip_bytes,
            )
    if r.status_code >= 400:
        msg = r.text
        try:
            msg = r.json().get("message", r.text)
        except Exception as e:
            logger.error(f"Error parsing Netlify error response: {e}")
        raise HTTPException(status_code=502, detail=f"Netlify deploy failed: {msg}")
    data = r.json()
    # For site-creation response the site_id is at data["id"]; for deploy response it's data["site_id"]
    site_id = (
        data.get("id")
        if not netlify_site_id
        else (data.get("site_id") or netlify_site_id)
    )
    url = data.get("ssl_url") or data.get("url") or ""
    if not url and data.get("default_subdomain"):
        url = f"https://{data['default_subdomain']}.netlify.app"
    if not url and data.get("name"):
        url = f"https://{data['name']}.netlify.app"
    updates: dict = {}
    if url:
        updates["live_url"] = url
    if site_id and site_id != netlify_site_id:
        updates["netlify_site_id"] = site_id
    if updates:
        await db.projects.update_one(
            {"id": project_id, "user_id": user["id"]}, {"$set": updates}
        )
    if url and audit_logger:
        await audit_logger.log(
            user["id"],
            "project_deployed",
            resource_type="project",
            resource_id=project_id,
            new_value={"live_url": url},
            ip_address=getattr(request.client, "host", None),
        )
    return {"url": url, "site_id": site_id}


@projects_router.patch("/projects/{project_id}/publish-settings")
async def patch_project_publish_settings(
    project_id: str,
    body: ProjectPublishSettingsBody,
    user: dict = Depends(
        require_permission(Permission.EDIT_PROJECT if Permission else None)
    ),
):
    db = get_db()
    """Persist custom domain hint and optional Railway dashboard URL (DNS still at your registrar / host)."""
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    updates = {}
    if body.custom_domain is not None:
        d = (body.custom_domain or "").strip().lower()
        if d and len(d) > 253:
            raise HTTPException(status_code=400, detail="custom_domain too long")
        if d and any(c in d for c in (" ", "/", "\\", ":", "?", "#", "<", ">", "@")):
            raise HTTPException(
                status_code=400, detail="custom_domain has invalid characters"
            )
        updates["custom_domain"] = d or None
    if body.railway_project_url is not None:
        u = (body.railway_project_url or "").strip()
        if u and len(u) > 500:
            raise HTTPException(status_code=400, detail="railway_project_url too long")
        updates["railway_project_url"] = u or None
    if not updates:
        return {"project": {k: v for k, v in project.items() if k != "_id"}}
    updates["publish_settings_updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.projects.update_one(
        {"id": project_id, "user_id": user["id"]}, {"$set": updates}
    )
    out = await db.projects.find_one(
        {"id": project_id, "user_id": user["id"]}, {"_id": 0}
    )
    return {"project": out}


@projects_router.post("/projects/{project_id}/deploy/railway")
async def deploy_railway_package(
    project_id: str,
    user: dict = Depends(
        require_permission(Permission.DEPLOY_PROJECT if Permission else None)
    ),
):
    """
    Railway deploy — two modes:
    1. RAILWAY_TOKEN set → trigger real deploy via Railway API (one-click).
    2. No token → return CLI instructions as before.
    """
    import os as _os
    import httpx as _httpx

    deploy_files, project_name = await _get_project_deploy_files(project_id, user["id"])
    from validate_deployment import validate_deployment

    validation = validate_deployment("railway", deploy_files, None)
    if not validation.valid and validation.errors:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Deploy validation failed for Railway package",
                "errors": validation.errors,
                "warnings": validation.warnings,
            },
        )

    railway_token = _os.environ.get("RAILWAY_TOKEN", "")
    railway_project_id = _os.environ.get("RAILWAY_PROJECT_ID", "")

    # --- ONE-CLICK MODE: Railway API deploy ---
    if railway_token and railway_project_id:
        try:
            # Trigger a Railway deployment via GraphQL API
            trigger_gql = """
            mutation triggerDeploy($projectId: String!) {
              deploymentTrigger(input: { projectId: $projectId }) {
                id
                url
                status
              }
            }
            """
            async with _httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://backboard.railway.app/graphql/v2",
                    headers={
                        "Authorization": f"Bearer {railway_token}",
                        "Content-Type": "application/json",
                    },
                    json={"query": trigger_gql, "variables": {"projectId": railway_project_id}},
                )
                data = resp.json()
                deployment = (data.get("data") or {}).get("deploymentTrigger") or {}
                deploy_url = deployment.get("url") or f"https://railway.app/project/{railway_project_id}"
                return {
                    "ok": True,
                    "platform": "railway",
                    "mode": "api",
                    "project_name": project_name,
                    "deploy_url": deploy_url,
                    "deployment_id": deployment.get("id"),
                    "status": deployment.get("status", "triggered"),
                    "dashboard_url": f"https://railway.app/project/{railway_project_id}",
                }
        except Exception as _re:
            logger.warning("Railway API deploy failed, falling back to CLI instructions: %s", _re)

    # --- FALLBACK: CLI instructions ---
    steps = [
        "Download Deploy ZIP from this modal (server build snapshot).",
        "Unzip into an empty folder.",
        "npm i -g @railway/cli && railway login",
        "railway init  (or railway link) in that folder.",
        "railway up — set DATABASE_URL, JWT_SECRET, and API keys in Railway Variables.",
        "Optional: connect GitHub repo to Railway for continuous deploy.",
    ]
    return {
        "ok": True,
        "platform": "railway",
        "mode": "cli",
        "project_name": project_name,
        "steps": steps,
        "dashboard_url": "https://railway.app/new",
        "zip_relative_path": f"/api/projects/{project_id}/deploy/zip",
    }


@projects_router.post("/projects/{project_id}/retry-phase")
async def retry_project_phase(
    project_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(
        require_permission(Permission.EDIT_PROJECT if Permission else None)
    ),
):
    db = get_db()
    """10/10: Retry full orchestration when Quality phase had many failures. Full re-run (no partial state)."""
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.projects.update_one(
        {"id": project_id},
        {
            "$set": {
                "status": "running",
                "progress_percent": 0,
                "current_phase": 0,
                "current_agent": None,
                "completed_at": None,
                "suggest_retry_phase": None,
                "suggest_retry_reason": None,
            }
        },
    )
    background_tasks.add_task(run_orchestration_v2, project_id, user["id"])
    return {"status": "accepted", "message": "Retry started. Build is running."}


@projects_router.get("/projects/{project_id}/logs")
async def get_project_logs(project_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    project = await db.projects.find_one(
        {"id": project_id, "user_id": user["id"]}, {"id": 1}
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    cursor = db.project_logs.find({"project_id": project_id}, {"_id": 0}).sort(
        "created_at", 1
    )
    logs = await cursor.to_list(500)
    return {"logs": logs}


@projects_router.get("/projects/{project_id}/build-history")
async def get_build_history(project_id: str, user: dict = Depends(get_current_user)):
    """Version history (item 13): list of past builds for this project (completed_at, status, quality_score, tokens_used)."""
    db = get_db()
    project = await db.projects.find_one(
        {"id": project_id, "user_id": user["id"]}, {"build_history": 1}
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    history = project.get("build_history") or []
    return {"build_history": history}


# Build phases for real-time progress UI (planning -> generating -> validating -> deployment)
BUILD_PHASES = [
    {
        "id": "planning",
        "name": "Planning",
        "agents": ["Planner", "Requirements Clarifier", "Stack Selector"],
    },
    {
        "id": "generating",
        "name": "Generating",
        "agents": [
            "Frontend Generation",
            "Backend Generation",
            "Database Agent",
            "API Integration",
            "Test Generation",
            "Image Generation",
        ],
    },
    {
        "id": "validating",
        "name": "Validating",
        "agents": [
            "Security Checker",
            "Test Executor",
            "UX Auditor",
            "Performance Analyzer",
        ],
    },
    {
        "id": "deployment",
        "name": "Deployment",
        "agents": ["Deployment Agent", "Error Recovery", "Memory Agent"],
    },
    {
        "id": "export_automation",
        "name": "Export & automation",
        "agents": [
            "PDF Export",
            "Excel Export",
            "Markdown Export",
            "Scraping Agent",
            "Automation Agent",
        ],
    },
]


@projects_router.get("/build/phases")
async def get_build_phases():
    """Return phase list for progress UI (Workspace or dashboard)."""
    return {"phases": BUILD_PHASES}


SWARM_TOKEN_MULTIPLIER = (
    1.5  # users pay more when using swarm (parallel); we don't lose money
)


@projects_router.post("/build/plan")
async def build_plan(data: BuildPlanRequest, user: dict = Depends(get_current_user)):
    """Return a structured plan for a build request. swarm=True runs plan and suggestions in parallel (faster, higher token cost). build_kind: fullstack|mobile|saas|bot|ai_agent."""
    db = get_db()
    prompt = (data.prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")
    _plan_block = screen_user_content(prompt)
    if _plan_block:
        raise HTTPException(status_code=400, detail=_plan_block)
    build_kind = (
        getattr(data, "build_kind", None) or ""
    ).strip().lower() or "fullstack"
    if build_kind not in (
        "landing",
        "fullstack",
        "mobile",
        "saas",
        "bot",
        "ai_agent",
        "game",
        "trading",
        "any",
    ):
        build_kind = "fullstack"
    use_swarm = getattr(data, "swarm", False) and user is not None
    if user is not None and not user.get("public_api"):
        credits = _user_credits(user)
        required = MIN_CREDITS_FOR_LLM * (SWARM_TOKEN_MULTIPLIER if use_swarm else 1)
        if credits < required:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits for {'Swarm ' if use_swarm else ''}plan. Need at least {int(required)}. Buy more in Credit Center.",
            )
        # Free/referral credits = landing only: if user has no paid purchase and requests non-landing, block
        # Free users with credits can build anything - no landing-only restriction
        # (The credit balance check above already ensures they have enough credits)
    user_keys_plan = await get_workspace_api_keys(user)
    effective_plan = _effective_api_keys(user_keys_plan)
    if is_real_agent_only() and not chat_llm_available(effective_plan):
        raise HTTPException(status_code=503, detail=REAL_AGENT_NO_LLM_KEYS_DETAIL)
    if stub_build_enabled():
        _pt, _sug = _stub_plan_and_suggestions(prompt, build_kind)
        return {
            "plan_text": _pt,
            "suggestions": _sug,
            "model_used": "dev-stub",
            "swarm_used": use_swarm,
            "plan_tokens": 500,
        }
    kind_instruction = {
        "landing": " The user wants a LANDING PAGE (single page or simple multi-section). Plan for hero, features, CTA, optional waitlist/form; no full app backend or SaaS billing.",
        "mobile": " The user wants a MOBILE APP (React Native, Flutter, or PWA). Plan for mobile-first UI, native or cross-platform, and app store / install considerations. Include in the plan: Mobile stack: Expo (or Flutter), targets: iOS, Android.",
        "saas": " The user wants a SAAS product. Plan for multi-tenant or single-tenant with billing: subscriptions (e.g. Stripe), plans/tiers, auth, and dashboard.",
        "bot": " The user wants a BOT (Slack, Discord, Telegram, or webhook). Plan for event handlers, commands, and optional persistence; no traditional web UI unless a simple status page.",
        "ai_agent": " The user wants an AI AGENT. Plan for tools/functions the agent can call, a system prompt, and optionally an API or runner that executes the agent (e.g. OpenAPI + LLM).",
        "game": " The user wants a GAME (browser, mobile, or desktop). Plan for game loop, UI/canvas, controls, levels or mechanics, and optional backend for scores/leaderboards.",
        "trading": " The user wants TRADING SOFTWARE (stocks, crypto, forex, or general). Plan for order types, positions, P&L, charts/visualization, risk controls, optional real-time or simulated data; consider compliance and disclaimers.",
        "any": " The user wants to build ANYTHING—no restriction. Plan according to the request: web app, game, tool, bot, SaaS, mobile, trading, automation, or combination. Choose the best stack and structure for the idea.",
    }.get(build_kind, "")
    system = f"""You are a product and engineering planner. Given a user request to build an application, output a concise plan in this exact format (use the headings and bullets, no extra text before/after).{kind_instruction}

Plan
Key Features:
• [Feature 1] – [one line]
• [Feature 2] – [one line]
• (add 4-8 features as needed)

Design Language:
• [e.g. Dark navy + white + gold accent for premium feel]
• Clean, spacious layout with card-based UI
• (2-4 short design points)

Color Palette:
• Primary: [name] (#hex)
• Secondary: [name] (#hex)
• Accent: [name] (#hex)
• Background: [name] (#hex)

Components:
• [e.g. Layout with sidebar navigation]
• [e.g. Dashboard stats cards, charts]
• (list 6-12 UI components or pages)

End with exactly: "Let me build this now."
"""
    try:
        user_keys = await get_workspace_api_keys(user)
        effective = _effective_api_keys(user_keys)
        model_chain = _get_model_chain("auto", prompt, effective_keys=effective)
        plan_text = ""
        suggestions = []

        async def get_plan():
            nonlocal plan_text
            pt, _ = await _call_llm_with_fallback(
                message=f"User request: {prompt}",
                system_message=system,
                session_id=str(uuid.uuid4()),
                model_chain=model_chain,
                api_keys=effective,
            )
            return (pt or "").strip()

        async def get_suggestions_standalone():
            sug_system = "Given the user request for an app, suggest exactly 3 short follow-up features or improvements (e.g. 'Add Loan Management', 'Implement Alerts System'). Reply with a JSON array of 3 strings, nothing else."
            resp, _ = await _call_llm_with_fallback(
                message=f"User request: {prompt[:800]}",
                system_message=sug_system,
                session_id=str(uuid.uuid4()),
                model_chain=model_chain,
                api_keys=effective,
            )
            import re

            m = re.search(r"\[.*?\]", resp or "", re.DOTALL)
            arr = json.loads(m.group()) if m else []
            return [str(x).strip() for x in arr[:3]] if isinstance(arr, list) else []

        if use_swarm:
            plan_text, sug_list = await asyncio.gather(
                get_plan(), get_suggestions_standalone()
            )
            suggestions = sug_list or [
                "Add more features",
                "Enhance reporting",
                "Improve accessibility",
            ]
        else:
            plan_text = await get_plan()
            try:
                sug_system = "Given the app plan above, suggest exactly 3 short follow-up features or improvements (e.g. 'Add Loan Management', 'Implement Alerts System'). Reply with a JSON array of 3 strings, nothing else."
                sug_resp, _ = await _call_llm_with_fallback(
                    message=f"Plan:\n{plan_text[:1500]}",
                    system_message=sug_system,
                    session_id=str(uuid.uuid4()),
                    model_chain=model_chain,
                    api_keys=effective,
                )
                import re

                m = re.search(r"\[.*?\]", sug_resp or "", re.DOTALL)
                arr = json.loads(m.group()) if m else []
                if isinstance(arr, list):
                    suggestions = [str(x).strip() for x in arr[:3]]
            except Exception:
                pass
            if not suggestions:
                suggestions = [
                    "Add more features",
                    "Enhance reporting",
                    "Improve accessibility",
                ]

        tokens_estimate = max(
            1000, len(plan_text) * 2 + sum(len(s) for s in suggestions) * 2
        )
        if use_swarm:
            tokens_estimate = int(tokens_estimate * SWARM_TOKEN_MULTIPLIER)
        if user and not user.get("public_api"):
            cred = _user_credits(user)
            credit_deduct = min(_tokens_to_credits(tokens_estimate), cred)
            if credit_deduct > 0:
                await _ensure_credit_balance(user["id"])
                await db.users.update_one(
                    {"id": user["id"]}, {"$inc": {"credit_balance": -credit_deduct}}
                )
        return {
            "plan_text": plan_text,
            "suggestions": suggestions,
            "model_used": "auto",
            "swarm_used": use_swarm,
            "plan_tokens": tokens_estimate,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("build/plan failed")
        raise HTTPException(status_code=500, detail=str(e))


@projects_router.get("/projects/{project_id}/phases")
async def get_project_phases(project_id: str, user: dict = Depends(get_current_user)):
    """Return current phase and per-phase status for a project."""
    db = get_db()
    project = await db.projects.find_one(
        {"id": project_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    statuses = await db.agent_status.find(
        {"project_id": project_id}, {"_id": 0}
    ).to_list(100)
    by_agent = {s["agent_name"]: s for s in statuses}
    phases_out = []
    current_phase_id = None
    for ph in BUILD_PHASES:
        agent_statuses = [
            by_agent.get(a, {"status": "pending", "progress": 0}) for a in ph["agents"]
        ]
        completed = sum(1 for a in agent_statuses if a.get("status") == "completed")
        total = len(ph["agents"])
        status = (
            "completed"
            if completed == total
            else (
                "running"
                if completed > 0 or current_phase_id == ph["id"]
                else "pending"
            )
        )
        if status == "running" and current_phase_id is None:
            current_phase_id = ph["id"]
        phases_out.append(
            {
                "id": ph["id"],
                "name": ph["name"],
                "status": status,
                "progress": round(100 * completed / total) if total else 0,
                "agents": agent_statuses,
            }
        )
    if not current_phase_id and project.get("status") == "completed":
        current_phase_id = "deployment"
    return {
        "phases": phases_out,
        "current_phase": current_phase_id,
        "project_status": project.get("status"),
    }


# ==================== ORCHESTRATION ====================


# Legacy orchestration views derive from the source-of-truth DAG so they stay
# in sync with the swarm runtime instead of drifting behind it.
def _token_budget_for_orchestration_agent(agent_name: str, system_msg: str) -> int:
    explicit = {
        "Frontend Generation": 150000,
        "Backend Generation": 120000,
        "Database Agent": 80000,
        "Test Generation": 100000,
        "Deployment Agent": 60000,
    }
    if agent_name in explicit:
        return explicit[agent_name]
    if agent_name.endswith("Tool Agent"):
        return 70000
    prompt_len = len(system_msg or "")
    return max(25000, min(110000, 22000 + prompt_len * 18))


_ORCHESTRATION_AGENTS = [
    (
        agent_name,
        _token_budget_for_orchestration_agent(
            agent_name, get_system_prompt_for_agent(agent_name)
        ),
        get_system_prompt_for_agent(agent_name),
    )
    for phase in get_execution_phases(AGENT_DAG)
    for agent_name in phase
]


async def run_orchestration(project_id: str, user_id: str):
    """Runs real agent orchestration: each agent calls the LLM when API keys are set. Uses user's Settings keys when available."""
    db = get_db()
    project = await db.projects.find_one({"id": project_id})
    if not project:
        return
    req = project.get("requirements") or {}
    prompt = (
        req.get("prompt")
        or req.get("description")
        or project.get("description")
        or "Build a web application"
    )
    if isinstance(prompt, dict):
        prompt = prompt.get("prompt") or str(prompt)
    user_keys = await get_workspace_api_keys({"id": user_id})
    effective = _effective_api_keys(user_keys)

    # Get user tier and derive speed from plan (no client speed_selector)
    user = await db.users.find_one({"id": user_id}, {"plan": 1, "credit_balance": 1})
    user_tier = user.get("plan", "free") if user else "free"
    available_credits = user.get("credit_balance", 0) if user else 0
    speed_selector = _speed_from_plan(user_tier)
    model_chain = _get_model_chain("auto", prompt, effective_keys=effective)

    await db.projects.update_one({"id": project_id}, {"$set": {"status": "running"}})
    total_used = 0

    for agent_name, base_tokens, system_msg in _ORCHESTRATION_AGENTS:
        await db.agent_status.update_one(
            {"project_id": project_id, "agent_name": agent_name},
            {
                "$set": {
                    "project_id": project_id,
                    "agent_name": agent_name,
                    "status": "running",
                    "progress": 0,
                    "tokens_used": 0,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                }
            },
            upsert=True,
        )
        await db.project_logs.insert_one(
            {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "agent": agent_name,
                "message": f"Starting {agent_name}...",
                "level": "info",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        tokens_used = 0
        try:
            if effective.get("anthropic"):
                response, _ = await _call_llm_with_fallback(
                    message=prompt,
                    system_message=system_msg,
                    session_id=f"orch_{project_id}",
                    model_chain=model_chain,
                    api_keys=effective,
                )
                tokens_used = max(
                    100, min(200000, (len(prompt) + len(response or "")) * 2)
                )
                await db.project_logs.insert_one(
                    {
                        "id": str(uuid.uuid4()),
                        "project_id": project_id,
                        "agent": agent_name,
                        "message": f"{agent_name} output: {(response or '')[:200]}...",
                        "level": "info",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
        except Exception as e:
            logger.warning(f"Orchestration agent {agent_name} LLM failed: {e}")

        for progress in range(0, 101, 25):
            await asyncio.sleep(0.2)
            await db.agent_status.update_one(
                {"project_id": project_id, "agent_name": agent_name},
                {
                    "$set": {
                        "progress": progress,
                        "tokens_used": int(tokens_used * progress / 100),
                    }
                },
            )
        await db.agent_status.update_one(
            {"project_id": project_id, "agent_name": agent_name},
            {
                "$set": {
                    "status": "completed",
                    "progress": 100,
                    "tokens_used": tokens_used,
                }
            },
        )
        await db.token_usage.insert_one(
            {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "user_id": user_id,
                "agent": agent_name,
                "tokens": tokens_used,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        total_used += tokens_used

        # --- METRICS: Track build completion ---
        try:
            _metrics.builds_total.labels(status="success").inc()
            _metrics.build_queue_depth.dec()
        except Exception:
            pass

        await db.project_logs.insert_one(
            {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "agent": agent_name,
                "message": f"{agent_name} completed. Used {tokens_used:,} tokens.",
                "level": "success",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    await db.projects.update_one(
        {"id": project_id},
        {
            "$set": {
                "status": "completed",
                "tokens_used": total_used,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "live_url": None,
            }
        },
    )

    project = await db.projects.find_one({"id": project_id})
    if project:
        refund_tokens = project["tokens_allocated"] - total_used
        if refund_tokens > 0:
            refund_credits = refund_tokens // CREDITS_PER_TOKEN
            await db.users.update_one(
                {"id": user_id}, {"$inc": {"credit_balance": refund_credits}}
            )
            await db.token_ledger.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "tokens": refund_tokens,
                    "credits": refund_credits,
                    "type": "refund",
                    "description": f"Unused from project {project_id[:8]}",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )


# ==================== ORCHESTRATION V2 (DAG + PARALLEL + OUTPUT CHAINING + ERROR RECOVERY) ====================
async def _run_single_agent_with_context(
    project_id: str,
    user_id: str,
    agent_name: str,
    project_prompt: str,
    previous_outputs: Dict[str, Dict[str, Any]],
    effective: Dict[str, Optional[str]],
    model_chain: list,
    build_kind: Optional[str] = None,
    user_tier: str = "free",
    speed_selector: str = "lite",
    available_credits: int = 0,
    retry_error: Optional[str] = None,
) -> Dict[str, Any]:
    """Run one agent with context from previous agents. Returns {output, tokens_used, status} or raises."""
    if agent_name not in AGENT_DAG:
        return {
            "output": "",
            "tokens_used": 0,
            "status": "skipped",
            "reason": "Unknown agent",
        }
    # Real tool agents: execute real tools (File, Browser, API, Database, Deployment) from DAG context
    if agent_name in REAL_AGENT_NAMES:
        real_result = await run_real_agent(
            agent_name, project_id, user_id, previous_outputs, project_prompt
        )
        if real_result is not None:
            persist_agent_output(project_id, agent_name, real_result)
            try:
                run_agent_real_behavior(
                    agent_name, project_id, real_result, previous_outputs
                )
            except Exception as e:
                logger.warning("run_agent_real_behavior %s: %s", agent_name, e)
            return real_result
    system_msg = get_system_prompt_for_agent(agent_name)
    if (
        agent_name == "Frontend Generation"
        and (build_kind or "").strip().lower() == "mobile"
    ):
        system_msg = "You are Frontend Generation for a mobile app. Output only Expo/React Native code (App.js, use React Native components from 'react-native', no DOM or web-only APIs). No markdown."
    enhanced_message = build_context_from_previous_agents(
        agent_name, previous_outputs, project_prompt
    )
    if retry_error:
        enhanced_message += (
            "\n\n[Previous attempt failed]\n"
            f"{retry_error[:1200]}\n"
            "Return corrected code/config only. Do not repeat the failure."
        )
    response, _ = await _call_llm_with_fallback(
        message=enhanced_message,
        system_message=system_msg,
        session_id=f"orch_{project_id}",
        model_chain=model_chain,
        api_keys=effective,
        user_id=user_id,
        user_tier=user_tier,
        speed_selector=speed_selector,
        available_credits=available_credits,
        agent_name=agent_name,
    )
    tokens_used = max(
        100, min(200000, (len(enhanced_message) + len(response or "")) * 2)
    )
    out = (response or "").strip()
    input_data = _agent_cache_input(agent_name, project_prompt, previous_outputs)
    result: Dict[str, Any] = {
        "output": out,
        "tokens_used": tokens_used,
        "status": "completed",
        "result": out,
        "code": out,
    }

    # Image Generation: LLM returns JSON prompts -> Together.ai generates images
    if (
        agent_name == "Image Generation"
        and generate_images_for_app
        and parse_image_prompts
    ):
        try:
            prompts_dict = parse_image_prompts(out)
            design_desc = (
                enhanced_message[:1000] if enhanced_message else project_prompt[:500]
            )
            images = await generate_images_for_app(
                design_desc, prompts_dict if prompts_dict else None
            )
            out = json.dumps(images) if images else out
            result = {
                "output": out,
                "tokens_used": tokens_used,
                "status": "completed",
                "result": out,
                "code": out,
                "images": images,
            }
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            result = {
                "output": out,
                "tokens_used": tokens_used,
                "status": "completed",
                "result": out,
                "code": out,
            }
    elif (
        agent_name == "Video Generation"
        and generate_videos_for_app
        and parse_video_queries
    ):
        try:
            queries_dict = parse_video_queries(out)
            design_desc = (
                enhanced_message[:1000] if enhanced_message else project_prompt[:500]
            )
            videos = await generate_videos_for_app(
                design_desc, queries_dict if queries_dict else None
            )
            out = json.dumps(videos) if videos else out
            result = {
                "output": out,
                "tokens_used": tokens_used,
                "status": "completed",
                "result": out,
                "code": out,
                "videos": videos,
            }
        except Exception as e:
            logger.warning("Video generation agent failed: %s", e)

    result = await _repair_generated_agent_output(
        agent_name=agent_name,
        result=result,
        model_chain=model_chain,
        effective=effective,
        user_id=user_id,
        user_tier=user_tier,
        speed_selector=speed_selector,
        available_credits=available_credits,
        project_id=project_id,
    )

    result = await run_real_post_step(agent_name, project_id, previous_outputs, result)
    persist_agent_output(project_id, agent_name, result)
    try:
        run_agent_real_behavior(agent_name, project_id, result, previous_outputs)
    except Exception as e:
        logger.warning("run_agent_real_behavior %s: %s", agent_name, e)

    # --- METRICS: Track agent execution ---
    try:
        safe_output = coerce_text_output(
            result.get("output") or result.get("result") or ""
        )
        _metrics.agent_executions_total.labels(
            agent=agent_name,
            status="success" if safe_output and len(safe_output) > 50 else "partial",
        ).inc()
        _metrics.active_agents.dec()
    except Exception:
        pass

    try:
        memory = await _init_agent_learning()
        if memory:
            safe_output = coerce_text_output(
                result.get("output") or result.get("result") or ""
            )
            await memory.record_execution(
                agent_name=agent_name,
                input_data={"prompt": input_data[:500], "project_id": project_id},
                output={"result": safe_output[:500], "tokens": tokens_used},
                status=(
                    ExecutionStatus.SUCCESS
                    if safe_output and len(safe_output) > 50
                    else ExecutionStatus.PARTIAL
                ),
                duration_ms=0,
                metadata={"build_kind": build_kind or "web"},
            )
    except Exception as e:
        logger.debug("Agent learning record failed (non-fatal): %s", e)

    try:
        if _vector_memory.is_available():
            await _vector_memory.store_agent_output(
                project_id=project_id,
                agent_name=agent_name,
                output=coerce_text_output(
                    result.get("output") or result.get("result") or "", limit=2000
                ),
                tokens_used=tokens_used,
            )
    except Exception as e:
        logger.debug("Vector memory store failed (non-fatal): %s", e)

    try:
        if (
            _pgvector_memory
            and getattr(_pgvector_memory, "is_available", lambda: False)()
        ):
            await _pgvector_memory.store_agent_output(
                project_id=project_id,
                agent_name=agent_name,
                output=coerce_text_output(
                    result.get("output") or result.get("result") or "", limit=2000
                ),
                tokens_used=tokens_used,
            )
    except Exception as e:
        logger.debug("PGVector memory store failed (non-fatal): %s", e)

    return result


async def _repair_generated_agent_output(
    *,
    agent_name: str,
    result: Dict[str, Any],
    model_chain: list,
    effective: Dict[str, Optional[str]],
    user_id: str,
    user_tier: str,
    speed_selector: str,
    available_credits: int,
    project_id: str,
) -> Dict[str, Any]:
    raw_output = (
        result.get("output") or result.get("result") or result.get("code") or ""
    )
    if not CodeRepairAgent.requires_validation(agent_name, raw_output):
        safe_text = coerce_text_output(raw_output)
        result["output"] = safe_text
        result["result"] = safe_text
        result["code"] = safe_text
        return result

    async def _llm_repair_callback(
        name: str, language: str, broken: str, error: str
    ) -> str:
        repair_prompt = (
            f"The previous output for agent '{name}' is invalid {language}.\n"
            f"Error: {error}\n\n"
            "Return ONLY corrected code/config. Do not explain. Do not wrap in markdown.\n\n"
            f"{broken[:12000]}"
        )
        repaired, _ = await _call_llm_with_fallback(
            message=repair_prompt,
            system_message=(
                "You are a precise code repair system. Make the smallest fix that produces valid syntax "
                "and preserves intent."
            ),
            session_id=f"repair_{project_id}_{name.lower().replace(' ', '_')}",
            model_chain=model_chain,
            api_keys=effective,
            user_id=user_id,
            user_tier=user_tier,
            speed_selector=speed_selector,
            available_credits=available_credits,
            agent_name=name,
        )
        return repaired or ""

    repaired = await CodeRepairAgent.repair_output(
        agent_name=agent_name,
        output=raw_output,
        error_message="agent_output_validation_failed",
        llm_repair=_llm_repair_callback,
    )
    if not repaired.get("valid"):
        raise AgentError(
            agent_name, f"output_validation_failed: {repaired.get('error')}", "high"
        )

    safe_text = repaired.get("output") or ""
    result["output"] = safe_text
    result["result"] = safe_text
    result["code"] = safe_text
    if repaired.get("repaired"):
        result["repair_metadata"] = {
            "language": repaired.get("language"),
            "strategy": repaired.get("strategy"),
            "status": "repaired",
        }
        logger.warning(
            "agent %s output repaired via %s",
            agent_name,
            repaired.get("strategy") or "unknown_strategy",
        )
    return result


def _agent_cache_input(
    agent_name: str, project_prompt: str, previous_outputs: Dict[str, Dict[str, Any]]
) -> str:
    """Build stable input string for agent cache key (prompt + dependent outputs)."""
    parts = [project_prompt]
    deps = list(AGENT_DAG.get(agent_name, {}).get("depends_on", []))
    for dep in sorted(deps):
        if dep in previous_outputs:
            out = coerce_text_output(
                previous_outputs[dep].get("output")
                or previous_outputs[dep].get("result")
                or "",
                limit=800,
            )
            parts.append(f"{dep}:{out}")
    return "\n".join(parts)


async def _run_single_agent_with_retry(
    project_id: str,
    user_id: str,
    agent_name: str,
    project_prompt: str,
    previous_outputs: Dict[str, Dict[str, Any]],
    effective: Dict[str, Optional[str]],
    model_chain: list,
    max_retries: int = 3,
    build_kind: Optional[str] = None,
    user_tier: str = "free",
    speed_selector: str = "lite",
    available_credits: int = 0,
) -> Dict[str, Any]:
    db = get_db()
    from agent_cache import get as cache_get
    from agent_cache import set as cache_set

    input_data = _agent_cache_input(agent_name, project_prompt, previous_outputs)
    cached = await cache_get(db, agent_name, input_data)
    if (
        cached
        and isinstance(cached, dict)
        and (cached.get("output") or cached.get("result"))
    ):
        return cached
    last_err = None
    for attempt in range(max_retries):
        try:
            r = await _run_single_agent_with_context(
                project_id,
                user_id,
                agent_name,
                project_prompt,
                previous_outputs,
                effective,
                model_chain,
                build_kind=build_kind,
                user_tier=user_tier,
                speed_selector=speed_selector,
                available_credits=available_credits,
                retry_error=str(last_err) if last_err else None,
            )
            if not (r.get("output") or r.get("result")):
                raise AgentError(agent_name, "Empty output", "medium")
            await cache_set(db, agent_name, input_data, r)
            return r
        except Exception as e:
            last_err = e
            logger.warning(
                "agent retry %s attempt %s/%s failed: %s",
                agent_name,
                attempt + 1,
                max_retries,
                str(e)[:300],
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)
    crit = get_criticality(agent_name)
    if crit == "critical":
        completed_at = datetime.now(timezone.utc).isoformat()
        await db.projects.update_one(
            {"id": project_id},
            {"$set": {"status": "failed", "completed_at": completed_at}},
        )
        # Append to build_history for version history UI (item 13)
        proj = await db.projects.find_one({"id": project_id})
        if proj is not None:
            history = list(proj.get("build_history") or [])
            history.insert(
                0,
                {
                    "completed_at": completed_at,
                    "status": "failed",
                    "quality_score": None,
                    "tokens_used": 0,
                },
            )
            await db.projects.update_one(
                {"id": project_id}, {"$set": {"build_history": history[:50]}}
            )
        return {
            "output": "",
            "tokens_used": 0,
            "status": "failed",
            "reason": str(last_err),
            "recoverable": False,
        }
    if crit == "high":
        fallback = generate_fallback(agent_name)
        return {
            "output": fallback,
            "result": fallback,
            "tokens_used": 0,
            "status": "failed_with_fallback",
            "reason": str(last_err),
            "recoverable": True,
        }
    return {
        "output": "",
        "tokens_used": 0,
        "status": "skipped",
        "reason": str(last_err),
        "recoverable": True,
    }


def _inject_media_into_jsx(
    jsx: str, images: Dict[str, str], videos: Dict[str, str]
) -> str:
    """Inject image/video URLs into generated JSX. Replaces placeholders or prepends a media section."""
    if not jsx or (not images and not videos):
        return jsx
    # Replace placeholders if present
    out = jsx
    if images.get("hero"):
        out = out.replace("CRUCIBAI_HERO_IMG", images["hero"]).replace(
            "{{HERO_IMAGE}}", images["hero"]
        )
    if images.get("feature_1"):
        out = out.replace("CRUCIBAI_FEATURE_1_IMG", images["feature_1"]).replace(
            "{{FEATURE_1_IMAGE}}", images["feature_1"]
        )
    if images.get("feature_2"):
        out = out.replace("CRUCIBAI_FEATURE_2_IMG", images["feature_2"]).replace(
            "{{FEATURE_2_IMAGE}}", images["feature_2"]
        )
    if videos.get("hero"):
        out = out.replace("CRUCIBAI_HERO_VIDEO", videos["hero"]).replace(
            "{{HERO_VIDEO}}", videos["hero"]
        )
    if videos.get("feature"):
        out = out.replace("CRUCIBAI_FEATURE_VIDEO", videos["feature"]).replace(
            "{{FEATURE_VIDEO}}", videos["feature"]
        )
    # If no placeholders were used, prepend a media section after "return ("
    if out == jsx and ("CRUCIBAI_" not in jsx and "{{HERO" not in jsx):
        media_parts = []
        if videos.get("hero"):
            media_parts.append(
                f'<section className="relative w-full h-48 md:h-64 overflow-hidden rounded-lg"><video autoPlay muted loop playsInline className="absolute inset-0 w-full h-full object-cover" src="{videos["hero"]}" /></section>'
            )
        img_keys = ["hero", "feature_1", "feature_2"]
        img_urls = [images.get(k) for k in img_keys if images.get(k)]
        if img_urls:
            divs = "".join(
                f'<div><img src="{u}" alt="Media" className="w-full h-32 object-cover rounded-lg" /></div>'
                for u in img_urls
            )
            media_parts.append(
                f'<section className="grid grid-cols-1 md:grid-cols-3 gap-4 py-4">{divs}</section>'
            )
        if media_parts:
            block = "\n      ".join(media_parts)
            idx = out.find("return (")
            if idx != -1:
                insert = idx + len("return (")
                out = (
                    out[:insert]
                    + "\n      "
                    + block
                    + "\n      "
                    + out[insert:].lstrip()
                )
    return out


# CrucibAI attribution: comment at top + footer. Free = iframe (served from our server, not removable). Paid = static div (user may remove).
CRUCIBAI_TOP_COMMENT = "// Built with CrucibAI · https://crucibai.com\n"
# URL for free-tier iframe: badge content is on our server so free users have no way to remove it (only the iframe tag in source).
_BRANDING_BASE_URL = os.environ.get("CRUCIBAI_BRANDING_URL") or (
    os.environ.get("BACKEND_PUBLIC_URL", "http://localhost:8000").rstrip("/")
    + "/branding"
)
# Free: iframe loads badge from our server — permanent, not in their editable content.
CRUCIBAI_FREE_FOOTER_JSX = (
    f'<iframe src="{_BRANDING_BASE_URL}" title="Built with CrucibAI" '
    'style={{ border: "none", height: "28px", width: "100%", display: "block" }} />'
)
# Paid: static div so they can remove it in the editor if they want.
CRUCIBAI_PAID_FOOTER_JSX = (
    '<div className="mt-8 py-3 text-center text-sm text-gray-500 border-t border-gray-200/50">'
    '<a href="https://crucibai.com" target="_blank" rel="noopener noreferrer" className="text-gray-500 hover:text-gray-700">Built with CrucibAI</a>'
    "</div>"
)


def _inject_crucibai_branding(jsx: str, plan: str) -> str:
    """Add CrucibAI attribution. Free: iframe (content on our server — cannot be removed). Paid: static div (user may remove)."""
    if not jsx or not jsx.strip():
        return jsx
    out = jsx
    # 1) Top comment (watermark in code)
    if "crucibai.com" not in out.lower() and "Built with CrucibAI" not in out:
        if out.lstrip().startswith("//") or out.lstrip().startswith("/*"):
            first_newline = out.find("\n")
            if first_newline != -1:
                out = (
                    out[: first_newline + 1]
                    + CRUCIBAI_TOP_COMMENT
                    + out[first_newline + 1 :]
                )
            else:
                out = CRUCIBAI_TOP_COMMENT + out
        else:
            out = CRUCIBAI_TOP_COMMENT + out
    # 2) Footer: free = iframe (permanent); paid = static div (removable)
    is_free = (plan or "free").lower() == "free"
    already_has = (CRUCIBAI_PAID_FOOTER_JSX in out) or (is_free and "/branding" in out)
    if not already_has:
        footer_jsx = CRUCIBAI_FREE_FOOTER_JSX if is_free else CRUCIBAI_PAID_FOOTER_JSX
        idx = out.rfind(");")
        if idx != -1:
            before = out[:idx]
            last_div = before.rfind("</div>")
            if last_div != -1:
                out = (
                    out[:last_div]
                    + "\n      "
                    + footer_jsx
                    + "\n      "
                    + out[last_div:]
                )
    return out


def _infer_build_kind(prompt: str) -> str:
    """Infer build_kind from prompt so we build the right artifact: web, mobile, agent/automation, software, etc."""
    if not prompt:
        return "fullstack"
    p = prompt.lower()
    if any(
        x in p
        for x in (
            "mobile app",
            "react native",
            "flutter",
            "ios app",
            "android app",
            "pwa ",
            "app store",
            "play store",
            "apple store",
            "google play",
            "build me a mobile",
            "mobile application",
        )
    ):
        return "mobile"
    if any(
        x in p
        for x in (
            "build me an agent",
            "automation agent",
            "automation",
            "scheduled task",
            "cron",
            "webhook agent",
            "run_agent",
            "build agent",
        )
    ):
        return "ai_agent"
    if any(
        x in p
        for x in (
            "saas",
            "subscription",
            "multi-tenant",
            "billing",
            "stripe",
            "plans/tiers",
        )
    ):
        return "saas"
    if any(
        x in p
        for x in (
            "slack bot",
            "discord bot",
            "telegram bot",
            "chatbot",
            " webhook bot",
            "bot that",
        )
    ):
        return "bot"
    if any(
        x in p
        for x in ("ai agent", "llm agent", "agent with tools", "autonomous agent")
    ):
        return "ai_agent"
    if any(
        x in p
        for x in (
            "game",
            "2d game",
            "3d game",
            "browser game",
            "mobile game",
            "arcade",
            "player score",
            "level design",
        )
    ):
        return "game"
    if any(
        x in p
        for x in (
            "trading software",
            "trading app",
            "stock trading",
            "crypto trading",
            "forex",
            "order book",
            "positions",
            "p&l",
            "trade execution",
            "portfolio tracker",
        )
    ):
        return "trading"
    if any(
        x in p for x in ("landing page", "landing only", "one-page", "marketing page")
    ):
        return "landing"
    if any(x in p for x in ("website", "build me a website", "build me a web")):
        return "fullstack"
    if any(x in p for x in ("anything", "whatever", "no limit", "any idea", "any app")):
        return "any"
    return "fullstack"


async def run_orchestration_v2(project_id: str, user_id: str):
    """DAG-based orchestration: parallel phases, output chaining, retry, timeout, quality score."""
    db = get_db()
    # --- METRICS: Track build start ---
    try:
        _metrics.build_queue_depth.inc()
    except Exception:
        pass
    project = await db.projects.find_one({"id": project_id})
    if not project:
        return
    req = project.get("requirements") or {}
    prompt = (
        req.get("prompt")
        or req.get("description")
        or project.get("description")
        or "Build a web application"
    )
    if isinstance(prompt, dict):
        prompt = prompt.get("prompt") or str(prompt)
    build_kind = (req.get("build_kind") or "").strip().lower() or _infer_build_kind(
        prompt
    )
    if build_kind not in (
        "fullstack",
        "landing",
        "mobile",
        "saas",
        "bot",
        "ai_agent",
        "game",
        "trading",
        "any",
    ):
        build_kind = "fullstack"
    project_prompt_with_kind = f"[Build kind: {build_kind}]\n{prompt}"
    try:
        from autonomous_domain_agent import initialize_autonomous_domain_agent

        _domain_agent = await initialize_autonomous_domain_agent(db)
        _analysis = await _domain_agent.analyze_requirements(prompt)
        _d = _analysis.get("detected_domain") or "general"
        _best = _analysis.get("best_practices") or []
        _constraints = _analysis.get("applicable_constraints") or []
        _extra = f"\n[Domain: {_d}]"
        if _best:
            _extra += "\nBest practices: " + "; ".join(str(x) for x in _best[:5])
        if _constraints:
            _extra += "\nConstraints: " + str(_constraints[:3])
        project_prompt_with_kind = f"[Build kind: {build_kind}]{_extra}\n{prompt}"
    except Exception as _dom_err:
        logger.debug("Autonomous domain enrichment skipped: %s", _dom_err)
    user_keys = await get_workspace_api_keys({"id": user_id})
    effective = _effective_api_keys(user_keys)

    # Get user tier and derive speed from plan (no client speed_selector)
    user = await db.users.find_one({"id": user_id}, {"plan": 1, "credit_balance": 1})
    user_tier = user.get("plan", "free") if user else "free"
    available_credits = user.get("credit_balance", 0) if user else 0
    speed_selector = _speed_from_plan(user_tier)
    model_chain = _get_model_chain("auto", prompt, effective_keys=effective)
    if not effective.get("anthropic"):
        await db.projects.update_one(
            {"id": project_id},
            {
                "$set": {
                    "status": "failed",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )
        emit_build_event(
            project_id, "build_completed", status="failed", message="No API keys"
        )
        return
    await db.projects.update_one(
        {"id": project_id},
        {"$set": {"status": "running", "current_phase": 0, "progress_percent": 0}},
    )
    phases = get_execution_phases(AGENT_DAG)
    # Item 29: Quick build — run only first 2 phases for preview in ~2 min
    if project.get("quick_build"):
        phases = phases[:2]
        emit_build_event(
            project_id,
            "build_started",
            phases=len(phases),
            message="Quick build started (preview in ~2 min)",
        )
    else:
        emit_build_event(
            project_id,
            "build_started",
            phases=len(phases),
            message="Orchestration started",
        )
    results: Dict[str, Dict[str, Any]] = {}
    total_used = 0
    suggest_retry_phase: Optional[int] = None
    suggest_retry_reason: Optional[str] = None

    # ── GAP 2.5 FIX: Checkpoint recovery — skip completed agents on restart ──
    # Reads agent_status table — if agent already has output, skip and reuse
    try:
        checkpoint_cursor = db.agent_status.find({"project_id": project_id})
        checkpoint_count = 0
        async for row in checkpoint_cursor:
            doc = row.get("doc", {})
            agent_nm = row.get("agent_name") or doc.get("agent_name", "")
            status = doc.get("status", "")
            output = doc.get("output", "")
            if agent_nm and status in ("complete", "failed_with_fallback") and output:
                results[agent_nm] = {
                    "output": output,
                    "result": output,
                    "status": status,
                    "from_checkpoint": True,
                }
                checkpoint_count += 1
        if checkpoint_count > 0:
            logger.info(
                f"Checkpoint recovery: {checkpoint_count} agents reloaded, skipping re-execution"
            )
            emit_build_event(
                project_id,
                "checkpoint_restored",
                count=checkpoint_count,
                message=f"Resuming from checkpoint: {checkpoint_count} agents already complete",
            )
    except Exception as _cp_err:
        logger.debug(f"Checkpoint load skipped: {_cp_err}")

    for phase_idx, agent_names in enumerate(phases):
        emit_build_event(
            project_id,
            "phase_started",
            phase=phase_idx,
            agents=agent_names,
            message=f"Phase {phase_idx + 1}: {', '.join(agent_names)}",
        )
        progress_pct = int((phase_idx + 1) / len(phases) * 100)
        await db.projects.update_one(
            {"id": project_id},
            {
                "$set": {
                    "current_phase": phase_idx,
                    "current_agent": ",".join(agent_names),
                    "progress_percent": progress_pct,
                    "tokens_used": total_used,
                }
            },
        )
        for agent_name in agent_names:
            # Skip agents already completed in a previous run (checkpoint recovery)
            if agent_name in results and results[agent_name].get("from_checkpoint"):
                emit_build_event(
                    project_id,
                    "agent_skipped",
                    agent=agent_name,
                    message=f"{agent_name} skipped (checkpoint)",
                )
                continue
            emit_build_event(
                project_id,
                "agent_started",
                agent=agent_name,
                message=f"{agent_name} started",
            )
            await db.agent_status.update_one(
                {"project_id": project_id, "agent_name": agent_name},
                {
                    "$set": {
                        "project_id": project_id,
                        "agent_name": agent_name,
                        "status": "running",
                        "progress": 0,
                        "tokens_used": 0,
                        "started_at": datetime.now(timezone.utc).isoformat(),
                    }
                },
                upsert=True,
            )
            await db.project_logs.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "project_id": project_id,
                    "agent": agent_name,
                    "message": f"Starting {agent_name}...",
                    "level": "info",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        timeout_sec = max(get_timeout(a) for a in agent_names)

        async def run_one(name: str):
            return await asyncio.wait_for(
                _run_single_agent_with_retry(
                    project_id,
                    user_id,
                    name,
                    project_prompt_with_kind,
                    results,
                    effective,
                    model_chain,
                    build_kind=build_kind,
                    user_tier=user_tier,
                    speed_selector=speed_selector,
                    available_credits=available_credits,
                ),
                timeout=timeout_sec + 30,
            )

        tasks = [run_one(name) for name in agent_names]
        phase_results = await asyncio.gather(*tasks, return_exceptions=True)
        phase_fail_count = 0
        for name, r in zip(agent_names, phase_results):
            if isinstance(r, Exception):
                phase_fail_count += 1
                crit = get_criticality(name)
                fallback = generate_fallback(name)
                if crit == "critical":
                    # Fallback on every critical path (9.5+): use minimal output and continue build
                    results[name] = {
                        "output": fallback,
                        "result": fallback,
                        "status": "failed_with_fallback",
                        "reason": str(r),
                    }
                else:
                    results[name] = {
                        "output": fallback,
                        "result": fallback,
                        "status": "failed_with_fallback",
                    }
            else:
                results[name] = r
                total_used += r.get("tokens_used", 0)
                if (r.get("status") or "").lower() in (
                    "skipped",
                    "failed",
                    "failed_with_fallback",
                ):
                    phase_fail_count += 1
            emit_build_event(
                project_id,
                "agent_completed",
                agent=name,
                tokens=results[name].get("tokens_used", 0),
                status=results[name].get("status", ""),
                message=f"{name} completed",
            )
            out_snippet = coerce_text_output(
                results[name].get("output") or results[name].get("result") or "",
                limit=200,
            )
            await db.agent_status.update_one(
                {"project_id": project_id, "agent_name": name},
                {
                    "$set": {
                        "status": "completed",
                        "progress": 100,
                        "tokens_used": results[name].get("tokens_used", 0),
                    }
                },
            )
            await db.project_logs.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "project_id": project_id,
                    "agent": name,
                    "message": f"{name} completed. Output: {out_snippet}...",
                    "level": "success",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            await db.token_usage.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "project_id": project_id,
                    "user_id": user_id,
                    "agent": name,
                    "tokens": results[name].get("tokens_used", 0),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        # 10/10: suggest phase retry when Quality phase (index 3) has many failures
        if phase_idx == 3 and phase_fail_count >= 2:
            suggest_retry_phase = 1
            suggest_retry_reason = (
                "Quality phase had many failures. Retry code generation?"
            )
        project = await db.projects.find_one({"id": project_id})
        if project and project.get("status") == "failed":
            return
    # Bounded autonomy loop: re-run tests/security once if they failed (self-heal)
    try:
        from autonomy_loop import run_bounded_autonomy_loop

        autonomy_result = run_bounded_autonomy_loop(
            project_id, results, emit_event=emit_build_event
        )
        if autonomy_result.get("iterations"):
            await db.project_logs.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "project_id": project_id,
                    "agent": "AutonomyLoop",
                    "message": f"Self-heal: re-ran tests={autonomy_result.get('ran_tests')}, security={autonomy_result.get('ran_security')}",
                    "level": "info",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
    except Exception as e:
        logger.warning("autonomy loop: %s", e)

    # --- SPECIALIZED AGENT (domain-matched: game, ml, blockchain, etc.) ---
    _spec_key = None
    if build_kind == "game":
        _spec_key = "games"
    elif (
        "ml" in prompt.lower()
        or "machine learning" in prompt.lower()
        or "model" in prompt.lower()
    ):
        _spec_key = "ml"
    elif (
        "blockchain" in prompt.lower()
        or "smart contract" in prompt.lower()
        or "crypto" in prompt.lower()
    ):
        _spec_key = "blockchain"
    elif (
        "iot" in prompt.lower()
        or "firmware" in prompt.lower()
        or "embedded" in prompt.lower()
    ):
        _spec_key = "iot"
    elif (
        "science" in prompt.lower()
        or "math" in prompt.lower()
        or "simulation" in prompt.lower()
    ):
        _spec_key = "science"
    if _spec_key:
        try:
            from specialized_agents_100_percent import SpecializedAgentOrchestrator

            _spec_orch = SpecializedAgentOrchestrator()
            _spec_req = {
                "prompt": prompt,
                "name": project_id[:12],
                "type": "2d_platformer" if _spec_key == "games" else "full",
            }
            _spec_out = await _spec_orch.execute_agent(_spec_key, _spec_req)
            _code = (
                _spec_out.get("game_code")
                or _spec_out.get("firmware_code")
                or _spec_out.get("model_code")
                or _spec_out.get("contract_code")
                or _spec_out.get("solution_code")
                or str(_spec_out)
            )
            results[f"SpecializedAgent-{_spec_key.title()}"] = {
                "output": _code,
                "result": _code,
                "status": _spec_out.get("status", "ok"),
                "tokens_used": 0,
            }
        except Exception as _spec_err:
            logger.debug("Specialized agent (%s) skipped: %s", _spec_key, _spec_err)

    # --- POST-BUILD: CRITIC + TRUTH (anti-hallucination) ---
    critic_review: Optional[Dict[str, Any]] = None
    truth_report: Optional[Dict[str, Any]] = None
    truth_result: Optional[Dict[str, Any]] = None
    emit_build_event(
        project_id,
        "quality_check_started",
        message="Running quality review and truth verification…",
    )
    try:
        emit_build_event(project_id, "critic_started", message="Critic review…")
        critic_review = await _critic_agent.review_build(
            project_id=project_id,
            agent_outputs=results,
            llm_caller=_call_llm_with_fallback,
            model_chain=model_chain,
            api_keys=effective,
        )
        logger.info(
            f"Critic review: score={critic_review.get('overall_score')}, pass_rate={critic_review.get('pass_rate')}%"
        )
        await db.project_logs.insert_one(
            {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "type": "critic_review",
                "data": critic_review,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as _critic_err:
        logger.debug("Critic review failed (non-fatal): %s", _critic_err)
    try:
        emit_build_event(project_id, "truth_started", message="Truth verification…")
        truth_report = await _truth_module.verify_claims(
            agent_outputs=results,
            llm_caller=_call_llm_with_fallback,
            model_chain=model_chain,
            api_keys=effective,
            project_prompt=prompt,
        )
        logger.info(
            "Truth verification: verdict=%s, truth_score=%s",
            truth_report.get("verdict"),
            truth_report.get("truth_score"),
        )
        await db.project_logs.insert_one(
            {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "type": "truth_verification",
                "data": truth_report,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as _truth_err:
        logger.debug("Truth verification failed (non-fatal): %s", _truth_err)

    # --- Optional: standalone truth_check (adversarial code honesty) ---
    try:
        from truth_module import truth_check as truth_check_build

        async def _llm_for_truth(msg: str, sys_msg: str, sid: str, mchain) -> str:
            r, _ = await _call_llm_with_fallback(
                message=msg,
                system_message=sys_msg,
                session_id=sid,
                model_chain=mchain if isinstance(mchain, list) else model_chain,
                api_keys=effective,
            )
            return r or ""

        build_output = {
            k: coerce_text_output(v.get("output") or v.get("result") or "", limit=5000)
            for k, v in list(results.items())[:15]
        }
        truth_result = await truth_check_build(project_id, build_output, _llm_for_truth)
        await db.project_logs.insert_one(
            {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "type": "truth_check_honesty",
                "data": truth_result,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as _tc_err:
        logger.debug("truth_check (honesty) failed (non-fatal): %s", _tc_err)

    critic_score = (critic_review or {}).get("overall_score")
    truth_verdict = (truth_report or {}).get("verdict")
    truth_score = (truth_report or {}).get("truth_score")
    truth_honest_score = (
        (truth_result or {}).get("honest_score") if truth_result else None
    )

    fe = (results.get("Frontend Generation") or {}).get("output") or ""
    be = (results.get("Backend Generation") or {}).get("output") or ""
    db_schema = (results.get("Database Agent") or {}).get("output") or ""
    tests = (results.get("Test Generation") or {}).get("output") or ""
    images = (results.get("Image Generation") or {}).get("images") or {}
    videos = (results.get("Video Generation") or {}).get("videos") or {}
    quality = score_generated_code(
        frontend_code=fe, backend_code=be, database_schema=db_schema, test_code=tests
    )
    deploy_files = {}
    if build_kind == "mobile" and fe:
        # Mobile project: Expo app + native config + store submission pack
        user_doc = await db.users.find_one({"id": user_id}, {"plan": 1})
        user_plan = (user_doc or {}).get("plan") or "free"
        fe_mobile = _inject_crucibai_branding(fe, user_plan)
        deploy_files["App.js"] = fe_mobile
        # Native Config Agent -> app.json, eas.json
        native_out = (results.get("Native Config Agent") or {}).get("output") or ""
        json_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)```", native_out)
        if len(json_blocks) >= 1:
            try:
                deploy_files["app.json"] = json_blocks[0].strip()
            except Exception:
                pass
        if len(json_blocks) >= 2:
            try:
                deploy_files["eas.json"] = json_blocks[1].strip()
            except Exception:
                pass
        if "app.json" not in deploy_files:
            deploy_files["app.json"] = (
                '{"name":"App","slug":"app","version":"1.0.0","ios":{"bundleIdentifier":"com.example.app"},"android":{"package":"com.example.app"}}'
            )
        if "eas.json" not in deploy_files:
            deploy_files["eas.json"] = (
                '{"build":{"preview":{"ios":{},"android":{}},"production":{"ios":{},"android":{}}}}'
            )
        deploy_files["package.json"] = (
            '{"name":"app","version":"1.0.0","main":"node_modules/expo/AppEntry.js","scripts":{"start":"expo start","android":"expo start --android","ios":"expo start --ios"},"dependencies":{"expo":"~50.0.0","react":"18.2.0","react-native":"0.73.0"}}'
        )
        deploy_files["babel.config.js"] = (
            "module.exports = function(api) { api.cache(true); return { presets: ['babel-preset-expo'] }; };"
        )
        # Store Prep Agent -> store-submission/
        store_out = (results.get("Store Prep Agent") or {}).get("output") or ""
        deploy_files["store-submission/STORE_SUBMISSION_GUIDE.md"] = (
            store_out
            or "See Expo EAS Submit docs for Apple App Store and Google Play submission."
        )
        metadata_match = re.search(r"\{[\s\S]*?\"app_name\"[\s\S]*?\}", store_out)
        if metadata_match:
            deploy_files["store-submission/metadata.json"] = metadata_match.group(0)
    else:
        # Web project — always emit a full preview bundle (like Manus): entry + App + styles so Sandpack preview works
        if fe:
            fe = _inject_media_into_jsx(fe, images, videos)
            user_doc = await db.users.find_one({"id": user_id}, {"plan": 1})
            user_plan = (user_doc or {}).get("plan") or "free"
            fe = _inject_crucibai_branding(fe, user_plan)
            deploy_files["src/App.jsx"] = fe
            # Ensure Sandpack has an entry and styles so preview runs (Manus-like minimal runnable set)
            if "src/index.js" not in deploy_files:
                deploy_files["src/index.js"] = """import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles.css';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
"""
            if "src/styles.css" not in deploy_files:
                deploy_files[
                    "src/styles.css"
                ] = """@import url('https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css');
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: Inter, system-ui, sans-serif; }
"""
            # Full build (not minimal): package.json + index.html so export/deploy is a complete project
            if "package.json" not in deploy_files:
                deploy_files["package.json"] = """{
  "name": "crucib-app",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test"
  },
  "browserslist": { "production": [">0.2%", "not dead"], "development": ["last 1 chrome version"] }
}
"""
            if "public/index.html" not in deploy_files:
                deploy_files["public/index.html"] = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="theme-color" content="#000000" />
  <title>App</title>
</head>
<body>
  <noscript>You need to enable JavaScript to run this app.</noscript>
  <div id="root"></div>
</body>
</html>
"""
        if be:
            deploy_files["server.py"] = be
        if db_schema:
            deploy_files["schema.sql"] = db_schema
        if tests:
            deploy_files["tests/test_basic.py"] = tests
    set_payload = {
        "status": "completed",
        "tokens_used": total_used,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "live_url": None,
        "quality_score": quality,
        "orchestration_version": "v2_dag",
        "build_kind": build_kind,
    }
    if critic_score is not None:
        set_payload["critic_score"] = critic_score
    if truth_verdict is not None:
        set_payload["truth_verdict"] = truth_verdict
    if truth_score is not None:
        set_payload["truth_score"] = truth_score
    if truth_honest_score is not None:
        set_payload["truth_honest_score"] = truth_honest_score
    if images:
        set_payload["images"] = images
    if videos:
        set_payload["videos"] = videos
    if deploy_files:
        set_payload["deploy_files"] = deploy_files
    if suggest_retry_phase is not None:
        set_payload["suggest_retry_phase"] = suggest_retry_phase
        set_payload["suggest_retry_reason"] = (
            suggest_retry_reason or "Retry code generation?"
        )
    update_op = {"$set": set_payload}
    if suggest_retry_phase is None:
        update_op["$unset"] = {"suggest_retry_phase": "", "suggest_retry_reason": ""}
    await db.projects.update_one({"id": project_id}, update_op)
    # Version history (item 13): append this build to build_history for UI
    project_after = await db.projects.find_one({"id": project_id})
    if project_after is not None:
        history = list(project_after.get("build_history") or [])
        history.insert(
            0,
            {
                "completed_at": set_payload.get("completed_at"),
                "status": "completed",
                "quality_score": quality,
                "tokens_used": total_used,
            },
        )
        await db.projects.update_one(
            {"id": project_id}, {"$set": {"build_history": history[:50]}}
        )
    emit_build_event(
        project_id,
        "build_completed",
        status="completed",
        tokens=total_used,
        message="Build completed",
        deploy_files=deploy_files,
        quality_score=quality,
        critic_score=critic_score,
        truth_verdict=truth_verdict,
        truth_score=truth_score,
        truth_honest_score=truth_honest_score,
    )
    project = await db.projects.find_one({"id": project_id})
    if project and project.get("tokens_allocated"):
        refund = project["tokens_allocated"] - total_used
        if refund > 0:
            await db.users.update_one(
                {"id": user_id}, {"$inc": {"token_balance": refund}}
            )
            await db.token_ledger.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "tokens": refund,
                    "type": "refund",
                    "description": f"Unused tokens from project {project_id[:8]}",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )


# ==================== EXPORTS ROUTES ====================


@projects_router.post("/exports")
async def create_export(data: dict, user: dict = Depends(get_current_user)):
    db = get_db()
    project = await db.projects.find_one(
        {"id": data.get("project_id"), "user_id": user["id"]}
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    export_id = str(uuid.uuid4())
    export_doc = {
        "id": export_id,
        "project_id": data.get("project_id"),
        "user_id": user["id"],
        "format": data.get("format", "pdf"),
        "status": "completed",
        "download_url": f"/api/exports/{export_id}/download",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.exports.insert_one(export_doc)

    return {"export": {k: v for k, v in export_doc.items() if k != "_id"}}


@projects_router.get("/exports")
async def get_exports(user: dict = Depends(get_current_user)):
    db = get_db()
    cursor = db.exports.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1)
    exports = await cursor.to_list(MAX_EXPORTS_LIST)
    return {"exports": exports}


@projects_router.post("/build/from-reference")
async def build_from_reference(
    data: ReferenceBuildBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """Use a URL or prompt as reference for build. Fetches URL content when provided."""
    context = ""
    if data.url:
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                r = await client.get(data.url, timeout=10)
                if r.status_code == 200:
                    text = r.text[:8000]
                    context = f"Reference site content (first 8000 chars):\n{text}\n\n"
        except Exception as e:
            context = f"(Could not fetch URL: {e})\n\n"
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    prompt = f"{context}Build a React app (Tailwind) that matches or is inspired by this. User request: {data.prompt}. Respond with ONLY the complete App.js code."
    model_chain = _get_model_chain("auto", prompt, effective_keys=effective)
    response, model_used = await _call_llm_with_fallback(
        message=prompt,
        system_message="You output only valid React/JSX code. No markdown.",
        session_id=str(uuid.uuid4()),
        model_chain=model_chain,
        api_keys=effective,
    )
    code = (
        (response or "")
        .strip()
        .removeprefix("```jsx")
        .removeprefix("```js")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )
    return {"code": code, "model_used": model_used}


@projects_router.post("/projects/{project_id}/duplicate")
async def duplicate_project(
    project_id: str,
    user: dict = Depends(
        require_permission(Permission.EDIT_PROJECT if Permission else None)
    ),
):
    db = get_db()
    project = await db.projects.find_one(
        {"id": project_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    new_id = str(uuid.uuid4())
    new_project = {
        **project,
        "id": new_id,
        "name": project.get("name", "Copy") + " (copy)",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "draft",
        "completed_at": None,
        "live_url": None,
        "tokens_used": 0,
    }
    new_project.pop("_id", None)
    await db.projects.insert_one(new_project)
    return {"project": new_project}


@projects_router.post("/projects/from-template")
async def create_from_template(
    body: dict,
    user: dict = Depends(
        require_permission(Permission.CREATE_PROJECT if Permission else None)
    ),
):
    tid = body.get("template_id")
    t = next((x for x in TEMPLATES_GALLERY if x["id"] == tid), None)
    if not t:
        raise HTTPException(status_code=400, detail="Template not found")
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    model_chain = _get_model_chain("auto", t["prompt"], effective_keys=effective)
    response, _ = await _call_llm_with_fallback(
        message=t["prompt"] + "\n\nRespond with ONLY the complete App.js code.",
        system_message="Output only valid React code.",
        session_id=str(uuid.uuid4()),
        model_chain=model_chain,
        api_keys=effective,
    )
    code = (
        (response or "")
        .strip()
        .removeprefix("```jsx")
        .removeprefix("```js")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )
    return {"files": {"/App.js": code}, "template_id": tid}


@projects_router.post("/projects/{project_id}/save-as-template")
async def save_project_as_template(
    project_id: str,
    body: dict,
    user: dict = Depends(
        require_permission(Permission.EDIT_PROJECT if Permission else None)
    ),
):
    db = get_db()
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    name = body.get("name", project.get("name", "My template"))
    template_id = str(uuid.uuid4())[:8]
    await db.user_templates.insert_one(
        {
            "id": template_id,
            "user_id": user["id"],
            "project_id": project_id,
            "name": name,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return {"template_id": template_id}

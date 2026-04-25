"""Skills routes — system skills, marketplace, user skills CRUD, and activation."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["skills"])


def _get_auth():
    from ..server import get_current_user

    return get_current_user


def _get_optional_user():
    from ..server import get_optional_user

    return get_optional_user


def _get_db():
    """Return a MongoDB-compatible DB handle, or None if unavailable.
    In production (no MongoDB), returns None — callers handle this gracefully."""
    try:
        from ..deps import get_db as _deps_get_db
        return _deps_get_db()
    except Exception:
        return None


SYSTEM_SKILLS = [
    {
        "name": "web-app-builder",
        "icon": "🌐",
        "color": "#3b82f6",
        "category": "build",
        "display_name": "Web App Builder",
        "short_desc": "Full-stack React + FastAPI with auth, PostgreSQL, and REST API",
        "trigger_prompt": "Build a full-stack web app with user authentication, dashboard, and REST API",
        "is_featured": True,
        "install_count": 1284,
        "rating_avg": 4.8,
        "tags": ["react", "fastapi", "postgres", "auth"],
        "preview_url": None,
    },
    {
        "name": "mobile-app-builder",
        "icon": "📱",
        "color": "#8b5cf6",
        "category": "build",
        "display_name": "Mobile App Builder",
        "short_desc": "React Native with Expo — iOS and Android with App Store submission guide",
        "trigger_prompt": "Build a mobile app with navigation, screens, and local storage",
        "is_featured": True,
        "install_count": 847,
        "rating_avg": 4.7,
        "tags": ["react-native", "expo", "ios", "android"],
        "preview_url": None,
    },
    {
        "name": "saas-mvp-builder",
        "icon": "💳",
        "color": "#f59e0b",
        "category": "build",
        "display_name": "SaaS MVP",
        "short_desc": "Auth, Stripe billing, user dashboard, multi-tenant — launch-ready in hours",
        "trigger_prompt": "Build a SaaS MVP with Stripe billing, user auth, and admin dashboard",
        "is_featured": True,
        "install_count": 2100,
        "rating_avg": 4.9,
        "tags": ["saas", "stripe", "auth", "billing"],
        "preview_url": None,
    },
    {
        "name": "ecommerce-builder",
        "icon": "🛒",
        "color": "#10b981",
        "category": "build",
        "display_name": "E-Commerce Store",
        "short_desc": "Product catalog, cart, Stripe checkout, inventory, order management",
        "trigger_prompt": "Build an e-commerce store with product catalog, cart, and Stripe checkout",
        "is_featured": False,
        "install_count": 633,
        "rating_avg": 4.6,
        "tags": ["ecommerce", "stripe", "inventory"],
        "preview_url": None,
    },
    {
        "name": "ai-chatbot-builder",
        "icon": "🤖",
        "color": "#ec4899",
        "category": "build",
        "display_name": "AI Chatbot",
        "short_desc": "Multi-agent chat, knowledge base RAG, streaming, embeddable widget",
        "trigger_prompt": "Build an AI chatbot with multi-agent support and document knowledge base",
        "is_featured": True,
        "install_count": 1520,
        "rating_avg": 4.8,
        "tags": ["ai", "chatbot", "rag", "streaming"],
        "preview_url": None,
    },
    {
        "name": "landing-page-builder",
        "icon": "🏠",
        "color": "#06b6d4",
        "category": "build",
        "display_name": "Landing Page",
        "short_desc": "Hero, features, pricing, testimonials, FAQ, waitlist — pixel perfect",
        "trigger_prompt": "Build a landing page with hero, features grid, pricing table, and FAQ",
        "is_featured": False,
        "install_count": 980,
        "rating_avg": 4.7,
        "tags": ["landing", "marketing", "waitlist"],
        "preview_url": None,
    },
    {
        "name": "automation-builder",
        "icon": "⚡",
        "color": "#f97316",
        "category": "automate",
        "display_name": "Automation Engine",
        "short_desc": "Scheduled agents, webhooks, cron jobs, AI-powered workflow automation",
        "trigger_prompt": "Build an automation that runs daily and sends results to Slack or email",
        "is_featured": False,
        "install_count": 412,
        "rating_avg": 4.5,
        "tags": ["automation", "cron", "webhook", "workflow"],
        "preview_url": None,
    },
    {
        "name": "internal-tool-builder",
        "icon": "🛠️",
        "color": "#64748b",
        "category": "build",
        "display_name": "Internal Tool",
        "short_desc": "Admin tables, CRUD forms, approval workflows, RBAC — enterprise-ready",
        "trigger_prompt": "Build an internal admin tool with data tables, forms, and user roles",
        "is_featured": False,
        "install_count": 756,
        "rating_avg": 4.6,
        "tags": ["admin", "crud", "rbac", "internal"],
        "preview_url": None,
    },
    {
        "name": "data-dashboard-builder",
        "icon": "📊",
        "color": "#6366f1",
        "category": "build",
        "display_name": "Data Dashboard",
        "short_desc": "Interactive Recharts/D3 charts, KPI cards, date filters, CSV export",
        "trigger_prompt": "Build a data analytics dashboard with charts and KPI cards",
        "is_featured": False,
        "install_count": 891,
        "rating_avg": 4.7,
        "tags": ["charts", "analytics", "kpi", "data-viz"],
        "preview_url": None,
    },
    {
        "name": "crm-builder",
        "icon": "👥",
        "color": "#0ea5e9",
        "category": "build",
        "display_name": "CRM Builder",
        "short_desc": "Contacts, pipeline, deals, tasks, email sequences, activity log",
        "trigger_prompt": "Build a CRM with contacts, deal pipeline, and email sequences",
        "is_featured": False,
        "install_count": 344,
        "rating_avg": 4.5,
        "tags": ["crm", "pipeline", "contacts"],
        "preview_url": None,
    },
    {
        "name": "booking-builder",
        "icon": "📅",
        "color": "#84cc16",
        "category": "build",
        "display_name": "Booking System",
        "short_desc": "Calendar scheduling, availability, reminders, Stripe deposits",
        "trigger_prompt": "Build a booking system with calendar, availability management, and payments",
        "is_featured": False,
        "install_count": 298,
        "rating_avg": 4.4,
        "tags": ["booking", "calendar", "scheduling"],
        "preview_url": None,
    },
    {
        "name": "api-builder",
        "icon": "🔌",
        "color": "#ef4444",
        "category": "build",
        "display_name": "REST API Builder",
        "short_desc": "FastAPI with JWT auth, OpenAPI docs, Pydantic validation, rate limiting",
        "trigger_prompt": "Build a REST API with JWT auth, CRUD endpoints, and auto-generated docs",
        "is_featured": False,
        "install_count": 567,
        "rating_avg": 4.6,
        "tags": ["api", "fastapi", "openapi", "jwt"],
        "preview_url": None,
    },
    {
        "name": "forum-builder",
        "icon": "💬",
        "color": "#a78bfa",
        "category": "build",
        "display_name": "Forum / Community",
        "short_desc": "Posts, threads, upvotes, user profiles, moderation panel",
        "trigger_prompt": "Build a forum with posts, comments, voting, and moderation",
        "is_featured": False,
        "install_count": 189,
        "rating_avg": 4.3,
        "tags": ["forum", "community", "social"],
        "preview_url": None,
    },
    {
        "name": "custom-user-skill",
        "icon": "✨",
        "color": "#a855f7",
        "category": "custom",
        "display_name": "Custom Skill",
        "short_desc": "Define your own building patterns and AI instructions — full control",
        "trigger_prompt": "",
        "is_featured": False,
        "install_count": 0,
        "rating_avg": 0,
        "tags": ["custom"],
        "preview_url": None,
    },
]

SKILLS_DIR = os.path.join(os.path.dirname(__file__), "..", "skills")


def _load_skill_md(skill_name: str) -> str:
    """Load SKILL.md content for a system skill."""
    skill_path = os.path.join(SKILLS_DIR, skill_name, "SKILL.md")
    try:
        if os.path.exists(skill_path):
            with open(skill_path, "r", encoding="utf-8") as f:
                return f.read()
    except Exception:
        pass
    return ""


async def _get_active_skills_context(user_id: str) -> str:
    """Build skills context string for prompt injection."""
    db = _get_db()
    if db is None:
        return ""
    try:
        user_doc = await db.users.find_one({"id": user_id})
        if not user_doc:
            return ""
        active_ids = user_doc.get("active_skill_ids", [])
        if not active_ids:
            return ""
        skill_sections = []
        system_skill_map = {s["name"]: s for s in SYSTEM_SKILLS}
        for skill_id in active_ids:
            if skill_id in system_skill_map:
                md = _load_skill_md(skill_id)
                skill_meta = system_skill_map[skill_id]
                if md:
                    # Use first 1500 chars of SKILL.md to keep prompt manageable
                    summary = md[:1500].strip()
                    skill_sections.append(f"[{skill_meta['display_name']}]\n{summary}")
                else:
                    skill_sections.append(
                        f"[{skill_meta['display_name']}]\n{skill_meta['short_desc']}"
                    )
            else:
                # User-defined skill
                user_skill_doc = await db.user_skills.find_one({"id": skill_id})
                if user_skill_doc:
                    instructions = user_skill_doc.get(
                        "instructions", user_skill_doc.get("short_desc", "")
                    )
                    display_name = user_skill_doc.get("display_name", skill_id)
                    skill_sections.append(f"[{display_name}]\n{instructions[:800]}")
        if not skill_sections:
            return ""
        context = "ACTIVE SKILLS — apply these patterns:\n" + "\n\n".join(
            skill_sections
        )
        return context
    except Exception as e:
        logger.warning(f"_get_active_skills_context error: {e}")
        return ""


# ==================== SKILLS MARKETPLACE ====================


@router.get("/skills/marketplace")
async def get_marketplace_skills(user: dict = Depends(_get_optional_user())):
    """Return system skills (always public) + published user skills."""
    db = _get_db()
    published_user_skills = []
    if db is not None:
        try:
            cursor = db.user_skills.find({"public": True})
            published_user_skills = await cursor.to_list(100)
            for s in published_user_skills:
                s.pop("_id", None)
        except Exception:
            published_user_skills = []
    return {"system_skills": SYSTEM_SKILLS, "community_skills": published_user_skills}


@router.post("/skills/{skill_id}/fork")
async def fork_skill(skill_id: str, user: dict = Depends(_get_auth())):
    """Copy a skill (system or public user skill) to the current user's library."""
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    # Check if it's a system skill
    system_skill = next((s for s in SYSTEM_SKILLS if s["name"] == skill_id), None)
    if system_skill:
        new_skill = {
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "name": f"{skill_id}-fork",
            "display_name": f"{system_skill.get('display_name', skill_id)} (Fork)",
            "icon": system_skill.get("icon", "✨"),
            "color": system_skill.get("color", "#a855f7"),
            "short_desc": system_skill.get("short_desc", ""),
            "instructions": _load_skill_md(skill_id)[:8000],
            "trigger_phrases": [],
            "forked_from": skill_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.user_skills.insert_one(new_skill)
        new_skill.pop("_id", None)
        return {"status": "ok", "skill": new_skill}
    # Check public user skills
    source_skill = await db.user_skills.find_one({"id": skill_id, "public": True})
    if not source_skill:
        raise HTTPException(status_code=404, detail="Skill not found or not public")
    new_skill = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "name": f"{source_skill.get('name', skill_id)}-fork",
        "display_name": f"{source_skill.get('display_name', skill_id)} (Fork)",
        "icon": source_skill.get("icon", "✨"),
        "color": source_skill.get("color", "#a855f7"),
        "short_desc": source_skill.get("short_desc", ""),
        "instructions": source_skill.get("instructions", "")[:8000],
        "trigger_phrases": source_skill.get("trigger_phrases", []),
        "forked_from": skill_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.user_skills.insert_one(new_skill)
    new_skill.pop("_id", None)
    return {"status": "ok", "skill": new_skill}


@router.patch("/skills/{skill_id}/publish")
async def publish_skill(skill_id: str, user: dict = Depends(_get_auth())):
    """Set a user skill as public in the marketplace."""
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    result = await db.user_skills.update_one(
        {"id": skill_id, "user_id": user["id"]}, {"$set": {"public": True}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"status": "ok", "published": True}


# ==================== SKILLS ROUTES ====================


class CreateUserSkillBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    display_name: str = Field(..., min_length=1, max_length=80)
    icon: Optional[str] = Field("✨", max_length=10)
    color: Optional[str] = Field("#a855f7", max_length=20)
    short_desc: Optional[str] = Field("", max_length=200)
    instructions: Optional[str] = Field("", max_length=8000)
    trigger_phrases: Optional[list] = Field(default_factory=list)


class UpdateUserSkillBody(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=80)
    icon: Optional[str] = Field(None, max_length=10)
    color: Optional[str] = Field(None, max_length=20)
    short_desc: Optional[str] = Field(None, max_length=200)
    instructions: Optional[str] = Field(None, max_length=8000)
    trigger_phrases: Optional[list] = None


@router.get("/skills/active")
async def get_active_skills(user: dict = Depends(_get_auth())):
    """Get all active skills for the current user."""
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    user_doc = await db.users.find_one({"id": user["id"]})
    active_ids = (user_doc or {}).get("active_skill_ids", [])
    return {"active_skill_ids": active_ids}


@router.get("/skills")
async def list_skills(user: dict = Depends(_get_auth())):
    """List all skills: system skills + user's custom skills + active state."""
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    user_doc = await db.users.find_one({"id": user["id"]})
    active_ids = (user_doc or {}).get("active_skill_ids", [])
    # Fetch user's custom skills
    user_skills_cursor = db.user_skills.find({"user_id": user["id"]})
    user_skills = await user_skills_cursor.to_list(200)
    return {
        "system_skills": SYSTEM_SKILLS,
        "user_skills": user_skills,
        "active_skill_ids": active_ids,
    }


@router.get("/skills/{skill_id}")
async def get_skill(skill_id: str, user: dict = Depends(_get_auth())):
    """Get skill details including SKILL.md content."""
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    # Check system skills first
    system_skill = next((s for s in SYSTEM_SKILLS if s["name"] == skill_id), None)
    if system_skill:
        md_content = _load_skill_md(skill_id)
        return {**system_skill, "skill_md": md_content, "source": "system"}
    # Check user skills
    user_skill = await db.user_skills.find_one({"id": skill_id})
    if user_skill:
        if user_skill.get("user_id") != user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")
        return {**user_skill, "source": "user"}
    raise HTTPException(status_code=404, detail="Skill not found")


@router.post("/skills")
async def create_user_skill(
    body: CreateUserSkillBody, user: dict = Depends(_get_auth())
):
    """Create a user-defined skill."""
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    skill_id = f"user-{user['id'][:8]}-{body.name.lower().replace(' ', '-')}-{str(uuid.uuid4())[:6]}"
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": skill_id,
        "user_id": user["id"],
        "name": body.name,
        "display_name": body.display_name,
        "icon": body.icon or "✨",
        "color": body.color or "#a855f7",
        "category": "custom",
        "short_desc": body.short_desc or "",
        "instructions": body.instructions or "",
        "trigger_phrases": body.trigger_phrases or [],
        "trigger_prompt": "",
        "created_at": now,
        "updated_at": now,
    }
    await db.user_skills.insert_one(doc)
    return {"status": "created", "skill": doc}


@router.put("/skills/{skill_id}")
async def update_user_skill(
    skill_id: str, body: UpdateUserSkillBody, user: dict = Depends(_get_auth())
):
    """Update a user-defined skill."""
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    existing = await db.user_skills.find_one({"id": skill_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Skill not found")
    if existing.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.user_skills.update_one({"id": skill_id}, {"$set": updates})
    updated = await db.user_skills.find_one({"id": skill_id})
    return {"status": "updated", "skill": updated}


@router.delete("/skills/{skill_id}")
async def delete_user_skill(skill_id: str, user: dict = Depends(_get_auth())):
    """Delete a user-defined skill."""
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    existing = await db.user_skills.find_one({"id": skill_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Skill not found")
    if existing.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    await db.user_skills.delete_one({"id": skill_id})
    # Also remove from active_skill_ids
    await db.users.update_one(
        {"id": user["id"]}, {"$pull": {"active_skill_ids": skill_id}}
    )
    return {"status": "deleted"}


@router.post("/skills/{skill_id}/activate")
async def toggle_skill_active(skill_id: str, user: dict = Depends(_get_auth())):
    """Toggle a skill active/inactive for the current user."""
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    # Validate skill exists
    is_system = any(s["name"] == skill_id for s in SYSTEM_SKILLS)
    if not is_system:
        user_skill = await db.user_skills.find_one({"id": skill_id})
        if not user_skill or user_skill.get("user_id") != user["id"]:
            raise HTTPException(status_code=404, detail="Skill not found")
    user_doc = await db.users.find_one({"id": user["id"]})
    active_ids = (user_doc or {}).get("active_skill_ids", [])
    if skill_id in active_ids:
        active_ids.remove(skill_id)
        action = "deactivated"
    else:
        active_ids.append(skill_id)
        action = "activated"
    await db.users.update_one(
        {"id": user["id"]}, {"$set": {"active_skill_ids": active_ids}}
    )
    return {"status": action, "skill_id": skill_id, "active_skill_ids": active_ids}


# ───────────────────────── File-based MD skill loader ─────────────────────────
# WS-A: Drop *.md into backend/skills/ and they're live after /skills/reload.
# Orthogonal to the DB-backed skills above — these are registry objects for
# prompt-level skill selection (not stored per-user in the DB).

from ..services.skills.md_loader import get_registry as _get_md_registry  # noqa: E402


@router.get("/skills/md/list")
async def md_skills_list():
    """List file-backed skills (MD + YAML frontmatter) known to the runtime."""
    reg = _get_md_registry()
    return {
        "directory": reg.directory,
        "count": len(reg.list_all()),
        "last_loaded_at": reg.last_loaded_at,
        "skills": [s.to_public() for s in reg.list_all()],
    }


@router.post("/skills/md/reload")
async def md_skills_reload():
    """Rescan the skills directory and reload every *.md — no redeploy needed."""
    reg = _get_md_registry()
    count = reg.reload()
    return {"status": "ok", "count": count, "directory": reg.directory}


@router.get("/skills/md/{name}")
async def md_skills_get(name: str):
    """Return a single MD skill including its full body."""
    reg = _get_md_registry()
    s = reg.get(name)
    if s is None:
        raise HTTPException(status_code=404, detail=f"skill '{name}' not found")
    return s.to_full()

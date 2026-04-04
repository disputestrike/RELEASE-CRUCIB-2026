"""
CrucibAI Backend — Blueprint Modules
=====================================
All new feature modules: Personas, Knowledge/RAG, Channels, Sessions,
Trust & Safety, Tenants/RBAC, Analytics, Commerce, and Auto-DB Schema Generation.

Register with: register_blueprint_routes(app)
"""

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Query, Body, Request
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
import json
import re
import os
import secrets
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# Lazy imports from server.py — resolved at runtime to avoid circular imports
# ---------------------------------------------------------------------------

def _get_db():
    """Return the global db instance from server.py."""
    import server
    return server.db


def _get_current_user():
    """Return get_current_user dependency from server.py."""
    import server
    return server.get_current_user


def _get_optional_user():
    """Return get_optional_user dependency from server.py."""
    import server
    return server.get_optional_user


# We resolve these once at module level after server has been imported.
# But since server imports us, we use Depends with a callable wrapper.

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# ---------------------------------------------------------------------------
# Re-export dependencies so route declarations work cleanly
# ---------------------------------------------------------------------------

async def _resolve_current_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))):
    """Forward to server.get_current_user at call time."""
    import server
    return await server.get_current_user(credentials)


async def _resolve_optional_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)), request: Request = None):
    """Forward to server.get_optional_user at call time."""
    import server
    return await server.get_optional_user(credentials, request)


def get_current_user():  # noqa: used as Depends
    return _resolve_current_user


def get_optional_user():  # noqa: used as Depends
    return _resolve_optional_user


# ---------------------------------------------------------------------------
# Convenience: typed db access
# ---------------------------------------------------------------------------

def _db():
    import server
    return server.db


# Routers
personas_router = APIRouter(prefix="/api", tags=["personas"])
knowledge_router = APIRouter(prefix="/api", tags=["knowledge"])
channels_router = APIRouter(prefix="/api", tags=["channels"])
sessions_router = APIRouter(prefix="/api", tags=["sessions"])
safety_router = APIRouter(prefix="/api", tags=["trust-safety"])
workspace_router = APIRouter(prefix="/api", tags=["workspace"])
analytics_router = APIRouter(prefix="/api", tags=["analytics"])
commerce_router = APIRouter(prefix="/api", tags=["commerce"])
appdb_router = APIRouter(prefix="/api", tags=["app-db"])


# ===========================================================================
# 1. PERSONAS / STUDIO MODULE
# ===========================================================================

class PersonaCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=2048)
    description: Optional[str] = Field(None, max_length=1000)
    tone: Optional[str] = Field(None, max_length=100)
    system_prompt: Optional[str] = Field(None, max_length=8000)
    voice: Optional[str] = Field(None, max_length=100)
    language: Optional[str] = Field(None, max_length=20)
    brand_kit: Optional[Dict[str, Any]] = None


class PersonaUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=2048)
    description: Optional[str] = Field(None, max_length=1000)
    tone: Optional[str] = Field(None, max_length=100)
    system_prompt: Optional[str] = Field(None, max_length=8000)
    voice: Optional[str] = Field(None, max_length=100)
    language: Optional[str] = Field(None, max_length=20)
    brand_kit: Optional[Dict[str, Any]] = None


@personas_router.get("/personas")
async def list_personas(user: dict = Depends(_resolve_current_user)):
    """List all personas for the current user."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    personas = await db.personas.find({"user_id": user["id"]}).sort("created_at", -1).to_list(100)
    return {"personas": personas, "count": len(personas)}


@personas_router.post("/personas", status_code=201)
async def create_persona(body: PersonaCreate, user: dict = Depends(_resolve_current_user)):
    """Create a new persona."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "name": body.name,
        "avatar_url": body.avatar_url,
        "description": body.description,
        "tone": body.tone,
        "system_prompt": body.system_prompt,
        "voice": body.voice,
        "language": body.language or "en",
        "brand_kit": body.brand_kit or {},
        "is_active": False,
        "created_at": now,
        "updated_at": now,
    }
    await db.personas.insert_one(doc)
    return {"status": "created", "persona": doc}


@personas_router.get("/personas/{persona_id}")
async def get_persona(persona_id: str, user: dict = Depends(_resolve_current_user)):
    """Get a single persona."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    doc = await db.personas.find_one({"id": persona_id, "user_id": user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Persona not found")
    return doc


@personas_router.put("/personas/{persona_id}")
async def update_persona(persona_id: str, body: PersonaUpdate, user: dict = Depends(_resolve_current_user)):
    """Update a persona."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    doc = await db.personas.find_one({"id": persona_id, "user_id": user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Persona not found")
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.personas.update_one({"id": persona_id, "user_id": user["id"]}, {"$set": updates})
    updated = await db.personas.find_one({"id": persona_id, "user_id": user["id"]})
    return {"status": "updated", "persona": updated}


@personas_router.delete("/personas/{persona_id}")
async def delete_persona(persona_id: str, user: dict = Depends(_resolve_current_user)):
    """Delete a persona."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    doc = await db.personas.find_one({"id": persona_id, "user_id": user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Persona not found")
    await db.personas.delete_one({"id": persona_id, "user_id": user["id"]})
    return {"status": "deleted", "id": persona_id}


@personas_router.post("/personas/{persona_id}/activate")
async def activate_persona(persona_id: str, user: dict = Depends(_resolve_current_user)):
    """Set this persona as the active one (deactivates all others)."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    doc = await db.personas.find_one({"id": persona_id, "user_id": user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Persona not found")
    # Deactivate all user's personas
    all_personas = await db.personas.find({"user_id": user["id"]}).to_list(200)
    for p in all_personas:
        await db.personas.update_one({"id": p["id"]}, {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}})
    # Activate the target persona
    now = datetime.now(timezone.utc).isoformat()
    await db.personas.update_one({"id": persona_id, "user_id": user["id"]}, {"$set": {"is_active": True, "updated_at": now}})
    # Also store active persona ref on user record
    await db.users.update_one({"id": user["id"]}, {"$set": {"active_persona_id": persona_id, "updated_at": now}})
    activated = await db.personas.find_one({"id": persona_id, "user_id": user["id"]})
    return {"status": "activated", "persona": activated}


# ===========================================================================
# 2. KNOWLEDGE / RAG MODULE
# ===========================================================================

class KnowledgeUpload(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    source_type: Optional[str] = Field("text", max_length=50)
    metadata: Optional[Dict[str, Any]] = None


class KnowledgeURL(BaseModel):
    url: str = Field(..., min_length=5, max_length=2048)
    title: Optional[str] = Field(None, max_length=200)
    metadata: Optional[Dict[str, Any]] = None


class KnowledgeSearch(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    limit: Optional[int] = Field(10, ge=1, le=50)
    source_id: Optional[str] = None


def _chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks for storage."""
    words = text.split()
    if not words:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += chunk_size - overlap
    return chunks


@knowledge_router.get("/knowledge")
async def list_knowledge_sources(user: dict = Depends(_resolve_current_user)):
    """List all knowledge sources for the current user."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    sources = await db.knowledge_sources.find({"user_id": user["id"]}).sort("created_at", -1).to_list(200)
    return {"sources": sources, "count": len(sources)}


@knowledge_router.post("/knowledge/upload", status_code=201)
async def upload_knowledge_document(body: KnowledgeUpload, user: dict = Depends(_resolve_current_user)):
    """Upload a text document as a knowledge source."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    now = datetime.now(timezone.utc).isoformat()
    source_id = str(uuid.uuid4())
    source = {
        "id": source_id,
        "user_id": user["id"],
        "title": body.title,
        "source_type": body.source_type or "text",
        "status": "ready",
        "metadata": body.metadata or {},
        "chunk_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    await db.knowledge_sources.insert_one(source)
    # Chunk and store documents
    chunks = _chunk_text(body.content)
    doc_ids = []
    for idx, chunk in enumerate(chunks):
        doc = {
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "source_id": source_id,
            "chunk_index": idx,
            "content": chunk,
            "word_count": len(chunk.split()),
            "created_at": now,
        }
        await db.knowledge_documents.insert_one(doc)
        doc_ids.append(doc["id"])
    # Update chunk count on source
    await db.knowledge_sources.update_one(
        {"id": source_id, "user_id": user["id"]},
        {"$set": {"chunk_count": len(chunks), "updated_at": now}},
    )
    source["chunk_count"] = len(chunks)
    return {"status": "created", "source": source, "chunks": len(chunks)}


@knowledge_router.post("/knowledge/url", status_code=201)
async def ingest_knowledge_url(body: KnowledgeURL, user: dict = Depends(_resolve_current_user)):
    """Ingest a URL as a knowledge source (stored as pending for async processing)."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    now = datetime.now(timezone.utc).isoformat()
    source_id = str(uuid.uuid4())
    source = {
        "id": source_id,
        "user_id": user["id"],
        "title": body.title or body.url,
        "source_type": "url",
        "url": body.url,
        "status": "pending",
        "metadata": body.metadata or {},
        "chunk_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    await db.knowledge_sources.insert_one(source)
    return {"status": "pending", "source": source, "message": "URL queued for ingestion"}


@knowledge_router.get("/knowledge/{source_id}")
async def get_knowledge_source(source_id: str, user: dict = Depends(_resolve_current_user)):
    """Get a knowledge source and its document chunks."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    source = await db.knowledge_sources.find_one({"id": source_id, "user_id": user["id"]})
    if not source:
        raise HTTPException(status_code=404, detail="Knowledge source not found")
    docs = await db.knowledge_documents.find({"source_id": source_id, "user_id": user["id"]}).sort("chunk_index", 1).to_list(500)
    return {"source": source, "documents": docs, "chunk_count": len(docs)}


@knowledge_router.delete("/knowledge/{source_id}")
async def delete_knowledge_source(source_id: str, user: dict = Depends(_resolve_current_user)):
    """Delete a knowledge source and all its document chunks."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    source = await db.knowledge_sources.find_one({"id": source_id, "user_id": user["id"]})
    if not source:
        raise HTTPException(status_code=404, detail="Knowledge source not found")
    # Delete all chunks
    docs = await db.knowledge_documents.find({"source_id": source_id, "user_id": user["id"]}).to_list(1000)
    for doc in docs:
        await db.knowledge_documents.delete_one({"id": doc["id"]})
    await db.knowledge_sources.delete_one({"id": source_id, "user_id": user["id"]})
    return {"status": "deleted", "id": source_id, "chunks_deleted": len(docs)}


@knowledge_router.post("/knowledge/search")
async def search_knowledge(body: KnowledgeSearch, user: dict = Depends(_resolve_current_user)):
    """Semantic search across knowledge documents (MVP: keyword text match)."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    query_lower = body.query.lower()
    query_words = set(query_lower.split())
    filter_q: Dict[str, Any] = {"user_id": user["id"]}
    if body.source_id:
        filter_q["source_id"] = body.source_id
    all_docs = await db.knowledge_documents.find(filter_q).to_list(2000)
    # Score documents by keyword overlap
    scored = []
    for doc in all_docs:
        content_lower = (doc.get("content") or "").lower()
        content_words = set(content_lower.split())
        overlap = len(query_words & content_words)
        if overlap > 0:
            # Also check if query phrase appears verbatim
            phrase_bonus = 3 if query_lower in content_lower else 0
            score = overlap + phrase_bonus
            scored.append({**doc, "_score": score})
    scored.sort(key=lambda x: x["_score"], reverse=True)
    results = scored[: body.limit]
    # Strip internal score field
    for r in results:
        r.pop("_score", None)
    return {"query": body.query, "results": results, "total": len(results)}


@knowledge_router.get("/knowledge/{source_id}/documents")
async def list_knowledge_documents(
    source_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: dict = Depends(_resolve_current_user),
):
    """List all document chunks for a knowledge source."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    source = await db.knowledge_sources.find_one({"id": source_id, "user_id": user["id"]})
    if not source:
        raise HTTPException(status_code=404, detail="Knowledge source not found")
    docs = await db.knowledge_documents.find({"source_id": source_id, "user_id": user["id"]}).sort("chunk_index", 1).to_list(500)
    paged = docs[offset: offset + limit]
    return {"source_id": source_id, "documents": paged, "total": len(docs), "limit": limit, "offset": offset}


# ===========================================================================
# 3. CHANNELS MODULE
# ===========================================================================

VALID_CHANNEL_TYPES = {"web_widget", "slack", "whatsapp", "api"}


class ChannelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., description="web_widget | slack | whatsapp | api")
    config: Optional[Dict[str, Any]] = None


class ChannelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


def _generate_embed_code(channel: dict) -> str:
    """Generate HTML embed snippet for a web widget channel."""
    channel_id = channel.get("id", "")
    name = channel.get("name", "CrucibAI Widget")
    backend_url = os.environ.get("BACKEND_URL", "https://api.crucibai.com")
    return (
        f'<!-- CrucibAI Web Widget: {name} -->\n'
        f'<script\n'
        f'  src="{backend_url}/widget.js"\n'
        f'  data-channel-id="{channel_id}"\n'
        f'  data-name="{name}"\n'
        f'  async\n'
        f'></script>\n'
        f'<!-- End CrucibAI Widget -->'
    )


@channels_router.get("/channels")
async def list_channels(user: dict = Depends(_resolve_current_user)):
    """List all channels for the current user."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    channels = await db.channels.find({"user_id": user["id"]}).sort("created_at", -1).to_list(200)
    return {"channels": channels, "count": len(channels)}


@channels_router.post("/channels", status_code=201)
async def create_channel(body: ChannelCreate, user: dict = Depends(_resolve_current_user)):
    """Create a new channel."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    if body.type not in VALID_CHANNEL_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid channel type. Must be one of: {', '.join(VALID_CHANNEL_TYPES)}")
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "name": body.name,
        "type": body.type,
        "config": body.config or {},
        "is_active": True,
        "api_key": secrets.token_urlsafe(32),
        "created_at": now,
        "updated_at": now,
    }
    await db.channels.insert_one(doc)
    return {"status": "created", "channel": doc}


@channels_router.get("/channels/{channel_id}")
async def get_channel(channel_id: str, user: dict = Depends(_resolve_current_user)):
    """Get a channel with its embed code (if web_widget)."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    doc = await db.channels.find_one({"id": channel_id, "user_id": user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Channel not found")
    embed_code = None
    if doc.get("type") == "web_widget":
        embed_code = _generate_embed_code(doc)
    return {"channel": doc, "embed_code": embed_code}


@channels_router.put("/channels/{channel_id}")
async def update_channel(channel_id: str, body: ChannelUpdate, user: dict = Depends(_resolve_current_user)):
    """Update a channel."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    doc = await db.channels.find_one({"id": channel_id, "user_id": user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Channel not found")
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.channels.update_one({"id": channel_id, "user_id": user["id"]}, {"$set": updates})
    updated = await db.channels.find_one({"id": channel_id, "user_id": user["id"]})
    return {"status": "updated", "channel": updated}


@channels_router.delete("/channels/{channel_id}")
async def delete_channel(channel_id: str, user: dict = Depends(_resolve_current_user)):
    """Delete a channel."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    doc = await db.channels.find_one({"id": channel_id, "user_id": user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Channel not found")
    await db.channels.delete_one({"id": channel_id, "user_id": user["id"]})
    return {"status": "deleted", "id": channel_id}


@channels_router.post("/channels/{channel_id}/test")
async def test_channel(channel_id: str, user: dict = Depends(_resolve_current_user)):
    """Test the connection for a channel."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    doc = await db.channels.find_one({"id": channel_id, "user_id": user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Channel not found")
    channel_type = doc.get("type", "")
    if channel_type == "web_widget":
        result = {"ok": True, "message": "Web widget channel is active and ready."}
    elif channel_type == "api":
        result = {"ok": True, "message": "API channel is reachable."}
    elif channel_type == "slack":
        webhook = (doc.get("config") or {}).get("webhook_url")
        if not webhook:
            result = {"ok": False, "message": "No Slack webhook_url configured."}
        else:
            result = {"ok": True, "message": "Slack webhook URL is configured. Test message not sent in MVP."}
    elif channel_type == "whatsapp":
        phone = (doc.get("config") or {}).get("phone_number_id")
        if not phone:
            result = {"ok": False, "message": "No WhatsApp phone_number_id configured."}
        else:
            result = {"ok": True, "message": "WhatsApp channel is configured. Test message not sent in MVP."}
    else:
        result = {"ok": False, "message": "Unknown channel type."}
    return {"channel_id": channel_id, "type": channel_type, **result}


@channels_router.get("/channels/{channel_id}/embed-code")
async def get_embed_code(channel_id: str, user: dict = Depends(_resolve_current_user)):
    """Get the HTML embed snippet for a web widget channel."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    doc = await db.channels.find_one({"id": channel_id, "user_id": user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Channel not found")
    if doc.get("type") != "web_widget":
        raise HTTPException(status_code=400, detail="Embed code is only available for web_widget channels")
    embed_code = _generate_embed_code(doc)
    return {"channel_id": channel_id, "embed_code": embed_code}


# ===========================================================================
# 4. SESSIONS MODULE
# ===========================================================================

VALID_SESSION_STATUSES = {"active", "ended", "archived"}


class SessionCreate(BaseModel):
    channel_id: Optional[str] = None
    user_identifier: Optional[str] = Field(None, max_length=200)
    metadata: Optional[Dict[str, Any]] = None


class SessionPatch(BaseModel):
    status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MessageAdd(BaseModel):
    role: str = Field(..., description="user | assistant | system")
    content: str = Field(..., min_length=1)
    metadata: Optional[Dict[str, Any]] = None


@sessions_router.get("/sessions/stats")
async def get_session_stats(
    period: str = Query("7d", description="7d | 30d | all"),
    user: dict = Depends(_resolve_current_user),
):
    """Aggregate session stats for the current user."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    now = datetime.now(timezone.utc)
    if period == "7d":
        cutoff = (now - timedelta(days=7)).isoformat()
    elif period == "30d":
        cutoff = (now - timedelta(days=30)).isoformat()
    else:
        cutoff = None
    all_sessions = await db.app_sessions.find({"user_id": user["id"]}).to_list(10000)
    if cutoff:
        all_sessions = [s for s in all_sessions if (s.get("created_at") or "") >= cutoff]
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    total = len(all_sessions)
    active = sum(1 for s in all_sessions if s.get("status") == "active")
    ended_today = sum(1 for s in all_sessions if s.get("status") == "ended" and (s.get("ended_at") or "") >= today_start)
    # Avg duration in seconds
    durations = []
    for s in all_sessions:
        if s.get("ended_at") and s.get("created_at"):
            try:
                start = datetime.fromisoformat(s["created_at"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(s["ended_at"].replace("Z", "+00:00"))
                durations.append((end - start).total_seconds())
            except Exception:
                pass
    avg_duration = round(sum(durations) / len(durations), 1) if durations else 0
    return {
        "period": period,
        "total": total,
        "active": active,
        "ended_today": ended_today,
        "avg_duration_seconds": avg_duration,
    }


@sessions_router.get("/sessions")
async def list_sessions(
    status: Optional[str] = Query(None),
    channel_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: dict = Depends(_resolve_current_user),
):
    """List sessions with optional filters (paginated)."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    query: Dict[str, Any] = {"user_id": user["id"]}
    if status:
        query["status"] = status
    if channel_id:
        query["channel_id"] = channel_id
    all_sessions = await db.app_sessions.find(query).sort("created_at", -1).to_list(10000)
    paged = all_sessions[offset: offset + limit]
    return {"sessions": paged, "total": len(all_sessions), "limit": limit, "offset": offset}


@sessions_router.post("/sessions", status_code=201)
async def create_session(body: SessionCreate, user: dict = Depends(_resolve_current_user)):
    """Create a new session."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "channel_id": body.channel_id,
        "user_identifier": body.user_identifier,
        "status": "active",
        "metadata": body.metadata or {},
        "message_count": 0,
        "created_at": now,
        "updated_at": now,
        "ended_at": None,
    }
    await db.app_sessions.insert_one(doc)
    return {"status": "created", "session": doc}


@sessions_router.get("/sessions/{session_id}")
async def get_session(session_id: str, user: dict = Depends(_resolve_current_user)):
    """Get a session with its messages."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    session = await db.app_sessions.find_one({"id": session_id, "user_id": user["id"]})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = await db.session_messages.find({"session_id": session_id}).sort("created_at", 1).to_list(500)
    return {"session": session, "messages": messages}


@sessions_router.get("/sessions/{session_id}/transcript")
async def get_session_transcript(session_id: str, user: dict = Depends(_resolve_current_user)):
    """Get the full plain-text transcript for a session."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    session = await db.app_sessions.find_one({"id": session_id, "user_id": user["id"]})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = await db.session_messages.find({"session_id": session_id}).sort("created_at", 1).to_list(500)
    lines = []
    for m in messages:
        role = (m.get("role") or "unknown").upper()
        content = m.get("content") or ""
        ts = m.get("created_at", "")
        lines.append(f"[{ts}] {role}: {content}")
    transcript = "\n".join(lines)
    return {
        "session_id": session_id,
        "transcript": transcript,
        "message_count": len(messages),
        "created_at": session.get("created_at"),
    }


@sessions_router.patch("/sessions/{session_id}")
async def patch_session(session_id: str, body: SessionPatch, user: dict = Depends(_resolve_current_user)):
    """Update session status or metadata."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    session = await db.app_sessions.find_one({"id": session_id, "user_id": user["id"]})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if body.status and body.status not in VALID_SESSION_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(VALID_SESSION_STATUSES)}")
    now = datetime.now(timezone.utc).isoformat()
    updates: Dict[str, Any] = {"updated_at": now}
    if body.status:
        updates["status"] = body.status
        if body.status == "ended":
            updates["ended_at"] = now
    if body.metadata is not None:
        updates["metadata"] = body.metadata
    await db.app_sessions.update_one({"id": session_id, "user_id": user["id"]}, {"$set": updates})
    updated = await db.app_sessions.find_one({"id": session_id, "user_id": user["id"]})
    return {"status": "updated", "session": updated}


@sessions_router.post("/sessions/{session_id}/messages", status_code=201)
async def add_session_message(
    session_id: str,
    body: MessageAdd,
    user: dict = Depends(_resolve_optional_user),
):
    """Add a message to a session (accepts authenticated or anonymous callers)."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    # Verify session exists — allow by session_id alone if no user (public widget)
    if user:
        session = await db.app_sessions.find_one({"id": session_id, "user_id": user["id"]})
    else:
        session = await db.app_sessions.find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.get("status") == "ended":
        raise HTTPException(status_code=400, detail="Cannot add messages to an ended session")
    now = datetime.now(timezone.utc).isoformat()
    msg = {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "role": body.role,
        "content": body.content,
        "metadata": body.metadata or {},
        "created_at": now,
    }
    await db.session_messages.insert_one(msg)
    # Increment message count on session
    owner_id = session.get("user_id")
    await db.app_sessions.update_one(
        {"id": session_id},
        {"$set": {"message_count": session.get("message_count", 0) + 1, "updated_at": now}},
    )
    return {"status": "created", "message": msg}


# ===========================================================================
# 5. TRUST & SAFETY MODULE
# ===========================================================================

PROFANITY_WORDS = {
    "badword1", "badword2",  # placeholder; extend with real list in production
}

CLAIM_TYPES = {"approved", "blocked"}


class SafetyPoliciesUpdate(BaseModel):
    block_profanity: Optional[bool] = None
    require_disclosure: Optional[bool] = None
    blocked_topics: Optional[List[str]] = None
    allowed_topics: Optional[List[str]] = None


class ClaimCreate(BaseModel):
    claim: str = Field(..., min_length=1, max_length=500)
    type: str = Field(..., description="approved | blocked")
    reason: Optional[str] = Field(None, max_length=500)


class ModerateText(BaseModel):
    text: str = Field(..., min_length=1)
    session_id: Optional[str] = None


@safety_router.get("/safety/policies")
async def get_safety_policies(user: dict = Depends(_resolve_current_user)):
    """Get the safety policies for the current user."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    policy = await db.safety_policies.find_one({"user_id": user["id"]})
    if not policy:
        # Return defaults
        policy = {
            "user_id": user["id"],
            "block_profanity": True,
            "require_disclosure": True,
            "blocked_topics": [],
            "allowed_topics": [],
        }
    return {"policies": policy}


@safety_router.put("/safety/policies")
async def update_safety_policies(body: SafetyPoliciesUpdate, user: dict = Depends(_resolve_current_user)):
    """Update safety policies for the current user."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    existing = await db.safety_policies.find_one({"user_id": user["id"]})
    now = datetime.now(timezone.utc).isoformat()
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    updates["updated_at"] = now
    if not existing:
        doc = {
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "block_profanity": True,
            "require_disclosure": True,
            "blocked_topics": [],
            "allowed_topics": [],
            "created_at": now,
            **updates,
        }
        await db.safety_policies.insert_one(doc)
    else:
        await db.safety_policies.update_one({"user_id": user["id"]}, {"$set": updates})
    policy = await db.safety_policies.find_one({"user_id": user["id"]})
    return {"status": "updated", "policies": policy}


@safety_router.get("/safety/claims")
async def list_claims(user: dict = Depends(_resolve_current_user)):
    """List all claims ledger entries for the current user."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    claims = await db.claims_ledger.find({"user_id": user["id"]}).sort("created_at", -1).to_list(500)
    return {"claims": claims, "count": len(claims)}


@safety_router.post("/safety/claims", status_code=201)
async def add_claim(body: ClaimCreate, user: dict = Depends(_resolve_current_user)):
    """Add a claim to the ledger."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    if body.type not in CLAIM_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid claim type. Must be one of: {', '.join(CLAIM_TYPES)}")
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "claim": body.claim,
        "type": body.type,
        "reason": body.reason,
        "created_at": now,
    }
    await db.claims_ledger.insert_one(doc)
    return {"status": "created", "claim": doc}


@safety_router.delete("/safety/claims/{claim_id}")
async def delete_claim(claim_id: str, user: dict = Depends(_resolve_current_user)):
    """Remove a claim from the ledger."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    doc = await db.claims_ledger.find_one({"id": claim_id, "user_id": user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Claim not found")
    await db.claims_ledger.delete_one({"id": claim_id, "user_id": user["id"]})
    return {"status": "deleted", "id": claim_id}


@safety_router.post("/safety/moderate")
async def moderate_text(body: ModerateText, user: dict = Depends(_resolve_current_user)):
    """Check text against the user's safety policies. Returns {safe, flags, score}."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    policy_doc = await db.safety_policies.find_one({"user_id": user["id"]})
    policy = policy_doc or {}
    block_profanity = policy.get("block_profanity", True)
    blocked_topics = [t.lower() for t in (policy.get("blocked_topics") or [])]
    allowed_topics = [t.lower() for t in (policy.get("allowed_topics") or [])]
    # Load approved/blocked claims
    claims = await db.claims_ledger.find({"user_id": user["id"]}).to_list(500)
    blocked_claims = {c["claim"].lower() for c in claims if c.get("type") == "blocked"}
    text_lower = body.text.lower()
    flags = []
    score = 0.0
    # Profanity check
    if block_profanity:
        words = set(re.findall(r'\b\w+\b', text_lower))
        hit_words = words & PROFANITY_WORDS
        if hit_words:
            flags.append({"type": "profanity", "matches": list(hit_words)})
            score += 0.5
    # Blocked topics
    for topic in blocked_topics:
        if topic in text_lower:
            flags.append({"type": "blocked_topic", "topic": topic})
            score += 0.3
    # Blocked claims
    for claim in blocked_claims:
        if claim in text_lower:
            flags.append({"type": "blocked_claim", "claim": claim})
            score += 0.4
    # Allowed topics override
    allowed_hit = any(t in text_lower for t in allowed_topics) if allowed_topics else False
    safe = len(flags) == 0 or allowed_hit
    score = min(round(score, 2), 1.0)
    # Log to audit
    now = datetime.now(timezone.utc).isoformat()
    audit_doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "session_id": body.session_id,
        "text_snippet": body.text[:200],
        "safe": safe,
        "flags": flags,
        "score": score,
        "created_at": now,
    }
    await db.safety_audit_log.insert_one(audit_doc)
    return {"safe": safe, "flags": flags, "score": score}


@safety_router.get("/safety/audit")
async def get_safety_audit(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: dict = Depends(_resolve_current_user),
):
    """Get moderation audit log for the current user."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    all_entries = await db.safety_audit_log.find({"user_id": user["id"]}).sort("created_at", -1).to_list(5000)
    paged = all_entries[offset: offset + limit]
    return {"audit": paged, "total": len(all_entries), "limit": limit, "offset": offset}


# ===========================================================================
# 6. TENANTS / WORKSPACE / RBAC
# ===========================================================================

VALID_ROLES = {"owner", "admin", "editor", "viewer"}


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class InviteMember(BaseModel):
    email: EmailStr
    role: str = Field("viewer", description="owner | admin | editor | viewer")


class UpdateMemberRole(BaseModel):
    role: str = Field(..., description="owner | admin | editor | viewer")


@workspace_router.get("/workspace")
async def get_workspace(user: dict = Depends(_resolve_current_user)):
    """Get the current user's workspace/tenant."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    # Find tenant where user is a member
    member = await db.tenant_members.find_one({"user_id": user["id"]})
    if not member:
        return {"workspace": None, "message": "No workspace found. Create one first."}
    tenant = await db.tenants.find_one({"id": member["tenant_id"]})
    if not tenant:
        return {"workspace": None, "message": "Workspace not found."}
    return {"workspace": tenant, "role": member.get("role")}


@workspace_router.post("/workspace", status_code=201)
async def create_workspace(body: WorkspaceCreate, user: dict = Depends(_resolve_current_user)):
    """Create a new workspace for the current user."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    now = datetime.now(timezone.utc).isoformat()
    tenant_id = str(uuid.uuid4())
    tenant = {
        "id": tenant_id,
        "name": body.name,
        "description": body.description,
        "owner_id": user["id"],
        "created_at": now,
        "updated_at": now,
    }
    await db.tenants.insert_one(tenant)
    # Add creator as owner
    member = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "user_id": user["id"],
        "email": user.get("email", ""),
        "role": "owner",
        "created_at": now,
    }
    await db.tenant_members.insert_one(member)
    return {"status": "created", "workspace": tenant, "role": "owner"}


@workspace_router.get("/workspace/members")
async def list_workspace_members(user: dict = Depends(_resolve_current_user)):
    """List all members of the current user's workspace."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    member_self = await db.tenant_members.find_one({"user_id": user["id"]})
    if not member_self:
        raise HTTPException(status_code=404, detail="Workspace not found")
    members = await db.tenant_members.find({"tenant_id": member_self["tenant_id"]}).to_list(200)
    return {"members": members, "count": len(members)}


@workspace_router.post("/workspace/members/invite", status_code=201)
async def invite_member(body: InviteMember, user: dict = Depends(_resolve_current_user)):
    """Invite a member to the workspace by email."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")
    member_self = await db.tenant_members.find_one({"user_id": user["id"]})
    if not member_self:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if member_self.get("role") not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Only owners and admins can invite members")
    tenant_id = member_self["tenant_id"]
    now = datetime.now(timezone.utc).isoformat()
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    invite = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "invited_by": user["id"],
        "email": body.email,
        "role": body.role,
        "token": token,
        "status": "pending",
        "expires_at": expires_at,
        "created_at": now,
    }
    await db.workspace_invitations.insert_one(invite)
    return {
        "status": "invited",
        "invite": invite,
        "accept_url": f"/workspace/invitations/{token}/accept",
    }


@workspace_router.delete("/workspace/members/{target_user_id}")
async def remove_member(target_user_id: str, user: dict = Depends(_resolve_current_user)):
    """Remove a member from the workspace."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    member_self = await db.tenant_members.find_one({"user_id": user["id"]})
    if not member_self:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if member_self.get("role") not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Only owners and admins can remove members")
    if target_user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot remove yourself from the workspace")
    target = await db.tenant_members.find_one({"user_id": target_user_id, "tenant_id": member_self["tenant_id"]})
    if not target:
        raise HTTPException(status_code=404, detail="Member not found in workspace")
    await db.tenant_members.delete_one({"user_id": target_user_id, "tenant_id": member_self["tenant_id"]})
    return {"status": "removed", "user_id": target_user_id}


@workspace_router.patch("/workspace/members/{target_user_id}")
async def update_member_role(target_user_id: str, body: UpdateMemberRole, user: dict = Depends(_resolve_current_user)):
    """Update a member's role."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")
    member_self = await db.tenant_members.find_one({"user_id": user["id"]})
    if not member_self:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if member_self.get("role") not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Only owners and admins can change roles")
    target = await db.tenant_members.find_one({"user_id": target_user_id, "tenant_id": member_self["tenant_id"]})
    if not target:
        raise HTTPException(status_code=404, detail="Member not found in workspace")
    now = datetime.now(timezone.utc).isoformat()
    await db.tenant_members.update_one(
        {"user_id": target_user_id, "tenant_id": member_self["tenant_id"]},
        {"$set": {"role": body.role, "updated_at": now}},
    )
    updated = await db.tenant_members.find_one({"user_id": target_user_id, "tenant_id": member_self["tenant_id"]})
    return {"status": "updated", "member": updated}


@workspace_router.get("/workspace/invitations")
async def list_invitations(user: dict = Depends(_resolve_current_user)):
    """List pending invitations for the current user's workspace."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    member_self = await db.tenant_members.find_one({"user_id": user["id"]})
    if not member_self:
        raise HTTPException(status_code=404, detail="Workspace not found")
    invites = await db.workspace_invitations.find(
        {"tenant_id": member_self["tenant_id"], "status": "pending"}
    ).sort("created_at", -1).to_list(200)
    return {"invitations": invites, "count": len(invites)}


@workspace_router.post("/workspace/invitations/{token}/accept")
async def accept_invitation(token: str, user: dict = Depends(_resolve_current_user)):
    """Accept a workspace invitation by token."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    invite = await db.workspace_invitations.find_one({"token": token, "status": "pending"})
    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found or already used")
    # Check not expired
    now = datetime.now(timezone.utc)
    expires_at_str = invite.get("expires_at", "")
    try:
        expires_dt = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        if now > expires_dt:
            raise HTTPException(status_code=400, detail="Invitation has expired")
    except ValueError:
        pass
    now_iso = now.isoformat()
    # Add user as member
    existing_member = await db.tenant_members.find_one({"user_id": user["id"], "tenant_id": invite["tenant_id"]})
    if existing_member:
        raise HTTPException(status_code=400, detail="You are already a member of this workspace")
    member = {
        "id": str(uuid.uuid4()),
        "tenant_id": invite["tenant_id"],
        "user_id": user["id"],
        "email": user.get("email", invite.get("email", "")),
        "role": invite["role"],
        "created_at": now_iso,
    }
    await db.tenant_members.insert_one(member)
    # Mark invite as accepted
    await db.workspace_invitations.update_one(
        {"token": token}, {"$set": {"status": "accepted", "accepted_at": now_iso, "accepted_by": user["id"]}}
    )
    tenant = await db.tenants.find_one({"id": invite["tenant_id"]})
    return {"status": "accepted", "workspace": tenant, "role": invite["role"]}


# ===========================================================================
# 7. ANALYTICS EVENTS
# ===========================================================================

class AnalyticsEvent(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=100)
    properties: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None


@analytics_router.post("/analytics/event", status_code=201)
async def track_event(
    body: AnalyticsEvent,
    request: Request,
    user: dict = Depends(_resolve_optional_user),
):
    """Track an analytics event. Accepts authenticated or anonymous callers."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    now = datetime.now(timezone.utc).isoformat()
    user_id = user["id"] if user else "anonymous"
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "event_type": body.event_type,
        "properties": body.properties or {},
        "session_id": body.session_id,
        "ip": request.client.host if request.client else None,
        "created_at": now,
    }
    await db.analytics_events.insert_one(doc)
    return {"status": "tracked", "id": doc["id"]}


@analytics_router.get("/analytics/summary")
async def get_analytics_summary(
    period: str = Query("7d", description="7d | 30d | all"),
    user: dict = Depends(_resolve_current_user),
):
    """Get analytics summary for the current user."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    now = datetime.now(timezone.utc)
    if period == "7d":
        cutoff = (now - timedelta(days=7)).isoformat()
    elif period == "30d":
        cutoff = (now - timedelta(days=30)).isoformat()
    else:
        cutoff = None
    def apply_cutoff(items):
        if cutoff:
            return [i for i in items if (i.get("created_at") or "") >= cutoff]
        return items
    all_tasks = await db.tasks.find({"user_id": user["id"]}).to_list(10000)
    all_sessions = await db.app_sessions.find({"user_id": user["id"]}).to_list(10000)
    all_events = await db.analytics_events.find({"user_id": user["id"]}).to_list(10000)
    tasks = apply_cutoff(all_tasks)
    sessions = apply_cutoff(all_sessions)
    events = apply_cutoff(all_events)
    # Count messages across sessions in period
    total_messages = sum(s.get("message_count", 0) for s in sessions)
    return {
        "period": period,
        "total_builds": len(tasks),
        "total_sessions": len(sessions),
        "total_messages": total_messages,
        "total_events": len(events),
    }


@analytics_router.get("/analytics/builds")
async def get_build_analytics(
    period: str = Query("30d"),
    user: dict = Depends(_resolve_current_user),
):
    """Build analytics: builds per day, build kinds, success rate."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    now = datetime.now(timezone.utc)
    days = 30 if period == "30d" else 7 if period == "7d" else 365
    cutoff = (now - timedelta(days=days)).isoformat()
    tasks = await db.tasks.find({"user_id": user["id"]}).to_list(10000)
    tasks = [t for t in tasks if (t.get("created_at") or "") >= cutoff]
    # Builds per day
    builds_per_day: Dict[str, int] = {}
    kind_counts: Dict[str, int] = {}
    success_count = 0
    for task in tasks:
        day = (task.get("created_at") or "")[:10]
        builds_per_day[day] = builds_per_day.get(day, 0) + 1
        kind = task.get("build_kind", "fullstack")
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
        if task.get("status") in ("complete", "completed"):
            success_count += 1
    total = len(tasks)
    success_rate = round(success_count / total, 3) if total > 0 else 0.0
    return {
        "period": period,
        "total_builds": total,
        "builds_per_day": [{"date": d, "count": c} for d, c in sorted(builds_per_day.items())],
        "build_kinds": [{"kind": k, "count": c} for k, c in kind_counts.items()],
        "success_rate": success_rate,
    }


@analytics_router.get("/analytics/sessions")
async def get_session_analytics(
    period: str = Query("30d"),
    user: dict = Depends(_resolve_current_user),
):
    """Session analytics: sessions per day, avg duration, channels breakdown."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    now = datetime.now(timezone.utc)
    days = 30 if period == "30d" else 7 if period == "7d" else 365
    cutoff = (now - timedelta(days=days)).isoformat()
    sessions = await db.app_sessions.find({"user_id": user["id"]}).to_list(10000)
    sessions = [s for s in sessions if (s.get("created_at") or "") >= cutoff]
    sessions_per_day: Dict[str, int] = {}
    channel_counts: Dict[str, int] = {}
    durations = []
    for s in sessions:
        day = (s.get("created_at") or "")[:10]
        sessions_per_day[day] = sessions_per_day.get(day, 0) + 1
        ch = s.get("channel_id") or "direct"
        channel_counts[ch] = channel_counts.get(ch, 0) + 1
        if s.get("ended_at") and s.get("created_at"):
            try:
                start = datetime.fromisoformat(s["created_at"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(s["ended_at"].replace("Z", "+00:00"))
                durations.append((end - start).total_seconds())
            except Exception:
                pass
    avg_duration = round(sum(durations) / len(durations), 1) if durations else 0
    return {
        "period": period,
        "total_sessions": len(sessions),
        "sessions_per_day": [{"date": d, "count": c} for d, c in sorted(sessions_per_day.items())],
        "avg_duration_seconds": avg_duration,
        "channels_breakdown": [{"channel_id": k, "count": v} for k, v in channel_counts.items()],
    }


@analytics_router.get("/analytics/funnel")
async def get_funnel_analytics(user: dict = Depends(_resolve_current_user)):
    """Funnel data: visits, signups, first_build, repeat_builds."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    events = await db.analytics_events.find({"user_id": user["id"]}).to_list(10000)
    visits = sum(1 for e in events if e.get("event_type") in ("page_view", "visit"))
    signups = sum(1 for e in events if e.get("event_type") in ("signup", "register"))
    tasks = await db.tasks.find({"user_id": user["id"]}).to_list(10000)
    first_build = 1 if tasks else 0
    repeat_builds = max(0, len(tasks) - 1)
    return {
        "visits": visits,
        "signups": signups,
        "first_build": first_build,
        "repeat_builds": repeat_builds,
        "total_builds": len(tasks),
    }


# ===========================================================================
# 8. COMMERCE / PRODUCTS
# ===========================================================================

VALID_PRODUCT_TYPES = {"one_time", "subscription"}
VALID_CURRENCIES = {"usd", "eur", "gbp", "cad", "aud"}


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price: float = Field(..., ge=0)
    currency: str = Field("usd", max_length=10)
    type: str = Field("one_time", description="one_time | subscription")
    metadata: Optional[Dict[str, Any]] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=10)
    metadata: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class CheckoutCreate(BaseModel):
    product_id: str
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None
    quantity: Optional[int] = Field(1, ge=1)


@commerce_router.get("/commerce/products")
async def list_products(user: dict = Depends(_resolve_current_user)):
    """List all products for the current user."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    products = await db.products.find({"user_id": user["id"]}).sort("created_at", -1).to_list(200)
    return {"products": products, "count": len(products)}


@commerce_router.post("/commerce/products", status_code=201)
async def create_product(body: ProductCreate, user: dict = Depends(_resolve_current_user)):
    """Create a new product."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    if body.type not in VALID_PRODUCT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid product type. Must be one of: {', '.join(VALID_PRODUCT_TYPES)}")
    currency = body.currency.lower()
    if currency not in VALID_CURRENCIES:
        raise HTTPException(status_code=400, detail=f"Invalid currency. Supported: {', '.join(VALID_CURRENCIES)}")
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "name": body.name,
        "description": body.description,
        "price": body.price,
        "currency": currency,
        "type": body.type,
        "is_active": True,
        "metadata": body.metadata or {},
        "stripe_product_id": None,
        "stripe_price_id": None,
        "created_at": now,
        "updated_at": now,
    }
    await db.products.insert_one(doc)
    return {"status": "created", "product": doc}


@commerce_router.put("/commerce/products/{product_id}")
async def update_product(product_id: str, body: ProductUpdate, user: dict = Depends(_resolve_current_user)):
    """Update a product."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    doc = await db.products.find_one({"id": product_id, "user_id": user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if "currency" in updates:
        updates["currency"] = updates["currency"].lower()
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.products.update_one({"id": product_id, "user_id": user["id"]}, {"$set": updates})
    updated = await db.products.find_one({"id": product_id, "user_id": user["id"]})
    return {"status": "updated", "product": updated}


@commerce_router.delete("/commerce/products/{product_id}")
async def delete_product(product_id: str, user: dict = Depends(_resolve_current_user)):
    """Delete a product."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    doc = await db.products.find_one({"id": product_id, "user_id": user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    await db.products.delete_one({"id": product_id, "user_id": user["id"]})
    return {"status": "deleted", "id": product_id}


@commerce_router.get("/commerce/orders")
async def list_orders(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: dict = Depends(_resolve_current_user),
):
    """List orders for the current user."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    all_orders = await db.orders.find({"user_id": user["id"]}).sort("created_at", -1).to_list(10000)
    paged = all_orders[offset: offset + limit]
    return {"orders": paged, "total": len(all_orders), "limit": limit, "offset": offset}


@commerce_router.get("/commerce/orders/{order_id}")
async def get_order(order_id: str, user: dict = Depends(_resolve_current_user)):
    """Get a single order."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    order = await db.orders.find_one({"id": order_id, "user_id": user["id"]})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@commerce_router.post("/commerce/checkout")
async def create_checkout(body: CheckoutCreate, request: Request, user: dict = Depends(_resolve_current_user)):
    """Create a Stripe checkout session for a product."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    product = await db.products.find_one({"id": body.product_id, "user_id": user["id"]})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if not product.get("is_active", True):
        raise HTTPException(status_code=400, detail="Product is not active")
    stripe_secret = os.environ.get("STRIPE_SECRET_KEY")
    if not stripe_secret:
        raise HTTPException(status_code=503, detail="Stripe is not configured")
    try:
        import stripe
        stripe.api_key = stripe_secret
        frontend_url = os.environ.get("FRONTEND_URL", str(request.base_url)).rstrip("/")
        success_url = body.success_url or f"{frontend_url}/commerce/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = body.cancel_url or f"{frontend_url}/commerce/cancel"
        # Create or reuse Stripe price
        stripe_price_id = product.get("stripe_price_id")
        if not stripe_price_id:
            # Create Stripe product + price on the fly
            sp = stripe.Product.create(
                name=product["name"],
                description=product.get("description") or "",
                metadata={"crucibai_product_id": product["id"], "user_id": user["id"]},
            )
            price_kwargs: Dict[str, Any] = {
                "unit_amount": int(product["price"] * 100),
                "currency": product["currency"],
                "product": sp["id"],
            }
            if product.get("type") == "subscription":
                price_kwargs["recurring"] = {"interval": "month"}
            sp_price = stripe.Price.create(**price_kwargs)
            stripe_price_id = sp_price["id"]
            now = datetime.now(timezone.utc).isoformat()
            await db.products.update_one(
                {"id": product["id"]},
                {"$set": {"stripe_product_id": sp["id"], "stripe_price_id": stripe_price_id, "updated_at": now}},
            )
        mode = "subscription" if product.get("type") == "subscription" else "payment"
        checkout_session = stripe.checkout.Session.create(
            line_items=[{"price": stripe_price_id, "quantity": body.quantity or 1}],
            mode=mode,
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=user["id"],
            metadata={"product_id": product["id"]},
            customer_email=user.get("email"),
        )
        # Create a pending order record
        now = datetime.now(timezone.utc).isoformat()
        order = {
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "product_id": product["id"],
            "stripe_checkout_id": checkout_session["id"],
            "amount": product["price"] * (body.quantity or 1),
            "currency": product["currency"],
            "status": "pending",
            "quantity": body.quantity or 1,
            "created_at": now,
            "updated_at": now,
        }
        await db.orders.insert_one(order)
        return {
            "status": "ok",
            "checkout_url": checkout_session["url"],
            "checkout_session_id": checkout_session["id"],
            "order_id": order["id"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")


@commerce_router.get("/commerce/stats")
async def get_commerce_stats(user: dict = Depends(_resolve_current_user)):
    """Revenue stats: total_revenue, total_orders, mrr."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    orders = await db.orders.find({"user_id": user["id"], "status": "paid"}).to_list(10000)
    total_revenue = sum(o.get("amount", 0) for o in orders)
    total_orders = len(orders)
    # MRR: subscription orders in last 30 days
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    products = await db.products.find({"user_id": user["id"], "type": "subscription"}).to_list(200)
    sub_product_ids = {p["id"] for p in products}
    mrr = sum(
        o.get("amount", 0)
        for o in orders
        if o.get("product_id") in sub_product_ids and (o.get("created_at") or "") >= cutoff
    )
    return {
        "total_revenue": round(total_revenue, 2),
        "total_orders": total_orders,
        "mrr": round(mrr, 2),
    }


# ===========================================================================
# 9. AUTO-DB SCHEMA GENERATION
# ===========================================================================

class AppDBProvision(BaseModel):
    project_id: Optional[str] = None
    description: str = Field(..., min_length=10, max_length=5000)
    project_name: Optional[str] = Field(None, max_length=100)
    features: Optional[List[str]] = None


class AppDBRegenerate(BaseModel):
    description: Optional[str] = Field(None, max_length=5000)
    features: Optional[List[str]] = None


def _generate_schema_from_description(description: str, project_name: str, features: List[str]) -> Dict[str, Any]:
    """
    Generate a complete PostgreSQL schema + Supabase-compatible setup from a
    project description. This is the core competitive advantage vs Lovable:
    full production-ready schema with RLS, seed data, and typed API routes.
    """
    name_slug = re.sub(r'[^a-z0-9_]', '_', (project_name or "app").lower())[:30]
    desc_lower = description.lower()
    feature_set = set(f.lower() for f in (features or []))

    # Heuristic feature detection
    has_users = True  # always
    has_auth = True
    has_teams = any(w in desc_lower for w in ("team", "organization", "org", "workspace", "tenant", "company", "member", "multi-tenant"))
    # Posts / knowledge base / articles / FAQ
    has_posts = any(w in desc_lower for w in ("post", "article", "blog", "content", "publish", "knowledge", "faq", "document", "wiki", "guide", "help"))
    has_products = any(w in desc_lower for w in ("product", "item", "listing", "sku", "store", "shop", "e-commerce", "ecommerce", "catalog", "inventory"))
    has_orders = any(w in desc_lower for w in ("order", "purchase", "checkout", "buy", "payment", "invoice", "cart"))
    # Messages / chat / sessions — covers live chat + sessions
    has_messages = any(w in desc_lower for w in ("message", "chat", "inbox", "conversation", "dm", "session", "transcript", "live chat", "support chat", "agent", "escalat"))
    has_tasks = any(w in desc_lower for w in ("task", "todo", "issue", "ticket", "kanban", "sprint", "project management"))
    has_files = any(w in desc_lower for w in ("file", "upload", "attachment", "media", "image", "video", "csv", "pdf", "storage"))
    has_analytics = any(w in desc_lower for w in ("analytic", "metric", "dashboard", "report", "stat", "event tracking", "funnel", "insight"))
    has_subscriptions = any(w in desc_lower for w in ("subscription", "plan", "billing", "stripe", "saas", "pricing", "tier", "upgrade"))

    # Feature flag overrides
    if "teams" in feature_set or "organizations" in feature_set:
        has_teams = True
    if "payments" in feature_set or "stripe" in feature_set:
        has_orders = True
        has_products = True
        has_subscriptions = True
    if "analytics" in feature_set:
        has_analytics = True

    tables_sql_parts = [
        "-- ============================================================",
        f"-- AUTO-GENERATED SCHEMA for: {project_name or description[:60]}",
        "-- Generated by CrucibAI Auto-DB Engine",
        "-- ============================================================",
        "",
        "-- Enable UUID extension",
        'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";',
        "",
        "-- =========== USERS ===========",
        "CREATE TABLE IF NOT EXISTS users (",
        "  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),",
        "  email TEXT UNIQUE NOT NULL,",
        "  name TEXT,",
        "  avatar_url TEXT,",
        "  role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin', 'superadmin')),",
        "  is_active BOOLEAN NOT NULL DEFAULT TRUE,",
        "  metadata JSONB NOT NULL DEFAULT '{}',",
        "  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),",
        "  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
        ");",
        "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);",
        "",
    ]

    rls_parts = [
        "-- ============================================================",
        "-- ROW-LEVEL SECURITY POLICIES",
        "-- ============================================================",
        "",
        "ALTER TABLE users ENABLE ROW LEVEL SECURITY;",
        "CREATE POLICY users_self_access ON users",
        "  USING (id = auth.uid()::uuid);",
        "",
    ]

    seed_parts = [
        "-- ============================================================",
        "-- SEED DATA",
        "-- ============================================================",
        "",
        "-- Admin user (replace password hash in production)",
        "INSERT INTO users (id, email, name, role) VALUES",
        "  (uuid_generate_v4(), 'admin@example.com', 'Admin', 'admin')",
        "ON CONFLICT (email) DO NOTHING;",
        "",
    ]

    api_routes: List[Dict[str, str]] = [
        {"method": "POST", "path": "/auth/register", "description": "Register a new user"},
        {"method": "POST", "path": "/auth/login", "description": "Login and receive JWT"},
        {"method": "GET", "path": "/users/me", "description": "Get current user profile"},
        {"method": "PATCH", "path": "/users/me", "description": "Update current user profile"},
    ]

    env_vars: List[str] = [
        "SUPABASE_URL=https://<project-ref>.supabase.co",
        "SUPABASE_ANON_KEY=<your-anon-key>",
        "SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>",
        "DATABASE_URL=postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres",
        "JWT_SECRET=<your-jwt-secret>",
    ]

    if has_teams:
        tables_sql_parts += [
            "-- =========== TEAMS / ORGANIZATIONS ===========",
            "CREATE TABLE IF NOT EXISTS teams (",
            "  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),",
            "  name TEXT NOT NULL,",
            "  slug TEXT UNIQUE NOT NULL,",
            "  description TEXT,",
            "  owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,",
            "  plan TEXT NOT NULL DEFAULT 'free',",
            "  metadata JSONB NOT NULL DEFAULT '{}',",
            "  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),",
            "  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
            ");",
            "",
            "CREATE TABLE IF NOT EXISTS team_members (",
            "  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),",
            "  team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,",
            "  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,",
            "  role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member', 'viewer')),",
            "  joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),",
            "  UNIQUE(team_id, user_id)",
            ");",
            "CREATE INDEX IF NOT EXISTS idx_team_members_team ON team_members(team_id);",
            "CREATE INDEX IF NOT EXISTS idx_team_members_user ON team_members(user_id);",
            "",
        ]
        rls_parts += [
            "ALTER TABLE teams ENABLE ROW LEVEL SECURITY;",
            "CREATE POLICY teams_member_access ON teams",
            "  USING (id IN (SELECT team_id FROM team_members WHERE user_id = auth.uid()::uuid));",
            "",
            "ALTER TABLE team_members ENABLE ROW LEVEL SECURITY;",
            "CREATE POLICY team_members_access ON team_members",
            "  USING (team_id IN (SELECT team_id FROM team_members WHERE user_id = auth.uid()::uuid));",
            "",
        ]
        api_routes += [
            {"method": "GET", "path": "/teams", "description": "List user's teams"},
            {"method": "POST", "path": "/teams", "description": "Create a team"},
            {"method": "GET", "path": "/teams/{id}", "description": "Get team details"},
            {"method": "POST", "path": "/teams/{id}/invite", "description": "Invite a member"},
        ]

    if has_posts:
        tables_sql_parts += [
            "-- =========== POSTS / CONTENT ===========",
            "CREATE TABLE IF NOT EXISTS posts (",
            "  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),",
            "  author_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,",
            "  title TEXT NOT NULL,",
            "  slug TEXT UNIQUE,",
            "  body TEXT,",
            "  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),",
            "  tags TEXT[] DEFAULT '{}',",
            "  metadata JSONB NOT NULL DEFAULT '{}',",
            "  published_at TIMESTAMPTZ,",
            "  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),",
            "  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
            ");",
            "CREATE INDEX IF NOT EXISTS idx_posts_author ON posts(author_id);",
            "CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);",
            "",
        ]
        rls_parts += [
            "ALTER TABLE posts ENABLE ROW LEVEL SECURITY;",
            "CREATE POLICY posts_author_access ON posts",
            "  USING (author_id = auth.uid()::uuid OR status = 'published');",
            "",
        ]
        api_routes += [
            {"method": "GET", "path": "/posts", "description": "List published posts"},
            {"method": "POST", "path": "/posts", "description": "Create a post"},
            {"method": "GET", "path": "/posts/{id}", "description": "Get post by id or slug"},
            {"method": "PUT", "path": "/posts/{id}", "description": "Update a post"},
            {"method": "DELETE", "path": "/posts/{id}", "description": "Delete a post"},
        ]

    if has_products:
        tables_sql_parts += [
            "-- =========== PRODUCTS ===========",
            "CREATE TABLE IF NOT EXISTS products (",
            "  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),",
            "  name TEXT NOT NULL,",
            "  description TEXT,",
            "  price NUMERIC(12,2) NOT NULL DEFAULT 0,",
            "  currency TEXT NOT NULL DEFAULT 'usd',",
            "  sku TEXT UNIQUE,",
            "  stock_quantity INT,",
            "  is_active BOOLEAN NOT NULL DEFAULT TRUE,",
            "  images TEXT[] DEFAULT '{}',",
            "  metadata JSONB NOT NULL DEFAULT '{}',",
            "  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),",
            "  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
            ");",
            "CREATE INDEX IF NOT EXISTS idx_products_active ON products(is_active);",
            "",
        ]
        rls_parts += [
            "ALTER TABLE products ENABLE ROW LEVEL SECURITY;",
            "CREATE POLICY products_public_read ON products",
            "  FOR SELECT USING (is_active = TRUE);",
            "CREATE POLICY products_admin_write ON products",
            "  FOR ALL USING (EXISTS (SELECT 1 FROM users WHERE id = auth.uid()::uuid AND role = 'admin'));",
            "",
        ]
        api_routes += [
            {"method": "GET", "path": "/products", "description": "List active products"},
            {"method": "POST", "path": "/products", "description": "Create a product (admin)"},
            {"method": "GET", "path": "/products/{id}", "description": "Get product detail"},
            {"method": "PUT", "path": "/products/{id}", "description": "Update product (admin)"},
        ]

    if has_orders:
        tables_sql_parts += [
            "-- =========== ORDERS ===========",
            "CREATE TABLE IF NOT EXISTS orders (",
            "  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),",
            "  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,",
            "  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'fulfilling', 'completed', 'cancelled', 'refunded')),",
            "  total_amount NUMERIC(12,2) NOT NULL DEFAULT 0,",
            "  currency TEXT NOT NULL DEFAULT 'usd',",
            "  stripe_session_id TEXT,",
            "  stripe_payment_intent TEXT,",
            "  items JSONB NOT NULL DEFAULT '[]',",
            "  metadata JSONB NOT NULL DEFAULT '{}',",
            "  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),",
            "  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
            ");",
            "CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);",
            "",
        ]
        rls_parts += [
            "ALTER TABLE orders ENABLE ROW LEVEL SECURITY;",
            "CREATE POLICY orders_owner_access ON orders",
            "  USING (user_id = auth.uid()::uuid);",
            "",
        ]
        api_routes += [
            {"method": "POST", "path": "/checkout", "description": "Create Stripe checkout session"},
            {"method": "GET", "path": "/orders", "description": "List user's orders"},
            {"method": "GET", "path": "/orders/{id}", "description": "Get order detail"},
        ]
        env_vars.append("STRIPE_SECRET_KEY=<your-stripe-secret-key>")
        env_vars.append("STRIPE_WEBHOOK_SECRET=<your-stripe-webhook-secret>")

    if has_messages:
        tables_sql_parts += [
            "-- =========== MESSAGES ===========",
            "CREATE TABLE IF NOT EXISTS conversations (",
            "  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),",
            "  participant_ids UUID[] NOT NULL DEFAULT '{}',",
            "  metadata JSONB NOT NULL DEFAULT '{}',",
            "  last_message_at TIMESTAMPTZ,",
            "  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
            ");",
            "",
            "CREATE TABLE IF NOT EXISTS messages (",
            "  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),",
            "  conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,",
            "  sender_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,",
            "  body TEXT NOT NULL,",
            "  read_by UUID[] DEFAULT '{}',",
            "  metadata JSONB NOT NULL DEFAULT '{}',",
            "  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
            ");",
            "CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);",
            "CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id);",
            "",
        ]
        rls_parts += [
            "ALTER TABLE messages ENABLE ROW LEVEL SECURITY;",
            "CREATE POLICY messages_participant_access ON messages",
            "  USING (conversation_id IN (",
            "    SELECT id FROM conversations WHERE auth.uid()::uuid = ANY(participant_ids)",
            "  ));",
            "",
        ]
        api_routes += [
            {"method": "GET", "path": "/conversations", "description": "List user's conversations"},
            {"method": "POST", "path": "/conversations", "description": "Start a conversation"},
            {"method": "GET", "path": "/conversations/{id}/messages", "description": "Get messages"},
            {"method": "POST", "path": "/conversations/{id}/messages", "description": "Send a message"},
        ]

    if has_tasks:
        tables_sql_parts += [
            "-- =========== TASKS / PROJECTS ===========",
            "CREATE TABLE IF NOT EXISTS projects_app (",
            "  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),",
            "  owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,",
            "  name TEXT NOT NULL,",
            "  description TEXT,",
            "  status TEXT NOT NULL DEFAULT 'active',",
            "  metadata JSONB NOT NULL DEFAULT '{}',",
            "  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),",
            "  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
            ");",
            "",
            "CREATE TABLE IF NOT EXISTS tasks (",
            "  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),",
            "  project_id UUID REFERENCES projects_app(id) ON DELETE CASCADE,",
            "  assignee_id UUID REFERENCES users(id) ON DELETE SET NULL,",
            "  title TEXT NOT NULL,",
            "  description TEXT,",
            "  status TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo', 'in_progress', 'review', 'done', 'cancelled')),",
            "  priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),",
            "  due_date TIMESTAMPTZ,",
            "  tags TEXT[] DEFAULT '{}',",
            "  metadata JSONB NOT NULL DEFAULT '{}',",
            "  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),",
            "  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
            ");",
            "CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);",
            "CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON tasks(assignee_id);",
            "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);",
            "",
        ]
        rls_parts += [
            "ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;",
            "CREATE POLICY tasks_project_member_access ON tasks",
            "  USING (project_id IN (SELECT id FROM projects_app WHERE owner_id = auth.uid()::uuid));",
            "",
        ]
        api_routes += [
            {"method": "GET", "path": "/tasks", "description": "List tasks"},
            {"method": "POST", "path": "/tasks", "description": "Create a task"},
            {"method": "PATCH", "path": "/tasks/{id}", "description": "Update task status/fields"},
            {"method": "DELETE", "path": "/tasks/{id}", "description": "Delete a task"},
        ]

    if has_files:
        tables_sql_parts += [
            "-- =========== FILES / ATTACHMENTS ===========",
            "CREATE TABLE IF NOT EXISTS files (",
            "  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),",
            "  uploader_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,",
            "  filename TEXT NOT NULL,",
            "  content_type TEXT,",
            "  size_bytes BIGINT,",
            "  storage_path TEXT NOT NULL,",
            "  public_url TEXT,",
            "  entity_type TEXT,",
            "  entity_id UUID,",
            "  metadata JSONB NOT NULL DEFAULT '{}',",
            "  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
            ");",
            "CREATE INDEX IF NOT EXISTS idx_files_uploader ON files(uploader_id);",
            "CREATE INDEX IF NOT EXISTS idx_files_entity ON files(entity_type, entity_id);",
            "",
        ]
        rls_parts += [
            "ALTER TABLE files ENABLE ROW LEVEL SECURITY;",
            "CREATE POLICY files_owner_access ON files",
            "  USING (uploader_id = auth.uid()::uuid);",
            "",
        ]
        api_routes += [
            {"method": "POST", "path": "/files/upload", "description": "Upload a file (multipart)"},
            {"method": "GET", "path": "/files/{id}", "description": "Get file metadata"},
            {"method": "DELETE", "path": "/files/{id}", "description": "Delete a file"},
        ]
        env_vars.append("SUPABASE_STORAGE_BUCKET=<your-storage-bucket>")

    if has_analytics:
        tables_sql_parts += [
            "-- =========== ANALYTICS ===========",
            "CREATE TABLE IF NOT EXISTS analytics_events (",
            "  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),",
            "  user_id UUID REFERENCES users(id) ON DELETE SET NULL,",
            "  event_type TEXT NOT NULL,",
            "  properties JSONB NOT NULL DEFAULT '{}',",
            "  session_id TEXT,",
            "  ip TEXT,",
            "  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
            ");",
            "CREATE INDEX IF NOT EXISTS idx_analytics_user ON analytics_events(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_analytics_type ON analytics_events(event_type);",
            "CREATE INDEX IF NOT EXISTS idx_analytics_created ON analytics_events(created_at);",
            "",
        ]
        api_routes += [
            {"method": "POST", "path": "/analytics/event", "description": "Track an event"},
            {"method": "GET", "path": "/analytics/summary", "description": "Get analytics summary"},
        ]

    if has_subscriptions:
        tables_sql_parts += [
            "-- =========== SUBSCRIPTIONS ===========",
            "CREATE TABLE IF NOT EXISTS subscriptions (",
            "  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),",
            "  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,",
            "  plan TEXT NOT NULL DEFAULT 'free',",
            "  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'past_due', 'cancelled', 'trialing')),",
            "  stripe_subscription_id TEXT,",
            "  stripe_customer_id TEXT,",
            "  current_period_start TIMESTAMPTZ,",
            "  current_period_end TIMESTAMPTZ,",
            "  cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,",
            "  metadata JSONB NOT NULL DEFAULT '{}',",
            "  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),",
            "  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
            ");",
            "CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);",
            "",
        ]
        rls_parts += [
            "ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;",
            "CREATE POLICY subscriptions_owner_access ON subscriptions",
            "  USING (user_id = auth.uid()::uuid);",
            "",
        ]
        api_routes += [
            {"method": "GET", "path": "/subscriptions/me", "description": "Get current subscription"},
            {"method": "POST", "path": "/subscriptions/upgrade", "description": "Upgrade plan"},
            {"method": "POST", "path": "/subscriptions/cancel", "description": "Cancel subscription"},
        ]

    # Updated_at trigger (generic)
    tables_sql_parts += [
        "-- =========== UPDATED_AT TRIGGER ===========",
        "CREATE OR REPLACE FUNCTION update_updated_at_column()",
        "RETURNS TRIGGER AS $$",
        "BEGIN",
        "  NEW.updated_at = NOW();",
        "  RETURN NEW;",
        "END;",
        "$$ language 'plpgsql';",
        "",
        "-- Apply to tables with updated_at",
        "DO $$ DECLARE t TEXT;",
        "BEGIN",
        "  FOREACH t IN ARRAY ARRAY['users'" + (", 'teams'" if has_teams else "") + (", 'posts'" if has_posts else "") + (", 'products'" if has_products else "") + (", 'orders'" if has_orders else "") + "]",
        "  LOOP",
        "    EXECUTE format(",
        "      'CREATE TRIGGER set_updated_at BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()',",
        "      t",
        "    );",
        "  END LOOP;",
        "EXCEPTION WHEN duplicate_object THEN NULL;",
        "END $$;",
    ]

    return {
        "tables_sql": "\n".join(tables_sql_parts),
        "rls_policies": "\n".join(rls_parts),
        "seed_data": "\n".join(seed_parts),
        "api_routes_spec": api_routes,
        "env_vars_needed": env_vars,
        "feature_flags": {
            "teams": has_teams,
            "posts": has_posts,
            "products": has_products,
            "orders": has_orders,
            "messages": has_messages,
            "tasks": has_tasks,
            "files": has_files,
            "analytics": has_analytics,
            "subscriptions": has_subscriptions,
        },
    }


@appdb_router.post("/app-db/provision", status_code=201)
async def provision_app_db(body: AppDBProvision, user: dict = Depends(_resolve_current_user)):
    """
    Generate a complete PostgreSQL schema + Supabase-compatible setup from a
    project description. CrucibAI's #1 competitive advantage vs Lovable.
    """
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    project_id = body.project_id or str(uuid.uuid4())
    project_name = body.project_name or f"Project {project_id[:8]}"
    features = body.features or []
    now = datetime.now(timezone.utc).isoformat()
    schema = _generate_schema_from_description(body.description, project_name, features)
    doc = {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "user_id": user["id"],
        "project_name": project_name,
        "description": body.description,
        "features": features,
        "tables_sql": schema["tables_sql"],
        "rls_policies": schema["rls_policies"],
        "seed_data": schema["seed_data"],
        "api_routes_spec": schema["api_routes_spec"],
        "env_vars_needed": schema["env_vars_needed"],
        "feature_flags": schema["feature_flags"],
        "version": 1,
        "created_at": now,
        "updated_at": now,
    }
    await db.app_db_schemas.insert_one(doc)
    return {
        "status": "provisioned",
        "project_id": project_id,
        "schema_id": doc["id"],
        **schema,
    }


@appdb_router.get("/app-db/{project_id}")
async def get_app_db_schema(project_id: str, user: dict = Depends(_resolve_current_user)):
    """Get the most recent generated schema for a project."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    # Find latest version for this project
    schemas = await db.app_db_schemas.find(
        {"project_id": project_id, "user_id": user["id"]}
    ).sort("created_at", -1).to_list(10)
    if not schemas:
        raise HTTPException(status_code=404, detail="Schema not found for this project")
    latest = schemas[0]
    return {"schema": latest, "versions": len(schemas)}


@appdb_router.post("/app-db/{project_id}/regenerate")
async def regenerate_app_db_schema(
    project_id: str, body: AppDBRegenerate, user: dict = Depends(_resolve_current_user)
):
    """Regenerate the schema for an updated project description."""
    db = _db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    existing_schemas = await db.app_db_schemas.find(
        {"project_id": project_id, "user_id": user["id"]}
    ).sort("created_at", -1).to_list(5)
    if not existing_schemas:
        raise HTTPException(status_code=404, detail="Project schema not found")
    latest = existing_schemas[0]
    description = body.description or latest.get("description", "")
    features = body.features or latest.get("features") or []
    project_name = latest.get("project_name", "Project")
    now = datetime.now(timezone.utc).isoformat()
    schema = _generate_schema_from_description(description, project_name, features)
    new_version = latest.get("version", 1) + 1
    doc = {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "user_id": user["id"],
        "project_name": project_name,
        "description": description,
        "features": features,
        "tables_sql": schema["tables_sql"],
        "rls_policies": schema["rls_policies"],
        "seed_data": schema["seed_data"],
        "api_routes_spec": schema["api_routes_spec"],
        "env_vars_needed": schema["env_vars_needed"],
        "feature_flags": schema["feature_flags"],
        "version": new_version,
        "created_at": now,
        "updated_at": now,
    }
    await db.app_db_schemas.insert_one(doc)
    return {
        "status": "regenerated",
        "project_id": project_id,
        "schema_id": doc["id"],
        "version": new_version,
        **schema,
    }


# ===========================================================================
# REGISTRATION
# ===========================================================================

def register_blueprint_routes(app: FastAPI) -> None:
    """
    Include all blueprint routers into the FastAPI app.
    Call this after the app is created in server.py.
    """
    app.include_router(personas_router)
    app.include_router(knowledge_router)
    app.include_router(channels_router)
    app.include_router(sessions_router)
    app.include_router(safety_router)
    app.include_router(workspace_router)
    app.include_router(analytics_router)
    app.include_router(commerce_router)
    app.include_router(appdb_router)

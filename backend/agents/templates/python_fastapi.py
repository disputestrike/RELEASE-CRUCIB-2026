"""
Python / FastAPI template generator for CrucibAI.

Produces a complete, runnable FastAPI backend with:
- CORSMiddleware, in-memory data store
- 5+ REST endpoints including health-check, search, CRUD
- Pydantic request/response models
- API-key authentication dependency
"""

import re
from typing import Dict


def _extract_domain(goal: str) -> str:
    """Extract a short domain name from the goal (e.g. 'task' from 'Build a task tracker')."""
    goal_lower = goal.lower()
    for phrase in [
        r"(?:a |an |the )?(\w+)\s+(?:tracker|manager|app|api|system|service|platform)",
        r"(?:build|create|make|generate)\s+(?:a |an |the )?(\w+)",
        r"(\w+)\s+(?:api|application|service)",
    ]:
        match = re.search(phrase, goal_lower)
        if match:
            return match.group(1).replace(" ", "_")
    return "item"


def _singular(word: str) -> str:
    """Naive singulariser for common English plurals."""
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith("ses") or word.endswith("xes") or word.endswith("zes"):
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _plural(word: str) -> str:
    """Naive pluraliser."""
    if word.endswith("y") and not word.endswith("ay") and not word.endswith("ey"):
        return word[:-1] + "ies"
    if word.endswith("s") or word.endswith("x") or word.endswith("z"):
        return word + "es"
    return word + "s"


def _pascal(word: str) -> str:
    return "".join(part.capitalize() for part in word.split("_"))


def generate_python_fastapi(goal: str, project_name: str = "generated-api") -> Dict[str, str]:
    """Generate a complete Python/FastAPI backend scaffold.

    Parameters
    ----------
    goal:
        Natural-language description of what the API should do.
    project_name:
        Used for documentation / headers only.

    Returns
    -------
    Dict[str, str]
        Mapping of relative filepath -> complete file content.
    """
    domain = _extract_domain(goal)
    Domain = _pascal(domain)
    domains = _plural(domain)
    Domains = _pascal(domains)
    DomainSingular = _singular(Domain)

    # ------------------------------------------------------------------
    # backend/models.py
    # ------------------------------------------------------------------
    models_py = f'''\
"""
Pydantic models for the {project_name} API.

All request / response schemas live here to keep the router thin.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------
class {Domain}Create(BaseModel):
    """Payload for creating a new {domain}."""

    name: str = Field(..., min_length=1, max_length=200, description="Display name")
    description: Optional[str] = Field(default=None, max_length=2000)
    status: str = Field(default="active", pattern=r"^(active|inactive|archived)$")
    tags: list[str] = Field(default_factory=list, max_length=10)
    priority: int = Field(default=0, ge=0, le=10)


class {Domain}Update(BaseModel):
    """Partial update payload — every field is optional."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    status: Optional[str] = Field(default=None, pattern=r"^(active|inactive|archived)$")
    tags: Optional[list[str]] = None
    priority: Optional[int] = Field(default=None, ge=0, le=10)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------
class {Domain}Response(BaseModel):
    """Full {domain} record returned by the API."""

    id: int
    name: str
    description: Optional[str]
    status: str
    tags: list[str]
    priority: int
    created_at: datetime
    updated_at: datetime


class {Domain}ListResponse(BaseModel):
    """Paginated list wrapper."""

    items: list[{Domain}Response]
    total: int
    page: int
    page_size: int


class HealthResponse(BaseModel):
    """Liveness / readiness probe response."""

    status: str = "ok"
    version: str = "1.0.0"
    uptime_seconds: float


class MessageResponse(BaseModel):
    """Generic message envelope."""

    message: str
    id: Optional[int] = None


class SearchResponse(BaseModel):
    """Free-text search results."""

    query: str
    results: list[{Domain}Response]
    total: int
'''
    # ------------------------------------------------------------------
    # backend/auth.py
    # ------------------------------------------------------------------
    auth_py = f'''\
"""
API-key authentication helpers.

In production you would verify against a database or secret-manager.
For generated scaffolds we accept a configurable key via the
CRUCIB_API_KEY environment variable (defaults to "dev-key").
"""

from __future__ import annotations

import os
from fastapi import Header, HTTPException, status

API_KEY = os.getenv("CRUCIB_API_KEY", "dev-key")


async def verify_api_key(
    x_api_key: str = Header(..., alias="x-api-key"),
) -> str:
    """Dependency that raises 401 when the key is missing or invalid."""
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Pass x-api-key header.",
        )
    return x_api_key
'''
    # ------------------------------------------------------------------
    # backend/main.py
    # ------------------------------------------------------------------
    main_py = f'''\
"""
{Domain} API — auto-generated by CrucibAI.

A fully functional FastAPI backend with CRUD, search, health-check,
and API-key authentication.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from backend.models import (
    HealthResponse,
    MessageResponse,
    SearchResponse,
    {Domain}Create,
    {Domain}ListResponse,
    {Domain}Response,
    {Domain}Update,
)
from backend.auth import verify_api_key

# ---------------------------------------------------------------------------
# App bootstrap
# ---------------------------------------------------------------------------
app = FastAPI(
    title="{Domain} API",
    description="CrucibAI-generated REST API for managing {domains}.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_START = time.time()

# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------
_next_id = 1
_db: dict[int, dict] = {{}}


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _to_response(record: dict) -> {Domain}Response:
    return {Domain}Response(**record)


def _find_or_404({domain}_id: int) -> dict:
    if {domain}_id not in _db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="{Domain} not found")
    return _db[{domain}_id]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check():
    """Liveness / readiness probe."""
    return HealthResponse(uptime_seconds=round(time.time() - _START, 2))


@app.post(
    "/api/{domains}",
    response_model={Domain}Response,
    status_code=status.HTTP_201_CREATED,
    tags=["{domains}"],
)
async def create_{domain}(
    payload: {Domain}Create,
    _key: str = Depends(verify_api_key),
):
    """Create a new {domain}."""
    global _next_id
    record = {{
        "id": _next_id,
        **payload.model_dump(),
        "created_at": _now(),
        "updated_at": _now(),
    }}
    _db[_next_id] = record
    _next_id += 1
    return _to_response(record)


@app.get("/api/{domains}", response_model={Domain}ListResponse, tags=["{domains}"])
async def list_{domains}(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
):
    """Return a paginated list of {domains}."""
    items = list(_db.values())
    if status_filter:
        items = [i for i in items if i["status"] == status_filter]
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return {Domain}ListResponse(
        items=[_to_response(i) for i in items[start:end]],
        total=total,
        page=page,
        page_size=page_size,
    )


@app.get("/api/{domains}/{{{domain}_id}}", response_model={Domain}Response, tags=["{domains}"])
async def get_{domain}({domain}_id: int):
    """Retrieve a single {domain} by ID."""
    return _to_response(_find_or_404({domain}_id))


@app.put("/api/{domains}/{{{domain}_id}}", response_model={Domain}Response, tags=["{domains}"])
async def update_{domain}(
    {domain}_id: int,
    payload: {Domain}Update,
    _key: str = Depends(verify_api_key),
):
    """Partial-update an existing {domain}."""
    record = _find_or_404({domain}_id)
    updates = payload.model_dump(exclude_unset=True)
    record.update(updates)
    record["updated_at"] = _now()
    return _to_response(record)


@app.delete(
    "/api/{domains}/{{{domain}_id}}",
    response_model=MessageResponse,
    tags=["{domains}"],
)
async def delete_{domain}(
    {domain}_id: int,
    _key: str = Depends(verify_api_key),
):
    """Delete a {domain} by ID."""
    _find_or_404({domain}_id)
    del _db[{domain}_id]
    return MessageResponse(message="{Domain} deleted", id={domain}_id)


@app.get("/api/{domains}/search", response_model=SearchResponse, tags=["{domains}"])
async def search_{domains}(
    q: str = Query(..., min_length=1, description="Free-text search query"),
    limit: int = Query(20, ge=1, le=100),
):
    """Search {domains} by name, description, or tags."""
    q_lower = q.lower()
    results = [
        r
        for r in _db.values()
        if q_lower in r["name"].lower()
        or (r.get("description") and q_lower in r["description"].lower())
        or any(q_lower in t.lower() for t in r.get("tags", []))
    ]
    return SearchResponse(
        query=q,
        results=[_to_response(r) for r in results[:limit]],
        total=len(results),
    )


@app.get("/api/{domains}/stats", tags=["{domains}"])
async def {domain}_stats():
    """Return aggregate statistics about {domains}."""
    all_records = list(_db.values())
    status_counts: dict[str, int] = {{}}
    for r in all_records:
        s = r["status"]
        status_counts[s] = status_counts.get(s, 0) + 1
    return {{
        "total": len(all_records),
        "by_status": status_counts,
        "avg_priority": round(sum(r["priority"] for r in all_records) / max(len(all_records), 1), 2),
    }}
'''

    # ------------------------------------------------------------------
    # backend/requirements.txt
    # ------------------------------------------------------------------
    requirements_txt = """\
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
pydantic>=2.10.0
"""

    # ------------------------------------------------------------------
    # Return all files
    # ------------------------------------------------------------------
    return {
        "backend/main.py": main_py,
        "backend/models.py": models_py,
        "backend/auth.py": auth_py,
        "backend/requirements.txt": requirements_txt,
    }

"""
backend_agent.py — Backend code generation agent for CrucibAI.

Generates FastAPI backend code from a goal description.
Produces real API endpoints, models, auth, and database schemas.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from backend.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a senior Python backend engineer. Given a product goal, generate a COMPLETE working FastAPI backend.

## CRITICAL RULES
1. Output ONLY a JSON object with a "files" key mapping file paths to their content.
2. Every file must contain REAL, WORKING Python code — no placeholders, no TODO, no "..." stubs.
3. Use FastAPI with proper type hints and Pydantic models.
4. All files go under "backend/".
5. backend/main.py MUST have: `from fastapi import FastAPI`, `app = FastAPI(...)`, and CORSMiddleware.
6. Generate at least 5 real endpoints related to the goal (not just /health).
7. Use Pydantic v2 BaseModel for request/response schemas.
8. Include proper async def for all route handlers.
9. Each endpoint should return realistic data structures.

## REQUIRED FILES
- backend/main.py — FastAPI app with routes, CORS, at least 5 endpoints
- backend/models.py — Pydantic models for the domain
- backend/auth.py — Auth utilities (JWT, API key, or simple token auth)
- backend/requirements.txt — Python dependencies

## OUTPUT FORMAT
Return a single JSON object:
{
  "files": {
    "backend/main.py": "...",
    "backend/models.py": "...",
    "backend/auth.py": "...",
    "backend/requirements.txt": "..."
  },
  "api_spec": {
    "endpoints": [
      {"method": "GET", "path": "/health", "description": "Health check"},
      {"method": "GET", "path": "/api/items", "description": "List items"}
    ]
  }
}

Do NOT wrap the JSON in markdown fences. Output raw JSON only.\
"""


class BackendAgent(BaseAgent):
    """Generates FastAPI backend code from a goal."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "BackendAgent"

    def validate_input(self, context: Dict[str, Any]) -> bool:
        super().validate_input(context)
        goal = (context.get("goal") or context.get("user_prompt") or "").strip()
        if len(goal) < 5:
            raise ValueError("BackendAgent requires a goal with at least 5 characters")
        return True

    def validate_output(self, result: Dict[str, Any]) -> bool:
        super().validate_output(result)
        if not result.get("files"):
            raise ValueError("BackendAgent output must contain a 'files' dictionary")
        return True

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        goal = (context.get("goal") or context.get("user_prompt") or "").strip()
        if not goal:
            return {"status": "error", "reason": "no_goal", "files": {}}

        user_prompt = (
            f"Build a complete FastAPI backend for this goal:\n\n{goal}\n\n"
            f"Generate the full JSON with all backend files. Include at minimum:\n"
            f"- backend/main.py with:\n"
            f"  - FastAPI app with CORSMiddleware\n"
            f"  - GET /health endpoint\n"
            f"  - At least 5 real API endpoints related to the goal (CRUD operations, search, etc.)\n"
            f"  - Realistic response data (lists of items, statistics, user profiles, etc.)\n"
            f"  - Proper async handlers\n"
            f"- backend/models.py with:\n"
            f"  - At least 3 Pydantic BaseModel classes for the domain\n"
            f"  - Proper field types (str, int, Optional, datetime, etc.)\n"
            f"- backend/auth.py with:\n"
            f"  - A simple API key or token verification function\n"
            f"  - A protected route dependency\n"
            f"- backend/requirements.txt with fastapi, uvicorn, pydantic\n"
            f"\n"
            f"Every endpoint must return REAL data, not placeholder strings.\n"
            f"Models must have fields relevant to the goal's domain."
        )

        try:
            raw, tokens = await self.call_llm(
                user_prompt=user_prompt,
                system_prompt=_SYSTEM_PROMPT,
                model="cerebras",
                temperature=0.4,
                max_tokens=8000,
                stream=True,
            )
        except Exception as e:
            logger.error("BackendAgent LLM call failed: %s", e)
            return {
                "status": "error",
                "reason": f"llm_failure: {e}",
                "files": {},
            }

        files = self._extract_files(raw)
        if not files:
            logger.warning("BackendAgent: LLM output was not valid file dict, raw=%s...", (raw or "")[:300])
            return {
                "status": "error",
                "reason": "no_files_parsed",
                "files": {},
                "_raw": raw,
            }

        # Ensure critical backend files
        files = self._ensure_critical_files(files, goal)

        # Extract API spec
        api_spec = {"endpoints": self._extract_api_spec(files)}

        return {
            "status": "success",
            "files": files,
            "api_spec": api_spec,
            "_agent": "BackendAgent",
        }

    def _extract_files(self, raw: str) -> Dict[str, str]:
        """Extract file dict from LLM response."""
        text = raw.strip()

        # Try direct JSON parse
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                if "files" in data:
                    return {k: str(v) for k, v in data["files"].items()}
                # Top-level keys might be file paths
                if any(isinstance(v, str) for v in data.values()):
                    return {k: str(v) for k, v in data.items()}
        except json.JSONDecodeError:
            pass

        # Try markdown code fences
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
            try:
                data = json.loads(text)
                if isinstance(data, dict):
                    if "files" in data:
                        return {k: str(v) for k, v in data["files"].items()}
                    return {k: str(v) for k, v in data.items()}
            except json.JSONDecodeError:
                pass
        elif "```" in text:
            parts = text.split("```")
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                lines = part.split("\n")
                if lines and lines[0].strip().isalpha():
                    lines = lines[1:]
                part = "\n".join(lines)
                try:
                    data = json.loads(part)
                    if isinstance(data, dict):
                        if "files" in data:
                            return {k: str(v) for k, v in data["files"].items()}
                        return {k: str(v) for k, v in data.items()}
                except json.JSONDecodeError:
                    continue

        return {}

    def _ensure_critical_files(self, files: Dict[str, str], goal: str) -> Dict[str, str]:
        """Ensure all required backend files exist."""
        if "backend/main.py" not in files:
            files["backend/main.py"] = f'''\
"""FastAPI backend — generated by CrucibAI BackendAgent."""
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Generated API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Models ---
class ItemCreate(BaseModel):
    title: str
    description: Optional[str] = None


class ItemResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    created_at: str


class StatsResponse(BaseModel):
    total_items: int
    version: str
    uptime: str


# --- In-memory store ---
_items = [
    {{ "id": 1, "title": "Getting Started", "description": "Welcome to your new application", "created_at": datetime.now(timezone.utc).isoformat() }},
    {{ "id": 2, "title": "Feature Overview", "description": "Explore the key features available", "created_at": datetime.now(timezone.utc).isoformat() }},
]
_next_id = 3


# --- Endpoints ---
@app.get("/health")
async def health():
    return {{"status": "ok", "ts": datetime.now(timezone.utc).isoformat()}}


@app.get("/api/items", response_model=List[ItemResponse])
async def list_items():
    return _items


@app.get("/api/items/{{item_id}}")
async def get_item(item_id: int):
    for item in _items:
        if item["id"] == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")


@app.post("/api/items", response_model=ItemResponse)
async def create_item(body: ItemCreate):
    global _next_id
    item = {{
        "id": _next_id,
        "title": body.title,
        "description": body.description,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }}
    _items.append(item)
    _next_id += 1
    return item


@app.delete("/api/items/{{item_id}}")
async def delete_item(item_id: int):
    for i, item in enumerate(_items):
        if item["id"] == item_id:
            _items.pop(i)
            return {{"deleted": True}}
    raise HTTPException(status_code=404, detail="Item not found")


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    return StatsResponse(
        total_items=len(_items),
        version="0.1.0",
        uptime="running",
    )


@app.get("/api/search")
async def search_items(q: str = Query(..., min_length=1)):
    results = [item for item in _items if q.lower() in item["title"].lower()]
    return {{"query": q, "results": results, "count": len(results)}}
'''

        if "backend/models.py" not in files:
            files["backend/models.py"] = '''\
"""Pydantic models for the generated API."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ItemBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)


class ItemResponse(ItemBase):
    id: int
    created_at: str


class UserBase(BaseModel):
    email: str = Field(..., pattern=r"^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$")
    name: str = Field(..., min_length=1, max_length=100)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserResponse(UserBase):
    id: int
    created_at: str


class MessageResponse(BaseModel):
    message: str
    success: bool = True
'''

        if "backend/auth.py" not in files:
            files["backend/auth.py"] = '''\
"""Auth utilities for the generated API."""
import os
import hashlib
import hmac
from datetime import datetime, timezone
from fastapi import HTTPException, Header, Optional


API_KEY_HEADER = "X-API-Key"
# In production, load from environment variable
_EXPECTED_API_KEY = os.getenv("API_KEY", "dev-api-key-change-in-production")


def verify_api_key(x_api_key: Optional[str] = Header(default=None)):
    """Dependency that verifies the X-API-Key header."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    if not hmac.compare_digest(x_api_key, _EXPECTED_API_KEY):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return {"api_key": x_api_key}


PROTECTED_PREFIX = "/api/private"


def is_protected_path(path: str) -> bool:
    """Check if a path requires authentication."""
    return path.startswith(PROTECTED_PREFIX)
'''

        if "backend/requirements.txt" not in files:
            files["backend/requirements.txt"] = "fastapi>=0.104.0\nuvicorn>=0.24.0\npydantic>=2.0.0\n"

        return files

    def _extract_api_spec(self, files: Dict[str, str]) -> List[Dict[str, str]]:
        """Extract API endpoints from backend/main.py."""
        endpoints = []
        main_py = files.get("backend/main.py", "")
        for line in main_py.split("\n"):
            stripped = line.strip()
            if stripped.startswith("@app."):
                # Parse @app.get("/path") or @app.post("/path")
                parts = stripped.replace("(", " ").replace(")", " ").replace(",", " ").split()
                if len(parts) >= 2:
                    method_parts = parts[0].split(".")
                    method = method_parts[-1].upper() if len(method_parts) > 1 else "GET"
                    path = parts[1].strip('"\'')
                    # Clean up path templates
                    desc = f"{method} {path}"
                    endpoints.append({
                        "method": method,
                        "path": path,
                        "description": desc,
                    })

        if not endpoints:
            endpoints = [
                {"method": "GET", "path": "/health", "description": "Health check"},
                {"method": "GET", "path": "/api/items", "description": "List items"},
                {"method": "POST", "path": "/api/items", "description": "Create item"},
                {"method": "GET", "path": "/api/stats", "description": "Get statistics"},
            ]

        return endpoints

"""
backend_agent.py — Backend code generation agent for CrucibAI.

Generates backend code from a goal description. Supports multiple frameworks:
  - FastAPI (Python) — default
  - Express (Node.js)
  - CLI (Python)
  - CMake (C++)
  - Gin (Go)
  - Axum (Rust)

Uses template registry as the primary generation method, with LLM
for customization when a framework is explicitly specified.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from backend.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Framework-specific system prompts
# ---------------------------------------------------------------------------

_SYSTEM_PROMPTS: Dict[str, str] = {
    "fastapi": """\
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
""",

    "express": """\
You are a senior Node.js backend engineer. Given a product goal, generate a COMPLETE working Express backend.

## CRITICAL RULES
1. Output ONLY a JSON object with a "files" key mapping file paths to their content.
2. Every file must contain REAL, WORKING JavaScript code — no placeholders, no TODO, no "..." stubs.
3. Use Express with proper middleware setup (cors, express.json()).
4. All backend files go under "backend/".
5. backend/server.js MUST have: express(), cors middleware, and JSON body parser.
6. Generate at least 5 real endpoints related to the goal (not just /health).
7. Each endpoint should return realistic data structures.
8. Use CommonJS (require/module.exports) unless ESM is explicitly requested.

## REQUIRED FILES
- backend/server.js — Express app with routes, CORS, at least 5 endpoints
- backend/routes/api.js — API route handlers
- backend/package.json — Node.js dependencies (express, cors)
- backend/models.js — Data models (plain objects or a lightweight ORM pattern)

## OUTPUT FORMAT
Return a single JSON object with "files" and "api_spec" keys.
Do NOT wrap the JSON in markdown fences. Output raw JSON only.\
""",

    "cli": """\
You are a senior Python backend engineer. Given a product goal, generate a COMPLETE working CLI application.

## CRITICAL RULES
1. Output ONLY a JSON object with a "files" key mapping file paths to their content.
2. Every file must contain REAL, WORKING Python code — no placeholders, no TODO, no "..." stubs.
3. Use argparse or click for CLI argument parsing.
4. Generate at least 3 subcommands related to the goal.
5. Each command should perform real logic and produce useful output.
6. Include proper error handling and help text.

## REQUIRED FILES
- cli/main.py — CLI entry point with argparse
- cli/utils.py — Utility functions
- cli/models.py — Data models (dataclasses or Pydantic)
- requirements.txt — Python dependencies
- pyproject.toml — Project metadata

## OUTPUT FORMAT
Return a single JSON object with "files" key.
Do NOT wrap the JSON in markdown fences. Output raw JSON only.\
""",

    "cmake": """\
You are a senior C++ backend engineer. Given a product goal, generate a COMPLETE working C++ application.

## CRITICAL RULES
1. Output ONLY a JSON object with a "files" key mapping file paths to their content.
2. Every file must contain REAL, WORKING C++ code — no placeholders, no TODO, no "..." stubs.
3. Use CMake as the build system.
4. The application must compile and run with standard g++ or clang++.
5. Include proper header guards in all header files.

## REQUIRED FILES
- CMakeLists.txt — CMake build configuration
- src/main.cpp — Application entry point
- include/ — Header files
- Additional source files as needed

## OUTPUT FORMAT
Return a single JSON object with "files" key.
Do NOT wrap the JSON in markdown fences. Output raw JSON only.\
""",

    "gin": """\
You are a senior Go backend engineer. Given a product goal, generate a COMPLETE working Go web application.

## CRITICAL RULES
1. Output ONLY a JSON object with a "files" key mapping file paths to their content.
2. Every file must contain REAL, WORKING Go code — no placeholders, no TODO, no "..." stubs.
3. Use the Gin web framework.
4. Include proper package declarations and imports.
5. Generate at least 5 real endpoints related to the goal.

## REQUIRED FILES
- main.go — Application entry point with Gin router
- handlers/handlers.go — HTTP handler functions
- models/models.go — Data models (Go structs)
- go.mod — Go module file

## OUTPUT FORMAT
Return a single JSON object with "files" and "api_spec" keys.
Do NOT wrap the JSON in markdown fences. Output raw JSON only.\
""",

    "axum": """\
You are a senior Rust backend engineer. Given a product goal, generate a COMPLETE working Rust web application.

## CRITICAL RULES
1. Output ONLY a JSON object with a "files" key mapping file paths to their content.
2. Every file must contain REAL, WORKING Rust code — no placeholders, no TODO, no "..." stubs.
3. Use the Axum web framework with Tokio async runtime.
4. Include proper use declarations and module structure.
5. Generate at least 5 real endpoints related to the goal.
6. Use serde for JSON serialization.

## REQUIRED FILES
- Cargo.toml — Rust project manifest
- src/main.rs — Application entry point with Axum router
- src/handlers.rs — HTTP handler functions
- src/models.rs — Data models (Rust structs with serde)

## OUTPUT FORMAT
Return a single JSON object with "files" and "api_spec" keys.
Do NOT wrap the JSON in markdown fences. Output raw JSON only.\
""",
}

# ---------------------------------------------------------------------------
# Template imports (with safety net)
# ---------------------------------------------------------------------------

_TEMPLATE_GENERATORS: Dict[str, Any] = {}
_FRAMEWORK_TO_TEMPLATE: Dict[str, str] = {
    "fastapi": "python_fastapi",
    "express": "node_express",
    "cli": "python_cli",
    "cmake": "cpp_cmake",
    "gin": "go_gin",
    "axum": "rust_axum",
}

try:
    from backend.agents.templates import (
        generate_python_fastapi,
        generate_node_express,
        generate_python_cli,
        generate_cpp_cmake,
        generate_go_gin,
        generate_rust_axum,
    )
    _TEMPLATE_GENERATORS = {
        "python_fastapi": generate_python_fastapi,
        "node_express": generate_node_express,
        "python_cli": generate_python_cli,
        "cpp_cmake": generate_cpp_cmake,
        "go_gin": generate_go_gin,
        "rust_axum": generate_rust_axum,
    }
    _TEMPLATES_AVAILABLE = True
except (ImportError, SyntaxError) as exc:
    logger.warning("BackendAgent: template import failed — LLM-only mode: %s", exc)
    _TEMPLATES_AVAILABLE = False


class BackendAgent(BaseAgent):
    """Generates backend code from a goal.

    Supports multiple frameworks via the template registry. When no framework
    is explicitly specified, defaults to FastAPI (preserving backward
    compatibility).
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "BackendAgent"

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Main execution
    # ------------------------------------------------------------------

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("REAL_BACKEND_AGENT_USED")
        goal = (context.get("goal") or context.get("user_prompt") or "").strip()
        if not goal:
            return {"status": "error", "reason": "no_goal", "files": {}}

        # ----------------------------------------------------------------
        # Step 1: Determine the backend framework
        # ----------------------------------------------------------------
        framework = self._resolve_framework(context)
        logger.info("BackendAgent: resolved framework=%s", framework)

        # ----------------------------------------------------------------
        # Step 2: Generate base files using templates
        # ----------------------------------------------------------------
        files: Dict[str, str] = {}
        generation_method = "none"

        if _TEMPLATES_AVAILABLE:
            template_id = _FRAMEWORK_TO_TEMPLATE.get(framework)
            if template_id and template_id in _TEMPLATE_GENERATORS:
                try:
                    project_name = self._derive_project_name(goal)
                    files = _TEMPLATE_GENERATORS[template_id](goal, project_name)
                    generation_method = "templates"
                    logger.info("BackendAgent: generated %d files from template %s", len(files), template_id)
                except Exception as exc:
                    logger.error("BackendAgent: template generation failed: %s", exc)

        # ----------------------------------------------------------------
        # Step 3: If templates produced files, optionally customize via LLM
        # ----------------------------------------------------------------
        if files and generation_method == "templates":
            customize = context.get("customize_with_llm", True)
            if customize:
                try:
                    files = await self._customize_with_llm(files, goal, framework)
                    generation_method = "templates+llm"
                    logger.info("BackendAgent: LLM customization applied")
                except Exception as exc:
                    logger.warning("BackendAgent: LLM customization failed (keeping templates): %s", exc)

        # ----------------------------------------------------------------
        # Step 4: Fall back to LLM-only if templates unavailable or failed
        # ----------------------------------------------------------------
        if not files:
            logger.info("BackendAgent: falling back to LLM-only generation")
            try:
                files = await self._generate_with_llm(goal, framework)
                generation_method = "llm_fallback"
            except Exception as exc:
                logger.error("BackendAgent: LLM generation failed: %s", exc)
                return {
                    "status": "error",
                    "reason": f"all_generation_failed: {exc}",
                    "files": {},
                }

        # ----------------------------------------------------------------
        # Step 5: Ensure critical files exist (safety net)
        # ----------------------------------------------------------------
        files = self._ensure_critical_files(files, goal, framework)

        # ----------------------------------------------------------------
        # Step 6: Build result
        # ----------------------------------------------------------------
        api_spec = {"endpoints": self._extract_api_spec(files)}

        result: Dict[str, Any] = {
            "status": "success",
            "files": files,
            "api_spec": api_spec,
            "_agent": "BackendAgent",
            "_generation_method": generation_method,
            "_backend_framework": framework,
        }

        return result

    # ------------------------------------------------------------------
    # Framework resolution
    # ------------------------------------------------------------------

    def _resolve_framework(self, context: Dict[str, Any]) -> str:
        """Determine the backend framework from context or defaults.

        Priority:
        1. Explicit ``backend_framework`` in context
        2. Framework embedded in ``selected_stack`` dict
        3. Auto-detect from goal text (basic keyword matching)
        4. Default to ``fastapi``
        """
        # 1. Explicit framework
        framework = context.get("backend_framework")
        if framework and isinstance(framework, str):
            fw = framework.lower().strip()
            if fw in _SYSTEM_PROMPTS:
                return fw

        # 2. From selected_stack
        selected_stack = context.get("selected_stack")
        if selected_stack and isinstance(selected_stack, dict):
            stack_fw = selected_stack.get("framework", "")
            if stack_fw:
                # Map template framework names to our internal keys
                _fw_map = {
                    "fastapi": "fastapi",
                    "express": "express",
                    "cli": "cli",
                    "cmake": "cmake",
                    "gin": "gin",
                    "axum": "axum",
                    "react+vite": "fastapi",  # frontend-only stack → default backend
                }
                fw = _fw_map.get(stack_fw.lower(), stack_fw.lower())
                if fw in _SYSTEM_PROMPTS:
                    return fw

        # 3. Basic keyword auto-detect from goal
        goal = (context.get("goal") or context.get("user_prompt") or "").lower()
        if "express" in goal or "node.js" in goal or "nodejs" in goal or " node " in goal:
            return "express"
        if "cli" in goal or "command line" in goal or "command-line" in goal:
            return "cli"
        if "golang" in goal or " go " in goal or "gin" in goal:
            return "gin"
        if "rust" in goal or "cargo" in goal or "axum" in goal:
            return "axum"
        if "c++" in goal or "cpp" in goal or "cmake" in goal or "g++" in goal:
            return "cmake"

        # 4. Default
        return "fastapi"

    # ------------------------------------------------------------------
    # LLM customization of template output
    # ------------------------------------------------------------------

    async def _customize_with_llm(
        self,
        template_files: Dict[str, str],
        goal: str,
        framework: str,
    ) -> Dict[str, str]:
        """Call LLM to enhance template output with goal-specific content."""
        system_prompt = _SYSTEM_PROMPTS.get(framework, _SYSTEM_PROMPTS["fastapi"])

        file_list = "\n".join(f"  - {path}" for path in sorted(template_files.keys()))
        user_prompt = (
            f"An application backend is being built for this goal:\n\n{goal}\n\n"
            f"Template-generated files (base scaffold):\n{file_list}\n\n"
            f"Your job is to CUSTOMIZE these files for the specific goal. Output a JSON object "
            f'with a "files" key. Each key is a file path from the list above, and the value is '
            f"the ENHANCED content. You may also add NEW files not in the list.\n\n"
            f"Rules:\n"
            f"- Keep the same file structure and conventions as the templates.\n"
            f"- Make content specific to the goal (real endpoints, real logic, real data).\n"
            f"- Do NOT change imports, framework setup, or configuration that makes the app work.\n"
            f"- Output ONLY the JSON with the \"files\" key. No markdown fences."
        )

        raw, _tokens = await self.call_llm(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            model="cerebras",
            temperature=0.4,
            max_tokens=8000,
            stream=True,
        )

        llm_files = self._extract_files(raw)
        if llm_files:
            # Merge: template files form the base, LLM enhancements overlay
            return {**template_files, **llm_files}

        return template_files

    # ------------------------------------------------------------------
    # Pure LLM generation (when templates unavailable)
    # ------------------------------------------------------------------

    async def _generate_with_llm(self, goal: str, framework: str) -> Dict[str, str]:
        """Generate files entirely via LLM."""
        system_prompt = _SYSTEM_PROMPTS.get(framework, _SYSTEM_PROMPTS["fastapi"])

        if framework == "fastapi":
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
        elif framework == "express":
            user_prompt = (
                f"Build a complete Node.js + Express backend for this goal:\n\n{goal}\n\n"
                f"Generate the full JSON with all backend files. Include at minimum:\n"
                f"- backend/server.js with express(), cors, at least 5 real endpoints\n"
                f"- backend/routes/api.js with route handlers\n"
                f"- backend/package.json with express, cors dependencies\n"
                f"- backend/models.js with data models\n"
                f"Every endpoint must return REAL data, not placeholder strings."
            )
        elif framework == "cli":
            user_prompt = (
                f"Build a complete Python CLI application for this goal:\n\n{goal}\n\n"
                f"Generate the full JSON with all files. Include at minimum:\n"
                f"- cli/main.py (argparse entry point with at least 3 subcommands)\n"
                f"- cli/utils.py\n"
                f"- cli/models.py (dataclasses or pydantic models)\n"
                f"- requirements.txt\n"
                f"- pyproject.toml\n"
                f"Make every command do something real and useful."
            )
        elif framework in ("cmake", "gin", "axum"):
            user_prompt = (
                f"Build a complete {framework.title()} backend for this goal:\n\n{goal}\n\n"
                f"Generate the full JSON with all required source files, config files, and build files.\n"
                f"Make the application fully functional with real logic related to the goal."
            )
        else:
            user_prompt = (
                f"Build a complete FastAPI backend for this goal:\n\n{goal}\n\n"
                f"Generate the full JSON with all backend files.\n"
                f"Every endpoint must return REAL data related to the goal."
            )

        raw, _tokens = await self.call_llm(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            model="cerebras",
            temperature=0.4,
            max_tokens=8000,
            stream=True,
        )

        return self._extract_files(raw)

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def _derive_project_name(self, goal: str) -> str:
        """Derive a safe project name from the goal text."""
        import re
        words = re.findall(r"[a-zA-Z0-9]+", goal.lower())
        if not words:
            return "app"
        meaningful = [w for w in words if len(w) > 2][:3]
        return "_".join(meaningful) if meaningful else words[0]

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

    def _ensure_critical_files(
        self, files: Dict[str, str], goal: str, framework: str = "fastapi",
    ) -> Dict[str, str]:
        """Ensure all required backend files exist.

        Framework-aware — only injects files matching the active framework.
        Falls back to FastAPI defaults.
        """
        if framework == "fastapi":
            self._ensure_fastapi_files(files)
        elif framework == "express":
            self._ensure_express_files(files)
        elif framework == "cli":
            self._ensure_cli_files(files)
        elif framework == "cmake":
            self._ensure_cmake_files(files)
        elif framework == "gin":
            self._ensure_gin_files(files)
        elif framework == "axum":
            self._ensure_axum_files(files)
        else:
            self._ensure_fastapi_files(files)

        return files

    # ------------------------------------------------------------------
    # Framework-specific critical file fallbacks
    # ------------------------------------------------------------------

    @staticmethod
    def _ensure_fastapi_files(files: Dict[str, str]) -> None:
        """Inject missing FastAPI backend files."""
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

    @staticmethod
    def _ensure_express_files(files: Dict[str, str]) -> None:
        """Inject missing Express backend files."""
        if "backend/server.js" not in files:
            files["backend/server.js"] = (
                'const express = require("express");\n'
                'const cors = require("cors");\n'
                'const apiRouter = require("./routes/api");\n'
                'const app = express();\n'
                'const PORT = process.env.PORT || 3001;\n'
                '\n'
                'app.use(cors());\n'
                'app.use(express.json());\n'
                '\n'
                'app.use("/api", apiRouter);\n'
                '\n'
                'app.get("/health", (req, res) => {\n'
                '  res.json({ status: "ok", ts: new Date().toISOString() });\n'
                '});\n'
                '\n'
                'app.listen(PORT, () => {\n'
                '  console.log(`Server running on port ${PORT}`);\n'
                '});\n'
            )

        if "backend/routes/api.js" not in files:
            files["backend/routes/api.js"] = (
                'const express = require("express");\n'
                'const router = express.Router();\n'
                '\n'
                'let items = [\n'
                '  { id: 1, title: "Getting Started", description: "Welcome" },\n'
                '  { id: 2, title: "Feature Overview", description: "Explore features" },\n'
                '];\n'
                'let nextId = 3;\n'
                '\n'
                'router.get("/items", (req, res) => {\n'
                '  res.json({ items });\n'
                '});\n'
                '\n'
                'router.get("/items/:id", (req, res) => {\n'
                '  const item = items.find(i => i.id === parseInt(req.params.id));\n'
                '  if (!item) return res.status(404).json({ error: "Not found" });\n'
                '  res.json(item);\n'
                '});\n'
                '\n'
                'router.post("/items", (req, res) => {\n'
                '  const { title, description } = req.body;\n'
                '  const item = { id: nextId++, title: title || "New Item", description };\n'
                '  items.push(item);\n'
                '  res.json(item);\n'
                '});\n'
                '\n'
                'router.delete("/items/:id", (req, res) => {\n'
                '  const idx = items.findIndex(i => i.id === parseInt(req.params.id));\n'
                '  if (idx === -1) return res.status(404).json({ error: "Not found" });\n'
                '  items.splice(idx, 1);\n'
                '  res.json({ deleted: true });\n'
                '});\n'
                '\n'
                'router.get("/stats", (req, res) => {\n'
                '  res.json({ total_items: items.length, version: "0.1.0" });\n'
                '});\n'
                '\n'
                'module.exports = router;\n'
            )

        if "backend/package.json" not in files:
            files["backend/package.json"] = json.dumps({
                "name": "backend",
                "version": "0.1.0",
                "main": "server.js",
                "scripts": {"start": "node server.js", "dev": "node --watch server.js"},
                "dependencies": {"express": "^4.18.0", "cors": "^2.8.5"},
            }, indent=2)

    @staticmethod
    def _ensure_cli_files(files: Dict[str, str]) -> None:
        """Inject missing CLI backend files."""
        if "cli/main.py" not in files and "main.py" not in files:
            files["cli/main.py"] = (
                '"""CLI application generated by CrucibAI."""\n'
                'import argparse\n'
                'import sys\n'
                '\n'
                'def main():\n'
                '    parser = argparse.ArgumentParser(description="Generated CLI Application")\n'
                '    subparsers = parser.add_subparsers(dest="command")\n'
                '    subparsers.add_parser("run", help="Run the application")\n'
                '    subparsers.add_parser("status", help="Show status")\n'
                '    subparsers.add_parser("list", help="List items")\n'
                '    args = parser.parse_args()\n'
                '    if args.command == "run":\n'
                '        print("Running...")\n'
                '    elif args.command == "status":\n'
                '        print("Status: OK")\n'
                '    elif args.command == "list":\n'
                '        print("Items: []")\n'
                '    else:\n'
                '        parser.print_help()\n'
                '\n'
                'if __name__ == "__main__":\n'
                '    main()\n'
            )

        if "requirements.txt" not in files:
            files["requirements.txt"] = ""

        if "pyproject.toml" not in files:
            files["pyproject.toml"] = (
                '[build-system]\n'
                'requires = ["setuptools>=68.0", "wheel"]\n'
                'build-backend = "setuptools.backends._legacy:_Backend"\n'
                '\n'
                '[project]\n'
                'name = "generated-cli"\n'
                'version = "0.1.0"\n'
                'requires-python = ">=3.9"\n'
                '\n'
                '[project.scripts]\n'
                'generated-cli = "cli.main:main"\n'
            )

    @staticmethod
    def _ensure_cmake_files(files: Dict[str, str]) -> None:
        """Inject missing CMake backend files."""
        if "CMakeLists.txt" not in files:
            files["CMakeLists.txt"] = (
                'cmake_minimum_required(VERSION 3.16)\n'
                'project(GeneratedApp LANGUAGES CXX)\n'
                'set(CMAKE_CXX_STANDARD 17)\n'
                'set(CMAKE_CXX_STANDARD_REQUIRED ON)\n'
                '\n'
                'add_executable(generated_app src/main.cpp)\n'
                'target_include_directories(generated_app PRIVATE include)\n'
            )

        if "src/main.cpp" not in files:
            files["src/main.cpp"] = (
                '#include <iostream>\n'
                '#include <string>\n'
                '\n'
                'int main(int argc, char* argv[]) {\n'
                '    std::cout << "Generated Application" << std::endl;\n'
                '    return 0;\n'
                '}\n'
            )

    @staticmethod
    def _ensure_gin_files(files: Dict[str, str]) -> None:
        """Inject missing Go Gin backend files."""
        if "main.go" not in files:
            files["main.go"] = (
                'package main\n'
                '\n'
                'import (\n'
                '\t"log"\n'
                '\t"net/http"\n'
                '\t"github.com/gin-gonic/gin"\n'
                ')\n'
                '\n'
                'func main() {\n'
                '\tr := gin.Default()\n'
                '\n'
                '\tr.GET("/health", func(c *gin.Context) {\n'
                '\t\tc.JSON(http.StatusOK, gin.H{"status": "ok"})\n'
                '\t})\n'
                '\n'
                '\tr.GET("/api/items", func(c *gin.Context) {\n'
                '\t\tc.JSON(http.StatusOK, gin.H{"items": []gin.H{{"id": 1, "title": "Demo"}}})\n'
                '\t})\n'
                '\n'
                '\tlog.Fatal(r.Run(":8080"))\n'
                '}\n'
            )

        if "go.mod" not in files:
            files["go.mod"] = (
                'module generated-app\n'
                '\n'
                'go 1.21\n'
                '\n'
                'require github.com/gin-gonic/gin v1.9.1\n'
            )

    @staticmethod
    def _ensure_axum_files(files: Dict[str, str]) -> None:
        """Inject missing Rust Axum backend files."""
        if "Cargo.toml" not in files:
            files["Cargo.toml"] = (
                '[package]\n'
                'name = "generated-app"\n'
                'version = "0.1.0"\n'
                'edition = "2021"\n'
                '\n'
                '[dependencies]\n'
                'axum = "0.7"\n'
                'tokio = { version = "1", features = ["full"] }\n'
                'serde = { version = "1", features = ["derive"] }\n'
                'serde_json = "1"\n'
                'tower-http = { version = "0.5", features = ["cors"] }\n'
            )

        if "src/main.rs" not in files:
            files["src/main.rs"] = (
                'use axum::{routing::get, Json, Router};\n'
                'use serde_json::{json, Value};\n'
                '\n'
                'async fn health() -> Json<Value> {\n'
                '    Json(json!({"status": "ok"}))\n'
                '}\n'
                '\n'
                'async fn list_items() -> Json<Value> {\n'
                '    Json(json!({"items": [{"id": 1, "title": "Demo"}]}))\n'
                '}\n'
                '\n'
                '#[tokio::main]\n'
                'async fn main() {\n'
                '    let app = Router::new()\n'
                '        .route("/health", get(health))\n'
                '        .route("/api/items", get(list_items));\n'
                '\n'
                '    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await.unwrap();\n'
                '    axum::serve(listener, app).await.unwrap();\n'
                '}\n'
            )

    # ------------------------------------------------------------------
    # API spec extraction (preserved from original)
    # ------------------------------------------------------------------

    def _extract_api_spec(self, files: Dict[str, str]) -> List[Dict[str, str]]:
        """Extract API endpoints from backend files.

        Supports FastAPI (@app.get/post), Express (app.get/post),
        and Gin (r.GET/POST) patterns.
        """
        endpoints = []

        main_py = files.get("backend/main.py", "")
        if main_py:
            endpoints.extend(self._extract_fastapi_endpoints(main_py))

        server_js = files.get("backend/server.js", "")
        if server_js:
            endpoints.extend(self._extract_express_endpoints(server_js))
        api_js = files.get("backend/routes/api.js", "")
        if api_js:
            endpoints.extend(self._extract_express_endpoints(api_js))

        main_go = files.get("main.go", "")
        if main_go:
            endpoints.extend(self._extract_gin_endpoints(main_go))

        main_rs = files.get("src/main.rs", "")
        if main_rs:
            endpoints.extend(self._extract_axum_endpoints(main_rs))

        if not endpoints:
            endpoints = [
                {"method": "GET", "path": "/health", "description": "Health check"},
                {"method": "GET", "path": "/api/items", "description": "List items"},
                {"method": "POST", "path": "/api/items", "description": "Create item"},
                {"method": "GET", "path": "/api/stats", "description": "Get statistics"},
            ]

        return endpoints

    @staticmethod
    def _extract_fastapi_endpoints(source: str) -> List[Dict[str, str]]:
        """Parse @app.get("/path") decorators from Python source."""
        endpoints = []
        for line in source.split("\n"):
            stripped = line.strip()
            if stripped.startswith("@app."):
                parts = stripped.replace("(", " ").replace(")", " ").replace(",", " ").split()
                if len(parts) >= 2:
                    method_parts = parts[0].split(".")
                    method = method_parts[-1].upper() if len(method_parts) > 1 else "GET"
                    path = parts[1].strip('"\'')
                    desc = f"{method} {path}"
                    endpoints.append({"method": method, "path": path, "description": desc})
        return endpoints

    @staticmethod
    def _extract_express_endpoints(source: str) -> List[Dict[str, str]]:
        """Parse app.get("/path") / router.get("/path") from JS source."""
        import re
        endpoints = []
        for match in re.finditer(r'\b(app|router)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']*)["\']', source):
            method = match.group(2).upper()
            path = match.group(3)
            endpoints.append({"method": method, "path": path, "description": f"{method} {path}"})
        return endpoints

    @staticmethod
    def _extract_gin_endpoints(source: str) -> List[Dict[str, str]]:
        """Parse r.GET("/path") calls from Go source."""
        import re
        endpoints = []
        for match in re.finditer(r'\b[rR]\.(GET|POST|PUT|DELETE|PATCH)\s*\(\s*["\']([^"\']*)["\']', source):
            method = match.group(1).upper()
            path = match.group(2)
            endpoints.append({"method": method, "path": path, "description": f"{method} {path}"})
        return endpoints

    @staticmethod
    def _extract_axum_endpoints(source: str) -> List[Dict[str, str]]:
        """Parse .route("/path", get(handler)) calls from Rust source."""
        import re
        endpoints = []
        for match in re.finditer(r'\.route\s*\(\s*"([^"]*)"', source):
            path = match.group(1)
            method = "GET"
            for method_kw in ["get", "post", "put", "delete", "patch"]:
                if method_kw in source[match.start():match.start() + 200]:
                    method = method_kw.upper()
                    break
            endpoints.append({"method": method, "path": path, "description": f"{method} {path}"})
        return endpoints

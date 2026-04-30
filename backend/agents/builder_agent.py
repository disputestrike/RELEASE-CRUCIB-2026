"""
builder_agent.py -- Full-system builder agent for CrucibAI.

Generates complete fullstack applications from a goal description.
Uses LLM to produce real, working code across frontend (Vite+React),
backend (FastAPI), database schemas, tests, and configuration.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from backend.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a senior fullstack engineer. Given a product goal, generate a COMPLETE working application.\n"
    "\n"
    "## CRITICAL RULES\n"
    "1. Output ONLY a JSON object with a \"files\" key mapping file paths to their content.\n"
    "2. Every file must contain REAL, WORKING code -- no placeholders, no TODO comments, no \"...\" stubs.\n"
    "3. Frontend: Use Vite + React + JavaScript (JSX). Use react-router-dom for routing.\n"
    "4. Backend: Use Python FastAPI. All backend files go under \"backend/\".\n"
    "5. Include: package.json, vite.config.js, index.html, src/main.jsx, src/App.jsx.\n"
    "6. Include: backend/main.py with at least 4 real endpoints (not just health).\n"
    "7. Include: backend/requirements.txt with all Python dependencies.\n"
    "8. The backend main.py MUST have: `app = FastAPI(...)` and import CORSMiddleware.\n"
    "9. Every React component must be a valid JSX module with proper imports.\n"
    "10. package.json must include: react, react-dom, react-router-dom, zustand, @vitejs/plugin-react, vite.\n"
    "\n"
    "## OUTPUT FORMAT\n"
    "Return a single JSON object:\n"
    "{\n"
    '  "files": {\n'
    '    "package.json": "{...json...}",\n'
    '    "vite.config.js": "...",\n'
    '    "index.html": "...",\n'
    '    "src/main.jsx": "...",\n'
    '    "src/App.jsx": "...",\n'
    '    "src/pages/HomePage.jsx": "...",\n'
    '    "src/pages/DashboardPage.jsx": "...",\n'
    '    "src/store/useAppStore.js": "...",\n'
    '    "src/components/ErrorBoundary.jsx": "...",\n'
    '    "backend/main.py": "...",\n'
    '    "backend/requirements.txt": "...",\n'
    '    "backend/models.py": "...",\n'
    '    "backend/auth.py": "..."\n'
    "  },\n"
    '  "api_spec": {\n'
    '    "endpoints": [\n'
    '      {"method": "GET", "path": "/health", "description": "..."},\n'
    '      {"method": "GET", "path": "/api/items", "description": "..."}\n'
    "    ]\n"
    "  }\n"
    "}\n"
    "\n"
    "Do NOT wrap the JSON in markdown fences. Output raw JSON only."
)


class BuilderAgent(BaseAgent):
    """Generates complete fullstack applications from a goal."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "BuilderAgent"

    def validate_input(self, context: Dict[str, Any]) -> bool:
        super().validate_input(context)
        goal = (context.get("goal") or context.get("user_prompt") or "").strip()
        if len(goal) < 5:
            raise ValueError("BuilderAgent requires a goal with at least 5 characters")
        return True

    def validate_output(self, result: Dict[str, Any]) -> bool:
        super().validate_output(result)
        if not result.get("files"):
            raise ValueError("BuilderAgent output must contain a 'files' dictionary")
        if not isinstance(result["files"], dict) or len(result["files"]) < 3:
            raise ValueError("BuilderAgent must generate at least 3 files")
        return True

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        goal = (context.get("goal") or context.get("user_prompt") or "").strip()
        if not goal:
            return {"status": "error", "reason": "no_goal", "files": {}}

        max_tokens = int(context.get("max_tokens") or 12000)
        model = context.get("llm_model") or "cerebras"

        user_prompt = (
            f"Build a complete fullstack application for this goal:\n\n{goal}\n\n"
            "Generate the full JSON with all files. Include at minimum:\n"
            "- package.json (with react, react-dom, react-router-dom, zustand, vite, @vitejs/plugin-react)\n"
            "- vite.config.js\n"
            '- index.html with <div id="root"></div> and <script type="module" src="/src/main.jsx"></script>\n'
            "- src/main.jsx (createRoot render)\n"
            "- src/App.jsx (router with at least 3 pages)\n"
            "- src/pages/HomePage.jsx (real content about the goal)\n"
            "- src/pages/DashboardPage.jsx (real dashboard with data)\n"
            "- src/store/useAppStore.js (zustand store)\n"
            "- src/components/ErrorBoundary.jsx\n"
            "- src/styles/global.css\n"
            "- backend/main.py (FastAPI app with CORSMiddleware, at least 4 real endpoints)\n"
            "- backend/requirements.txt (fastapi, uvicorn, pydantic)\n"
            "- backend/models.py (pydantic models)\n"
            "- backend/auth.py\n"
            "Make every endpoint return REAL data related to the goal. No placeholder responses."
        )

        try:
            raw, tokens = await self.call_llm(
                user_prompt=user_prompt,
                system_prompt=_SYSTEM_PROMPT,
                model=model,
                temperature=0.4,
                max_tokens=max_tokens,
                stream=True,
            )
        except Exception as e:
            logger.error("BuilderAgent LLM call failed: %s", e)
            return {
                "status": "error",
                "reason": f"llm_failure: {e}",
                "files": {},
            }

        # Parse the JSON response
        files = self._extract_files(raw)
        if not files:
            logger.warning("BuilderAgent: LLM output was not valid file dict, raw=%s...", (raw or "")[:300])
            return {
                "status": "error",
                "reason": "no_files_parsed",
                "files": {},
                "_raw": raw,
            }

        # Ensure critical files exist
        files = self._ensure_critical_files(files, goal)

        api_spec = {"endpoints": self._extract_api_spec(files)}
        return {
            "status": "success",
            "files": files,
            "api_spec": api_spec,
            "_agent": "BuilderAgent",
            "_build_target": "full_system_generator",
        }

    def _extract_files(self, raw: str) -> Dict[str, str]:
        """Extract file dict from LLM response."""
        text = raw.strip()

        # Try to parse as JSON directly
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "files" in data:
                return data["files"]
            if isinstance(data, dict):
                if any(isinstance(v, str) for v in data.values()):
                    return {k: str(v) for k, v in data.items()}
        except json.JSONDecodeError:
            pass

        # Try to extract from markdown code fences
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
            try:
                data = json.loads(text)
                if isinstance(data, dict) and "files" in data:
                    return data["files"]
                if isinstance(data, dict):
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
                    if isinstance(data, dict) and "files" in data:
                        return data["files"]
                    if isinstance(data, dict):
                        return {k: str(v) for k, v in data.items()}
                except json.JSONDecodeError:
                    continue

        return {}

    def _ensure_critical_files(self, files: Dict[str, str], goal: str) -> Dict[str, str]:
        """Add critical files if the LLM did not generate them."""
        # Ensure package.json has required dependencies
        if "package.json" in files:
            try:
                pkg = json.loads(files["package.json"])
                deps = pkg.setdefault("dependencies", {})
                deps.setdefault("react", "^18.2.0")
                deps.setdefault("react-dom", "^18.2.0")
                deps.setdefault("react-router-dom", "^6.20.0")
                deps.setdefault("zustand", "^4.5.0")
                deps.setdefault("@vitejs/plugin-react", "^4.3.0")
                deps.setdefault("vite", "^5.4.0")
                pkg.setdefault("scripts", {}).setdefault("dev", "vite")
                pkg.setdefault("scripts", {}).setdefault("build", "vite build")
                pkg["type"] = "module"
                files["package.json"] = json.dumps(pkg, indent=2)
            except (json.JSONDecodeError, TypeError):
                pass

        # Ensure index.html has root div and main.jsx script
        if "index.html" in files:
            html = files["index.html"]
            if 'id="root"' not in html:
                html = html.replace("</body>", '<div id="root"></div>\n    <script type="module" src="/src/main.jsx"></script>\n  </body>')
            if "main.jsx" not in html:
                html = html.replace("</body>", '    <script type="module" src="/src/main.jsx"></script>\n  </body>')
            files["index.html"] = html

        # Ensure src/main.jsx exists
        if "src/main.jsx" not in files and "src/main.js" not in files:
            files["src/main.jsx"] = (
                "import React from 'react';\n"
                "import { createRoot } from 'react-dom/client';\n"
                "import App from './App';\n"
                "\n"
                "createRoot(document.getElementById('root')).render(\n"
                "  <React.StrictMode>\n"
                "    <App />\n"
                "  </React.StrictMode>,\n"
                ");\n"
            )

        # Ensure src/App.jsx exists
        if "src/App.jsx" not in files and "src/App.js" not in files:
            files["src/App.jsx"] = (
                "import React from 'react';\n"
                "import { BrowserRouter, Routes, Route } from 'react-router-dom';\n"
                "import HomePage from './pages/HomePage';\n"
                "import DashboardPage from './pages/DashboardPage';\n"
                "import './styles/global.css';\n"
                "\n"
                "export default function App() {\n"
                "  return (\n"
                "    <BrowserRouter>\n"
                "      <Routes>\n"
                '        <Route path="/" element={<HomePage />} />\n'
                '        <Route path="/dashboard" element={<DashboardPage />} />\n'
                "      </Routes>\n"
                "    </BrowserRouter>\n"
                "  );\n"
                "}\n"
            )

        # Ensure store exists
        if "src/store/useAppStore.js" not in files:
            files["src/store/useAppStore.js"] = (
                "import { create } from 'zustand';\n"
                "\n"
                "const useAppStore = create((set) => ({\n"
                "  user: null,\n"
                "  items: [],\n"
                "  isLoading: false,\n"
                "  setUser: (user) => set({ user }),\n"
                "  setItems: (items) => set({ items }),\n"
                "  setLoading: (isLoading) => set({ isLoading }),\n"
                "}));\n"
                "\n"
                "export default useAppStore;\n"
            )

        # Ensure ErrorBoundary exists
        if "src/components/ErrorBoundary.jsx" not in files:
            files["src/components/ErrorBoundary.jsx"] = (
                "import React from 'react';\n"
                "\n"
                "export default class ErrorBoundary extends React.Component {\n"
                "  constructor(props) {\n"
                "    super(props);\n"
                '    this.state = { hasError: false, error: null };\n'
                "  }\n"
                "  static getDerivedStateFromError(error) {\n"
                '    return { hasError: true, error };\n'
                "  }\n"
                "  render() {\n"
                "    if (this.state.hasError) {\n"
                "      return (\n"
                '        <div style={{ padding: 24, color: "#c00" }}>\n'
                '          <h2>Something went wrong</h2>\n'
                '          <p>{this.state.error?.message}</p>\n'
                "        </div>\n"
                "      );\n"
                "    }\n"
                "    return this.props.children;\n"
                "  }\n"
                "}\n"
            )

        # Ensure global.css exists
        if "src/styles/global.css" not in files:
            files["src/styles/global.css"] = (
                "* { box-sizing: border-box; margin: 0; padding: 0; }\n"
                "body { font-family: system-ui, -apple-system, sans-serif; background: #fff; color: #111; }\n"
                "a { color: inherit; text-decoration: none; }\n"
            )

        # Ensure vite.config.js exists
        if "vite.config.js" not in files:
            files["vite.config.js"] = (
                "import { defineConfig } from 'vite';\n"
                "import react from '@vitejs/plugin-react';\n"
                "\n"
                "export default defineConfig({\n"
                "  plugins: [react()],\n"
                "  server: { host: '0.0.0.0', port: 5173 },\n"
                "});\n"
            )

        # Ensure backend/main.py exists with FastAPI
        if "backend/main.py" not in files:
            files["backend/main.py"] = (
                '"""FastAPI backend generated by CrucibAI BuilderAgent."""\n'
                "from fastapi import FastAPI\n"
                "from fastapi.middleware.cors import CORSMiddleware\n"
                "from datetime import datetime, timezone\n"
                "\n"
                'app = FastAPI(title="Generated API", version="0.1.0")\n'
                "app.add_middleware(\n"
                "    CORSMiddleware,\n"
                '    allow_origins=["*"],\n'
                '    allow_methods=["*"],\n'
                '    allow_headers=["*"],\n'
                ")\n"
                "\n"
                "\n"
                "@app.get(\"/health\")\n"
                "async def health():\n"
                '    return {"status": "ok", "ts": datetime.now(timezone.utc).isoformat()}\n'
                "\n"
                "\n"
                '@app.get("/api/items")\n'
                "async def list_items():\n"
                '    return {"items": [{"id": 1, "title": "Demo item", "created": datetime.now(timezone.utc).isoformat()}]}\n'
                "\n"
                "\n"
                '@app.get("/api/stats")\n'
                "async def stats():\n"
                '    return {"total_items": 1, "version": "0.1.0"}\n'
                "\n"
                "\n"
                '@app.post("/api/items")\n'
                'async def create_item(title: str = "New Item"):\n'
                '    return {"id": 2, "title": title}\n'
            )

        # Ensure backend/requirements.txt exists
        if "backend/requirements.txt" not in files:
            files["backend/requirements.txt"] = "fastapi\nuvicorn\npydantic\n"

        return files

    def _extract_api_spec(self, files: Dict[str, str]) -> List[Dict[str, str]]:
        """Extract API endpoints from backend/main.py."""
        endpoints = []
        main_py = files.get("backend/main.py", "")
        _DQUOTE = '"'
        _SQUOTE = "'"
        for line in main_py.split("\n"):
            line = line.strip()
            if line.startswith("@app."):
                parts = line.replace("(", " ").replace(")", " ").split()
                if len(parts) >= 2:
                    method_parts = parts[0].split(".")
                    method = method_parts[-1].upper() if len(method_parts) > 1 else "GET"
                    path = parts[1].strip(_DQUOTE).strip(_SQUOTE)
                    endpoints.append({
                        "method": method,
                        "path": path,
                        "description": f"Auto-detected {method} {path}",
                    })

        if not endpoints:
            endpoints = [
                {"method": "GET", "path": "/health", "description": "Health check"},
                {"method": "GET", "path": "/api/items", "description": "List items"},
            ]

        return endpoints

"""
builder_agent.py -- Full-system builder agent for CrucibAI.

Generates complete fullstack applications from a goal description.
Supports multiple language/framework stacks via the template registry:
  - Python FastAPI + React/Vite (default)
  - Node Express + React/Vite
  - Python CLI (no frontend)
  - C++ CMake (no frontend)
  - Go Gin (no frontend)
  - Rust Axum (no frontend)

Templates provide the base scaffold; LLM is used for goal-specific customization.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from backend.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stack-aware system prompt builder
# ---------------------------------------------------------------------------

def _build_system_prompt(stack_id: str) -> str:
    """Return a system prompt tailored to the selected stack."""
    # ---- Python FastAPI + React/Vite (default) ----
    if stack_id == "python_fastapi":
        return (
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

    # ---- Node Express + React/Vite ----
    if stack_id == "node_express":
        return (
            "You are a senior fullstack engineer. Given a product goal, generate a COMPLETE working application.\n"
            "\n"
            "## CRITICAL RULES\n"
            "1. Output ONLY a JSON object with a \"files\" key mapping file paths to their content.\n"
            "2. Every file must contain REAL, WORKING code -- no placeholders, no TODO comments, no \"...\" stubs.\n"
            "3. Frontend: Use Vite + React + JavaScript (JSX). Use react-router-dom for routing.\n"
            "4. Backend: Use Node.js + Express. All backend files go under \"backend/\".\n"
            "5. Include: package.json, vite.config.js, index.html, src/main.jsx, src/App.jsx.\n"
            "6. Include: backend/server.js with at least 4 real endpoints (not just health).\n"
            "7. Include: backend/package.json with express, cors, and other Node dependencies.\n"
            "8. The backend server.js MUST have: express(), cors middleware, and JSON body parser.\n"
            "9. Every React component must be a valid JSX module with proper imports.\n"
            "10. package.json must include: react, react-dom, react-router-dom, zustand, @vitejs/plugin-react, vite.\n"
            "\n"
            "## OUTPUT FORMAT\n"
            "Return a single JSON object with \"files\" and \"api_spec\" keys.\n"
            "Do NOT wrap the JSON in markdown fences. Output raw JSON only."
        )

    # ---- Python CLI ----
    if stack_id == "python_cli":
        return (
            "You are a senior Python engineer. Given a product goal, generate a COMPLETE working CLI application.\n"
            "\n"
            "## CRITICAL RULES\n"
            "1. Output ONLY a JSON object with a \"files\" key mapping file paths to their content.\n"
            "2. Every file must contain REAL, WORKING Python code -- no placeholders, no TODO comments, no \"...\" stubs.\n"
            "3. Use argparse or click for CLI argument parsing.\n"
            "4. Include: cli/main.py (entry point), cli/utils.py, cli/models.py, requirements.txt, pyproject.toml.\n"
            "5. The CLI must have at least 3 subcommands related to the goal.\n"
            "6. Include helpful --help output for all commands.\n"
            "\n"
            "## OUTPUT FORMAT\n"
            "Return a single JSON object with \"files\" key.\n"
            "Do NOT wrap the JSON in markdown fences. Output raw JSON only."
        )

    # ---- C++ CMake ----
    if stack_id == "cpp_cmake":
        return (
            "You are a senior C++ engineer. Given a product goal, generate a COMPLETE working C++ application.\n"
            "\n"
            "## CRITICAL RULES\n"
            "1. Output ONLY a JSON object with a \"files\" key mapping file paths to their content.\n"
            "2. Every file must contain REAL, WORKING C++ code -- no placeholders, no TODO comments, no \"...\" stubs.\n"
            "3. Use CMake as the build system.\n"
            "4. Include: CMakeLists.txt, src/main.cpp, and all header/source files.\n"
            "5. The application must compile with g++ or clang++.\n"
            "\n"
            "## OUTPUT FORMAT\n"
            "Return a single JSON object with \"files\" key.\n"
            "Do NOT wrap the JSON in markdown fences. Output raw JSON only."
        )

    # ---- Go Gin ----
    if stack_id == "go_gin":
        return (
            "You are a senior Go engineer. Given a product goal, generate a COMPLETE working Go web application.\n"
            "\n"
            "## CRITICAL RULES\n"
            "1. Output ONLY a JSON object with a \"files\" key mapping file paths to their content.\n"
            "2. Every file must contain REAL, WORKING Go code -- no placeholders, no TODO comments, no \"...\" stubs.\n"
            "3. Use the Gin web framework.\n"
            "4. Include: main.go, handlers/handlers.go, models/models.go, go.mod.\n"
            "5. The main.go MUST have: gin.Default(), CORS middleware, and at least 4 real endpoints.\n"
            "\n"
            "## OUTPUT FORMAT\n"
            "Return a single JSON object with \"files\" and \"api_spec\" keys.\n"
            "Do NOT wrap the JSON in markdown fences. Output raw JSON only."
        )

    # ---- Rust Axum ----
    if stack_id == "rust_axum":
        return (
            "You are a senior Rust engineer. Given a product goal, generate a COMPLETE working Rust web application.\n"
            "\n"
            "## CRITICAL RULES\n"
            "1. Output ONLY a JSON object with a \"files\" key mapping file paths to their content.\n"
            "2. Every file must contain REAL, WORKING Rust code -- no placeholders, no TODO comments, no \"...\" stubs.\n"
            "3. Use the Axum web framework with Tokio.\n"
            "4. Include: Cargo.toml, src/main.rs, src/handlers.rs, src/models.rs.\n"
            "5. The main.rs MUST have: axum::Router, tower-http CORS, and at least 4 real endpoints.\n"
            "\n"
            "## OUTPUT FORMAT\n"
            "Return a single JSON object with \"files\" and \"api_spec\" keys.\n"
            "Do NOT wrap the JSON in markdown fences. Output raw JSON only."
        )

    # ---- Generic fallback ----
    return (
        "You are a senior fullstack engineer. Given a product goal, generate a COMPLETE working application.\n"
        "\n"
        "## CRITICAL RULES\n"
        "1. Output ONLY a JSON object with a \"files\" key mapping file paths to their content.\n"
        "2. Every file must contain REAL, WORKING code -- no placeholders, no TODO comments, no \"...\" stubs.\n"
        "\n"
        "## OUTPUT FORMAT\n"
        "Return a single JSON object with \"files\" key.\n"
        "Do NOT wrap the JSON in markdown fences. Output raw JSON only."
    )


# ---------------------------------------------------------------------------
# Mapping of stack IDs to their template generator functions
# ---------------------------------------------------------------------------

# Import template generators with a safety net
_TEMPLATE_GENERATORS: Dict[str, Any] = {}
try:
    from backend.agents.templates import (
        generate_python_fastapi,
        generate_node_express,
        generate_react_vite,
        generate_python_cli,
        generate_cpp_cmake,
        generate_go_gin,
        generate_rust_axum,
    )
    _TEMPLATE_GENERATORS = {
        "python_fastapi": generate_python_fastapi,
        "node_express": generate_node_express,
        "react_vite": generate_react_vite,
        "python_cli": generate_python_cli,
        "cpp_cmake": generate_cpp_cmake,
        "go_gin": generate_go_gin,
        "rust_axum": generate_rust_axum,
    }
    _TEMPLATES_AVAILABLE = True
except (ImportError, SyntaxError) as exc:
    logger.warning("Template module import failed — falling back to LLM-only: %s", exc)
    _TEMPLATES_AVAILABLE = False

# Stacks that include a frontend (React/Vite)
_FULLSTACK_BACKENDS = {"python_fastapi", "node_express"}

# Stacks with no frontend
_BACKEND_ONLY = {"python_cli", "cpp_cmake", "go_gin", "rust_axum"}


class BuilderAgent(BaseAgent):
    """Generates complete fullstack applications from a goal.

    Supports multiple language/framework stacks via the template registry.
    Templates provide the base scaffold; LLM is used for goal-specific
    customization on top of the template output.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "BuilderAgent"

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Main execution
    # ------------------------------------------------------------------

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("REAL_BUILDER_AGENT_USED")
        goal = (context.get("goal") or context.get("user_prompt") or "").strip()
        if not goal:
            return {"status": "error", "reason": "no_goal", "files": {}}

        max_tokens = int(context.get("max_tokens") or 12000)
        model = context.get("llm_model") or "cerebras"

        # ----------------------------------------------------------------
        # Step 1: Determine the selected stack
        # ----------------------------------------------------------------
        selected_stack = context.get("selected_stack")
        template_entry = None
        stack_id = None

        if selected_stack and isinstance(selected_stack, dict):
            # StackSelectorAgent or upstream agent already chose a stack
            stack_id = selected_stack.get("id") or selected_stack.get("template_id")
            logger.info("BuilderAgent: using context-provided stack: %s", stack_id)
        elif selected_stack and isinstance(selected_stack, str):
            stack_id = selected_stack
            logger.info("BuilderAgent: using context-provided stack string: %s", stack_id)

        # Resolve via template registry
        if _TEMPLATES_AVAILABLE and stack_id:
            try:
                from backend.agents.templates.registry import TEMPLATE_REGISTRY
                if stack_id in TEMPLATE_REGISTRY:
                    template_entry = TEMPLATE_REGISTRY[stack_id]
            except (ImportError, SyntaxError):
                pass

        if template_entry is None and _TEMPLATES_AVAILABLE:
            try:
                from backend.agents.templates import select_template
                template_entry = select_template(goal)
                stack_id = template_entry.get("id")
                logger.info("BuilderAgent: auto-detected template: %s (confidence: %s)",
                            stack_id, template_entry.get("confidence"))
            except Exception as exc:
                logger.warning("BuilderAgent: template auto-detection failed: %s", exc)

        # ----------------------------------------------------------------
        # Step 2: Generate base files using templates
        # ----------------------------------------------------------------
        files: Dict[str, str] = {}
        generation_method = "none"

        if template_entry and _TEMPLATES_AVAILABLE and stack_id:
            try:
                files = self._generate_from_templates(stack_id, goal)
                generation_method = "templates"
                logger.info("BuilderAgent: generated %d files from templates (stack=%s)",
                            len(files), stack_id)
            except Exception as exc:
                logger.error("BuilderAgent: template generation failed: %s — falling back to LLM", exc)
                files = {}

        # ----------------------------------------------------------------
        # Step 3: If templates produced files, optionally customize via LLM
        # ----------------------------------------------------------------
        if files and generation_method == "templates":
            customize = context.get("customize_with_llm", True)
            if customize:
                try:
                    files = await self._customize_with_llm(files, goal, stack_id, model, max_tokens)
                    generation_method = "templates+llm"
                    logger.info("BuilderAgent: LLM customization applied (%d files after merge)", len(files))
                except Exception as exc:
                    logger.warning("BuilderAgent: LLM customization failed (keeping templates only): %s", exc)

        # ----------------------------------------------------------------
        # Step 4: If templates failed entirely, fall back to LLM-only
        # ----------------------------------------------------------------
        if not files:
            logger.info("BuilderAgent: falling back to LLM-only generation")
            try:
                files = await self._generate_with_llm(goal, stack_id, model, max_tokens)
                generation_method = "llm_fallback"
            except Exception as exc:
                logger.error("BuilderAgent: LLM generation also failed: %s", exc)
                return {
                    "status": "error",
                    "reason": f"all_generation_failed: {exc}",
                    "files": {},
                }

        # ----------------------------------------------------------------
        # Step 5: Safety net — ensure critical files for the selected stack
        # ----------------------------------------------------------------
        files = self._ensure_critical_files(files, goal, stack_id=stack_id)

        # ----------------------------------------------------------------
        # Step 6: Build result
        # ----------------------------------------------------------------
        api_spec = {"endpoints": self._extract_api_spec(files)}

        result: Dict[str, Any] = {
            "status": "success",
            "files": files,
            "api_spec": api_spec,
            "_agent": "BuilderAgent",
            "_build_target": "full_system_generator",
            "_generation_method": generation_method,
            "_stack_id": stack_id,
        }

        # Include confidence if we have it from the template
        if template_entry:
            result["_template_confidence"] = template_entry.get("confidence", 0.0)
            result["_template_info"] = {
                "id": template_entry.get("id"),
                "language": template_entry.get("language"),
                "framework": template_entry.get("framework"),
                "build_command": template_entry.get("build_command"),
                "run_command": template_entry.get("run_command"),
            }

        return result

    # ------------------------------------------------------------------
    # Template-based generation
    # ------------------------------------------------------------------

    def _generate_from_templates(self, stack_id: str, goal: str) -> Dict[str, str]:
        """Generate base project files using the template registry.

        Wraps each template generator call in try/except so that a single
        broken template does not prevent the entire build.
        """
        project_name = self._derive_project_name(goal)
        files: Dict[str, str] = {}

        def _safe_call(fn, label: str) -> Dict[str, str]:
            """Call *fn* and return its output, or an empty dict on error."""
            try:
                return fn(goal, project_name)
            except Exception as exc:
                logger.warning("BuilderAgent: template %s failed: %s", label, exc)
                return {}

        # Determine backend and frontend template IDs
        if stack_id in _FULLSTACK_BACKENDS:
            # Fullstack: backend template + React/Vite frontend
            backend_fn = _TEMPLATE_GENERATORS.get(stack_id)
            frontend_fn = _TEMPLATE_GENERATORS.get("react_vite")

            if backend_fn:
                files.update(_safe_call(backend_fn, f"backend({stack_id})"))
            if frontend_fn:
                files.update(_safe_call(frontend_fn, "frontend(react_vite)"))

        elif stack_id in _BACKEND_ONLY:
            # Backend-only stacks
            gen_fn = _TEMPLATE_GENERATORS.get(stack_id)
            if gen_fn:
                files.update(_safe_call(gen_fn, stack_id))

        elif stack_id == "react_vite":
            # Frontend-only
            gen_fn = _TEMPLATE_GENERATORS.get("react_vite")
            if gen_fn:
                files.update(_safe_call(gen_fn, "react_vite"))

        if not files:
            raise ValueError(f"No files generated for stack_id={stack_id!r}")

        return files

    # ------------------------------------------------------------------
    # LLM customization of template output
    # ------------------------------------------------------------------

    async def _customize_with_llm(
        self,
        template_files: Dict[str, str],
        goal: str,
        stack_id: str,
        model: str,
        max_tokens: int,
    ) -> Dict[str, str]:
        """Call LLM to enhance template output with goal-specific content.

        The LLM receives the template file *paths* and a summary, and returns
        a JSON dict of file contents to **merge** on top of the templates.
        Template files always win on conflicts — LLM can only add or refine.
        """
        system_prompt = _build_system_prompt(stack_id or "python_fastapi")

        file_list = "\n".join(f"  - {path}" for path in sorted(template_files.keys()))
        user_prompt = (
            f"An application is being built for this goal:\n\n{goal}\n\n"
            f"Template-generated files (base scaffold):\n{file_list}\n\n"
            f"Your job is to CUSTOMIZE these files for the specific goal. Output a JSON object "
            f'with a "files" key. Each key is a file path from the list above, and the value is '
            f"the ENHANCED content. You may also add NEW files not in the list.\n\n"
            f"Rules:\n"
            f"- Keep the same file structure and conventions as the templates.\n"
            f"- Make content specific to the goal (real endpoints, real page content, real data).\n"
            f"- Do NOT change imports, framework setup, or configuration that makes the app work.\n"
            f"- Output ONLY the JSON with the \"files\" key. No markdown fences."
        )

        raw, _tokens = await self.call_llm(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=0.4,
            max_tokens=max_tokens,
            stream=True,
        )

        llm_files = self._extract_files(raw)
        if llm_files:
            # Merge: template files form the base, LLM enhancements overlay
            merged = {**template_files, **llm_files}
            return merged

        return template_files

    # ------------------------------------------------------------------
    # Pure LLM fallback (when templates are unavailable)
    # ------------------------------------------------------------------

    async def _generate_with_llm(
        self, goal: str, stack_id: Optional[str], model: str, max_tokens: int,
    ) -> Dict[str, str]:
        """Generate files entirely via LLM when templates are unavailable."""
        stack_id = stack_id or "python_fastapi"
        system_prompt = _build_system_prompt(stack_id)

        if stack_id == "python_fastapi":
            user_prompt = (
                f"Build a complete fullstack application for this goal:\n\n{goal}\n\n"
                f"Generate the full JSON with all files. Include at minimum:\n"
                f"- package.json (with react, react-dom, react-router-dom, zustand, vite, @vitejs/plugin-react)\n"
                f"- vite.config.js\n"
                f'- index.html with <div id="root"></div> and <script type="module" src="/src/main.jsx"></script>\n'
                f"- src/main.jsx (createRoot render)\n"
                f"- src/App.jsx (router with at least 3 pages)\n"
                f"- src/pages/HomePage.jsx (real content about the goal)\n"
                f"- src/pages/DashboardPage.jsx (real dashboard with data)\n"
                f"- src/store/useAppStore.js (zustand store)\n"
                f"- src/components/ErrorBoundary.jsx\n"
                f"- src/styles/global.css\n"
                f"- backend/main.py (FastAPI app with CORSMiddleware, at least 4 real endpoints)\n"
                f"- backend/requirements.txt (fastapi, uvicorn, pydantic)\n"
                f"- backend/models.py (pydantic models)\n"
                f"- backend/auth.py\n"
                f"Make every endpoint return REAL data related to the goal. No placeholder responses."
            )
        elif stack_id == "node_express":
            user_prompt = (
                f"Build a complete Node.js + Express fullstack application for this goal:\n\n{goal}\n\n"
                f"Generate the full JSON with all files. Include at minimum:\n"
                f"- package.json (with react, react-dom, react-router-dom, zustand, vite)\n"
                f"- vite.config.js\n"
                f'- index.html with <div id="root"></div> and <script type="module" src="/src/main.jsx"></script>\n'
                f"- src/main.jsx, src/App.jsx, src/pages/HomePage.jsx, src/pages/DashboardPage.jsx\n"
                f"- src/store/useAppStore.js, src/components/ErrorBoundary.jsx, src/styles/global.css\n"
                f"- backend/server.js (Express app with CORS, at least 4 real endpoints)\n"
                f"- backend/package.json (express, cors)\n"
                f"- backend/routes/api.js\n"
                f"Make every endpoint return REAL data related to the goal. No placeholder responses."
            )
        elif stack_id == "python_cli":
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
        elif stack_id in ("go_gin", "rust_axum", "cpp_cmake"):
            user_prompt = (
                f"Build a complete {stack_id.replace('_', ' ').title()} application for this goal:\n\n{goal}\n\n"
                f"Generate the full JSON with all required source files, config files, and build files.\n"
                f"Make the application fully functional with real logic related to the goal."
            )
        else:
            user_prompt = (
                f"Build a complete fullstack application for this goal:\n\n{goal}\n\n"
                f"Generate the full JSON with all files. Use React+Vite frontend and FastAPI backend.\n"
                f"Make every endpoint and page contain REAL content related to the goal."
            )

        raw, _tokens = await self.call_llm(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=0.4,
            max_tokens=max_tokens,
            stream=True,
        )

        return self._extract_files(raw)

    # ------------------------------------------------------------------
    # Utility helpers (preserved from original)
    # ------------------------------------------------------------------

    def _derive_project_name(self, goal: str) -> str:
        """Derive a safe project name from the goal text."""
        import re
        words = re.findall(r"[a-zA-Z0-9]+", goal.lower())
        if not words:
            return "app"
        # Take up to 3 meaningful words
        meaningful = [w for w in words if len(w) > 2][:3]
        return "_".join(meaningful) if meaningful else words[0]

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

    def _ensure_critical_files(
        self,
        files: Dict[str, str],
        goal: str,
        stack_id: Optional[str] = None,
    ) -> Dict[str, str]:
        """Add critical files if the LLM/templates did not generate them.

        Acts as a safety net. Stack-aware — only adds files relevant to the
        selected stack. Falls back to React+FastAPI defaults when stack_id is
        None.
        """
        stack_id = stack_id or "python_fastapi"

        # --- React/Vite frontend checks (for fullstack stacks) ---
        if stack_id in _FULLSTACK_BACKENDS or stack_id == "react_vite":
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
                    "}\n"
                    "  static getDerivedStateFromError(error) {\n"
                    '    return { hasError: true, error };\n'
                    "}\n"
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

        # --- Backend checks per stack ---
        if stack_id == "python_fastapi":
            self._ensure_fastapi_files(files)
        elif stack_id == "node_express":
            self._ensure_express_files(files)

        # Backend-only stacks: minimal safety checks
        if stack_id == "python_cli":
            if "cli/main.py" not in files and "main.py" not in files:
                files["cli/main.py"] = (
                    '"""CLI application generated by CrucibAI."""\n'
                    'import argparse\n'
                    'import sys\n'
                    '\n'
                    'def main():\n'
                    '    parser = argparse.ArgumentParser(description="Generated CLI")\n'
                    '    subparsers = parser.add_subparsers(dest="command")\n'
                    '    subparsers.add_parser("run", help="Run the application")\n'
                    '    subparsers.add_parser("status", help="Show status")\n'
                    '    args = parser.parse_args()\n'
                    '    if args.command == "run":\n'
                    '        print("Running...")\n'
                    '    elif args.command == "status":\n'
                    '        print("OK")\n'
                    '    else:\n'
                    '        parser.print_help()\n'
                    '\n'
                    'if __name__ == "__main__":\n'
                    '    main()\n'
                )

        return files

    def _ensure_fastapi_files(self, files: Dict[str, str]) -> None:
        """Ensure critical FastAPI backend files exist (mutates *files* in place)."""
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

        if "backend/requirements.txt" not in files:
            files["backend/requirements.txt"] = "fastapi\nuvicorn\npydantic\n"

    def _ensure_express_files(self, files: Dict[str, str]) -> None:
        """Ensure critical Express backend files exist (mutates *files* in place)."""
        if "backend/server.js" not in files:
            files["backend/server.js"] = (
                'const express = require("express");\n'
                'const cors = require("cors");\n'
                'const app = express();\n'
                'const PORT = process.env.PORT || 3001;\n'
                '\n'
                'app.use(cors());\n'
                'app.use(express.json());\n'
                '\n'
                'app.get("/health", (req, res) => {\n'
                '  res.json({ status: "ok", ts: new Date().toISOString() });\n'
                '});\n'
                '\n'
                'app.get("/api/items", (req, res) => {\n'
                '  res.json({ items: [{ id: 1, title: "Demo item" }] });\n'
                '});\n'
                '\n'
                'app.post("/api/items", (req, res) => {\n'
                '  const { title } = req.body;\n'
                '  res.json({ id: 2, title: title || "New Item" });\n'
                '});\n'
                '\n'
                'app.get("/api/stats", (req, res) => {\n'
                '  res.json({ total_items: 1, version: "0.1.0" });\n'
                '});\n'
                '\n'
                'app.listen(PORT, () => {\n'
                '  console.log(`Server running on port ${PORT}`);\n'
                '});\n'
            )

        if "backend/package.json" not in files:
            files["backend/package.json"] = json.dumps({
                "name": "backend",
                "version": "0.1.0",
                "main": "server.js",
                "scripts": {"start": "node server.js", "dev": "node --watch server.js"},
                "dependencies": {"express": "^4.18.0", "cors": "^2.8.5"},
            }, indent=2)

    def _extract_api_spec(self, files: Dict[str, str]) -> List[Dict[str, str]]:
        """Extract API endpoints from backend files.

        Supports FastAPI (@app.get/post), Express (app.get/post),
        and Gin (r.GET/POST) patterns.
        """
        endpoints = []

        # Check FastAPI backend
        main_py = files.get("backend/main.py", "")
        if main_py:
            endpoints.extend(self._extract_fastapi_endpoints(main_py))

        # Check Express backend
        server_js = files.get("backend/server.js", "")
        if server_js:
            endpoints.extend(self._extract_express_endpoints(server_js))

        # Check Go Gin backend
        main_go = files.get("main.go", "")
        handlers_go = files.get("handlers/handlers.go", "")
        if main_go:
            endpoints.extend(self._extract_gin_endpoints(main_go))
        if handlers_go:
            endpoints.extend(self._extract_gin_endpoints(handlers_go))

        # Check Rust Axum backend
        main_rs = files.get("src/main.rs", "")
        handlers_rs = files.get("src/handlers.rs", "")
        if main_rs:
            endpoints.extend(self._extract_axum_endpoints(main_rs))
        if handlers_rs:
            endpoints.extend(self._extract_axum_endpoints(handlers_rs))

        if not endpoints:
            endpoints = [
                {"method": "GET", "path": "/health", "description": "Health check"},
                {"method": "GET", "path": "/api/items", "description": "List items"},
            ]

        return endpoints

    @staticmethod
    def _extract_fastapi_endpoints(source: str) -> List[Dict[str, str]]:
        """Parse @app.get("/path") decorators from Python source."""
        endpoints = []
        for line in source.split("\n"):
            line = line.strip()
            if line.startswith("@app."):
                parts = line.replace("(", " ").replace(")", " ").split()
                if len(parts) >= 2:
                    method_parts = parts[0].split(".")
                    method = method_parts[-1].upper() if len(method_parts) > 1 else "GET"
                    path = parts[1].strip('"\'')
                    endpoints.append({"method": method, "path": path, "description": f"Auto-detected {method} {path}"})
        return endpoints

    @staticmethod
    def _extract_express_endpoints(source: str) -> List[Dict[str, str]]:
        """Parse app.get("/path") calls from JS source."""
        endpoints = []
        import re
        for match in re.finditer(r'\bapp\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']*)["\']', source):
            method = match.group(1).upper()
            path = match.group(2)
            endpoints.append({"method": method, "path": path, "description": f"Auto-detected {method} {path}"})
        return endpoints

    @staticmethod
    def _extract_gin_endpoints(source: str) -> List[Dict[str, str]]:
        """Parse r.GET("/path") calls from Go source."""
        endpoints = []
        import re
        for match in re.finditer(r'\b[rR]\.(GET|POST|PUT|DELETE|PATCH)\s*\(\s*["\']([^"\']*)["\']', source):
            method = match.group(1).upper()
            path = match.group(2)
            endpoints.append({"method": method, "path": path, "description": f"Auto-detected {method} {path}"})
        return endpoints

    @staticmethod
    def _extract_axum_endpoints(source: str) -> List[Dict[str, str]]:
        """Parse .route("/path", get(handler)) calls from Rust source."""
        endpoints = []
        import re
        for match in re.finditer(r'\.route\s*\(\s*"([^"]*)"', source):
            path = match.group(1)
            method = "GET"
            # Look for method annotations near the route
            for method_kw in ["get", "post", "put", "delete", "patch"]:
                if method_kw in source[match.start():match.start() + 200]:
                    method = method_kw.upper()
                    break
            endpoints.append({"method": method, "path": path, "description": f"Auto-detected {method} {path}"})
        return endpoints

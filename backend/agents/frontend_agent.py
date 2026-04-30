"""
frontend_agent.py — Frontend code generation agent for CrucibAI.

Generates frontend code from a goal description. Currently supports:
  - React/Vite (default, fully implemented)

Architecture is multi-framework ready — new frontend templates
(nextjs, vue, etc.) can be added to the template registry and this
agent will route to them via ``context["frontend_framework"]``.
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
    "react_vite": """\
You are a senior React frontend engineer. Given a product goal, generate a COMPLETE working React frontend.

## CRITICAL RULES
1. Output ONLY a JSON object with a "files" key mapping file paths to their content.
2. Every file must contain REAL, WORKING JSX code — no placeholders, no TODO, no "..." stubs.
3. Use Vite + React + JavaScript (JSX).
4. Use react-router-dom for routing (BrowserRouter, Routes, Route).
5. Use zustand for state management.
6. All files are under "src/" unless they're config files at root level.
7. Components must import React and use proper JSX syntax.
8. Pages must be complete, with real content related to the goal.
9. CSS goes in src/styles/global.css using standard CSS (no Tailwind, no CSS modules).
10. Every component must be a default export function.

## REQUIRED FILES
- src/main.jsx — createRoot render with StrictMode
- src/App.jsx — BrowserRouter with Routes
- src/pages/HomePage.jsx — Landing/home page with real content
- src/pages/DashboardPage.jsx — Dashboard with data display
- src/pages/LoginPage.jsx — Login form
- src/store/useAppStore.js — zustand store
- src/components/ErrorBoundary.jsx — React error boundary
- src/components/ShellLayout.jsx — App shell with nav
- src/styles/global.css — Base styles

## OUTPUT FORMAT
Return a single JSON object:
{
  "files": {
    "src/main.jsx": "...",
    "src/App.jsx": "...",
    "src/pages/HomePage.jsx": "...",
    ...
  }
}

Do NOT wrap the JSON in markdown fences. Output raw JSON only.\
""",

    # --- Placeholder prompts for future frameworks ---
    "nextjs": """\
You are a senior React/Next.js frontend engineer. Given a product goal, generate a COMPLETE working Next.js application.

## CRITICAL RULES
1. Output ONLY a JSON object with a "files" key mapping file paths to their content.
2. Every file must contain REAL, WORKING code — no placeholders, no TODO, no "..." stubs.
3. Use Next.js with App Router.
4. Use TypeScript (.tsx, .ts).
5. All pages go under "app/" directory.
6. Components must be valid React Server Components or Client Components as appropriate.

## OUTPUT FORMAT
Return a single JSON object with "files" key.
Do NOT wrap the JSON in markdown fences. Output raw JSON only.\
""",

    "vue": """\
You are a senior Vue.js frontend engineer. Given a product goal, generate a COMPLETE working Vue.js application.

## CRITICAL RULES
1. Output ONLY a JSON object with a "files" key mapping file paths to their content.
2. Every file must contain REAL, WORKING code — no placeholders, no TODO, no "..." stubs.
3. Use Vue 3 with Composition API.
4. Use Vue Router for routing.
5. Use Pinia for state management.

## OUTPUT FORMAT
Return a single JSON object with "files" key.
Do NOT wrap the JSON in markdown fences. Output raw JSON only.\
""",
}

# ---------------------------------------------------------------------------
# Template imports (with safety net)
# ---------------------------------------------------------------------------

_TEMPLATE_GENERATORS: Dict[str, Any] = {}

try:
    from backend.agents.templates import generate_react_vite
    _TEMPLATE_GENERATORS["react_vite"] = generate_react_vite
    _TEMPLATES_AVAILABLE = True
except (ImportError, SyntaxError) as exc:
    logger.warning("FrontendAgent: template import failed — LLM-only mode: %s", exc)
    _TEMPLATES_AVAILABLE = False

# Mapping of context framework names to template generator keys
_FRAMEWORK_TO_TEMPLATE: Dict[str, str] = {
    "react_vite": "react_vite",
    "react": "react_vite",
    "react+vite": "react_vite",
    "nextjs": "nextjs",
    "vue": "vue",
}


class FrontendAgent(BaseAgent):
    """Generates frontend code from a goal.

    Currently supports React/Vite as the primary template. The architecture
    is multi-framework ready — new frameworks can be added by registering
    their template generators in the template registry and updating
    ``_SYSTEM_PROMPTS`` / ``_FRAMEWORK_TO_TEMPLATE`` above.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "FrontendAgent"

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_input(self, context: Dict[str, Any]) -> bool:
        super().validate_input(context)
        goal = (context.get("goal") or context.get("user_prompt") or "").strip()
        if len(goal) < 5:
            raise ValueError("FrontendAgent requires a goal with at least 5 characters")
        return True

    def validate_output(self, result: Dict[str, Any]) -> bool:
        super().validate_output(result)
        if not result.get("files"):
            raise ValueError("FrontendAgent output must contain a 'files' dictionary")
        return True

    # ------------------------------------------------------------------
    # Main execution
    # ------------------------------------------------------------------

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("REAL_FRONTEND_AGENT_USED")
        goal = (context.get("goal") or context.get("user_prompt") or "").strip()
        if not goal:
            return {"status": "error", "reason": "no_goal", "files": {}}

        # ----------------------------------------------------------------
        # Step 1: Determine the frontend framework
        # ----------------------------------------------------------------
        framework = self._resolve_framework(context)
        logger.info("FrontendAgent: resolved framework=%s", framework)

        # ----------------------------------------------------------------
        # Step 2: Generate base files using templates
        # ----------------------------------------------------------------
        files: Dict[str, str] = {}
        generation_method = "none"

        if _TEMPLATES_AVAILABLE:
            template_key = _FRAMEWORK_TO_TEMPLATE.get(framework)
            if template_key and template_key in _TEMPLATE_GENERATORS:
                try:
                    project_name = self._derive_project_name(goal)
                    files = _TEMPLATE_GENERATORS[template_key](goal, project_name)
                    generation_method = "templates"
                    logger.info("FrontendAgent: generated %d files from template %s", len(files), template_key)
                except Exception as exc:
                    logger.error("FrontendAgent: template generation failed: %s", exc)

        # ----------------------------------------------------------------
        # Step 3: If templates produced files, optionally customize via LLM
        # ----------------------------------------------------------------
        if files and generation_method == "templates":
            customize = context.get("customize_with_llm", True)
            if customize:
                try:
                    files = await self._customize_with_llm(files, goal, framework)
                    generation_method = "templates+llm"
                    logger.info("FrontendAgent: LLM customization applied")
                except Exception as exc:
                    logger.warning("FrontendAgent: LLM customization failed (keeping templates): %s", exc)

        # ----------------------------------------------------------------
        # Step 4: Fall back to LLM-only if templates unavailable or failed
        # ----------------------------------------------------------------
        if not files:
            logger.info("FrontendAgent: falling back to LLM-only generation")
            try:
                files = await self._generate_with_llm(goal, framework)
                generation_method = "llm_fallback"
            except Exception as exc:
                logger.error("FrontendAgent: LLM generation failed: %s", exc)
                return {
                    "status": "error",
                    "reason": f"all_generation_failed: {exc}",
                    "files": {},
                }

        # ----------------------------------------------------------------
        # Step 5: Ensure critical frontend files exist (safety net)
        # ----------------------------------------------------------------
        files = self._ensure_critical_files(files, goal, framework)

        # ----------------------------------------------------------------
        # Step 6: Build result
        # ----------------------------------------------------------------
        result: Dict[str, Any] = {
            "status": "success",
            "files": files,
            "_agent": "FrontendAgent",
            "_generation_method": generation_method,
            "_frontend_framework": framework,
        }

        return result

    # ------------------------------------------------------------------
    # Framework resolution
    # ------------------------------------------------------------------

    def _resolve_framework(self, context: Dict[str, Any]) -> str:
        """Determine the frontend framework from context or defaults.

        Priority:
        1. Explicit ``frontend_framework`` in context
        2. Framework embedded in ``selected_stack`` dict
        3. Auto-detect from goal text (basic keyword matching)
        4. Default to ``react_vite``
        """
        # 1. Explicit framework
        framework = context.get("frontend_framework")
        if framework and isinstance(framework, str):
            fw = framework.lower().strip()
            if fw in _SYSTEM_PROMPTS or fw in _FRAMEWORK_TO_TEMPLATE:
                return _FRAMEWORK_TO_TEMPLATE.get(fw, fw)

        # 2. From selected_stack
        selected_stack = context.get("selected_stack")
        if selected_stack and isinstance(selected_stack, dict):
            stack_fw = selected_stack.get("framework", "")
            if stack_fw:
                _fw_map = {
                    "react+vite": "react_vite",
                    "fastapi": "react_vite",    # backend stack → default frontend
                    "express": "react_vite",    # backend stack → default frontend
                }
                fw = _fw_map.get(stack_fw.lower(), stack_fw.lower())
                if fw in _SYSTEM_PROMPTS or fw in _FRAMEWORK_TO_TEMPLATE:
                    return _FRAMEWORK_TO_TEMPLATE.get(fw, fw)

        # 3. Basic keyword auto-detect from goal
        goal = (context.get("goal") or context.get("user_prompt") or "").lower()
        if "next.js" in goal or "nextjs" in goal or "next js" in goal:
            return "nextjs"
        if "vue" in goal and "vue" not in "preview" and "review" not in goal:
            return "vue"
        # React/Vite is the default — any mention of react/vite reinforces it

        # 4. Default
        return "react_vite"

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
        system_prompt = _SYSTEM_PROMPTS.get(framework, _SYSTEM_PROMPTS["react_vite"])

        file_list = "\n".join(f"  - {path}" for path in sorted(template_files.keys()))
        user_prompt = (
            f"An application frontend is being built for this goal:\n\n{goal}\n\n"
            f"Template-generated files (base scaffold):\n{file_list}\n\n"
            f"Your job is to CUSTOMIZE these files for the specific goal. Output a JSON object "
            f'with a "files" key. Each key is a file path from the list above, and the value is '
            f"the ENHANCED content. You may also add NEW files not in the list.\n\n"
            f"Rules:\n"
            f"- Keep the same file structure and conventions as the templates.\n"
            f"- Make content specific to the goal (real headings, real descriptions, real data).\n"
            f"- Do NOT change imports, framework setup, or configuration that makes the app work.\n"
            f"- Every page should have REAL content — real headings, real descriptions, real data.\n"
            f"- Output ONLY the JSON with the \"files\" key. No markdown fences."
        )

        raw, _tokens = await self.call_llm(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            model="cerebras",
            temperature=0.4,
            max_tokens=10000,
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
        system_prompt = _SYSTEM_PROMPTS.get(framework, _SYSTEM_PROMPTS["react_vite"])

        if framework == "react_vite":
            user_prompt = (
                f"Build a complete React frontend for this goal:\n\n{goal}\n\n"
                f"Generate the full JSON with all frontend files. Include at minimum:\n"
                f"- src/main.jsx (createRoot with StrictMode)\n"
                f"- src/App.jsx (BrowserRouter with at least 3 routes: /, /dashboard, /login)\n"
                f"- src/pages/HomePage.jsx (real landing page content about the goal)\n"
                f"- src/pages/DashboardPage.jsx (real dashboard with cards, stats, data)\n"
                f"- src/pages/LoginPage.jsx (working login form with email/password)\n"
                f"- src/store/useAppStore.js (zustand store with user, items, loading state)\n"
                f"- src/components/ErrorBoundary.jsx (class component error boundary)\n"
                f"- src/components/ShellLayout.jsx (nav bar + main content area)\n"
                f"- src/styles/global.css (professional styling with CSS variables)\n"
                f"Make every page have REAL content — real headings, real descriptions, real data.\n"
                f"Use inline styles or CSS classes. The app should look like a real product."
            )
        elif framework == "nextjs":
            user_prompt = (
                f"Build a complete Next.js frontend for this goal:\n\n{goal}\n\n"
                f"Generate the full JSON with all frontend files. Use App Router with TypeScript.\n"
                f"Include at minimum: app/layout.tsx, app/page.tsx, and at least 3 more pages.\n"
                f"Make every page have REAL content related to the goal."
            )
        elif framework == "vue":
            user_prompt = (
                f"Build a complete Vue.js frontend for this goal:\n\n{goal}\n\n"
                f"Generate the full JSON with all frontend files. Use Vue 3 with Composition API.\n"
                f"Include at minimum: src/main.ts, src/App.vue, and at least 3 pages/views.\n"
                f"Make every page have REAL content related to the goal."
            )
        else:
            user_prompt = (
                f"Build a complete React frontend for this goal:\n\n{goal}\n\n"
                f"Generate the full JSON with all frontend files.\n"
                f"Make every page have REAL content related to the goal."
            )

        raw, _tokens = await self.call_llm(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            model="cerebras",
            temperature=0.4,
            max_tokens=10000,
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
            if isinstance(data, dict) and "files" in data:
                return {k: str(v) for k, v in data["files"].items()}
            if isinstance(data, dict):
                return {k: str(v) for k, v in data.items()}
        except json.JSONDecodeError:
            pass

        # Try markdown code fences
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
            try:
                data = json.loads(text)
                if isinstance(data, dict) and "files" in data:
                    return {k: str(v) for k, v in data["files"].items()}
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
                        return {k: str(v) for k, v in data["files"].items()}
                    if isinstance(data, dict):
                        return {k: str(v) for k, v in data.items()}
                except json.JSONDecodeError:
                    continue

        return {}

    def _ensure_critical_files(
        self, files: Dict[str, str], goal: str, framework: str = "react_vite",
    ) -> Dict[str, str]:
        """Ensure all required frontend files exist.

        Framework-aware — only injects files matching the active framework.
        Falls back to React/Vite defaults.
        """
        if framework in ("react_vite", "react"):
            self._ensure_react_vite_files(files)
        elif framework == "nextjs":
            # Future: add Next.js critical file injection
            logger.info("FrontendAgent: nextjs critical file checks not yet implemented")
        elif framework == "vue":
            # Future: add Vue critical file injection
            logger.info("FrontendAgent: vue critical file checks not yet implemented")
        else:
            self._ensure_react_vite_files(files)

        return files

    # ------------------------------------------------------------------
    # React/Vite critical file fallback (preserved from original)
    # ------------------------------------------------------------------

    @staticmethod
    def _ensure_react_vite_files(files: Dict[str, str]) -> None:
        """Inject missing React/Vite frontend files."""
        goal_escaped = "{}"  # Safety escape for f-string templates

        if "src/main.jsx" not in files:
            files["src/main.jsx"] = """\
import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
"""

        if "src/App.jsx" not in files:
            files["src/App.jsx"] = """\
import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import ShellLayout from './components/ShellLayout';
import HomePage from './pages/HomePage';
import DashboardPage from './pages/DashboardPage';
import LoginPage from './pages/LoginPage';
import './styles/global.css';

export default function App() {
  return (
    <BrowserRouter>
      <ShellLayout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/login" element={<LoginPage />} />
        </Routes>
      </ShellLayout>
    </BrowserRouter>
  );
}
"""

        if "src/store/useAppStore.js" not in files:
            files["src/store/useAppStore.js"] = """\
import { create } from 'zustand';

const useAppStore = create((set) => ({
  user: null,
  items: [],
  isLoading: false,
  error: null,
  setUser: (user) => set({ user }),
  setItems: (items) => set({ items }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
}));

export default useAppStore;
"""

        if "src/components/ErrorBoundary.jsx" not in files:
            files["src/components/ErrorBoundary.jsx"] = """\
import React from 'react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 24, color: '#c00' }}>
          <h2>Something went wrong</h2>
          <p>{this.state.error?.message}</p>
        </div>
      );
    }
    return this.props.children;
  }
}
"""

        if "src/components/ShellLayout.jsx" not in files:
            files["src/components/ShellLayout.jsx"] = """\
import React from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';

export default function ShellLayout({ children }) {
  const location = useLocation();
  const navItems = [
    { path: '/', label: 'Home' },
    { path: '/dashboard', label: 'Dashboard' },
    { path: '/login', label: 'Login' },
  ];

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <nav style={{
        display: 'flex',
        alignItems: 'center',
        gap: 24,
        padding: '12px 24px',
        borderBottom: '1px solid #e5e7eb',
        background: '#fff',
      }}>
        <strong style={{ fontSize: 18 }}>App</strong>
        <div style={{ display: 'flex', gap: 16 }}>
          {navItems.map(item => (
            <Link
              key={item.path}
              to={item.path}
              style={{
                color: location.pathname === item.path ? '#111' : '#666',
                fontWeight: location.pathname === item.path ? 700 : 400,
                fontSize: 14,
              }}
            >
              {item.label}
            </Link>
          ))}
        </div>
      </nav>
      <main style={{ flex: 1 }}>
        <Outlet />
      </main>
    </div>
  );
}
"""

        if "src/styles/global.css" not in files:
            files["src/styles/global.css"] = """\
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: system-ui, -apple-system, sans-serif; background: #fff; color: #111; line-height: 1.6; }
a { color: inherit; text-decoration: none; }
button { cursor: pointer; font: inherit; }
input, textarea { font: inherit; }
"""

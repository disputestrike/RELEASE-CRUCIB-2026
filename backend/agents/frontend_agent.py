"""
frontend_agent.py — Frontend code generation agent for CrucibAI.

Generates React/Vite frontend code from a goal description.
Produces real components, pages, routing, and styling.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from backend.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
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
"""


class FrontendAgent(BaseAgent):
    """Generates React/Vite frontend code from a goal."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "FrontendAgent"

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

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        goal = (context.get("goal") or context.get("user_prompt") or "").strip()
        if not goal:
            return {"status": "error", "reason": "no_goal", "files": {}}

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

        try:
            raw, tokens = await self.call_llm(
                user_prompt=user_prompt,
                system_prompt=_SYSTEM_PROMPT,
                model="cerebras",
                temperature=0.4,
                max_tokens=10000,
                stream=True,
            )
        except Exception as e:
            logger.error("FrontendAgent LLM call failed: %s", e)
            return {
                "status": "error",
                "reason": f"llm_failure: {e}",
                "files": {},
            }

        files = self._extract_files(raw)
        if not files:
            logger.warning("FrontendAgent: LLM output was not valid file dict, raw=%s...", (raw or "")[:300])
            return {
                "status": "error",
                "reason": "no_files_parsed",
                "files": {},
                "_raw": raw,
            }

        # Ensure critical frontend files exist
        files = self._ensure_critical_files(files, goal)

        return {
            "status": "success",
            "files": files,
            "_agent": "FrontendAgent",
        }

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

    def _ensure_critical_files(self, files: Dict[str, str], goal: str) -> Dict[str, str]:
        """Ensure all required frontend files exist."""
        goal_escaped = json.dumps(goal[:200])

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

        return files

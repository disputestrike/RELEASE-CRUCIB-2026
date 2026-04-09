"""
Production-shaped frontend bundle for Auto-Runner workspace (Sandpack-ready).
Explicit README marks gaps vs a full production deploy.

When ``job["build_target"]`` is set (e.g. ``next_app_router``), extra track files are added
without breaking the root Vite bundle verifiers expect.
"""
import json
import re
from typing import Dict, List, Tuple

from .build_targets import build_target_meta, normalize_build_target
from .enterprise_command_pack import build_enterprise_frontend_file_set, enterprise_command_intent


def _safe_goal_summary(goal: str) -> str:
    goal = re.sub(r"\s+", " ", (goal or "").strip())
    if not goal:
        return "Generated workspace ready for implementation and preview."
    if "helios aegis command" in goal.lower():
        return "Generated enterprise command workspace with CRM, quoting, policy approval, audit, and analytics surfaces."
    if len(goal) > 140:
        goal = goal[:137].rstrip() + "..."
    return f"Generated workspace aligned to: {goal}"


def _crucib_build_target_doc(job: Dict, target: str) -> str:
    meta = build_target_meta(target)
    g = "\n".join(f"- {x}" for x in meta["guarantees"])
    run = "\n".join(f"- {x}" for x in meta["on_this_run"])
    road = "\n".join(f"- {x}" for x in meta["roadmap"])
    return f"""# CrucibAI — build target for this job

**{meta["label"]}**

{meta["tagline"]}

Goal (excerpt): {(job.get("goal") or "").strip()[:500] or "(none)"}

## What this run is designed to deliver

{g}

## On this run (exactly)

{run}

## Roadmap (platform breadth — not narrowed)

{road}

---
*CrucibAI’s product direction is multi-stack and multi-modal; each Auto-Runner execution mode documents honest guarantees while we expand tracks (Next-native DAG, mobile, deeper automation, etc.).*
"""


def _next_app_stub_files(goal_snippet: str) -> List[Tuple[str, str]]:
    """Parallel Next.js 14 App Router starter — separate from root Vite package.json."""
    readme = f"""# Next.js App Router track (parallel to root Vite app)

This folder is a **standalone** Next.js app. The Auto-Runner still verifies the **root** Vite bundle for this job;
use this directory when you want to grow an App Router codebase without waiting for a first-class Next DAG.

## Your goal (reference)
{goal_snippet[:1200]}

## Commands
```bash
cd next-app-stub
npm install
npm run dev
```

## Notes
- Keep root `package.json` (Vite) intact for existing preview/verify flows.
- Merge or replace with a single Next monorepo when we ship a dedicated Next pipeline.
"""
    pkg = {
        "name": "crucibai-next-stub",
        "version": "0.1.0",
        "private": True,
        "scripts": {"dev": "next dev", "build": "next build", "start": "next start"},
        "dependencies": {"next": "14.2.18", "react": "^18.2.0", "react-dom": "^18.2.0"},
    }
    layout = """export const metadata = { title: 'CrucibAI Next stub' };

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: 'system-ui', margin: 0, background: '#0f172a', color: '#e2e8f0' }}>
        {children}
      </body>
    </html>
  );
}
"""
    page = """export default function Page() {
  return (
    <main style={{ padding: 24 }}>
      <h1>Next.js App Router (stub)</h1>
      <p style={{ maxWidth: 560, lineHeight: 1.6 }}>
        This track ships alongside the Vite app at repo root. Expand routes under <code>app/</code> and move
        business logic here as the platform adds a native Next execution mode.
      </p>
    </main>
  );
}
"""
    nconf = """/** @type {import('next').NextConfig} */
const nextConfig = { reactStrictMode: true };
export default nextConfig;
"""
    return [
        ("next-app-stub/README.md", readme),
        ("next-app-stub/package.json", json.dumps(pkg, indent=2)),
        ("next-app-stub/next.config.mjs", nconf),
        ("next-app-stub/app/layout.tsx", layout),
        ("next-app-stub/app/page.tsx", page),
        ("next-app-stub/.gitignore", "node_modules\n.next\nout\n"),
    ]


def build_frontend_file_set(job: Dict) -> List[Tuple[str, str]]:
    """(relative_path, utf-8 content)."""
    if enterprise_command_intent(job) and not job.get("preview_contract_only"):
        return build_enterprise_frontend_file_set(job)

    target = normalize_build_target(job.get("build_target"))
    goal_raw = (job.get("goal") or "").strip()[:2000] or "(no goal text)"
    goal_literal = json.dumps(_safe_goal_summary(job.get("goal") or ""))
    pkg = {
        "name": "crucibai-generated-app",
        "version": "0.1.0",
        "private": True,
        "type": "module",
        "scripts": {
            "dev": "vite",
            "build": "vite build",
            "preview": "vite preview",
        },
        "dependencies": {
            "react": "^18.2.0",
            "react-dom": "^18.2.0",
            "react-router-dom": "^6.22.0",
            "zustand": "^4.5.0",
        },
        "devDependencies": {
            "vite": "^5.4.11",
            "@vitejs/plugin-react": "^4.3.4",
        },
    }

    focus_line = ""
    if target == "static_site":
        focus_line = "\n**Build target:** Marketing / static site — Vite SPA structured for landing-style pages.\n"
    elif target == "api_backend":
        focus_line = "\n**Build target:** API-first — emphasize `backend/` and treat UI as thin/demo layer.\n"
    elif target == "agent_workflow":
        focus_line = "\n**Build target:** Agents & automation — crew/workflow sketches complement this scaffold.\n"

    readme = f"""# Generated app (CrucibAI Auto-Runner)
{focus_line}
## Product goal
{goal_raw}

## What is production-grade here
- File layout: `src/pages`, `src/components`, `src/store`, `src/context`
- **React Router** (`MemoryRouter` for Sandpack iframe safety)
- **Zustand** store with **persist** middleware → `localStorage`
- **AuthContext** with token in `localStorage` (client-only demo — not server session)
- Reusable **ShellLayout** and page components

## Explicitly incomplete (CRUCIB_INCOMPLETE)
- No real OAuth / server session — replace `AuthContext` login with your API
- Backend in `backend/` is a sketch; wire your own API base URL

## Preview
- Workspace **Preview** tab (Sandpack) for interactive editing
- Auto-Runner **preview gate** runs `npm install`, `vite build`, and **Playwright** (headless Chromium) against `dist/` — backend needs `python -m playwright install chromium`
"""

    store = """import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

/**
 * Global UI + preferences (persisted to localStorage).
 * CRUCIB_INCOMPLETE: sync with server when you add a real API.
 */
export const useAppStore = create(
  persist(
    (set, get) => ({
      theme: 'dark',
      lastRoute: '/',
      notes: '',
      setTheme: (theme) => set({ theme }),
      setLastRoute: (lastRoute) => set({ lastRoute }),
      setNotes: (notes) => set({ notes }),
      reset: () => set({ theme: 'dark', lastRoute: '/', notes: '' }),
    }),
    {
      name: 'crucibai-app-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({ theme: s.theme, lastRoute: s.lastRoute, notes: s.notes }),
    },
  ),
);
"""

    auth = """import React, { createContext, useContext, useMemo, useState, useEffect } from 'react';

const AuthContext = createContext(null);

const STORAGE_KEY = 'crucibai_demo_token';

/**
 * Client-only auth demo. CRUCIB_INCOMPLETE: exchange credentials with your API.
 */
export function AuthProvider({ children }) {
  const [token, setTokenState] = useState(() => localStorage.getItem(STORAGE_KEY) || '');

  useEffect(() => {
    if (token) localStorage.setItem(STORAGE_KEY, token);
    else localStorage.removeItem(STORAGE_KEY);
  }, [token]);

  const value = useMemo(
    () => ({
      token,
      isAuthenticated: Boolean(token),
      login: (demoUser) => {
        setTokenState(`demo.${(demoUser || 'user').slice(0, 24)}.${Date.now()}`);
      },
      logout: () => setTokenState(''),
    }),
    [token],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
"""

    shell = """import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';

export default function ShellLayout() {
  const link = (to, label) => (
    <NavLink
      to={to}
      style={({ isActive }) => ({
        padding: '6px 12px',
        borderRadius: 8,
        textDecoration: 'none',
        color: isActive ? '#fff' : '#94a3b8',
        background: isActive ? 'rgba(59,130,246,0.35)' : 'transparent',
        border: '1px solid rgba(148,163,184,0.25)',
      })}
    >
      {label}
    </NavLink>
  );

  return (
    <div style={{ minHeight: '100vh', background: '#0f172a', color: '#e2e8f0', fontFamily: 'Inter, system-ui, sans-serif' }}>
      <header style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '14px 20px', borderBottom: '1px solid rgba(148,163,184,0.2)' }}>
        <strong style={{ marginRight: 12 }}>CrucibAI App</strong>
        <nav style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {link('/', 'Home')}
          {link('/login', 'Login')}
          {link('/dashboard', 'Dashboard')}
          {link('/team', 'Team')}
          {/* CRUCIB_ROUTE_ANCHOR */}
        </nav>
      </header>
      <main style={{ padding: '28px 20px', maxWidth: 900, margin: '0 auto' }}>
        <Outlet />
      </main>
    </div>
  );
}
"""

    error_boundary = """import React from 'react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <main style={{ padding: 24, color: '#e2e8f0', background: '#0f172a', minHeight: '100vh' }}>
          <h1>Something needs attention</h1>
          <p>The preview caught a recoverable UI error. Adjust the component and try again.</p>
        </main>
      );
    }
    return this.props.children;
  }
}
"""

    home = f"""import React from 'react';
import {{ useNavigate }} from 'react-router-dom';
import {{ useAppStore }} from '../store/useAppStore';

export default function HomePage() {{
  const navigate = useNavigate();
  const theme = useAppStore((s) => s.theme);
  const setTheme = useAppStore((s) => s.setTheme);
  const goal = {goal_literal};

  return (
    <div>
      <h1 style={{{{ fontSize: '1.75rem', marginBottom: 12 }}}}>Home</h1>
      <p style={{{{ color: '#94a3b8', lineHeight: 1.6, marginBottom: 16 }}}}>{{goal}}</p>
      <div style={{{{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 20 }}}}>
        <button
          type="button"
          onClick={{() => setTheme(theme === 'dark' ? 'light' : 'dark')}}
          style={{{{ padding: '8px 14px', borderRadius: 8, border: '1px solid #475569', background: '#1e293b', color: '#e2e8f0', cursor: 'pointer' }}}}
        >
          Toggle theme ({{theme}}) — persisted
        </button>
        <button
          type="button"
          onClick={{() => navigate('/dashboard')}}
          style={{{{ padding: '8px 14px', borderRadius: 8, background: '#3b82f6', color: '#fff', border: 'none', cursor: 'pointer' }}}}
        >
          Go to Dashboard
        </button>
      </div>
      <p style={{{{ fontSize: 13, color: '#64748b' }}}}>Theme and routes sync to localStorage via Zustand persist.</p>
    </div>
  );
}}
"""

    login = """import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState('');

  if (isAuthenticated) {
    navigate('/dashboard', { replace: true });
    return null;
  }

  return (
    <div style={{ maxWidth: 400 }}>
      <h1 style={{ marginBottom: 12 }}>Login (demo)</h1>
      <p style={{ color: '#94a3b8', fontSize: 14, marginBottom: 16 }}>
        Client-only token stored in localStorage. CRUCIB_INCOMPLETE: call your API.
      </p>
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Display name"
        style={{ width: '100%', padding: 10, borderRadius: 8, border: '1px solid #475569', background: '#1e293b', color: '#fff', marginBottom: 12 }}
      />
      <button
        type="button"
        onClick={() => { login(name || 'builder'); navigate('/dashboard'); }}
        style={{ padding: '10px 18px', borderRadius: 8, background: '#22c55e', color: '#0f172a', border: 'none', fontWeight: 600, cursor: 'pointer' }}
      >
        Sign in (demo)
      </button>
    </div>
  );
}
"""

    team_page = """import React from 'react';

export default function TeamPage() {
  return (
    <div>
      <h1 style={{ marginBottom: 12 }}>Team</h1>
      <p style={{ color: '#94a3b8', lineHeight: 1.6 }}>
        Sample team page — included in the scaffold so routing and preview never reference a missing component.
      </p>
    </div>
  );
}
"""

    dashboard = """import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useAppStore } from '../store/useAppStore';

export default function DashboardPage() {
  const { isAuthenticated, token, logout } = useAuth();
  const notes = useAppStore((s) => s.notes);
  const setNotes = useAppStore((s) => s.setNotes);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div>
      <h1 style={{ marginBottom: 8 }}>Dashboard</h1>
      <p style={{ color: '#94a3b8', marginBottom: 16, wordBreak: 'break-all' }}>Token: {token.slice(0, 48)}…</p>
      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Notes (persisted)"
        rows={4}
        style={{ width: '100%', padding: 10, borderRadius: 8, border: '1px solid #475569', background: '#1e293b', color: '#e2e8f0' }}
      />
      <button type="button" onClick={logout} style={{ marginTop: 12, padding: '8px 14px', borderRadius: 8, background: '#ef4444', color: '#fff', border: 'none', cursor: 'pointer' }}>
        Log out
      </button>
    </div>
  );
}
"""

    app = """import React from 'react';
import { MemoryRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ErrorBoundary from './components/ErrorBoundary';
import ShellLayout from './components/ShellLayout';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import TeamPage from './pages/TeamPage';

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route element={<ShellLayout />}>
              <Route path="/" element={<HomePage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/team" element={<TeamPage />} />
              {/* CRUCIB_APP_ROUTE_ANCHOR */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </ErrorBoundary>
  );
}
"""

    index_html = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>CrucibAI Generated App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
"""

    vite_config = """import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
});
"""

    main_jsx = """import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import './styles/global.css';

const el = document.getElementById('root');
const root = createRoot(el);
root.render(<App />);
"""

    global_css = """* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: Inter, system-ui, sans-serif;
  background: #0f172a;
  color: #e2e8f0;
}
"""

    preview_contract = """import React from 'react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

/**
 * Contract-only marker component for preview verification.
 * It does not need to be mounted by the generated app, but it documents
 * that the workspace includes React Router primitives the preview gate expects.
 */
export default function PreviewContract() {
  return (
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path="/" element={<div>Preview contract</div>} />
      </Routes>
    </MemoryRouter>
  );
}
"""

    out = [
        ("package.json", json.dumps(pkg, indent=2)),
        ("index.html", index_html),
        ("vite.config.js", vite_config),
        ("README_BUILD.md", readme),
        ("src/store/useAppStore.js", store),
        ("src/context/AuthContext.jsx", auth),
        ("src/components/ErrorBoundary.jsx", error_boundary),
        ("src/components/ShellLayout.jsx", shell),
        ("src/pages/HomePage.jsx", home),
        ("src/pages/LoginPage.jsx", login),
        ("src/pages/DashboardPage.jsx", dashboard),
        ("src/pages/TeamPage.jsx", team_page),
        ("src/preview/PreviewContract.jsx", preview_contract),
        ("src/App.jsx", app),
        ("src/main.jsx", main_jsx),
        # Sandpack in Workspace.jsx expects /src/index.js; Vite uses main.jsx from index.html
        ("src/index.js", main_jsx),
        ("src/styles/global.css", global_css),
        ("docs/CRUCIB_BUILD_TARGET.md", _crucib_build_target_doc(job, target)),
    ]
    if target == "next_app_router":
        out.extend(_next_app_stub_files(goal_raw))
    return out

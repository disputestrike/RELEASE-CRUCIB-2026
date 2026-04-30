"""
React / Vite template generator for CrucibAI.

Produces a complete, runnable React frontend with:
- Vite bundler, React Router, Zustand state management
- Three page routes: Home, Dashboard, Login
- Shell layout with responsive nav bar
- Auth context, error boundary, global CSS with variables
"""

import re
from typing import Dict


def _extract_domain(goal: str) -> str:
    """Extract a short domain name from the goal."""
    goal_lower = goal.lower()
    for phrase in [
        r"(?:a |an |the )?(\w+)\s+(?:tracker|manager|app|webapp|frontend|dashboard)",
        r"(?:build|create|make|generate)\s+(?:a |an |the )?(\w+)",
        r"(\w+)\s+(?:frontend|web app|application)",
    ]:
        match = re.search(phrase, goal_lower)
        if match:
            return match.group(1).replace(" ", "_")
    return "app"


def _pascal(word: str) -> str:
    return "".join(part.capitalize() for part in word.split("_"))


def generate_react_vite(goal: str, project_name: str = "generated-app") -> Dict[str, str]:
    """Generate a complete React/Vite frontend scaffold.

    Parameters
    ----------
    goal:
        Natural-language description of the application.
    project_name:
        NPM package name.

    Returns
    -------
    Dict[str, str]
        Mapping of relative filepath -> complete file content.
    """
    domain = _extract_domain(goal)
    Domain = _pascal(domain)

    # ------------------------------------------------------------------
    # package.json
    # ------------------------------------------------------------------
    package_json = f'''\
{{
  "name": "{project_name}",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {{
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  }},
  "dependencies": {{
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.28.0",
    "zustand": "^5.0.0"
  }},
  "devDependencies": {{
    "@vitejs/plugin-react": "^4.3.4",
    "vite": "^6.0.0"
  }}
}}
'''

    # ------------------------------------------------------------------
    # vite.config.js
    # ------------------------------------------------------------------
    vite_config = """\
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    open: true,
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
});
"""

    # ------------------------------------------------------------------
    # index.html
    # ------------------------------------------------------------------
    index_html = f'''\
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{Domain}</title>
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
'''

    # ------------------------------------------------------------------
    # src/main.jsx
    # ------------------------------------------------------------------
    main_jsx = f'''\
import React from "react";
import ReactDOM from "react-dom/client";
import {{ BrowserRouter }} from "react-router-dom";
import App from "./App";
import {{ AuthProvider }} from "./context/AuthContext";
import ErrorBoundary from "./components/ErrorBoundary";
import "./styles/global.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ErrorBoundary>
      <AuthProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </AuthProvider>
    </ErrorBoundary>
  </React.StrictMode>
);
'''

    # ------------------------------------------------------------------
    # src/App.jsx
    # ------------------------------------------------------------------
    app_jsx = f'''\
import {{ Routes, Route, Navigate }} from "react-router-dom";
import ShellLayout from "./components/ShellLayout";
import HomePage from "./pages/HomePage";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import {{ useAuth }} from "./context/AuthContext";

function ProtectedRoute({{ children }}) {{
  const {{ user }} = useAuth();
  if (!user) {{
    return <Navigate to="/login" replace />;
  }}
  return children;
}}

export default function App() {{
  return (
    <Routes>
      <Route element={{<ShellLayout />}}>
        <Route path="/" element={{<HomePage />}} />
        <Route
          path="/dashboard"
          element={{(
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          )}}
        />
        <Route path="/login" element={{<LoginPage />}} />
        <Route path="*" element={{<div className="not-found"><h1>404</h1><p>Page not found</p></div>}} />
      </Route>
    </Routes>
  );
}}
'''

    # ------------------------------------------------------------------
    # src/pages/HomePage.jsx
    # ------------------------------------------------------------------
    home_page = f'''\
import {{ Link }} from "react-router-dom";

export default function HomePage() {{
  return (
    <div className="home-page">
      <section className="hero">
        <h1>Welcome to {Domain}</h1>
        <p className="hero-sub">
          A modern web application generated by CrucibAI. Get started by
          signing in or exploring the dashboard.
        </p>
        <div className="hero-actions">
          <Link to="/login" className="btn btn-primary">
            Sign In
          </Link>
          <Link to="/dashboard" className="btn btn-secondary">
            Go to Dashboard
          </Link>
        </div>
      </section>

      <section className="features">
        <div className="feature-card">
          <h3>Fast &amp; Modern</h3>
          <p>Built with React 18, Vite, and Zustand for a snappy experience.</p>
        </div>
        <div className="feature-card">
          <h3>Responsive</h3>
          <p>Looks great on desktop, tablet, and mobile devices.</p>
        </div>
        <div className="feature-card">
          <h3>Secure</h3>
          <p>Authentication context with protected routes out of the box.</p>
        </div>
      </section>
    </div>
  );
}}
'''

    # ------------------------------------------------------------------
    # src/pages/DashboardPage.jsx
    # ------------------------------------------------------------------
    dashboard_page = f'''\
import {{ useEffect, useState }} from "react";
import {{ useAuth }} from "../context/AuthContext";
import {{ useAppStore }} from "../store/useAppStore";

const SAMPLE_DATA = [
  {{ id: 1, name: "Project Alpha", status: "active", progress: 72 }},
  {{ id: 2, name: "Project Beta", status: "pending", progress: 35 }},
  {{ id: 3, name: "Project Gamma", status: "completed", progress: 100 }},
  {{ id: 4, name: "Project Delta", status: "active", progress: 58 }},
  {{ id: 5, name: "Project Epsilon", status: "active", progress: 89 }},
];

export default function DashboardPage() {{
  const {{ user }} = useAuth();
  const {{ items, setItems }} = useAppStore();
  const [filter, setFilter] = useState("all");

  useEffect(() => {{
    if (items.length === 0) {{
      setItems(SAMPLE_DATA);
    }}
  }}, [items, setItems]);

  const filtered =
    filter === "all" ? items : items.filter((i) => i.status === filter);

  return (
    <div className="dashboard-page">
      <h2>Dashboard</h2>
      <p className="dashboard-greeting">Hello, {{user?.name || "User"}}!</p>

      <div className="stats-bar">
        <div className="stat">
          <span className="stat-value">{{items.length}}</span>
          <span className="stat-label">Total</span>
        </div>
        <div className="stat">
          <span className="stat-value">{{items.filter((i) => i.status === "active").length}}</span>
          <span className="stat-label">Active</span>
        </div>
        <div className="stat">
          <span className="stat-value">{{items.filter((i) => i.status === "completed").length}}</span>
          <span className="stat-label">Completed</span>
        </div>
      </div>

      <div className="filter-bar">
        {{["all", "active", "pending", "completed"].map((s) => (
          <button
            key={{s}}
            className={{`btn btn-small ${{filter === s ? "btn-primary" : "btn-secondary"}}`}}
            onClick={{() => setFilter(s)}}
          >
            {{s.charAt(0).toUpperCase() + s.slice(1)}}
          </button>
        ))}}
      </div>

      <div className="data-table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Status</th>
              <th>Progress</th>
            </tr>
          </thead>
          <tbody>
            {{filtered.map((item) => (
              <tr key={{item.id}}>
                <td>{{item.id}}</td>
                <td>{{item.name}}</td>
                <td>
                  <span className={{`badge badge-${{item.status}}`}}>{{item.status}}</span>
                </td>
                <td>
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{{{ width: `${{item.progress}}%` }}}}
                    />
                  </div>
                </td>
              </tr>
            ))}}
          </tbody>
        </table>
      </div>
    </div>
  );
}}
'''

    # ------------------------------------------------------------------
    # src/pages/LoginPage.jsx
    # ------------------------------------------------------------------
    login_page = f'''\
import {{ useState }} from "react";
import {{ useNavigate }} from "react-router-dom";
import {{ useAuth }} from "../context/AuthContext";

export default function LoginPage() {{
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const {{ login }} = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {{
    e.preventDefault();
    setError("");

    if (!email.trim() || !password.trim()) {{
      setError("Please fill in all fields.");
      return;
    }}

    setLoading(true);
    try {{
      // Simulated authentication — replace with real API call
      await new Promise((resolve) => setTimeout(resolve, 800));
      login({{ id: 1, name: email.split("@")[0], email }});
      navigate("/dashboard", {{ replace: true }});
    }} catch {{
      setError("Login failed. Please try again.");
    }} finally {{
      setLoading(false);
    }}
  }};

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={{handleSubmit}}>
        <h2>Sign In</h2>
        <p className="login-subtitle">Access your {Domain} account</p>

        {{error && <div className="alert alert-error">{{error}}</div>}}

        <div className="form-group">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            placeholder="you@example.com"
            value={{email}}
            onChange={{(e) => setEmail(e.target.value)}}
            autoComplete="email"
          />
        </div>

        <div className="form-group">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            placeholder="Enter your password"
            value={{password}}
            onChange={{(e) => setPassword(e.target.value)}}
            autoComplete="current-password"
          />
        </div>

        <button type="submit" className="btn btn-primary btn-full" disabled={{loading}}>
          {{loading ? "Signing in..." : "Sign In"}}
        </button>

        <p className="login-hint">
          This is a demo. Enter any email and password to continue.
        </p>
      </form>
    </div>
  );
}}
'''

    # ------------------------------------------------------------------
    # src/store/useAppStore.js
    # ------------------------------------------------------------------
    store_js = '''\
/**
 * Global application store powered by Zustand.
 *
 * Holds shared state that persists across page navigation without
 * needing a context provider.
 */

import { create } from "zustand";

const useAppStore = create((set) => ({
  // -- Dashboard items --------------------------------------------------
  items: [],
  setItems: (items) => set({ items }),

  addItem: (item) =>
    set((state) => ({
      items: [...state.items, { ...item, id: Date.now() }],
    })),

  removeItem: (id) =>
    set((state) => ({
      items: state.items.filter((i) => i.id !== id),
    })),

  // -- UI state ---------------------------------------------------------
  sidebarOpen: true,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  closeSidebar: () => set({ sidebarOpen: false }),

  // -- Notifications ----------------------------------------------------
  notifications: [],
  addNotification: (notification) =>
    set((state) => ({
      notifications: [
        ...state.notifications,
        { id: Date.now(), ...notification, read: false },
      ],
    })),
  markRead: (id) =>
    set((state) => ({
      notifications: state.notifications.map((n) =>
        n.id === id ? { ...n, read: true } : n
      ),
    })),
  clearNotifications: () => set({ notifications: [] }),
}));

export default useAppStore;
'''

    # ------------------------------------------------------------------
    # src/components/ErrorBoundary.jsx
    # ------------------------------------------------------------------
    error_boundary = '''\
import { Component } from "react";

/**
 * Catches render errors anywhere in the React tree so the UI
 * degrades gracefully instead of going blank.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <h2>Something went wrong</h2>
          <p>{this.state.error?.message || "An unexpected error occurred."}</p>
          <button
            className="btn btn-primary"
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            Try Again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
'''

    # ------------------------------------------------------------------
    # src/components/ShellLayout.jsx
    # ------------------------------------------------------------------
    shell_layout = f'''\
import {{ Link, Outlet, useLocation }} from "react-router-dom";
import {{ useAuth }} from "../context/AuthContext";

const NAV_LINKS = [
  {{ to: "/", label: "Home" }},
  {{ to: "/dashboard", label: "Dashboard" }},
];

export default function ShellLayout() {{
  const {{ pathname }} = useLocation();
  const {{ user, logout }} = useAuth();

  return (
    <div className="shell-layout">
      <header className="shell-header">
        <Link to="/" className="shell-logo">
          {Domain}
        </Link>

        <nav className="shell-nav">
          {{NAV_LINKS.map((link) => (
            <Link
              key={{link.to}}
              to={{link.to}}
              className={{`shell-nav-link ${{pathname === link.to ? "active" : ""}}`}}
            >
              {{link.label}}
            </Link>
          ))}}
        </nav>

        <div className="shell-actions">
          {{user ? (
            <div className="user-menu">
              <span className="user-name">{{user.name}}</span>
              <button className="btn btn-small btn-secondary" onClick={{logout}}>
                Logout
              </button>
            </div>
          ) : (
            <Link to="/login" className="btn btn-small btn-primary">
              Sign In
            </Link>
          )}}
        </div>
      </header>

      <main className="shell-main">
        <Outlet />
      </main>

      <footer className="shell-footer">
        <p>&copy; {{new Date().getFullYear()}} {Domain}. Generated by CrucibAI.</p>
      </footer>
    </div>
  );
}}
'''

    # ------------------------------------------------------------------
    # src/context/AuthContext.jsx
    # ------------------------------------------------------------------
    auth_context = '''\
import { createContext, useContext, useState, useCallback } from "react";

const AuthContext = createContext(null);

/**
 * Provides authentication state (user object or null) and
 * login/logout helpers to the entire React tree.
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem("crucib_user");
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  const login = useCallback((userData) => {
    setUser(userData);
    localStorage.setItem("crucib_user", JSON.stringify(userData));
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    localStorage.removeItem("crucib_user");
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

/**
 * Convenience hook — throws if used outside of AuthProvider.
 */
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
'''

    # ------------------------------------------------------------------
    # src/styles/global.css
    # ------------------------------------------------------------------
    global_css = '''\
/* ================================================================
   {DOMAIN} — Global Styles
   Generated by CrucibAI
   ================================================================ */

:root {
  --color-primary: #6366f1;
  --color-primary-hover: #4f46e5;
  --color-secondary: #f1f5f9;
  --color-secondary-hover: #e2e8f0;
  --color-success: #22c55e;
  --color-warning: #f59e0b;
  --color-danger: #ef4444;
  --color-bg: #ffffff;
  --color-bg-muted: #f8fafc;
  --color-text: #1e293b;
  --color-text-muted: #64748b;
  --color-border: #e2e8f0;
  --radius: 8px;
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.1);
  --font-sans: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --max-width: 1100px;
}

*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: var(--font-sans);
  color: var(--color-text);
  background: var(--color-bg);
  line-height: 1.6;
}

a {
  color: var(--color-primary);
  text-decoration: none;
}

/* -- Shell layout ---------------------------------------------------- */
.shell-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.shell-header {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  padding: 0.75rem 1.5rem;
  background: var(--color-bg);
  border-bottom: 1px solid var(--color-border);
  position: sticky;
  top: 0;
  z-index: 50;
}

.shell-logo {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-primary);
}

.shell-nav {
  display: flex;
  gap: 0.5rem;
  flex: 1;
}

.shell-nav-link {
  padding: 0.4rem 0.75rem;
  border-radius: var(--radius);
  font-size: 0.9rem;
  color: var(--color-text-muted);
  transition: background 0.15s, color 0.15s;
}

.shell-nav-link:hover,
.shell-nav-link.active {
  background: var(--color-secondary);
  color: var(--color-text);
}

.shell-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.shell-main {
  flex: 1;
  padding: 2rem 1.5rem;
  max-width: var(--max-width);
  width: 100%;
  margin: 0 auto;
}

.shell-footer {
  text-align: center;
  padding: 1rem;
  border-top: 1px solid var(--color-border);
  color: var(--color-text-muted);
  font-size: 0.85rem;
}

/* -- Buttons --------------------------------------------------------- */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.55rem 1.1rem;
  border: none;
  border-radius: var(--radius);
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s, transform 0.1s;
}

.btn:active {
  transform: scale(0.97);
}

.btn-primary {
  background: var(--color-primary);
  color: #fff;
}

.btn-primary:hover {
  background: var(--color-primary-hover);
}

.btn-secondary {
  background: var(--color-secondary);
  color: var(--color-text);
}

.btn-secondary:hover {
  background: var(--color-secondary-hover);
}

.btn-small {
  padding: 0.35rem 0.7rem;
  font-size: 0.8rem;
}

.btn-full {
  width: 100%;
}

/* -- Home page ------------------------------------------------------- */
.home-page {
  text-align: center;
}

.hero {
  padding: 3rem 0;
}

.hero h1 {
  font-size: 2.5rem;
  margin-bottom: 0.75rem;
}

.hero-sub {
  color: var(--color-text-muted);
  max-width: 500px;
  margin: 0 auto 1.5rem;
}

.hero-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: center;
}

.features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1.5rem;
  margin-top: 2rem;
}

.feature-card {
  padding: 1.5rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  text-align: left;
}

.feature-card h3 {
  margin-bottom: 0.5rem;
}

/* -- Login ----------------------------------------------------------- */
.login-page {
  display: flex;
  justify-content: center;
  padding-top: 4rem;
}

.login-card {
  width: 100%;
  max-width: 400px;
  padding: 2rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  background: var(--color-bg);
  box-shadow: var(--shadow-md);
}

.login-card h2 {
  margin-bottom: 0.25rem;
}

.login-subtitle {
  color: var(--color-text-muted);
  margin-bottom: 1.5rem;
}

.form-group {
  margin-bottom: 1rem;
  text-align: left;
}

.form-group label {
  display: block;
  font-size: 0.85rem;
  font-weight: 500;
  margin-bottom: 0.3rem;
}

.form-group input {
  width: 100%;
  padding: 0.55rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font-size: 0.9rem;
  outline: none;
  transition: border-color 0.15s;
}

.form-group input:focus {
  border-color: var(--color-primary);
}

.login-hint {
  margin-top: 1rem;
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

/* -- Dashboard ------------------------------------------------------- */
.dashboard-page h2 {
  margin-bottom: 0.25rem;
}

.dashboard-greeting {
  color: var(--color-text-muted);
  margin-bottom: 1.5rem;
}

.stats-bar {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.stat {
  flex: 1;
  padding: 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 1.75rem;
  font-weight: 700;
}

.stat-label {
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

.filter-bar {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.data-table-wrapper {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.data-table th,
.data-table td {
  text-align: left;
  padding: 0.6rem 0.75rem;
  border-bottom: 1px solid var(--color-border);
}

.data-table th {
  font-weight: 600;
  background: var(--color-bg-muted);
}

.badge {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: capitalize;
}

.badge-active {
  background: #dcfce7;
  color: #15803d;
}

.badge-pending {
  background: #fef3c7;
  color: #92400e;
}

.badge-completed {
  background: #dbeafe;
  color: #1d4ed8;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: var(--color-secondary);
  border-radius: 999px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--color-primary);
  border-radius: 999px;
  transition: width 0.3s;
}

/* -- Alerts ---------------------------------------------------------- */
.alert {
  padding: 0.75rem 1rem;
  border-radius: var(--radius);
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

.alert-error {
  background: #fef2f2;
  color: var(--color-danger);
  border: 1px solid #fecaca;
}

/* -- Error boundary -------------------------------------------------- */
.error-boundary {
  text-align: center;
  padding: 4rem 1rem;
}

.error-boundary h2 {
  margin-bottom: 0.5rem;
}

.error-boundary p {
  color: var(--color-text-muted);
  margin-bottom: 1.5rem;
}

.not-found {
  text-align: center;
  padding: 4rem 1rem;
  color: var(--color-text-muted);
}

/* -- Responsive ------------------------------------------------------ */
@media (max-width: 640px) {
  .hero h1 {
    font-size: 1.75rem;
  }

  .shell-header {
    flex-wrap: wrap;
  }

  .stats-bar {
    flex-direction: column;
  }
}
'''

    # ------------------------------------------------------------------
    # Assemble return
    # ------------------------------------------------------------------
    return {
        "package.json": package_json,
        "vite.config.js": vite_config,
        "index.html": index_html,
        "src/main.jsx": main_jsx,
        "src/App.jsx": app_jsx,
        "src/pages/HomePage.jsx": home_page,
        "src/pages/DashboardPage.jsx": dashboard_page,
        "src/pages/LoginPage.jsx": login_page,
        "src/store/useAppStore.js": store_js,
        "src/components/ErrorBoundary.jsx": error_boundary,
        "src/components/ShellLayout.jsx": shell_layout,
        "src/context/AuthContext.jsx": auth_context,
        "src/styles/global.css": global_css,
    }

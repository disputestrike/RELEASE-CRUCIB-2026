import { AuthContext, useAuth as _useAuth } from "./authContext";
import { useState, useEffect, useRef, createContext, useContext, Component, useCallback } from "react";

// Theme system — respects user preference stored in localStorage
const THEME_KEY = 'crucibai-theme';
const getInitialTheme = () => localStorage.getItem(THEME_KEY) || 'light';
const applyTheme = (theme) => {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem(THEME_KEY, theme);
};
// Apply immediately on load (before React renders)
applyTheme(getInitialTheme());

import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import axios from "axios";

// Error boundary so blank screen shows a message
class AppErrorBoundary extends Component {
  state = { hasError: false, error: null };
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ minHeight: "100vh", background: "#FAFAF8", color: "#1A1A1A", padding: 24, fontFamily: "sans-serif" }}>
          <h1 style={{ fontSize: 18 }}>Something went wrong</h1>
          <p style={{ color: "#888" }}>{this.state.error?.message || "Unknown error"}</p>
          <button onClick={() => window.location.reload()} style={{ marginTop: 16, padding: "8px 16px", cursor: "pointer" }}>Reload</button>
        </div>
      );
    }
    return this.props.children;
  }
}

// Pages
import LandingPage from "./pages/LandingPage";
import OurProjectsPage from "./pages/OurProjectsPage";
import AuthPage from "./pages/AuthPage";
import Dashboard from "./pages/Dashboard";
import ProjectBuilder from "./pages/ProjectBuilder";
import AgentMonitor from "./pages/AgentMonitor";
import TokenCenter from "./pages/TokenCenter";
import ExportCenter from "./pages/ExportCenter";
import PatternLibrary from "./pages/PatternLibrary";
import Settings from "./pages/Settings";
import Builder from "./pages/Builder";
import Workspace from "./pages/Workspace";
import WorkspaceManus from "./pages/WorkspaceManus";
import Layout from "./components/Layout";
import ShareView from "./pages/ShareView";
import ExamplesGallery from "./pages/ExamplesGallery";
import TemplatesGallery from "./pages/TemplatesGallery";
import PromptLibrary from "./pages/PromptLibrary";
import LearnPanel from "./pages/LearnPanel";
import EnvPanel from "./pages/EnvPanel";
import ShortcutCheatsheet from "./pages/ShortcutCheatsheet";
import PaymentsWizard from "./pages/PaymentsWizard";
import Privacy from "./pages/Privacy";
import Terms from "./pages/Terms";
import Security from "./pages/Security";
import Aup from "./pages/Aup";
import Dmca from "./pages/Dmca";
import Cookies from "./pages/Cookies";
import About from "./pages/About";
import Pricing from "./pages/Pricing";
import Billing from "./pages/Billing";
import Enterprise from "./pages/Enterprise";
import Contact from "./pages/Contact";
import GetHelp from "./pages/GetHelp";
import Features from "./pages/Features";
import TemplatesPublic from "./pages/TemplatesPublic";
import PatternsPublic from "./pages/PatternsPublic";
import LearnPublic from "./pages/LearnPublic";
import DocsPage from "./pages/DocsPage";
import TutorialsPage from "./pages/TutorialsPage";
import ShortcutsPublic from "./pages/ShortcutsPublic";
import Changelog from "./pages/Changelog";
import Status from "./pages/Status";
import PromptsPublic from "./pages/PromptsPublic";
import Benchmarks from "./pages/Benchmarks";
import Blog from "./pages/Blog";
import GenerateContent from "./pages/GenerateContent";
import AdminDashboard from "./pages/AdminDashboard";
import AdminUsers from "./pages/AdminUsers";
import AdminUserProfile from "./pages/AdminUserProfile";
import AdminBilling from "./pages/AdminBilling";
import AdminAnalytics from "./pages/AdminAnalytics";
import AdminLegal from "./pages/AdminLegal";
import AuditLog from "./pages/AuditLog";
import AgentsPage from "./pages/AgentsPage";
import WhatIfPage from "./pages/WhatIfPage";
import OnboardingPage from "./pages/OnboardingPage";
import MonitoringDashboard from "./pages/MonitoringDashboard";
import VibeCodePage from "./pages/VibeCodePage";
import ModelManager from "./pages/ModelManager";
import FineTuning from "./pages/FineTuning";
import SafetyDashboard from "./pages/SafetyDashboard";
import UnifiedIDEPage from "./pages/UnifiedIDEPage";
import StudioPage from "./pages/StudioPage";
import KnowledgePage from "./pages/KnowledgePage";
import ChannelsPage from "./pages/ChannelsPage";
import SessionsPage from "./pages/SessionsPage";
import CommerceManagePage from "./pages/CommerceManagePage";
import WorkspaceMembersPage from "./pages/WorkspaceMembersPage";
import SkillsPage from "./pages/SkillsPage";
import SkillsMarketplace from "./pages/SkillsMarketplace";
import UnifiedWorkspace from "./pages/UnifiedWorkspace";
import { LayoutProvider } from "./stores/useLayoutStore";
import { TaskProvider } from "./stores/useTaskStore";

import { API_BASE } from "./apiBase";

// Same-origin /api when unset (CRA dev proxy to backend).
export const API = API_BASE;
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";
console.log("API configured as:", API, "BACKEND_URL:", BACKEND_URL || "(same-origin / proxy to :8000 in dev)");

// Auth Context
export const useAuth = _useAuth; // re-export from authContext

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem("token"));

  const mergeWorkspaceMode = (u) => {
    if (!u) return u;
    if (!u.workspace_mode) {
      const local = localStorage.getItem('crucibai_workspace_mode');
      if (local === 'simple' || local === 'developer') u = { ...u, workspace_mode: local };
    }
    return u;
  };

  // SSO callback — loginWithToken from URL param (?sso_token=...)
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const ssoToken = urlParams.get('sso_token');
    if (ssoToken) {
      // Remove the param from URL without reload
      const clean = new URL(window.location.href);
      clean.searchParams.delete('sso_token');
      clean.searchParams.delete('email');
      window.history.replaceState({}, '', clean.pathname + (clean.search || '') + (clean.hash || ''));
      // Log in with the SSO token
      localStorage.setItem('token', ssoToken);
      setToken(ssoToken);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    let cancelled = false;
    const ensureGuest = async () => {
      try {
        const res = await axios.post(`${API}/auth/guest`, {}, { timeout: 10000 });
        if (!cancelled && res.data?.token && res.data?.user) {
          localStorage.setItem("token", res.data.token);
          setToken(res.data.token);
          setUser(mergeWorkspaceMode(res.data.user));
        }
      } catch (e) {
        if (!cancelled) setUser(null);
      }
    };
    const checkAuth = async () => {
      if (token) {
        try {
          const res = await axios.get(`${API}/auth/me`, {
            headers: { Authorization: `Bearer ${token}` },
            timeout: 5000,
          });
          if (!cancelled) setUser(mergeWorkspaceMode(res.data));
        } catch (e) {
          if (!cancelled) {
            localStorage.removeItem("token");
            setToken(null);
            await ensureGuest();
          }
        }
      } else {
        await ensureGuest();
      }
      if (!cancelled) setLoading(false);
    };
    checkAuth();
    return () => { cancelled = true; };
  }, [token]);

  const login = async (email, password) => {
    const res = await axios.post(`${API}/auth/login`, { email, password });
    if (res.data.status === "mfa_required" && res.data.mfa_token) {
      return res.data;
    }
    localStorage.setItem("token", res.data.token);
    setToken(res.data.token);
    setUser(res.data.user);
    return res.data;
  };

  const verifyMfa = async (code, mfaToken) => {
    const res = await axios.post(`${API}/auth/verify-mfa`, { code, mfa_token: mfaToken });
    localStorage.setItem("token", res.data.token);
    setToken(res.data.token);
    setUser(res.data.user);
    return res.data;
  };

  const register = async (email, password, name) => {
    const res = await axios.post(`${API}/auth/register`, { email, password, name });
    localStorage.setItem("token", res.data.token);
    setToken(res.data.token);
    setUser(res.data.user);
    return res.data;
  };

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("crucibai_workspace_mode");
    setToken(null);
    setUser(null);
  };

  const loginWithToken = async (t) => {
    localStorage.setItem("token", t);
    setToken(t);
    try {
      const res = await axios.get(`${API}/auth/me`, { headers: { Authorization: `Bearer ${t}` } });
      setUser(mergeWorkspaceMode(res.data));
    } catch (e) {
      localStorage.removeItem("token");
      setToken(null);
      throw e;
    }
  };

  const refreshUser = async () => {
    if (!token) return;
    try {
      const res = await axios.get(`${API}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUser(mergeWorkspaceMode(res.data));
    } catch (e) {
      // 429: global API rate limit — do not surface as uncaught runtime error (Layout/Workspace call this often)
      if (e.response?.status === 429) {
        if (process.env.NODE_ENV === "development") {
          console.warn("[auth/me] rate limited (429). Set CRUCIBAI_DEV=1 on backend for local dev, or raise RATE_LIMIT_PER_MINUTE).");
        }
        return;
      }
      throw e;
    }
  };

  const ensureGuest = useCallback(async () => {
    try {
      const res = await axios.post(`${API}/auth/guest`, {}, { timeout: 10000 });
      if (res.data?.token && res.data?.user) {
        localStorage.setItem("token", res.data.token);
        setToken(res.data.token);
        setUser(mergeWorkspaceMode(res.data.user));
        return true;
      }
    } catch {
      // Guest bootstrap is optional; caller falls back to demo / retry UI.
    }
    return false;
  }, []);

  const enterDemoMode = useCallback(() => {
    setUser(mergeWorkspaceMode({ id: "demo", email: "demo@local", name: "Guest", workspace_mode: "simple" }));
    setToken(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, login, register, logout, loading, refreshUser, loginWithToken, verifyMfa, ensureGuest, enterDemoMode }}>
      <LayoutProvider>
        <TaskProvider>
          {children}
        </TaskProvider>
      </LayoutProvider>
    </AuthContext.Provider>
  );
};

// Onboarding route — authenticated only; if workspace_mode set, redirect to /app
const OnboardingRoute = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen bg-[#FAFAF8] flex items-center justify-center p-6">
        <div className="flex flex-col items-center gap-6 max-w-sm text-center">
          <div className="w-12 h-12 border-2 border-[#666666] border-t-transparent rounded-full animate-spin" />
          <p className="text-[#666666]">Checking...</p>
        </div>
      </div>
    );
  }
  if (!user) return <Navigate to="/app" replace />;
  if (user.workspace_mode) return <Navigate to="/app" replace />;
  return children;
};

// Protected Route — no redirect to /auth; retry guest so user always gets in
const ProtectedRoute = ({ children }) => {
  const { user, loading, ensureGuest, enterDemoMode } = useAuth();
  const [retrying, setRetrying] = useState(false);
  const didRetryRef = useRef(false);

  useEffect(() => {
    if (user || loading || retrying || didRetryRef.current) return;
    didRetryRef.current = true;
    setRetrying(true);
    ensureGuest().then(() => setRetrying(false));
  }, [user, loading, retrying, ensureGuest]);

  if (loading || (retrying && !user)) {
    return (
      <div className="min-h-screen bg-[#FAFAF8] flex items-center justify-center p-6">
        <div className="flex flex-col items-center gap-6 max-w-sm text-center">
          <div className="w-12 h-12 border-2 border-[#666666] border-t-transparent rounded-full animate-spin" />
          <p className="text-[#666666]">Opening workspace...</p>
          <a href="/" className="w-full py-3 px-6 bg-[#1A1A1A] text-white font-medium rounded-lg hover:bg-[#333] no-underline">View website →</a>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-[#FAFAF8] flex items-center justify-center p-6">
        <div className="flex flex-col items-center gap-6 max-w-sm text-center">
          <p className="text-[#666666]">Could not start session.</p>
          <a href="/auth" className="w-full py-3 px-6 bg-[#1A1A1A] text-white font-medium rounded-lg hover:bg-[#333] no-underline block text-center">Sign in</a>
          <a href="/auth?mode=register" className="w-full py-3 px-6 bg-[#F3F1ED] text-[#1A1A1A] font-medium rounded-lg hover:bg-[#E0DCD5] border border-black/10 no-underline block text-center">Sign up</a>
          <button
            type="button"
            onClick={() => { setRetrying(true); ensureGuest().then(() => setRetrying(false)); }}
            className="w-full py-2 text-sm text-[#666666] hover:text-[#1A1A1A]"
          >
            Retry guest session
          </button>
          <a href="/" className="text-sm text-[#666666] hover:text-[#1A1A1A]">Go to home</a>
          <button type="button" onClick={enterDemoMode} className="mt-4 text-sm text-[#666666] hover:text-[#1A1A1A] underline">Continue to workspace (demo — won&apos;t save)</button>
          <p className="text-xs text-[#888] mt-4 max-w-xs">If this keeps happening, redeploy the backend so <code className="bg-black/10 px-1 rounded">POST /api/auth/guest</code> is available. Check Railway logs for errors.</p>
        </div>
      </div>
    );
  }
  if (!user.workspace_mode) {
    return <Navigate to="/onboarding" replace />;
  }
  return children;
};

// Admin route: require admin_role or redirect to app
const AdminRoute = ({ children }) => {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) {
    return (
      <div className="min-h-screen bg-[#FAFAF8] flex items-center justify-center p-6">
        <div className="flex flex-col items-center gap-6 max-w-sm text-center">
          <div className="w-12 h-12 border-2 border-[#666666] border-t-transparent rounded-full animate-spin" />
          <a href="/" className="w-full py-3 px-6 bg-[#1A1A1A] text-white font-medium rounded-lg hover:bg-[#333] no-underline">View website →</a>
        </div>
      </div>
    );
  }
  if (!user) return <Navigate to="/auth" state={{ from: location }} replace />;
  if (!user.admin_role) return <Navigate to="/app" replace />;
  return children;
};

// Redirect /workspace → /app/workspace so the left sidebar (Layout) always shows; preserve query string.
function RedirectWorkspaceToApp() {
  const { search } = useLocation();
  return <Navigate to={`/app/workspace${search}`} replace />;
}

/** Deep links to /app/auto-runner land on the unified workspace (same shell, query preserved). */
function AutoRunnerRedirect() {
  const { search } = useLocation();
  return <Navigate to={`/app/workspace${search}`} replace />;
}

// On route change: scroll to top so new page starts at top. When URL has a hash, scroll to that section so "go to" links land in the right place.
function ScrollToPlace() {
  const { pathname, hash } = useLocation();
  const prevPathRef = useRef(pathname);
  useEffect(() => {
    if (pathname !== prevPathRef.current) {
      prevPathRef.current = pathname;
      window.scrollTo(0, 0);
    }
    if (hash) {
      const id = hash.slice(1);
      const el = document.getElementById(id);
      if (el) {
        const t = setTimeout(() => {
          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
        return () => clearTimeout(t);
      }
    }
  }, [pathname, hash]);
  return null;
}

function App() {
  return (
    <AppErrorBoundary>
      <AuthProvider>
        <BrowserRouter>
        <ScrollToPlace />
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/our-projects" element={<OurProjectsPage />} />
          <Route path="/projects" element={<OurProjectsPage />} />
          <Route path="/project" element={<OurProjectsPage />} />
          <Route path="/auth" element={<AuthPage />} />
          <Route path="/onboarding" element={<OnboardingRoute><OnboardingPage /></OnboardingRoute>} />
          <Route path="/builder" element={<Builder />} />
          <Route path="/workspace" element={<RedirectWorkspaceToApp />} />
          <Route path="/share/:token" element={<ShareView />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="/terms" element={<Terms />} />
          <Route path="/security" element={<Security />} />
          <Route path="/aup" element={<Aup />} />
          <Route path="/dmca" element={<Dmca />} />
          <Route path="/cookies" element={<Cookies />} />
          <Route path="/about" element={<About />} />
          <Route path="/pricing" element={<Pricing />} />
          <Route path="/billing" element={<Navigate to="/app/billing" replace />} />
          <Route path="/account/billing" element={<Navigate to="/app/account/billing" replace />} />
          <Route path="/enterprise" element={<Enterprise />} />
          <Route path="/contact" element={<Contact />} />
          <Route path="/get-help" element={<GetHelp />} />
          <Route path="/features" element={<Features />} />
          <Route path="/templates" element={<TemplatesPublic />} />
          <Route path="/patterns" element={<PatternsPublic />} />
          <Route path="/learn" element={<LearnPublic />} />
          <Route path="/docs" element={<DocsPage />} />
          <Route path="/documentation" element={<DocsPage />} />
          <Route path="/tutorials" element={<TutorialsPage />} />
          <Route path="/shortcuts" element={<ShortcutsPublic />} />
          <Route path="/prompts" element={<PromptsPublic />} />
          <Route path="/benchmarks" element={<Benchmarks />} />
          <Route path="/blog" element={<Blog />} />
          <Route path="/blog/:slug" element={<Blog />} />
          <Route path="/changelog" element={<Changelog />} />
          <Route path="/status" element={<Status />} />
          <Route path="/app" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route index element={<Dashboard />} />
            <Route path="builder" element={<Builder />} />
            <Route path="workspace" element={<UnifiedWorkspace />} />
            <Route path="workspace-manus" element={<WorkspaceManus />} />
            <Route path="workspace-classic" element={<Workspace />} />
            <Route path="projects/new" element={<ProjectBuilder />} />
            <Route path="projects/:id" element={<AgentMonitor />} />
            <Route path="tokens" element={<TokenCenter />} />
            <Route path="billing" element={<Billing />} />
            <Route path="account/billing" element={<Billing />} />
            <Route path="exports" element={<ExportCenter />} />
            <Route path="patterns" element={<PatternLibrary />} />
            <Route path="templates" element={<TemplatesGallery />} />
            <Route path="prompts" element={<PromptLibrary />} />
            <Route path="learn" element={<LearnPanel />} />
            <Route path="env" element={<EnvPanel />} />
            <Route path="shortcuts" element={<ShortcutCheatsheet />} />
            <Route path="payments-wizard" element={<PaymentsWizard />} />
            <Route path="examples" element={<ExamplesGallery />} />
            <Route path="generate" element={<GenerateContent />} />
            <Route path="agents" element={<AgentsPage />} />
            <Route path="what-if" element={<WhatIfPage />} />
            <Route path="agents/:id" element={<AgentsPage />} />
            <Route path="settings" element={<Settings />} />
            <Route path="audit-log" element={<AuditLog />} />
            <Route path="monitoring" element={<MonitoringDashboard />} />
            <Route path="vibecode" element={<VibeCodePage />} />
            <Route path="ide" element={<UnifiedIDEPage />} />
            <Route path="models" element={<ModelManager />} />
            <Route path="fine-tuning" element={<FineTuning />} />
            <Route path="safety" element={<SafetyDashboard />} />
            <Route path="admin" element={<AdminRoute><AdminDashboard /></AdminRoute>} />
            <Route path="admin/users" element={<AdminRoute><AdminUsers /></AdminRoute>} />
            <Route path="admin/users/:id" element={<AdminRoute><AdminUserProfile /></AdminRoute>} />
            <Route path="admin/billing" element={<AdminRoute><AdminBilling /></AdminRoute>} />
            <Route path="admin/analytics" element={<AdminRoute><AdminAnalytics /></AdminRoute>} />
            <Route path="admin/legal" element={<AdminRoute><AdminLegal /></AdminRoute>} />
            <Route path="studio" element={<StudioPage />} />
            <Route path="knowledge" element={<KnowledgePage />} />
            <Route path="channels" element={<ChannelsPage />} />
            <Route path="sessions" element={<SessionsPage />} />
            <Route path="commerce" element={<CommerceManagePage />} />
            <Route path="members" element={<WorkspaceMembersPage />} />
            <Route path="skills" element={<SkillsPage />} />
            <Route path="skills/marketplace" element={<SkillsMarketplace />} />
            <Route path="auto-runner" element={<AutoRunnerRedirect />} />
          </Route>
        </Routes>
        </BrowserRouter>
      </AuthProvider>
    </AppErrorBoundary>
  );
}

export default App;

import { useState, useEffect, useRef, createContext, useContext, Component } from "react";
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation } from "react-router-dom";
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
        <div style={{ minHeight: "100vh", background: "#050505", color: "#fff", padding: 24, fontFamily: "sans-serif" }}>
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
import Enterprise from "./pages/Enterprise";
import Features from "./pages/Features";
import TemplatesPublic from "./pages/TemplatesPublic";
import PatternsPublic from "./pages/PatternsPublic";
import LearnPublic from "./pages/LearnPublic";
import ShortcutsPublic from "./pages/ShortcutsPublic";
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

// Empty REACT_APP_BACKEND_URL => same-origin /api (for single-URL deploy on Railway)
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL !== undefined ? process.env.REACT_APP_BACKEND_URL : 'http://localhost:8000';
export const API = BACKEND_URL ? `${BACKEND_URL}/api` : '/api';

// Auth Context
const AuthContext = createContext(null);

export const useAuth = () => useContext(AuthContext);

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem("token"));

  useEffect(() => {
    const checkAuth = async () => {
      if (token) {
        try {
          const res = await axios.get(`${API}/auth/me`, {
            headers: { Authorization: `Bearer ${token}` }
          });
          setUser(res.data);
        } catch (e) {
          localStorage.removeItem("token");
          setToken(null);
        }
      }
      setLoading(false);
    };
    checkAuth();
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
    setToken(null);
    setUser(null);
  };

  const loginWithToken = async (t) => {
    localStorage.setItem("token", t);
    setToken(t);
    try {
      const res = await axios.get(`${API}/auth/me`, { headers: { Authorization: `Bearer ${t}` } });
      setUser(res.data);
    } catch (e) {
      localStorage.removeItem("token");
      setToken(null);
    }
  };

  const refreshUser = async () => {
    if (token) {
      const res = await axios.get(`${API}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUser(res.data);
    }
  };

  return (
    <AuthContext.Provider value={{ user, token, login, register, logout, loading, refreshUser, loginWithToken, verifyMfa }}>
      {children}
    </AuthContext.Provider>
  );
};

// Protected Route
const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen bg-[#050505] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-gray-400">Loading...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/auth" state={{ from: location }} replace />;
  }

  return children;
};

// Admin route: require admin_role or redirect to app
const AdminRoute = ({ children }) => {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) {
    return (
      <div className="min-h-screen bg-[#050505] flex items-center justify-center">
        <div className="w-12 h-12 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }
  if (!user) return <Navigate to="/auth" state={{ from: location }} replace />;
  if (!user.admin_role) return <Navigate to="/app" replace />;
  return children;
};

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
          <Route path="/auth" element={<AuthPage />} />
          <Route path="/builder" element={<Builder />} />
          <Route path="/workspace" element={<ProtectedRoute><Workspace /></ProtectedRoute>} />
          <Route path="/share/:token" element={<ShareView />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="/terms" element={<Terms />} />
          <Route path="/security" element={<Security />} />
          <Route path="/aup" element={<Aup />} />
          <Route path="/dmca" element={<Dmca />} />
          <Route path="/cookies" element={<Cookies />} />
          <Route path="/about" element={<About />} />
          <Route path="/pricing" element={<Pricing />} />
          <Route path="/enterprise" element={<Enterprise />} />
          <Route path="/features" element={<Features />} />
          <Route path="/templates" element={<TemplatesPublic />} />
          <Route path="/patterns" element={<PatternsPublic />} />
          <Route path="/learn" element={<LearnPublic />} />
          <Route path="/shortcuts" element={<ShortcutsPublic />} />
          <Route path="/prompts" element={<PromptsPublic />} />
          <Route path="/benchmarks" element={<Benchmarks />} />
          <Route path="/blog" element={<Blog />} />
          <Route path="/app" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route index element={<Dashboard />} />
            <Route path="builder" element={<Builder />} />
            <Route path="workspace" element={<Workspace />} />
            <Route path="projects/new" element={<ProjectBuilder />} />
            <Route path="projects/:id" element={<AgentMonitor />} />
            <Route path="tokens" element={<TokenCenter />} />
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
            <Route path="agents/:id" element={<AgentsPage />} />
            <Route path="settings" element={<Settings />} />
            <Route path="audit-log" element={<AuditLog />} />
            <Route path="admin" element={<AdminRoute><AdminDashboard /></AdminRoute>} />
            <Route path="admin/users" element={<AdminRoute><AdminUsers /></AdminRoute>} />
            <Route path="admin/users/:id" element={<AdminRoute><AdminUserProfile /></AdminRoute>} />
            <Route path="admin/billing" element={<AdminRoute><AdminBilling /></AdminRoute>} />
            <Route path="admin/analytics" element={<AdminRoute><AdminAnalytics /></AdminRoute>} />
            <Route path="admin/legal" element={<AdminRoute><AdminLegal /></AdminRoute>} />
          </Route>
        </Routes>
        </BrowserRouter>
      </AuthProvider>
    </AppErrorBoundary>
  );
}

export default App;

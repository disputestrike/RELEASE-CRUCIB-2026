import { useState, useEffect, useCallback, useRef } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { API_BASE as API } from '../apiBase';
import { useLayoutStore } from '../stores/useLayoutStore';
import { useTaskStore } from '../stores/useTaskStore';
import axios from 'axios';
import { logApiError } from '../utils/apiError';
import { AnimatePresence, motion } from 'framer-motion';
import { Menu, X, Sparkles } from 'lucide-react';
import Layout3Column from './Layout3Column';
import Logo from './Logo';
import './Layout.css';
import Sidebar from './Sidebar';
import RightPanel from './RightPanel';
import OnboardingTour from './OnboardingTour';

/**
 * Layout — Redesigned wrapper
 * 
 * Changes from spec:
 * - Right panel hidden by default on non-workspace pages
 * - Right panel auto-slides in when on workspace/project build views
 * - Sidebar now receives only tasks (projects section removed per spec)
 * - Center panel state is managed by child pages (Dashboard = EMPTY state)
 */

const Layout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  /** Dashboard home (`/app`) — Manus-like: hide heavy footer rule so chat feels open */
  const isAppHomeDashboard = location.pathname === '/app' || location.pathname === '/app/';
  const { user, logout, token, refreshUser } = useAuth();
  const { sidebarOpen, setSidebarOpen, toggleSidebar } = useLayoutStore();
  const { tasks: storeTasks } = useTaskStore();
  const [backendOk, setBackendOk] = useState(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Right panel: HIDDEN on workspace (workspace has its own Sandpack panel)
  const isWorkspaceView = ['/app/workspace', '/app/workspace-manus', '/app/builder', '/app/auto-runner'].some(p => location.pathname.startsWith(p))
    || location.pathname.match(/\/app\/projects\/[^/]+$/);
  const [rightPanelVisible, setRightPanelVisible] = useState(false);

  // Auto-hide right panel on workspace views (workspace manages its own preview)
  useEffect(() => {
    setRightPanelVisible(false);
  }, [isWorkspaceView]);

  const [projects, setProjects] = useState([]);

  // Data for right panel
  const [previewContent, setPreviewContent] = useState(null);
  const [codeContent, setCodeContent] = useState(null);
  const [codeFiles, setCodeFiles] = useState({});
  const [terminalOutput, setTerminalOutput] = useState([]);
  const [buildHistory, setBuildHistory] = useState([]);
  /** Throttle refreshUser after health: every ping was hitting /auth/me and burning the API rate limit. */
  const lastUserRefreshRef = useRef(0);

  const checkBackend = useCallback(() => {
    setBackendOk(null);
    const healthUrl = API ? `${API.replace(/\/$/, '')}/health` : '/api/health';
    axios.get(healthUrl, { timeout: 5000 })
      .then(() => {
        setBackendOk(true);
        const now = Date.now();
        if (token && refreshUser && now - lastUserRefreshRef.current > 60_000) {
          lastUserRefreshRef.current = now;
          refreshUser().catch(() => {});
        }
      })
      .catch((e) => { logApiError('Layout health', e); setBackendOk(false); });
  }, [token, refreshUser]);

  // Fetch projects for sidebar. Do NOT overwrite task store — All Tasks list is from local store so clicks open workspace with correct task.
  const fetchSidebarData = useCallback(async () => {
    if (!token) return;
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const projRes = await axios.get(`${API}/projects`, { headers, timeout: 5000 }).catch((e) => { logApiError('Layout projects', e); return null; });
      if (projRes?.data) {
        setProjects(projRes.data?.projects || projRes.data || []);
      }
    } catch (e) {
      logApiError('Layout fetchSidebarData', e);
    }
  }, [token]);

  useEffect(() => {
    checkBackend();
    fetchSidebarData();
  }, [checkBackend, fetchSidebarData]);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const creditsAmount =
    user != null
      ? (user.credit_balance ?? Math.floor((user.token_balance ?? 0) / 1000) ?? 0).toLocaleString()
      : '—';

  // Sidebar content (receives collapse state for collapsed strip + account menu)
  const sidebarContent = (
    <Sidebar
      user={user}
      onLogout={handleLogout}
      projects={projects}
      tasks={storeTasks}
      sidebarOpen={sidebarOpen}
      onToggleSidebar={toggleSidebar}
    />
  );

  // Right panel content (only for workspace views, hidden by default elsewhere)
  const rightPanelContent = rightPanelVisible ? (
    <RightPanel
      preview={previewContent}
      code={codeContent}
      files={codeFiles}
      terminalOutput={terminalOutput}
      buildHistory={buildHistory}
      onClose={() => setRightPanelVisible(false)}
      onShare={() => {
        navigator.clipboard.writeText(window.location.href);
      }}
      onDownload={() => {
        // Trigger download of current code
      }}
      onRefreshPreview={() => {
        // Refresh preview iframe
      }}
    />
  ) : null;

  // Main content
  const mainContent = (
    <div className="layout-main-wrapper">
      {/* Credits — dashboard / rest of app only (workspace uses full vertical space) */}
      {!isWorkspaceView && (
        <div className="layout-topbar" role="region" aria-label="Credits">
          <Link to="/app/tokens" className="layout-topbar-credits" title="Credits & Billing">
            <Sparkles size={16} className="layout-topbar-credits-icon" aria-hidden />
            <span className="layout-topbar-credits-value">{creditsAmount}</span>
          </Link>
        </div>
      )}

      {user?.internal_team && (
        <div className="layout-internal-banner">
          {user?.internal_label || '[INTERNAL]'} — Internal use only
        </div>
      )}

      <div
        className={`layout-page-content ${isWorkspaceView ? 'layout-page-content--fullbleed' : ''} ${isAppHomeDashboard ? 'layout-page-content--dash-home' : ''}`}
      >
        <Outlet context={{
          setPreviewContent,
          setCodeContent,
          setCodeFiles,
          setTerminalOutput,
          setBuildHistory,
          setRightPanelVisible,
          backendOk,
          checkBackend,
        }} />
      </div>

      {/* Footer — hidden on workspace (max vertical space); home chat trust line; elsewhere status + legal */}
      {!isWorkspaceView && (
        <footer className={`layout-footer ${isAppHomeDashboard ? 'layout-footer--dash-home layout-footer--chat-trust-only' : ''}`}>
          {isAppHomeDashboard ? (
            <p className="layout-footer-trust">
              CrucibAI can make mistakes. Please double-check important responses.
            </p>
          ) : (
            <>
              <span className="layout-footer-status">
                {backendOk === true && <span className="status-green">● Connected</span>}
                {backendOk === false && (
                  <>
                    <span className="status-amber">● Disconnected</span>
                    <button type="button" onClick={checkBackend} className="status-retry">Retry</button>
                  </>
                )}
                {backendOk === null && <span className="status-gray">● Checking…</span>}
              </span>
              <span className="layout-footer-links">
                <Link to="/about">About</Link>
                <Link to="/get-help">Get help</Link>
                <Link to="/contact">Contact</Link>
                <Link to="/privacy">Privacy</Link>
                <Link to="/terms">Terms</Link>
              </span>
            </>
          )}
        </footer>
      )}
    </div>
  );

  return (
    <div className="app-viewport">
      {/* Mobile Header */}
      <header className="layout-mobile-header-bar">
        <Logo variant="full" height={28} href="/app" className="layout-mobile-logo" showTagline={false} />
        <div className="layout-mobile-header-actions">
          {!isWorkspaceView && (
            <Link to="/app/tokens" className="layout-mobile-credits" title="Credits & Billing">
              <Sparkles size={16} className="layout-mobile-credits-icon" aria-hidden />
              <span className="layout-mobile-credits-value">{creditsAmount}</span>
            </Link>
          )}
          <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="layout-mobile-menu-btn" aria-label="Toggle menu">
            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </header>

      {/* Mobile Menu Overlay */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, x: '-100%' }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: '-100%' }}
            className="layout-mobile-overlay"
          >
            {sidebarContent}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Desktop 3-Column Layout — sidebar state from store (Phase 3) */}
      <Layout3Column
        sidebar={sidebarContent}
        main={mainContent}
        rightPanel={rightPanelContent}
        sidebarOpen={sidebarOpen}
        onToggleSidebar={toggleSidebar}
        setSidebarOpen={setSidebarOpen}
        hideSidebarToggle={false}
        className={isAppHomeDashboard ? 'layout-shell--dash-home' : ''}
      />

      {/* Onboarding Tour for first-time users */}
      <OnboardingTour />
    </div>
  );
};

export default Layout;

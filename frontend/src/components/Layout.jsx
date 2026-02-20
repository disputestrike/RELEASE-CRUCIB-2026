import { useState, useEffect, useCallback } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth, API } from '../App';
import axios from 'axios';
import { AnimatePresence, motion } from 'framer-motion';
import { Menu, X, PanelRightOpen, PanelRightClose } from 'lucide-react';
import Layout3Column from './Layout3Column';
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
  const { user, logout, token } = useAuth();
  const [backendOk, setBackendOk] = useState(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Right panel: hidden by default, auto-shown on workspace/project views
  const isWorkspaceView = ['/app/workspace', '/app/builder'].some(p => location.pathname.startsWith(p))
    || location.pathname.match(/\/app\/projects\/[^/]+$/);
  const [rightPanelVisible, setRightPanelVisible] = useState(isWorkspaceView);

  // Auto-show/hide right panel based on route
  useEffect(() => {
    setRightPanelVisible(isWorkspaceView);
  }, [isWorkspaceView]);

  // Data for sidebar
  const [projects, setProjects] = useState([]);
  const [tasks, setTasks] = useState([]);

  // Data for right panel
  const [previewContent, setPreviewContent] = useState(null);
  const [codeContent, setCodeContent] = useState(null);
  const [codeFiles, setCodeFiles] = useState({});
  const [terminalOutput, setTerminalOutput] = useState([]);
  const [buildHistory, setBuildHistory] = useState([]);

  const checkBackend = useCallback(() => {
    setBackendOk(null);
    axios.get(`${API}/health`, { timeout: 5000 })
      .then(() => setBackendOk(true))
      .catch(() => setBackendOk(false));
  }, []);

  // Fetch projects and tasks for sidebar
  const fetchSidebarData = useCallback(async () => {
    if (!token) return;
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [projRes, taskRes] = await Promise.allSettled([
        axios.get(`${API}/api/projects`, { headers, timeout: 5000 }),
        axios.get(`${API}/api/tasks`, { headers, timeout: 5000 }),
      ]);
      if (projRes.status === 'fulfilled') {
        setProjects(projRes.value.data?.projects || projRes.value.data || []);
      }
      if (taskRes.status === 'fulfilled') {
        setTasks(taskRes.value.data?.tasks || taskRes.value.data || []);
      }
    } catch (e) {
      // Silently fail — sidebar still works with empty lists
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

  // Sidebar content
  const sidebarContent = (
    <Sidebar
      user={user}
      onLogout={handleLogout}
      projects={projects}
      tasks={tasks}
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
      {/* Top bar toggle for right panel (only when panel is hidden on workspace views) */}
      {isWorkspaceView && !rightPanelVisible && (
        <div className="layout-topbar">
          <button
            className="layout-panel-toggle"
            onClick={() => setRightPanelVisible(true)}
            title="Show preview panel"
          >
            <PanelRightOpen size={18} />
          </button>
        </div>
      )}

      {user?.internal_team && (
        <div className="layout-internal-banner">
          {user?.internal_label || '[INTERNAL]'} — Internal use only
        </div>
      )}

      <div className="layout-page-content">
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

      {/* Footer */}
      <footer className="layout-footer">
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
          <Link to="/privacy">Privacy</Link>
          <Link to="/terms">Terms</Link>
        </span>
      </footer>
    </div>
  );

  return (
    <>
      {/* Mobile Header */}
      <header className="layout-mobile-header-bar">
        <Link to="/app" className="layout-mobile-logo">
          CrucibAI
        </Link>
        <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="layout-mobile-menu-btn">
          {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
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

      {/* Desktop 3-Column Layout */}
      <Layout3Column
        sidebar={sidebarContent}
        main={mainContent}
        rightPanel={rightPanelContent}
      />

      {/* Onboarding Tour for first-time users */}
      <OnboardingTour />
    </>
  );
};

export default Layout;

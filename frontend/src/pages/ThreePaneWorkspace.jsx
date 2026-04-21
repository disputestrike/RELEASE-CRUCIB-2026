/**
 * ThreePaneWorkspace.jsx — CF24
 * Strict 3-pane layout: LEFT nav | MIDDLE chat | RIGHT everything
 * Dev/Non-dev mode toggle gates which right-pane tabs are visible.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  Home, FolderKanban, Bot, Wrench, Store, BarChart3,
  History, Code2, Settings as SettingsIcon,
  ChevronLeft, ChevronRight, Play, Square,
} from 'lucide-react';
import axios from 'axios';
import { API_BASE as API } from '../apiBase';
import { useAuth } from '../authContext';
import '../styles/three_pane.css';

const NAV = [
  { to: '/app/workspace',       label: 'Workspace', icon: Home },
  { to: '/app/dashboard',       label: 'Projects',  icon: FolderKanban },
  { to: '/app/agents',          label: 'Agents',    icon: Bot },
  { to: '/app/skills',          label: 'Skills',    icon: Wrench },
  { to: '/app/marketplace',     label: 'Marketplace', icon: Store },
  { to: '/app/benchmarks',      label: 'Benchmarks', icon: BarChart3 },
  { to: '/app/changelog',       label: 'Changelog', icon: History },
  { to: '/app/developer',       label: 'Developer', icon: Code2, devOnly: true },
  { to: '/app/settings',        label: 'Settings',  icon: SettingsIcon },
];

const EXECUTION_MODES = [
  { value: 'build',        label: 'Build' },
  { value: 'analyze_only', label: 'Analyze' },
  { value: 'plan_first',   label: 'Plan' },
  { value: 'migration',    label: 'Migrate' },
  { value: 'repair',       label: 'Repair' },
];

const DEV_TABS    = ['Artifacts', 'Plan', 'Preview', 'Logs', 'Code', 'Runs', 'Capability', 'Trust'];
const SIMPLE_TABS = ['Preview', 'Plan', 'Screenshots', 'Runs'];

export default function ThreePaneWorkspace() {
  const navigate = useNavigate();
  const { user } = useAuth() || {};
  const [collapsed, setCollapsed] = useState(false);
  const [mobileView, setMobileView] = useState('mid');
  const [workspaceMode, setWorkspaceMode] = useState(() => {
    if (user?.workspace_mode) return user.workspace_mode;
    return localStorage.getItem('crucibai_workspace_mode') || 'developer';
  });
  const [mode, setMode] = useState('build');
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [running, setRunning] = useState(false);
  const [activeTab, setActiveTab] = useState('Preview');
  const textareaRef = useRef(null);

  const isDev = workspaceMode === 'developer';
  const tabs = isDev ? DEV_TABS : SIMPLE_TABS;

  useEffect(() => {
    if (!tabs.includes(activeTab)) setActiveTab(tabs[0]);
  }, [isDev, tabs, activeTab]);

  const toggleMode = (next) => {
    setWorkspaceMode(next);
    localStorage.setItem('crucibai_workspace_mode', next);
    const token = localStorage.getItem('token');
    if (token) {
      axios.post(`${API}/user/workspace-mode`, { mode: next }, {
        headers: { Authorization: `Bearer ${token}` },
        timeout: 5000,
      }).catch(() => { /* localStorage is enough */ });
    }
  };

  const onRun = async () => {
    const text = input.trim();
    if (!text || running) return;
    setMessages((m) => [...m, { role: 'user', text, ts: Date.now() }]);
    setInput('');
    setRunning(true);
    try {
      const token = localStorage.getItem('token');
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const r = await axios.post(`${API}/runs`, { prompt: text, mode }, { headers, timeout: 30000 });
      const reply = r?.data?.message || r?.data?.summary || 'Run started. See Runs tab for status.';
      setMessages((m) => [...m, { role: 'assistant', text: reply, ts: Date.now(), run_id: r?.data?.run_id }]);
      setActiveTab(isDev ? 'Logs' : 'Preview');
    } catch (err) {
      setMessages((m) => [...m, {
        role: 'assistant',
        text: `Run queued locally. (${err?.response?.status || 'offline'})`,
        ts: Date.now(),
      }]);
    } finally {
      setRunning(false);
    }
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      onRun();
    }
  };

  const visibleNav = useMemo(() => NAV.filter((n) => !n.devOnly || isDev), [isDev]);

  return (
    <div className="tp-root" data-testid="crucib-three-pane-root" data-mobile-view={mobileView}>
      {/* LEFT — nav */}
      <aside className="tp-left" data-collapsed={collapsed}>
        <div className="tp-left__header">
          <span>CrucibAI</span>
          <button type="button" className="tp-collapse-btn" onClick={() => setCollapsed((c) => !c)} aria-label="Collapse nav">
            {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
        </div>
        <nav className="tp-left__nav">
          {visibleNav.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end className={({ isActive }) => `tp-nav-item${isActive ? ' active' : ''}`}>
              <Icon />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="tp-left__footer">
          <div style={{ marginBottom: 8, color: '#71717a' }}>View</div>
          <div className="tp-mode-toggle" role="tablist" aria-label="Workspace view mode">
            <button
              type="button"
              className={`tp-mode-btn${isDev ? ' active' : ''}`}
              onClick={() => toggleMode('developer')}
              data-testid="tp-mode-dev"
            >Developer</button>
            <button
              type="button"
              className={`tp-mode-btn${!isDev ? ' active' : ''}`}
              onClick={() => toggleMode('simple')}
              data-testid="tp-mode-simple"
            >Builder</button>
          </div>
        </div>
      </aside>

      {/* MIDDLE — chat */}
      <section className="tp-mid" role="main">
        <div className="tp-mid__header">
          <div className="tp-mid__title">Thread</div>
          <select
            className="tp-mid__mode-select"
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            aria-label="Execution mode"
          >
            {EXECUTION_MODES.map((m) => (<option key={m.value} value={m.value}>{m.label}</option>))}
          </select>
        </div>
        <div className="tp-mid__messages" aria-live="polite">
          {messages.length === 0 ? (
            <div className="tp-empty-state">
              <strong>Start a thread</strong>
              Describe what you want to build, improve, or automate. Crucib will pick skills, tools, and a plan.
            </div>
          ) : messages.map((m, i) => (
            <div key={i} className={`tp-msg tp-msg--${m.role}`}>
              <div className="tp-msg__bubble">{m.text}</div>
            </div>
          ))}
        </div>
        <div className="tp-mid__composer">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Describe what you want to build… (⌘/Ctrl+Enter to run)"
            aria-label="Chat input"
          />
          <button
            type="button"
            className="tp-mid__run-btn"
            onClick={onRun}
            disabled={running || !input.trim()}
            data-testid="tp-run-btn"
          >
            {running ? <><Square size={14} /> Running</> : <><Play size={14} /> Run</>}
          </button>
        </div>
      </section>

      {/* RIGHT — everything else */}
      <aside className="tp-right" role="complementary">
        <div className="tp-right__tabs" role="tablist">
          {tabs.map((t) => (
            <button
              key={t}
              type="button"
              role="tab"
              aria-selected={activeTab === t}
              className={`tp-right__tab${activeTab === t ? ' active' : ''}`}
              onClick={() => setActiveTab(t)}
            >{t}</button>
          ))}
        </div>
        <div className="tp-right__pane" role="tabpanel">
          <RightPaneContent tab={activeTab} isDev={isDev} />
        </div>
      </aside>

      {/* Mobile tab bar */}
      <div className="tp-mobile-tabbar">
        {['nav', 'mid', 'right'].map((v) => (
          <button key={v} className={mobileView === v ? 'active' : ''} onClick={() => setMobileView(v)}>
            {v === 'nav' ? 'Menu' : v === 'mid' ? 'Chat' : 'More'}
          </button>
        ))}
      </div>
    </div>
  );
}

function RightPaneContent({ tab, isDev }) {
  if (tab === 'Preview') {
    return (
      <div>
        <div style={{ marginBottom: 12, fontSize: 13, color: '#52525b' }}>Live preview</div>
        <div style={{ border: '1px solid #e4e4e7', borderRadius: 8, overflow: 'hidden', background: '#fff', minHeight: 280 }}>
          <iframe
            title="preview"
            src="about:blank"
            style={{ width: '100%', minHeight: 280, border: 0 }}
          />
        </div>
        <div className="tp-empty-state" style={{ padding: '12px 0' }}>
          Preview attaches to the active run. Kick off a run from the chat to see it render here.
        </div>
      </div>
    );
  }
  if (tab === 'Plan')        return <SimpleList title="Plan"        empty="No plan yet. The plan tab shows steps as they're generated." />;
  if (tab === 'Artifacts')   return <SimpleList title="Artifacts"   empty="Files produced by the current run will appear here." />;
  if (tab === 'Screenshots') return <SimpleList title="Screenshots" empty="Visual snapshots from the preview will appear here." />;
  if (tab === 'Runs')        return <SimpleList title="Runs"        empty="Run history — click any run to resume or inspect." />;
  if (tab === 'Logs')        return <SimpleList title="Logs"        empty="Raw runtime logs. (Developer view only.)" />;
  if (tab === 'Code')        return <SimpleList title="Code"        empty="Changed files + diffs from the latest run." />;
  if (tab === 'Capability')  return <SimpleList title="Capability"  empty="Capability audit — what this run needed vs what was granted." />;
  if (tab === 'Trust')       return <SimpleList title="Trust"       empty="Proof score, test coverage, and reproducibility signals." />;
  return <div className="tp-empty-state">Pick a tab.</div>;
}

function SimpleList({ title, empty }) {
  return (
    <div>
      <div style={{ marginBottom: 12, fontSize: 13, fontWeight: 600, color: '#27272a' }}>{title}</div>
      <div className="tp-empty-state"><strong>Empty</strong>{empty}</div>
    </div>
  );
}

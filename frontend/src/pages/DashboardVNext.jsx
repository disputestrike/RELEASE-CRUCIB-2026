/**
 * DashboardVNext — Approved CrucibAI dashboard (CF34).
 *
 * This is the canonical post-login intent-intake surface. Route `/app/dashboard`
 * and `/app` (index) both mount this component. It owns its own chrome
 * (sidebar + center + top utility row) because the screenshot-exact layout
 * differs from the global Layout/Sidebar used by /app/workspace etc.
 *
 * Backend wiring (real endpoints only):
 *   GET  /api/auth/me                 — identity, plan, credits
 *   POST /api/ai/chat                 — main composer send
 *   POST /api/voice/transcribe        — mic dictation
 *   GET  /api/projects                — history/search + project list
 *   GET  /api/prompts/recent          — history enrichment
 *   GET  /api/prompts/saved           — Browse
 *   GET  /api/prompts/templates       — Template chip
 *   GET  /api/templates               — Browse + Template
 *   POST /api/templates/{id}/remix    — Template remix
 *   POST /api/runtime/what-if         — What-if chip
 *   GET  /api/automation/workflows    — Automation nav preview
 *   GET  /api/agents                  — Agents nav preview
 *   GET  /api/tokens/bundles          — Upgrade context
 *
 * Non-goals: this page does not render proof/trust panels, cost panels,
 * doctor, live-view, or engine-room widgets. Dashboard = intake. Workspace = execution.
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  Search,
  Plus,
  ChevronDown,
  Home,
  Folder,
  Bot,
  GitBranch,
  Zap,
  Bell,
  MessageSquare,
  Paperclip,
  Globe,
  Mic,
  ArrowUp,
  Sparkles,
  LayoutGrid,
  BarChart3,
  Briefcase,
  MoreHorizontal,
  PanelLeftClose,
  HelpCircle,
  Shield,
  Hammer,
  LineChart,
  ChevronRight,
} from 'lucide-react';
import { useAuth } from '../authContext';
import { API_BASE as API } from '../apiBase';
import Logo from '../components/Logo';
import './DashboardVNext.css';

// ---------- helpers ----------
function greetingByTime(d = new Date()) {
  const h = d.getHours();
  if (h < 12) return 'Good morning';
  if (h < 18) return 'Good afternoon';
  return 'Good evening';
}

function firstNameFromUser(user) {
  if (!user) return 'Guest';
  const raw =
    user.first_name ||
    user.name ||
    user.display_name ||
    user.full_name ||
    (user.email && !String(user.email).toLowerCase().includes('guest')
      ? String(user.email).split('@')[0]
      : null);
  if (!raw) return 'Guest';
  // Clean up "ben.xp" or "ben_xp" → "Ben"
  const cleaned = String(raw).split(/[._\s]+/)[0];
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

function relativeTime(ts) {
  if (!ts) return '';
  const date = new Date(ts);
  if (Number.isNaN(date.getTime())) return '';
  const sec = Math.round((Date.now() - date.getTime()) / 1000);
  if (sec < 60) return 'just now';
  const min = Math.round(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const d = Math.round(hr / 24);
  return `${d}d ago`;
}

function classifyHistoryItem(item) {
  // best-effort: map projects/jobs/prompts into dashboard history icon category
  const kind = (item?.kind || item?.type || item?.category || '').toLowerCase();
  const title = String(item?.title || item?.name || item?.goal || '').toLowerCase();
  if (kind.includes('automat') || title.includes('automat') || title.includes('schedule')) return 'automation';
  if (kind.includes('analysis') || title.includes('analyz') || title.includes('research') || title.includes('data')) return 'analysis';
  if (kind.includes('build') || kind.includes('project') || title.includes('build') || title.includes('app') || title.includes('landing') || title.includes('dashboard')) return 'build';
  return 'chat';
}

function iconForKind(kind, size = 14) {
  switch (kind) {
    case 'build':
      return <Hammer size={size} aria-hidden />;
    case 'analysis':
      return <LineChart size={size} aria-hidden />;
    case 'automation':
      return <Zap size={size} aria-hidden />;
    case 'chat':
    default:
      return <MessageSquare size={size} aria-hidden />;
  }
}

function isBuildIntent(text) {
  const t = String(text || '').toLowerCase();
  return /\b(build|create|make|fix|refactor|deploy|automate|scaffold|generate|app|site|dashboard|tool|import)\b/.test(t);
}

function normalizeReadiness(result, opts = {}) {
  if (result.status === 'fulfilled') return { state: 'ready', detail: opts.okText || 'ready' };
  const code = result.reason?.response?.status;
  if (code === 403) return { state: 'policy', detail: opts.policyText || 'policy gated' };
  if (code === 401) return { state: 'policy', detail: opts.authText || 'auth required' };
  return { state: 'degraded', detail: opts.failText || 'unavailable' };
}

function SystemsSummaryCard({ readiness, loading }) {
  const rows = [
    { key: 'simulation', label: 'Simulation orchestrator' },
    { key: 'mobile', label: 'Mobile builder' },
    { key: 'terminal', label: 'Terminal tooling' },
  ];

  const stateClass = {
    ready: 'dvx-systems-state--ready',
    policy: 'dvx-systems-state--policy',
    degraded: 'dvx-systems-state--degraded',
  };

  return (
    <div className="dvx-systems-card" aria-label="Systems readiness summary">
      <div className="dvx-systems-head">
        <div>
          <h3>Systems readiness</h3>
          <p>Current operator capabilities for workspace systems panel.</p>
        </div>
        <Link
          to="/app/workspace?mode=developer&surface=inspect&panel=systems"
          className="dvx-systems-open"
        >
          Open systems panel
          <ChevronRight size={14} aria-hidden />
        </Link>
      </div>
      <div className="dvx-systems-grid">
        {rows.map(({ key, label }) => {
          const entry = readiness[key] || { state: 'degraded', detail: 'unknown' };
          return (
            <div key={key} className="dvx-systems-row">
              <span>{label}</span>
              <div className="dvx-systems-status-wrap">
                <span className={`dvx-systems-state ${stateClass[entry.state] || 'dvx-systems-state--degraded'}`}>
                  {loading ? 'Checking…' : entry.state}
                </span>
                <small>{loading ? 'running checks' : entry.detail}</small>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------- sidebar ----------
function DashSidebar({
  user,
  creditsDisplay,
  onNewClick,
  searchQuery,
  setSearchQuery,
  history,
  onUpgradeClick,
  onLogoClick,
}) {
  const navItems = [
    { to: '/app/workspace', label: 'Workspace', Icon: Home },
    { to: '/app/projects', label: 'Projects', Icon: Folder },
    { to: '/app/agents', label: 'Agents', Icon: Bot },
    { to: '/app/what-if', label: 'What-if Analysis', Icon: GitBranch },
    { to: '/app/automation', label: 'Automation', Icon: Zap },
  ];

  return (
    <aside className="dvx-side" aria-label="Primary navigation">
      {/* Logo + collapse */}
      <div className="dvx-side-header">
        <Link to="/app/dashboard" className="dvx-logo-link" onClick={onLogoClick} aria-label="CrucibAI home">
          <Logo
            variant="full"
            height={28}
            href={null}
            className="dvx-logo"
            showTagline={false}
            showWordmark
            nameClassName="dvx-logo-text"
          />
        </Link>
        <button type="button" className="dvx-side-collapse" aria-label="Collapse sidebar" title="Collapse">
          <PanelLeftClose size={18} aria-hidden />
        </button>
      </div>

      {/* Search */}
      <div className="dvx-side-search">
        <Search size={14} className="dvx-side-search-icon" aria-hidden />
        <input
          type="text"
          className="dvx-side-search-input"
          placeholder="Search..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          aria-label="Search your work"
        />
        <span className="dvx-side-search-kbd" aria-hidden>⌘K</span>
      </div>

      {/* New button */}
      <button type="button" className="dvx-side-new" onClick={onNewClick}>
        <span className="dvx-side-new-left">
          <Plus size={16} aria-hidden />
          <span>New</span>
        </span>
        <ChevronDown size={16} aria-hidden className="dvx-side-new-chevron" />
      </button>

      {/* WORK nav */}
      <div className="dvx-side-section">
        <div className="dvx-side-label">WORK</div>
        <nav className="dvx-side-nav" aria-label="Work">
          {navItems.map(({ to, label, Icon }) => (
            <Link key={to} to={to} className="dvx-side-item">
              <Icon size={16} aria-hidden />
              <span>{label}</span>
            </Link>
          ))}
        </nav>
      </div>

      {/* HISTORY */}
      <div className="dvx-side-section dvx-side-section--history">
        <div className="dvx-side-label">HISTORY</div>
        <nav className="dvx-side-history" aria-label="Recent history">
          {history.length === 0 ? (
            <div className="dvx-side-history-empty">No recent items yet.</div>
          ) : (
            history.slice(0, 7).map((h) => {
              const kind = classifyHistoryItem(h);
              const title = h.title || h.name || h.goal || 'Untitled';
              const stamp = relativeTime(h.updated_at || h.created_at || h.last_updated);
              return (
                <Link
                  key={h.id || `${kind}-${title}`}
                  to={h.id ? `/app/projects/${h.id}` : '/app/workspace'}
                  state={h.id ? undefined : { initialPrompt: title }}
                  className="dvx-side-history-item"
                  title={title}
                >
                  <span className="dvx-side-history-icon">{iconForKind(kind, 14)}</span>
                  <span className="dvx-side-history-title">{title}</span>
                  {stamp && <span className="dvx-side-history-time">{stamp}</span>}
                </Link>
              );
            })
          )}
          <Link to="/app/projects" className="dvx-side-history-view-all">
            <span>View all history</span>
            <ChevronRight size={14} aria-hidden />
          </Link>
        </nav>
      </div>

      {/* Account row */}
      <div className="dvx-side-account">
        <div className="dvx-side-account-avatar" aria-hidden>
          {(firstNameFromUser(user)[0] || 'G').toUpperCase()}
        </div>
        <div className="dvx-side-account-info">
          <div className="dvx-side-account-name">{firstNameFromUser(user)}</div>
          <div className="dvx-side-account-plan">
            {user?.plan ? `${user.plan.charAt(0).toUpperCase()}${user.plan.slice(1)}` : 'Free'}
          </div>
        </div>
        <button type="button" className="dvx-side-account-upgrade" onClick={onUpgradeClick}>
          <Zap size={13} aria-hidden />
          <span>Upgrade to Pro</span>
        </button>
        <Link to="/app/settings" className="dvx-side-account-more" aria-label="Account menu" title="Account">
          <MoreHorizontal size={16} aria-hidden />
        </Link>
      </div>
    </aside>
  );
}

// ---------- center canvas ----------
function TopUtility({ creditsDisplay, user, onBellClick }) {
  return (
    <div className="dvx-top-utility">
      <Link to="/app/tokens" className="dvx-credits" title="Credits & Billing">
        <Zap size={14} aria-hidden className="dvx-credits-icon" />
        <span className="dvx-credits-value">{creditsDisplay}</span>
      </Link>
      <button type="button" className="dvx-bell" onClick={onBellClick} aria-label="Notifications" title="Notifications">
        <Bell size={16} aria-hidden />
      </button>
      <Link to="/app/settings" className="dvx-avatar" title="Account">
        {(firstNameFromUser(user)[0] || 'G').toUpperCase()}
      </Link>
    </div>
  );
}

function Composer({
  text,
  setText,
  onSend,
  busy,
  onAttach,
  onMic,
  recording,
  fileAttached,
}) {
  const inputRef = useRef(null);
  return (
    <div className={`dvx-composer ${busy ? 'dvx-composer--busy' : ''}`}>
      <textarea
        ref={inputRef}
        className="dvx-composer-input"
        placeholder="Ask anything or give an instruction..."
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (text.trim() && !busy) onSend();
          }
        }}
        rows={2}
        disabled={busy}
      />
      <div className="dvx-composer-tools">
        <button type="button" className="dvx-composer-tool" onClick={onAttach} title="Attach file" aria-label="Attach file">
          <Paperclip size={16} aria-hidden />
          {fileAttached && <span className="dvx-composer-tool-dot" aria-hidden />}
        </button>
        <div className="dvx-composer-tools-right">
          <button type="button" className="dvx-composer-tool" title="Web context" aria-label="Web context">
            <Globe size={16} aria-hidden />
          </button>
          <button
            type="button"
            className={`dvx-composer-tool ${recording ? 'dvx-composer-tool--rec' : ''}`}
            onClick={onMic}
            title={recording ? 'Stop dictation' : 'Start dictation'}
            aria-label={recording ? 'Stop dictation' : 'Start dictation'}
          >
            <Mic size={16} aria-hidden />
          </button>
          <button
            type="button"
            className="dvx-composer-send"
            onClick={onSend}
            disabled={busy || !text.trim()}
            aria-label="Send"
            title="Send"
          >
            <ArrowUp size={16} aria-hidden />
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------- component ----------
export default function DashboardVNext() {
  const navigate = useNavigate();
  const { user, token } = useAuth();
  const headers = useMemo(() => (token ? { Authorization: `Bearer ${token}` } : {}), [token]);

  // Composer state
  const [text, setText] = useState('');
  const [sendBusy, setSendBusy] = useState(false);
  const [sendError, setSendError] = useState('');
  const [fileAttached, setFileAttached] = useState(null);
  const fileInputRef = useRef(null);

  // Mic state
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const [recording, setRecording] = useState(false);

  // History / data
  const [projects, setProjects] = useState([]);
  const [recentPrompts, setRecentPrompts] = useState([]);
  const [history, setHistory] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');

  // Credits
  const creditsDisplay = useMemo(() => {
    if (!user) return '—';
    const val = user.credit_balance ?? Math.floor((user.token_balance ?? 0) / 1000);
    if (val == null || Number.isNaN(val)) return '—';
    return Number(val).toLocaleString();
  }, [user]);

  // ---------- load dashboard data ----------
  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    (async () => {
      try {
        const [projRes, recentRes] = await Promise.allSettled([
          axios.get(`${API}/projects`, { headers, timeout: 10000 }),
          axios.get(`${API}/prompts/recent`, { headers, timeout: 10000 }),
        ]);
        if (cancelled) return;
        if (projRes.status === 'fulfilled') {
          const rows = projRes.value.data?.projects || projRes.value.data || [];
          setProjects(Array.isArray(rows) ? rows : []);
        }
        if (recentRes.status === 'fulfilled') {
          const rows = recentRes.value.data?.prompts || recentRes.value.data || [];
          setRecentPrompts(Array.isArray(rows) ? rows : []);
        }
      } catch {
        /* ignored */
      }
    })();
    return () => { cancelled = true; };
  }, [token, headers]);

  // Build unified history from projects + recentPrompts, filtered by searchQuery
  useEffect(() => {
    const projectItems = (projects || []).map((p) => ({
      id: p.id || p.project_id,
      title: p.name || p.title || 'Untitled project',
      kind: 'build',
      updated_at: p.updated_at || p.last_updated || p.created_at,
    }));
    const promptItems = (recentPrompts || []).map((pr, i) => ({
      id: pr.id || `prompt-${i}`,
      title: pr.title || pr.prompt || pr.text || 'Recent prompt',
      kind: pr.kind || 'chat',
      updated_at: pr.updated_at || pr.created_at,
    }));
    const merged = [...projectItems, ...promptItems].sort((a, b) => {
      const ta = a.updated_at ? new Date(a.updated_at).getTime() : 0;
      const tb = b.updated_at ? new Date(b.updated_at).getTime() : 0;
      return tb - ta;
    });
    const q = searchQuery.trim().toLowerCase();
    const filtered = q ? merged.filter((m) => String(m.title).toLowerCase().includes(q)) : merged;
    setHistory(filtered);
  }, [projects, recentPrompts, searchQuery]);

  // ---------- send flow ----------
  const handleSend = useCallback(async () => {
    const raw = text.trim();
    if (!raw || sendBusy) return;
    setSendBusy(true);
    setSendError('');
    try {
      // If execution-heavy, hand off straight to workspace with the prompt (autoStart).
      if (isBuildIntent(raw)) {
        navigate('/app/workspace', {
          state: {
            initialPrompt: raw,
            autoStart: true,
            handoffNonce: Date.now(),
            attachment: fileAttached?.name || null,
          },
        });
        return;
      }

      // Otherwise answer inline via /api/ai/chat.
      const fd = new FormData();
      fd.append('message', raw);
      fd.append('model', 'auto');
      if (fileAttached) fd.append('file', fileAttached);

      const res = await axios.post(`${API}/ai/chat`, fd, {
        headers: { ...headers },
        timeout: 60000,
      }).catch(async (err) => {
        // Retry with JSON body if multipart isn't accepted.
        if (err?.response?.status === 415 || err?.response?.status === 422) {
          return axios.post(
            `${API}/ai/chat`,
            { message: raw, model: 'auto' },
            { headers: { ...headers, 'Content-Type': 'application/json' }, timeout: 60000 },
          );
        }
        throw err;
      });

      // If the backend recommends workspace handoff, honor it.
      const data = res?.data || {};
      if (data.route === 'workspace' || data.next === 'workspace' || data.handoff === true) {
        navigate('/app/workspace', {
          state: {
            initialPrompt: raw,
            autoStart: true,
            handoffNonce: Date.now(),
          },
        });
        return;
      }

      // Inline answer: move the user into workspace chat for continuity (dashboard is intake, workspace is execution).
      navigate('/app/workspace', {
        state: {
          initialPrompt: raw,
          initialReply: data.reply || data.response || data.message || '',
          autoStart: false,
          handoffNonce: Date.now(),
        },
      });
    } catch (e) {
      setSendError(e?.response?.data?.detail || e?.message || 'Send failed.');
    } finally {
      setSendBusy(false);
      setText('');
      setFileAttached(null);
    }
  }, [text, sendBusy, fileAttached, headers, navigate]);

  // ---------- attach ----------
  const handleAttachClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);
  const handleFilePicked = useCallback((e) => {
    const f = e.target.files?.[0];
    if (f) setFileAttached(f);
    e.target.value = '';
  }, []);

  // ---------- mic ----------
  const startRecording = useCallback(async () => {
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        setSendError('Microphone not supported in this browser.');
        return;
      }
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      audioChunksRef.current = [];
      mr.ondataavailable = (ev) => { if (ev.data.size > 0) audioChunksRef.current.push(ev.data); };
      mr.onstop = async () => {
        try {
          const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          const fd = new FormData();
          fd.append('file', blob, 'voice.webm');
          const res = await axios.post(`${API}/voice/transcribe`, fd, { headers, timeout: 45000 });
          const t = res?.data?.transcript || res?.data?.text || '';
          if (t) setText((prev) => (prev ? `${prev} ${t}` : t));
        } catch (e) {
          setSendError('Transcription failed.');
        } finally {
          stream.getTracks().forEach((tr) => tr.stop());
        }
      };
      mr.start();
      mediaRecorderRef.current = mr;
      setRecording(true);
    } catch (e) {
      setSendError('Microphone permission denied.');
    }
  }, [headers]);

  const stopRecording = useCallback(() => {
    try {
      mediaRecorderRef.current?.stop();
    } catch { /* ignore */ }
    setRecording(false);
  }, []);

  const handleMicClick = useCallback(() => {
    if (recording) stopRecording();
    else startRecording();
  }, [recording, startRecording, stopRecording]);

  // ---------- chips ----------
  const handleChipUseAI = useCallback(() => {
    if (!text.trim()) {
      setText('Help me phrase this: ');
    }
  }, [text]);

  const [showBrowse, setShowBrowse] = useState(false);
  const [browseItems, setBrowseItems] = useState({ templates: [], saved: [], recent: [] });
  const openBrowse = useCallback(async () => {
    setShowBrowse(true);
    try {
      const [tpl, saved, recent] = await Promise.allSettled([
        axios.get(`${API}/prompts/templates`, { headers, timeout: 10000 }),
        axios.get(`${API}/prompts/saved`, { headers, timeout: 10000 }),
        axios.get(`${API}/prompts/recent`, { headers, timeout: 10000 }),
      ]);
      setBrowseItems({
        templates: tpl.status === 'fulfilled' ? (tpl.value.data?.templates || tpl.value.data || []) : [],
        saved: saved.status === 'fulfilled' ? (saved.value.data?.prompts || saved.value.data || []) : [],
        recent: recent.status === 'fulfilled' ? (recent.value.data?.prompts || recent.value.data || []) : [],
      });
    } catch { /* ignore */ }
  }, [headers]);

  const handleChipWhatIf = useCallback(async () => {
    const raw = text.trim() || 'Simulate the next best step for my current goal';
    try {
      setSendBusy(true);
      await axios.post(`${API}/runtime/what-if`, { goal: raw, prompt: raw }, { headers, timeout: 30000 }).catch(() => null);
      navigate('/app/workspace', {
        state: { initialPrompt: raw, mode: 'what-if', autoStart: true, handoffNonce: Date.now() },
      });
    } finally {
      setSendBusy(false);
    }
  }, [text, headers, navigate]);

  const [showMore, setShowMore] = useState(false);
  const [systemsReadyLoading, setSystemsReadyLoading] = useState(false);
  const [systemsReadiness, setSystemsReadiness] = useState({
    simulation: { state: 'degraded', detail: 'unknown' },
    mobile: { state: 'degraded', detail: 'unknown' },
    terminal: { state: 'degraded', detail: 'unknown' },
  });

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setSystemsReadyLoading(true);
    (async () => {
      const [simulationRes, mobileRes, terminalRes] = await Promise.allSettled([
        axios.get(`${API}/runtime/inspect?limit=1`, { headers, timeout: 8000 }),
        axios.get(`${API}/mobile/jobs`, { headers, timeout: 8000 }),
        axios.get(`${API}/terminal/audit?limit=1`, { headers, timeout: 8000 }),
      ]);
      if (cancelled) return;
      setSystemsReadiness({
        simulation: normalizeReadiness(simulationRes, {
          okText: 'runtime online',
          failText: 'runtime unavailable',
        }),
        mobile: normalizeReadiness(mobileRes, {
          okText: 'queue route online',
          failText: 'route unavailable',
        }),
        terminal: normalizeReadiness(terminalRes, {
          okText: 'terminal route online',
          policyText: 'policy disabled',
          authText: 'auth required',
          failText: 'route unavailable',
        }),
      });
      setSystemsReadyLoading(false);
    })().catch(() => {
      if (!cancelled) {
        setSystemsReadyLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [token, headers]);

  // ---------- suggested prompts ----------
  const suggestedPrompts = [
    { label: 'Build a task management app', Icon: Hammer },
    { label: 'Analyze my website performance', Icon: LineChart },
    { label: 'Create a marketing plan', Icon: Briefcase },
  ];

  // ---------- greeting ----------
  const first = firstNameFromUser(user);
  const greeting = `${greetingByTime()}, ${first}`;

  // ---------- render ----------
  return (
    <div className="dvx-root">
      <DashSidebar
        user={user}
        creditsDisplay={creditsDisplay}
        onNewClick={() => {
          setText('');
          setFileAttached(null);
          setTimeout(() => document.querySelector('.dvx-composer-input')?.focus(), 0);
        }}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        history={history}
        onUpgradeClick={() => navigate('/pricing')}
        onLogoClick={() => { /* already navigating via Link */ }}
      />

      <main className="dvx-main" role="main">
        <TopUtility
          creditsDisplay={creditsDisplay}
          user={user}
          onBellClick={() => navigate('/app/settings', { state: { openTab: 'notifications' } })}
        />

        <div className="dvx-hero">
          <h1 className="dvx-hero-greet">
            {greeting} <span aria-hidden>👋</span>
          </h1>
          <p className="dvx-hero-sub">What can I do for you today?</p>

          <Composer
            text={text}
            setText={setText}
            onSend={handleSend}
            busy={sendBusy}
            onAttach={handleAttachClick}
            onMic={handleMicClick}
            recording={recording}
            fileAttached={!!fileAttached}
          />

          {sendError && <div className="dvx-error" role="alert">{sendError}</div>}
          {fileAttached && (
            <div className="dvx-attached" role="status">
              Attached: <strong>{fileAttached.name}</strong>
              <button type="button" className="dvx-attached-clear" onClick={() => setFileAttached(null)}>Remove</button>
            </div>
          )}

          {/* hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            style={{ display: 'none' }}
            onChange={handleFilePicked}
            accept="image/*,application/pdf,text/*,.zip,.doc,.docx,.csv,.json,.md,.py,.js,.jsx,.ts,.tsx,.html"
          />

          {/* Action chips */}
          <div className="dvx-chips">
            <button type="button" className="dvx-chip" onClick={handleChipUseAI}>
              <Sparkles size={14} aria-hidden />
              <span>Use AI</span>
            </button>
            <Link to="/app/templates" className="dvx-chip">
              <LayoutGrid size={14} aria-hidden />
              <span>Template</span>
            </Link>
            <button type="button" className="dvx-chip" onClick={handleChipWhatIf}>
              <GitBranch size={14} aria-hidden />
              <span>What-if Analysis</span>
            </button>
            <button type="button" className="dvx-chip" onClick={openBrowse}>
              <Globe size={14} aria-hidden />
              <span>Browse</span>
            </button>
            <div className="dvx-chip-more-wrap">
              <button type="button" className="dvx-chip" onClick={() => setShowMore((v) => !v)}>
                <MoreHorizontal size={14} aria-hidden />
                <span>More</span>
                <ChevronDown size={12} aria-hidden />
              </button>
              {showMore && (
                <div className="dvx-chip-more-menu" role="menu">
                  <button type="button" className="dvx-chip-more-item" role="menuitem" onClick={() => { setShowMore(false); fileInputRef.current?.click(); }}>
                    Import code / zip
                  </button>
                  <Link to="/app/projects" className="dvx-chip-more-item" role="menuitem" onClick={() => setShowMore(false)}>
                    Connect a project
                  </Link>
                  <Link to="/app/exports" className="dvx-chip-more-item" role="menuitem" onClick={() => setShowMore(false)}>
                    Export
                  </Link>
                  <Link to="/app/settings" className="dvx-chip-more-item" role="menuitem" onClick={() => setShowMore(false)}>
                    Advanced options
                  </Link>
                </div>
              )}
            </div>
          </div>

          <SystemsSummaryCard readiness={systemsReadiness} loading={systemsReadyLoading} />

          {/* Suggested prompts */}
          <div className="dvx-suggested-label">Try asking</div>
          <div className="dvx-suggested">
            {suggestedPrompts.map(({ label, Icon }) => (
              <button
                key={label}
                type="button"
                className="dvx-suggested-chip"
                onClick={() => setText(label)}
              >
                <Icon size={14} aria-hidden />
                <span>{label}</span>
              </button>
            ))}
            <Link to="/app/prompts" className="dvx-suggested-chip dvx-suggested-chip--more">
              <span>More examples</span>
              <ChevronRight size={14} aria-hidden />
            </Link>
          </div>
        </div>

        {/* Footer disclaimer */}
        <div className="dvx-footer">
          <p>CrucibAI can make mistakes. Please verify important information.</p>
          <Link to="/learn" className="dvx-footer-learn">
            <span>Learn more</span>
            <ChevronRight size={12} aria-hidden />
          </Link>
        </div>
      </main>

      {/* Help floating button */}
      <Link to="/get-help" className="dvx-help" aria-label="Help" title="Help">
        <HelpCircle size={18} aria-hidden />
      </Link>

      {/* Browse modal */}
      {showBrowse && (
        <div className="dvx-modal" role="dialog" aria-label="Browse prompts and templates" onClick={() => setShowBrowse(false)}>
          <div className="dvx-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="dvx-modal-head">
              <h2>Browse</h2>
              <button type="button" className="dvx-modal-close" onClick={() => setShowBrowse(false)}>Close</button>
            </div>
            <div className="dvx-modal-body">
              <BrowseList title="Templates" items={browseItems.templates} onPick={(t) => { setText(t.prompt || t.description || t.name || ''); setShowBrowse(false); }} />
              <BrowseList title="Saved prompts" items={browseItems.saved} onPick={(t) => { setText(t.prompt || t.text || t.name || ''); setShowBrowse(false); }} />
              <BrowseList title="Recent prompts" items={browseItems.recent} onPick={(t) => { setText(t.prompt || t.text || t.name || ''); setShowBrowse(false); }} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function BrowseList({ title, items, onPick }) {
  if (!items || !items.length) {
    return (
      <section className="dvx-browse-section">
        <h3>{title}</h3>
        <p className="dvx-browse-empty">No items.</p>
      </section>
    );
  }
  return (
    <section className="dvx-browse-section">
      <h3>{title}</h3>
      <ul className="dvx-browse-list">
        {items.slice(0, 10).map((it, idx) => (
          <li key={it.id || idx}>
            <button type="button" onClick={() => onPick(it)} className="dvx-browse-item">
              <span className="dvx-browse-item-title">{it.title || it.name || it.prompt || 'Untitled'}</span>
              {(it.description || it.summary) && (
                <span className="dvx-browse-item-desc">{it.description || it.summary}</span>
              )}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

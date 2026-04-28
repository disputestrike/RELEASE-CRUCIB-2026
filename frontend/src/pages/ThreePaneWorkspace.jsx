import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  ArrowUp,
  Bell,
  Bot,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronsLeftRight,
  Circle,
  Database,
  ExternalLink,
  FileCode2,
  FolderKanban,
  Globe,
  LayoutDashboard,
  Mic,
  MoreHorizontal,
  Paperclip,
  Pencil,
  Plus,
  RefreshCw,
  Rocket,
  Search,
  Share2,
  Sparkles,
  Square,
  Zap,
} from 'lucide-react';
import axios from 'axios';
import { API_BASE as API } from '../apiBase';
import { useAuth } from '../authContext';
import { useTaskStore } from '../stores/useTaskStore';
import { useJobStream } from '../hooks/useJobStream';
import PreviewPanel from '../components/AutoRunner/PreviewPanel';
import WorkspaceFileTree from '../components/AutoRunner/WorkspaceFileTree';
import WorkspaceFileViewer from '../components/AutoRunner/WorkspaceFileViewer';
import ProofPanel from '../components/AutoRunner/ProofPanel';
import ExecutionTimeline from '../components/AutoRunner/ExecutionTimeline';
import Logo from '../components/Logo';
import '../styles/three_pane.css';

const RIGHT_TABS = ['Preview', 'Proof', 'Files', 'Database', 'Deploy', 'Logs'];
const LEFT_MIN = 240;
const LEFT_MAX = 340;
const RIGHT_MIN = 360;
const RIGHT_MAX = 560;

const NAV_ITEMS = [
  { key: 'workspace', label: 'Workspace', icon: LayoutDashboard, action: '/app/workspace' },
  { key: 'projects', label: 'Projects', icon: FolderKanban, action: '/app/projects/new' },
  { key: 'agents', label: 'Agents', icon: Bot, action: '/app/agents' },
  { key: 'files', label: 'Files', icon: FileCode2, action: '#tab:Files' },
  { key: 'proof', label: 'Proof', icon: CheckCircle2, action: '#tab:Proof' },
  { key: 'deploy', label: 'Deploy', icon: Rocket, action: '#tab:Deploy' },
  { key: 'automation', label: 'Automation', icon: Zap, action: '/app/live' },
  { key: 'settings', label: 'Settings', icon: Database, action: '/app/settings' },
];

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function compactTitle(text) {
  const value = String(text || '').trim();
  if (!value) return 'New workspace';
  return value.length > 42 ? `${value.slice(0, 42).trim()}...` : value;
}

function titleFromStep(step) {
  const key = String(step?.step_key || step?.phase || step?.agent_name || 'phase').replace(/[._-]+/g, ' ').trim();
  if (!key) return 'Phase';
  return key
    .split(' ')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function descFromStep(step) {
  if (step?.agent_name) return `Handled by ${String(step.agent_name).replace(/_/g, ' ')}`;
  if (step?.phase) return `Runtime phase: ${String(step.phase).replace(/_/g, ' ')}`;
  return 'Runtime step created by orchestrator';
}

function toPhaseStatus(stepStatus) {
  const value = String(stepStatus || '').toLowerCase();
  if (value === 'completed') return 'completed';
  if (value === 'failed' || value === 'error') return 'failed';
  if (value === 'running' || value === 'in_progress' || value === 'queued') return 'active';
  return 'pending';
}

function humanStatus(raw) {
  const value = String(raw || '').toLowerCase();
  if (value === 'running' || value === 'planning' || value === 'queued' || value === 'in_progress' || value === 'active') return 'In Progress';
  if (value === 'completed') return 'Completed';
  if (value === 'failed' || value === 'error') return 'Failed';
  if (value === 'deployed') return 'Deployed';
  if (value === 'waiting_input') return 'Waiting Input';
  if (value === 'blocked') return 'Blocked';
  return 'Pending';
}

function timeOf(ts) {
  const parsed = typeof ts === 'number' ? ts : Date.parse(String(ts || ''));
  const value = Number.isFinite(parsed) ? parsed : Date.now();
  return new Intl.DateTimeFormat('en-US', { hour: 'numeric', minute: '2-digit' }).format(value);
}

function timeAgo(ts) {
  if (!ts) return 'now';
  const parsed = typeof ts === 'number' ? ts : Date.parse(String(ts));
  if (!Number.isFinite(parsed)) return 'now';
  const diffMin = Math.max(0, Math.round((Date.now() - parsed) / 60000));
  if (diffMin < 1) return 'now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHour = Math.round(diffMin / 60);
  if (diffHour < 24) return `${diffHour}h ago`;
  return `${Math.round(diffHour / 24)}d ago`;
}

function extractLogText(payload) {
  if (!payload) return '';
  if (typeof payload.message === 'string' && payload.message.trim()) return payload.message;
  if (typeof payload.reason === 'string' && payload.reason.trim()) return payload.reason;
  if (typeof payload.status === 'string' && payload.status.trim()) return payload.status;
  return '';
}

function PhaseCard({ phase, index, open, onToggle, onLogs, onDatabase, onFiles }) {
  const icon = phase.status === 'completed'
    ? <CheckCircle2 size={18} />
    : phase.status === 'active'
      ? <ChevronsLeftRight size={18} />
      : <Circle size={18} />;

  return (
    <div className={`workspace-phase workspace-phase--${phase.status}`}>
      <div className="workspace-phase__spine" />
      <div className="workspace-phase__icon">{icon}</div>
      <div className="workspace-phase__card">
        <button type="button" className="workspace-phase__header" onClick={onToggle}>
          <div>
            <div className="workspace-phase__title">{index}. {phase.title}</div>
            <div className="workspace-phase__description">{phase.description}</div>
          </div>
          <div className="workspace-phase__meta">
            <span className={`workspace-phase__badge workspace-phase__badge--${phase.status}`}>{humanStatus(phase.status)}</span>
            {phase.timestamp ? <span>{timeOf(phase.timestamp)}</span> : null}
            <ChevronDown size={15} className={open ? 'workspace-phase__chevron-open' : ''} />
          </div>
        </button>

        {open ? (
          <div className="workspace-phase__details">
            {phase.substeps.length ? (
              <ul className="workspace-phase__checklist">
                {phase.substeps.slice(0, 4).map((substep) => (
                  <li key={substep.id}><Circle size={10} /> {substep.label}</li>
                ))}
              </ul>
            ) : null}

            {phase.logs.length ? (
              <div className="workspace-phase__logbox">
                {phase.logs.slice(0, 8).map((line) => (
                  <div key={line.id} className="workspace-phase__logline">
                    <span>{timeOf(line.ts)}</span>
                    <span>{line.text}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="workspace-phase__no-logs">No live logs yet for this phase.</div>
            )}

            <div className="workspace-phase__actions">
              <button type="button" onClick={onLogs}><FileCode2 size={14} /> View Logs</button>
              <button type="button" onClick={onDatabase}><Database size={14} /> Open Database</button>
              <button type="button" onClick={onFiles}><FileCode2 size={14} /> View Files</button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

export default function ThreePaneWorkspace() {
  const navigate = useNavigate();
  const location = useLocation();
  const fileInputRef = useRef(null);
  const messageRef = useRef([]);
  const draggingRef = useRef(null);
  const { user, token } = useAuth() || {};
  const { tasks, addTask, updateTask } = useTaskStore();

  const [mode, setMode] = useState('auto');
  const [workspaceMode, setWorkspaceMode] = useState(() => {
    if (user?.workspace_mode) return user.workspace_mode;
    return localStorage.getItem('crucibai_workspace_mode') || 'builder';
  });
  const [activeTab, setActiveTab] = useState('Preview');
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [running, setRunning] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [taskId, setTaskId] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [attachmentName, setAttachmentName] = useState('');
  const [railCollapsed, setRailCollapsed] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [leftPane, setLeftPane] = useState(() => {
    const raw = Number(localStorage.getItem('crucibai_workspace_left_width'));
    return Number.isFinite(raw) ? clamp(raw, LEFT_MIN, LEFT_MAX) : 272;
  });
  const [rightPane, setRightPane] = useState(() => {
    const raw = Number(localStorage.getItem('crucibai_workspace_right_width'));
    return Number.isFinite(raw) ? clamp(raw, RIGHT_MIN, RIGHT_MAX) : 440;
  });
  const [openPhaseId, setOpenPhaseId] = useState(null);

  const { job, steps, events, proof, isConnected, error: streamError } = useJobStream(jobId, token);

  useEffect(() => {
    messageRef.current = messages;
  }, [messages]);

  useEffect(() => {
    if (!RIGHT_TABS.includes(activeTab)) setActiveTab('Preview');
  }, [activeTab]);

  useEffect(() => {
    localStorage.setItem('crucibai_workspace_left_width', String(leftPane));
  }, [leftPane]);

  useEffect(() => {
    localStorage.setItem('crucibai_workspace_right_width', String(rightPane));
  }, [rightPane]);

  useEffect(() => {
    const st = location?.state;
    if (!st || typeof st.initialPrompt !== 'string') return;
    const trimmed = st.initialPrompt.trim();
    if (!trimmed) return;
    setInput(trimmed);
    navigate(location.pathname + location.search, { replace: true, state: {} });
  }, [location.pathname, location.search, location.state, navigate]);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const fromQuery = params.get('taskId');
    if (!fromQuery) return;
    setTaskId(fromQuery);
    const fromStore = tasks.find((task) => task.id === fromQuery);
    if (!fromStore) return;
    setJobId(fromStore.jobId || null);
    if (Array.isArray(fromStore.messages) && fromStore.messages.length) {
      setMessages(fromStore.messages);
    } else if (fromStore.prompt) {
      setMessages([{ role: 'user', text: fromStore.prompt, ts: fromStore.createdAt || Date.now() }]);
    }
  }, [location.search, tasks]);

  useEffect(() => {
    const onMove = (event) => {
      if (!draggingRef.current) return;
      if (draggingRef.current === 'left') {
        setLeftPane(clamp(event.clientX, LEFT_MIN, LEFT_MAX));
        return;
      }
      const nextRight = clamp(window.innerWidth - event.clientX, RIGHT_MIN, RIGHT_MAX);
      setRightPane(nextRight);
    };

    const onUp = () => {
      draggingRef.current = null;
      document.body.classList.remove('workspace-resizing');
    };

    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, []);

  const beginResize = (target) => {
    if (window.innerWidth < 900) return;
    draggingRef.current = target;
    document.body.classList.add('workspace-resizing');
  };

  const syncTask = useCallback((id, patch) => {
    if (!id) return;
    updateTask(id, {
      updatedAt: Date.now(),
      ...patch,
    });
  }, [updateTask]);

  const runGoal = useCallback(async (goalText) => {
    const text = (goalText || input).trim();
    if (!text || running) return;

    const now = Date.now();
    const userMessage = { role: 'user', text, ts: now };
    const nextTaskId = taskId || addTask({
      name: compactTitle(text),
      prompt: text,
      status: 'running',
      type: 'build',
      messages: [userMessage],
      createdAt: now,
    });

    if (!taskId) {
      setTaskId(nextTaskId);
      navigate(`/app/workspace?taskId=${encodeURIComponent(nextTaskId)}`, { replace: true });
    }

    const nextMessages = [...messageRef.current, userMessage];
    setMessages(nextMessages);
    syncTask(nextTaskId, {
      name: compactTitle(text),
      prompt: text,
      status: 'running',
      messages: nextMessages,
    });

    setInput('');
    setRunning(true);
    const headers = token ? { Authorization: `Bearer ${token}` } : {};

    try {
      const planRes = await axios.post(
        `${API}/orchestrator/plan`,
        { goal: text, mode: mode === 'auto' ? 'auto' : 'guided', build_target: null },
        { headers, timeout: 30000 },
      );
      const newJid = planRes?.data?.job_id;
      if (!newJid) throw new Error('no job_id returned from planner');

      setJobId(newJid);
      const assistant = {
        role: 'assistant',
        text: `Plan ready (${newJid.slice(0, 8)}). Starting orchestrator...`,
        ts: Date.now(),
      };
      const afterPlan = [...nextMessages, assistant];
      setMessages(afterPlan);
      syncTask(nextTaskId, {
        jobId: newJid,
        status: 'running',
        messages: afterPlan,
      });

      await axios.post(`${API}/orchestrator/run-auto`, { job_id: newJid }, { headers, timeout: 15000 });
      setActiveTab('Preview');
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || 'Run failed';
      const fail = { role: 'assistant', text: `Could not start run: ${detail}`, ts: Date.now() };
      const failedMessages = [...nextMessages, fail];
      setMessages(failedMessages);
      syncTask(nextTaskId, { status: 'failed', messages: failedMessages });
    } finally {
      setRunning(false);
    }
  }, [input, running, taskId, addTask, navigate, syncTask, token, mode]);

  const onRun = () => runGoal(input);

  const onKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      onRun();
    }
  };

  const headerTitle = useMemo(() => {
    const selectedTask = tasks.find((task) => task.id === taskId);
    if (selectedTask?.name) return selectedTask.name;
    const firstUser = messages.find((message) => message.role === 'user');
    return compactTitle(firstUser?.text || 'Build workspace');
  }, [messages, taskId, tasks]);

  const currentStatus = useMemo(() => {
    if (running) return 'In Progress';
    if (job?.status) return humanStatus(job.status);
    const selectedTask = tasks.find((task) => task.id === taskId);
    if (selectedTask?.status) return humanStatus(selectedTask.status);
    return messages.length ? 'Pending' : 'Draft';
  }, [running, job, tasks, taskId, messages.length]);

  const userInitial = String(user?.name || user?.email || 'G').trim().charAt(0).toUpperCase() || 'G';
  const credits = user != null
    ? (user.credit_balance ?? Math.floor((user.token_balance ?? 0) / 1000) ?? 200)
    : 200;

  const historyItems = useMemo(() => {
    const q = searchText.trim().toLowerCase();
    return (tasks || [])
      .filter((task) => {
        if (!q) return true;
        const haystack = `${task.name || ''} ${task.prompt || ''}`.toLowerCase();
        return haystack.includes(q);
      })
      .slice(0, 8);
  }, [tasks, searchText]);

  const phases = useMemo(() => {
    if (!jobId && !messages.length) return [];

    const byStepId = new Map();
    (events || []).forEach((event) => {
      const sid = event.step_id;
      if (!sid) return;
      if (!byStepId.has(sid)) byStepId.set(sid, []);
      byStepId.get(sid).push(event);
    });

    const normalized = (steps || []).map((step, index) => {
      const stepEvents = byStepId.get(step.id) || [];
      const logs = stepEvents
        .map((event, i) => ({
          id: `${event.id || event.event_type || 'event'}-${i}`,
          ts: event.created_at || event.ts || Date.now(),
          text: extractLogText(event.payload || {}) || event.event_type || 'event',
        }))
        .filter((line) => line.text);

      const substeps = stepEvents
        .filter((event) => ['step_started', 'step_retrying', 'step_completed', 'step_failed'].includes(String(event.event_type || '')))
        .map((event, i) => ({
          id: `${event.id || event.event_type || 'sub'}-${i}`,
          label: extractLogText(event.payload || {}) || String(event.event_type || 'update').replace(/_/g, ' '),
          status: String(event.event_type || 'pending').includes('failed') ? 'failed' : 'completed',
        }));

      return {
        id: step.id || `step-${index}`,
        title: titleFromStep(step),
        description: descFromStep(step),
        status: toPhaseStatus(step.status),
        timestamp: step.started_at || step.created_at || null,
        logs,
        substeps,
      };
    });

    if (normalized.length) return normalized;

    return [{
      id: `job-${jobId || 'draft'}`,
      title: titleFromStep({ step_key: job?.current_phase || 'planning' }),
      description: 'Waiting for runtime steps from orchestrator...',
      status: toPhaseStatus(job?.status || 'queued'),
      timestamp: job?.started_at || job?.created_at || null,
      logs: [],
      substeps: [],
    }];
  }, [events, jobId, job, messages.length, steps]);

  useEffect(() => {
    const firstActive = phases.find((phase) => phase.status === 'active') || phases[0] || null;
    if (!firstActive) {
      setOpenPhaseId(null);
      return;
    }
    setOpenPhaseId((prev) => prev || firstActive.id);
  }, [phases]);

  const previewUrl = job?.preview_url || proof?.preview_url || null;
  const addressValue = previewUrl || (jobId ? `https://preview.crucibai.app/${jobId}` : 'Start a build to generate preview URL');

  const openHistory = (item) => {
    setTaskId(item.id);
    setJobId(item.jobId || null);
    if (Array.isArray(item.messages) && item.messages.length) {
      setMessages(item.messages);
    }
    navigate(`/app/workspace?taskId=${encodeURIComponent(item.id)}`, { replace: true });
  };

  const onRename = () => {
    if (!taskId) return;
    const value = window.prompt('Rename project', headerTitle);
    if (!value || !value.trim()) return;
    syncTask(taskId, { name: value.trim() });
  };

  const onShare = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
    } catch {
      void 0;
    }
  };

  const onNav = (path) => {
    if (path.startsWith('#tab:')) {
      const nextTab = path.replace('#tab:', '').trim();
      if (RIGHT_TABS.includes(nextTab)) setActiveTab(nextTab);
      return;
    }
    if (path === '/app/workspace') return;
    navigate(path);
  };

  const isDeveloper = workspaceMode === 'developer';
  const isEmptyWorkspace = !jobId && messages.length === 0;

  return (
    <div
      className="workspace-shell"
      data-testid="crucib-three-pane-root"
      style={{
        gridTemplateColumns: `${railCollapsed ? 84 : leftPane}px 6px minmax(0,1fr)`,
      }}
    >
      <input
        ref={fileInputRef}
        className="workspace-hidden-input"
        type="file"
        onChange={(event) => setAttachmentName(event.target.files?.[0]?.name || '')}
      />

      <aside className={`workspace-rail${railCollapsed ? ' workspace-rail--collapsed' : ''}`}>
        <div className="workspace-rail__brand">
          <Logo variant="full" height={30} href="/app/dashboard" showTagline={false} className="workspace-rail__logo" />
          <button type="button" className="workspace-rail__utility" onClick={() => setRailCollapsed((value) => !value)}>
            <MoreHorizontal size={16} />
          </button>
        </div>

        <label className="workspace-rail__search">
          <Search size={15} />
          <input
            value={searchText}
            onChange={(event) => setSearchText(event.target.value)}
            placeholder="Search..."
            aria-label="Search"
          />
          <span>⌘K</span>
        </label>

        <button type="button" className="workspace-rail__new">
          <Plus size={15} />
          <span>New</span>
          <ChevronDown size={14} />
        </button>

        <div className="workspace-rail__section">
          <div className="workspace-rail__label">WORK</div>
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.key}
                type="button"
                className={`workspace-rail__nav${item.key === 'workspace' ? ' workspace-rail__nav--active' : ''}`}
                onClick={() => onNav(item.action)}
              >
                <Icon size={16} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>

        <div className="workspace-rail__section workspace-rail__section--history">
          <div className="workspace-rail__label">HISTORY</div>
          {historyItems.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`workspace-history${item.id === taskId ? ' workspace-history--active' : ''}`}
              onClick={() => openHistory(item)}
            >
              <span className={`workspace-history__dot workspace-history__dot--${String(item.status || 'pending').toLowerCase()}`} />
              <span className="workspace-history__body">
                <span className="workspace-history__title">{item.name || compactTitle(item.prompt)}</span>
                <span className="workspace-history__meta">{humanStatus(item.status)} · {timeAgo(item.updatedAt || item.createdAt)}</span>
              </span>
            </button>
          ))}
          <button type="button" className="workspace-rail__view-all">View all history <ChevronLeft size={14} className="workspace-rail__view-all-arrow" /></button>
        </div>

        <div className="workspace-rail__account">
          <div className="workspace-avatar workspace-avatar--large">{userInitial}</div>
          <div className="workspace-rail__account-meta">
            <strong>{user?.name || 'Guest'}</strong>
            <span>{user?.plan || 'Free'}</span>
          </div>
          <button type="button" className="workspace-rail__upgrade">Upgrade to Pro</button>
        </div>
      </aside>

      <div className="workspace-splitter" onMouseDown={() => beginResize('left')} aria-hidden>
        <ChevronsLeftRight size={14} />
      </div>

      <section className="workspace-canvas">
        <header className="workspace-header">
          <div className="workspace-header__title">
            <button type="button" className="workspace-icon-btn" onClick={() => navigate('/app/dashboard')}>
              <ChevronLeft size={18} />
            </button>
            <div>
              <div className="workspace-header__heading-row">
                <h1>{headerTitle}</h1>
                <button type="button" className="workspace-icon-btn" onClick={onRename}>
                  <Pencil size={14} />
                </button>
                <span className={`workspace-status workspace-status--${currentStatus.toLowerCase().replace(/\s+/g, '-')}`}>{currentStatus}</span>
              </div>
            </div>
          </div>

          <div className="workspace-header__actions">
            <div className="workspace-mode-toggle" role="tablist" aria-label="Workspace view mode">
              <button
                type="button"
                className={workspaceMode === 'builder' ? 'active' : ''}
                onClick={() => {
                  setWorkspaceMode('builder');
                  localStorage.setItem('crucibai_workspace_mode', 'builder');
                }}
              >
                Builder
              </button>
              <button
                type="button"
                className={workspaceMode === 'developer' ? 'active' : ''}
                onClick={() => {
                  setWorkspaceMode('developer');
                  localStorage.setItem('crucibai_workspace_mode', 'developer');
                }}
              >
                Developer
              </button>
            </div>
            <button type="button" className="workspace-action-btn" onClick={onShare}><Share2 size={15} /> Share</button>
            <button type="button" className="workspace-publish-btn" onClick={() => setActiveTab('Deploy')}><Rocket size={15} /> Publish <ChevronDown size={14} /></button>
            <div className="workspace-credit-pill"><Sparkles size={14} /> {credits}</div>
            <button type="button" className="workspace-icon-btn"><Bell size={16} /></button>
            <div className="workspace-avatar">{userInitial}</div>
          </div>
        </header>

        <div className="workspace-grid" style={{ gridTemplateColumns: `minmax(0,1fr) 6px ${rightPane}px` }}>
          <div className="workspace-thread">
            <div className="workspace-thread__messages">
              {messages.map((message, index) => (
                <div key={`${message.role}-${index}-${message.ts || 'ts'}`} className={`workspace-bubble workspace-bubble--${message.role}`}>
                  <div className="workspace-bubble__avatar">{message.role === 'assistant' ? <Logo variant="mark" height={20} showTagline={false} /> : userInitial}</div>
                  <div className="workspace-bubble__content">
                    <p>{message.text}</p>
                    <span>{timeOf(message.ts)}</span>
                  </div>
                </div>
              ))}

              {isEmptyWorkspace ? (
                <div className="workspace-empty-state">
                  <h2>Start a build</h2>
                  <p>Use the composer to create or resume a runtime project. Timeline phases will appear from live orchestrator state after the run starts.</p>
                </div>
              ) : (
                <div className="workspace-timeline">
                  {phases.map((phase, index) => (
                    <PhaseCard
                      key={phase.id}
                      phase={phase}
                      index={index + 1}
                      open={openPhaseId === phase.id}
                      onToggle={() => setOpenPhaseId((prev) => (prev === phase.id ? null : phase.id))}
                      onLogs={() => setActiveTab('Logs')}
                      onDatabase={() => setActiveTab('Database')}
                      onFiles={() => {
                        setWorkspaceMode('developer');
                        setActiveTab('Files');
                      }}
                    />
                  ))}
                </div>
              )}
            </div>

            <div className="workspace-composer">
              {attachmentName ? <div className="workspace-composer__attachment">Attached: {attachmentName}</div> : null}
              <div className="workspace-composer__box">
                <button type="button" className="workspace-icon-btn" onClick={() => fileInputRef.current?.click()}>
                  <Paperclip size={16} />
                </button>
                <textarea
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={onKeyDown}
                  placeholder="Ask anything or give an instruction..."
                  aria-label="Ask anything or give an instruction"
                />
                <button type="button" className="workspace-icon-btn"><Globe size={16} /></button>
                <button type="button" className="workspace-icon-btn"><Mic size={16} /></button>
                <button type="button" className="workspace-send-btn" onClick={onRun} disabled={running || !input.trim()}>
                  {running ? <Square size={16} /> : <ArrowUp size={16} />}
                </button>
              </div>
            </div>
          </div>

          <div className="workspace-splitter workspace-splitter--inner" onMouseDown={() => beginResize('right')} aria-hidden>
            <ChevronsLeftRight size={14} />
          </div>

          <aside className="workspace-inspector">
            <div className="workspace-tabs" role="tablist">
              {RIGHT_TABS.map((tab) => (
                <button key={tab} type="button" className={activeTab === tab ? 'active' : ''} onClick={() => setActiveTab(tab)}>
                  {tab === 'Preview' ? <LayoutDashboard size={14} /> : null}
                  {tab === 'Proof' ? <CheckCircle2 size={14} /> : null}
                  {tab === 'Files' ? <FileCode2 size={14} /> : null}
                  {tab === 'Database' ? <Database size={14} /> : null}
                  {tab === 'Deploy' ? <Rocket size={14} /> : null}
                  {tab === 'Logs' ? <FileCode2 size={14} /> : null}
                  <span>{tab}</span>
                </button>
              ))}
            </div>

            {activeTab === 'Preview' ? (
              <>
                <div className="workspace-browser-bar">
                  <button type="button" className="workspace-icon-btn"><ChevronLeft size={16} /></button>
                  <button type="button" className="workspace-icon-btn"><ChevronLeft size={16} className="workspace-browser-bar__flip" /></button>
                  <button type="button" className="workspace-icon-btn"><RefreshCw size={15} /></button>
                  <div className="workspace-browser-bar__address">{addressValue}</div>
                  <button type="button" className="workspace-icon-btn" onClick={() => previewUrl && window.open(previewUrl, '_blank', 'noopener,noreferrer')}>
                    <ExternalLink size={15} />
                  </button>
                </div>
                <div className="workspace-inspector__body">
                  <PreviewPanel
                    previewUrl={previewUrl}
                    status={job?.status || (running ? 'building' : 'idle')}
                    sandpackFiles={null}
                    sandpackDeps={null}
                    filesReadyKey={`job-${jobId || 'draft'}`}
                    blockedDetail={streamError || null}
                    jobId={jobId}
                    token={token}
                    apiBase={API}
                  />
                </div>
              </>
            ) : null}

            {activeTab === 'Proof' ? (
              <div className="workspace-inspector__body workspace-inspector__body--plain">
                {jobId ? <ProofPanel jobId={jobId} jobStatus={job?.status} proof={proof} /> : <div className="workspace-panel-empty">No proof yet. Start a run to generate evidence artifacts.</div>}
              </div>
            ) : null}

            {activeTab === 'Files' ? (
              <div className="workspace-inspector__body workspace-inspector__body--plain">
                {jobId ? (
                  <div className="workspace-file-surface">
                    <div className="workspace-file-surface__tree">
                      <WorkspaceFileTree
                        jobId={jobId}
                        token={token}
                        apiBase={API}
                        onSelect={setSelectedFile}
                        selected={selectedFile}
                      />
                    </div>
                    <div className="workspace-file-surface__viewer">
                      <WorkspaceFileViewer
                        jobId={jobId}
                        token={token}
                        apiBase={API}
                        file={selectedFile}
                      />
                    </div>
                  </div>
                ) : (
                  <div className="workspace-panel-empty">Files appear here when the orchestrator creates artifacts.</div>
                )}
              </div>
            ) : null}

            {activeTab === 'Database' ? (
              <div className="workspace-inspector__body workspace-inspector__body--plain">
                <div className="workspace-panel-card">
                  <h3>Database state</h3>
                  <p>Connected to runtime project data. This panel reflects schema-related artifacts and log-derived status.</p>
                  <div className="workspace-panel-card__meta">
                    <span>Connection: {isConnected ? 'Stream' : jobId ? 'Polling' : 'Idle'}</span>
                    <span>Mode: {isDeveloper ? 'Developer' : 'Builder'}</span>
                  </div>
                </div>
                <div className="workspace-database-list">
                  {(proof?.bundle?.database || []).slice(0, 8).map((item, index) => (
                    <div key={`${item?.title || item?.kind || 'db'}-${index}`} className="workspace-db-item">
                      <strong>{item?.title || item?.kind || 'Database artifact'}</strong>
                      <span>{item?.summary || item?.path || 'Generated by runtime phase execution.'}</span>
                    </div>
                  ))}
                  {!proof?.bundle?.database?.length ? <div className="workspace-panel-empty">No database artifacts yet for this run.</div> : null}
                </div>
              </div>
            ) : null}

            {activeTab === 'Deploy' ? (
              <div className="workspace-inspector__body workspace-inspector__body--plain">
                <div className="workspace-panel-card">
                  <h3>Publish and deploy</h3>
                  <p>State is read from the active runtime job and deploy proof artifacts when available.</p>
                  <div className="workspace-panel-card__meta">
                    <span>Status: {currentStatus}</span>
                    <span>Job: {jobId || 'not started'}</span>
                  </div>
                </div>
                {(proof?.bundle?.deploy || []).slice(0, 6).map((item, index) => (
                  <div key={`${item?.title || item?.kind || 'deploy'}-${index}`} className="workspace-db-item">
                    <strong>{item?.title || item?.kind || 'Deploy artifact'}</strong>
                    <span>{item?.summary || item?.path || 'Deploy metadata from proof bundle.'}</span>
                  </div>
                ))}
              </div>
            ) : null}

            {activeTab === 'Logs' ? (
              <div className="workspace-inspector__body workspace-inspector__body--plain">
                {jobId ? <ExecutionTimeline job={job} steps={steps || []} events={events || []} /> : <div className="workspace-panel-empty">Runtime logs appear here once a run starts.</div>}
              </div>
            ) : null}
          </aside>
        </div>
      </section>
    </div>
  );
}

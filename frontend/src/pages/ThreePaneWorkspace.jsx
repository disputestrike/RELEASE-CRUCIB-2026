import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  ArrowUp,
  Bell,
  Bot,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  Circle,
  CircleDashed,
  Database,
  ExternalLink,
  FileCode2,
  FolderKanban,
  GitBranch,
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

const EXECUTION_MODES = [
  { value: 'auto', label: 'Auto' },
  { value: 'build', label: 'Build' },
  { value: 'analyze_only', label: 'Analyze' },
  { value: 'plan_first', label: 'Plan' },
  { value: 'migration', label: 'Migrate' },
  { value: 'repair', label: 'Repair' },
];

const RIGHT_TABS = ['Preview', 'Proof', 'Database', 'Deploy', 'Logs'];

const PHASES = [
  { key: 'initialize', title: 'Initialize project', description: 'Creating project structure, installing dependencies...' },
  { key: 'schema', title: 'Design database schema', description: 'Analyzing requirements, tenant isolation, and schema planning.' },
  { key: 'auth', title: 'Setup authentication', description: 'Setting up auth system and user management.' },
  { key: 'modules', title: 'Build core modules', description: 'Creating tenant, billing, and dashboard modules.' },
  { key: 'payments', title: 'Integrate payment system', description: 'Setting up payment integration and billing.' },
  { key: 'analytics', title: 'Build analytics dashboard', description: 'Creating analytics and reporting dashboard.' },
  { key: 'deploy', title: 'Deploy to production', description: 'Setting up CI/CD and deploying application.' },
];

const NAV_ITEMS = [
  { key: 'workspace', label: 'Workspace', icon: LayoutDashboard, action: '/app/workspace' },
  { key: 'projects', label: 'Projects', icon: FolderKanban, action: '/app/projects/new' },
  { key: 'agents', label: 'Agents', icon: Bot, action: '/app/agents' },
  { key: 'files', label: 'Files', icon: FileCode2, action: '#tab:Database' },
  { key: 'proof', label: 'Proof', icon: CheckCircle2, action: '#tab:Proof' },
  { key: 'deploy', label: 'Deploy', icon: Rocket, action: '#tab:Deploy' },
  { key: 'automation', label: 'Automation', icon: Zap, action: '/app/live' },
  { key: 'settings', label: 'Settings', icon: GitBranch, action: '/app/settings' },
];

function compactTitle(text) {
  const value = String(text || '').trim();
  if (!value) return 'New workspace';
  return value.length > 32 ? `${value.slice(0, 32).trim()}...` : value;
}

function humanStatus(raw) {
  const value = String(raw || '').toLowerCase();
  if (value === 'running' || value === 'planning' || value === 'queued' || value === 'in_progress') return 'In Progress';
  if (value === 'completed') return 'Completed';
  if (value === 'failed' || value === 'error') return 'Failed';
  if (value === 'deployed') return 'Deployed';
  if (value === 'active') return 'In Progress';
  return 'Pending';
}

function timeOf(ts) {
  return new Intl.DateTimeFormat('en-US', { hour: 'numeric', minute: '2-digit' }).format(typeof ts === 'number' ? ts : Date.now());
}

function timeAgo(ts) {
  if (!ts) return 'now';
  const diffMin = Math.max(0, Math.round((Date.now() - ts) / 60000));
  if (diffMin < 1) return 'now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHour = Math.round(diffMin / 60);
  if (diffHour < 24) return `${diffHour}h ago`;
  return `${Math.round(diffHour / 24)}d ago`;
}

function PhaseCard({ phase, index, logs, onLogs, onDatabase, onFiles }) {
  const icon = phase.status === 'completed'
    ? <CheckCircle2 size={18} />
    : phase.status === 'active'
      ? <CircleDashed size={18} />
      : <Circle size={18} />;

  return (
    <div className={`workspace-phase workspace-phase--${phase.status}`}>
      <div className="workspace-phase__spine" />
      <div className="workspace-phase__icon">{icon}</div>
      <div className="workspace-phase__card">
        <div className="workspace-phase__header">
          <div>
            <div className="workspace-phase__title">{index}. {phase.title}</div>
            <div className="workspace-phase__description">{phase.description}</div>
          </div>
          <div className="workspace-phase__meta">
            <span className={`workspace-phase__badge workspace-phase__badge--${phase.status}`}>{humanStatus(phase.status)}</span>
            {phase.timestamp ? <span>{phase.timestamp}</span> : null}
            <ChevronDown size={15} />
          </div>
        </div>

        {phase.status === 'active' ? (
          <div className="workspace-phase__details">
            <ul className="workspace-phase__checklist">
              <li><Circle size={10} /> Analyzing requirements...</li>
              <li><Circle size={10} /> Designing multi-tenant schema...</li>
              <li><Circle size={10} /> Creating 28 tables...</li>
            </ul>
            <div className="workspace-phase__logbox">
              {logs.map((line) => (
                <div key={line.id} className="workspace-phase__logline">
                  <span>{timeOf(line.ts)}</span>
                  <span>{line.text}</span>
                </div>
              ))}
            </div>
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

  const { job, steps, events, proof, isConnected, error: streamError } = useJobStream(jobId, token);

  useEffect(() => {
    if (!RIGHT_TABS.includes(activeTab)) setActiveTab('Preview');
  }, [activeTab]);

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

    setMessages((prev) => [...prev, userMessage]);
    syncTask(nextTaskId, {
      name: compactTitle(text),
      prompt: text,
      status: 'running',
      messages: [...messages, userMessage],
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
        text: `I'll build this in the same workspace thread and keep progress visible. Job ${newJid.slice(0, 8)} started.`,
        ts: Date.now(),
      };
      setMessages((prev) => [...prev, assistant]);
      syncTask(nextTaskId, {
        jobId: newJid,
        status: 'running',
        messages: [...messages, userMessage, assistant],
      });

      await axios.post(`${API}/orchestrator/run-auto`, { job_id: newJid }, { headers, timeout: 15000 });
      setActiveTab('Preview');
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || 'Run failed';
      const fail = { role: 'assistant', text: `Could not start run: ${detail}`, ts: Date.now() };
      setMessages((prev) => [...prev, fail]);
      syncTask(nextTaskId, { status: 'failed', messages: [...messages, userMessage, fail] });
    } finally {
      setRunning(false);
    }
  }, [input, running, taskId, addTask, navigate, syncTask, messages, token, mode]);

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
    return compactTitle(firstUser?.text || 'Build SaaS platform');
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
      .slice(0, 6);
  }, [tasks, searchText]);

  const eventLines = useMemo(() => {
    if (events?.length) {
      return events.slice(-5).map((event) => ({
        id: event.id || `${event.event_type}-${event.created_at}`,
        ts: event.created_at ? new Date(event.created_at).getTime() : Date.now(),
        text: event.payload?.message || event.event_type || 'Processing event',
      }));
    }
    if (jobId) {
      return [
        { id: 'l1', ts: Date.now(), text: 'Analyzing business requirements' },
        { id: 'l2', ts: Date.now(), text: 'Identified 28 core entities' },
        { id: 'l3', ts: Date.now(), text: 'Designing tenant isolation strategy' },
        { id: 'l4', ts: Date.now(), text: 'Creating relationships and constraints' },
        { id: 'l5', ts: Date.now(), text: 'Schema design 75% complete' },
      ];
    }
    return [];
  }, [events, jobId]);

  const phases = useMemo(() => {
    const status = String(job?.status || '').toLowerCase();
    return PHASES.map((phase, index) => {
      let state = 'pending';
      if (status === 'completed') state = 'completed';
      else if (status === 'failed' || status === 'error') state = index <= 1 ? (index === 1 ? 'failed' : 'completed') : 'pending';
      else if (jobId) state = index === 0 ? 'completed' : index === 1 ? 'active' : 'pending';
      else if (messages.length) state = index === 0 ? 'active' : 'pending';

      return {
        ...phase,
        status: state,
        timestamp: index === 0 && (jobId || messages.length) ? timeOf(messages[0]?.ts || Date.now()) : null,
      };
    });
  }, [jobId, job?.status, messages]);

  const previewUrl = job?.preview_url || proof?.preview_url || null;
  const addressValue = previewUrl || `https://preview.crucibai.app/${headerTitle.toLowerCase().replace(/\s+/g, '-')}`;

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
      if (RIGHT_TABS.includes(nextTab)) {
        setActiveTab(nextTab);
      }
      return;
    }
    if (path === '/app/workspace') return;
    navigate(path);
  };

  const isDeveloper = workspaceMode === 'developer';

  return (
    <div className="workspace-shell" data-testid="crucib-three-pane-root">
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

        <div className="workspace-grid">
          <div className="workspace-thread">
            <div className="workspace-thread__messages">
              {messages.slice(0, 2).map((message, index) => (
                <div key={`${message.role}-${index}`} className={`workspace-bubble workspace-bubble--${message.role}`}>
                  <div className="workspace-bubble__avatar">{message.role === 'assistant' ? <Logo variant="mark" height={20} showTagline={false} /> : userInitial}</div>
                  <div className="workspace-bubble__content">
                    <p>{message.text}</p>
                    <span>{timeOf(message.ts)}</span>
                  </div>
                </div>
              ))}

              <div className="workspace-timeline">
                {phases.map((phase, index) => (
                  <PhaseCard
                    key={phase.key}
                    phase={phase}
                    index={index + 1}
                    logs={phase.key === 'schema' ? eventLines : []}
                    onLogs={() => setActiveTab('Logs')}
                    onDatabase={() => setActiveTab('Database')}
                    onFiles={() => {
                      setWorkspaceMode('developer');
                      setActiveTab('Database');
                    }}
                  />
                ))}
              </div>
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

          <aside className="workspace-inspector">
            <div className="workspace-tabs" role="tablist">
              {RIGHT_TABS.map((tab) => (
                <button key={tab} type="button" className={activeTab === tab ? 'active' : ''} onClick={() => setActiveTab(tab)}>
                  {tab === 'Preview' ? <LayoutDashboard size={14} /> : null}
                  {tab === 'Proof' ? <CheckCircle2 size={14} /> : null}
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
                <ProofPanel jobId={jobId} proof={proof} />
              </div>
            ) : null}

            {activeTab === 'Database' ? (
              <div className="workspace-inspector__body workspace-inspector__body--plain">
                <div className="workspace-panel-card">
                  <h3>Database artifacts</h3>
                  <p>Schema, generated files, and database-related evidence for this run appear here.</p>
                  <div className="workspace-panel-card__meta">
                    <span>Connection: {isConnected ? 'Live' : 'Polling'}</span>
                    <span>Mode: {isDeveloper ? 'Developer' : 'Builder'}</span>
                  </div>
                </div>
                {isDeveloper && jobId ? (
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
                ) : null}
              </div>
            ) : null}

            {activeTab === 'Deploy' ? (
              <div className="workspace-inspector__body workspace-inspector__body--plain">
                <div className="workspace-panel-card">
                  <h3>Publish and deploy</h3>
                  <p>Promote this build, inspect preview URLs, and open deployment logs from here.</p>
                  <div className="workspace-panel-card__meta">
                    <span>Status: {currentStatus}</span>
                    <span>Job: {jobId || 'not started'}</span>
                  </div>
                </div>
              </div>
            ) : null}

            {activeTab === 'Logs' ? (
              <div className="workspace-inspector__body workspace-inspector__body--plain">
                <ExecutionTimeline job={job} steps={steps || []} events={events || []} />
              </div>
            ) : null}
          </aside>
        </div>
      </section>
    </div>
  );
}

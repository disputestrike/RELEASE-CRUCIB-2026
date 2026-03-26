import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useNavigate, useSearchParams, useLocation, Link } from 'react-router-dom';
import JSZip from 'jszip';
import Editor from '@monaco-editor/react';
import {
  SandpackProvider,
  SandpackPreview,
} from '@codesandbox/sandpack-react';
import SandpackErrorBoundary from '../components/SandpackErrorBoundary';
import '../components/SandpackErrorBoundary.css';
import './Workspace.css';
import VoiceWaveform from '../components/VoiceWaveform';
import '../components/VoiceWaveform.css';
import Logo from '../components/Logo';
import {
  ChevronDown,
  ChevronRight,
  Send,
  Loader2,
  ArrowLeft,
  Download,
  Copy,
  Check,
  Mic,
  MicOff,
  Paperclip,
  X,
  FileCode,
  FolderOpen,
  Terminal,
  Eye,
  Maximize2,
  Minimize2,
  Sparkles,
  Image,
  FileText,
  Zap,
  RefreshCw,
  ExternalLink,
  Github,
  History,
  Settings,
  Menu,
  Globe,
  Upload,
  MoreHorizontal,
  Plus,
  PanelRightOpen,
  PanelLeftClose,
  Search,
  HelpCircle,
  Play,
  SplitSquareVertical,
  CreditCard,
  Wrench,
  ShieldCheck,
  Smartphone,
  Monitor,
  Rocket,
  RotateCcw,
  Share2,
  Folder,
  Database,
  BarChart3,
  BookOpen,
  GitBranch,
  Layers,
  Cpu,
  Globe2,
  Activity,
  Network,
  Sun,
  Moon,
} from 'lucide-react';
import { useAuth, API } from '../App';
import { useLayoutStore } from '../stores/useLayoutStore';
import { useTaskStore } from '../stores/useTaskStore';
import axios from 'axios';
import InlineAgentMonitor from '../components/InlineAgentMonitor';
import ManusComputer from '../components/ManusComputer';
import { CommandPalette } from '../components/AdvancedIDEUX';
import { VibeCodingInput } from '../components/VibeCoding';
import {
  DEFAULT_FILES,
  ConsolePanel,
  BuildHistoryPanel,
  formatMsgContent,
  getBuildEventPresentation,
  normalizeWorkspacePath,
  isWorkspaceDbPath,
  isWorkspaceDocPath,
  docSortKey,
  extractSqlTableNames,
  WorkspaceProPanels,
} from '../components/workspace';

// Main Workspace Component
const Workspace = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const { user, token } = useAuth();
  
  const [files, setFiles] = useState(DEFAULT_FILES);
  const [activeFile, setActiveFile] = useState('/App.js');

  // Files safe to pass to Sandpack — exclude backend/test/config files.
  // Sandpack React template expects /src/index.js and /src/App.js; map root-level App.js, index.js, styles.css into /src/ so preview runs.
  // Also post-process: BrowserRouter → MemoryRouter, inject Tailwind CDN into styles.css.
  const sandpackFiles = useMemo(() => {
    const EXCLUDED = /\.(test|spec)\.[jt]sx?$|Dockerfile|docker-compose|\.md$|\.sh$|\.ya?ml$|\.env|\.gitignore|server\.(js|ts)$|express|mongoose/i;
    const ALLOWED  = /\.(jsx?|tsx?|css|html|json)$/i;
    const BACKEND_CODE = /require\(['"]express['"]\)|require\(['"]mongoose['"]\)|require\(['"]mongodb['"]\)|from ['"]express['"]|from ['"]mongoose['"]|app\.listen\(|mongoose\.connect\(/;

    const filtered = Object.entries(files).filter(([path, f]) => {
      if (!ALLOWED.test(path) || EXCLUDED.test(path)) return false;
      if (f?.code && BACKEND_CODE.test(f.code)) return false;
      return true;
    });

    const ROOT_TO_SRC = { '/App.js': '/src/App.js', '/App.jsx': '/src/App.jsx', '/index.js': '/src/index.js', '/index.jsx': '/src/index.jsx', '/styles.css': '/src/styles.css' };

    const result = Object.fromEntries(
      filtered.map(([path, f]) => {
        const normalizedPath = path.startsWith('/') ? path : `/${path}`;
        const sandpackPath = ROOT_TO_SRC[normalizedPath] || normalizedPath;
        let code = f?.code || '';
        code = code
          .replace(/import\s*\{\s*BrowserRouter(\s*,\s*|\s+as\s+\w+\s*,?\s*)/g, 'import { MemoryRouter$1')
          .replace(/import\s*\{\s*([^}]*),?\s*BrowserRouter\s*,?\s*([^}]*)\}/g, (_, a, b) =>
            `import { ${[a, b].filter(Boolean).join(', ')}, MemoryRouter }`)
          .replace(/<BrowserRouter>/g, '<MemoryRouter>')
          .replace(/<\/BrowserRouter>/g, '</MemoryRouter>')
          .replace(/BrowserRouter\b/g, 'MemoryRouter');
        if (sandpackPath === '/src/index.js' || sandpackPath === '/src/index.jsx') {
          code = code.replace(/from\s+['"]\.\/App['"]/g, "from './App'");
        }
        if ((sandpackPath === '/src/styles.css' || normalizedPath === '/styles.css' || normalizedPath === '/src/styles.css') && !code.includes('tailwindcss') && !code.includes('tailwind')) {
          code = `@import url('https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css');\n\n` + code;
        }
        return [sandpackPath, { ...f, code }];
      })
    );

    const hasAppJsx = !!result['/src/App.jsx'];
    const hasAppJs = !!result['/src/App.js'];
    const hasApp = hasAppJsx || hasAppJs;
    const existingIndex = result['/src/index.js']?.code || result['/src/index.jsx']?.code || '';
    const indexValid = existingIndex.includes("getElementById('root')") && (existingIndex.includes('createRoot') || existingIndex.includes('render('));
    if (Object.keys(result).length > 0 && hasApp && (!result['/src/index.js'] && !result['/src/index.jsx'] || !indexValid)) {
      const appImport = hasAppJsx ? "import App from './App.jsx';" : "import App from './App.js';";
      result['/src/index.js'] = {
        code: `import React from 'react';
import ReactDOM from 'react-dom/client';
${appImport}
${result['/src/styles.css'] ? "import './styles.css';" : ''}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);`,
      };
    }
    return result;
  }, [files]);

  // Parse dependencies from package.json if the AI generated one
  const sandpackDeps = useMemo(() => {
    const base = {
      axios: '^1.6.2',
      'react-router-dom': '^6.8.0',
      'lucide-react': '^0.263.1',
      'date-fns': '^2.30.0',
      recharts: '^2.8.0',
      'framer-motion': '^10.16.4',
      clsx: '^2.0.0',
    };
    try {
      const pkgJson = files['/package.json']?.code || files['package.json']?.code;
      if (pkgJson) {
        const pkg = JSON.parse(pkgJson);
        return { ...base, ...(pkg.dependencies || {}), ...(pkg.devDependencies || {}) };
      }
    } catch (_) {}
    return base;
  }, [files]);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [isBuilding, setIsBuilding] = useState(false);
  const [buildProgress, setBuildProgress] = useState(0);
  const [sessionId, setSessionId] = useState(() => `session_${Date.now()}`);
  const [selectedModel, setSelectedModel] = useState('auto');
  const [autoLevel, setAutoLevel] = useState('balanced'); // quick | balanced | deep
  const [logs, setLogs] = useState([]);
  const [copied, setCopied] = useState(false);
  const [activePanel, setActivePanel] = useState('preview');
  const [activeBottomPanel, setActiveBottomPanel] = useState('terminal');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [versions, setVersions] = useState([]);
  const [currentVersion, setCurrentVersion] = useState(null);
  const [filesReadyKey, setFilesReadyKey] = useState('default');
  const [lastBuildKind, setLastBuildKind] = useState('fullstack'); // web=Sandpack preview, mobile=Expo Snack iframe
  const [expandedFolders, setExpandedFolders] = useState({}); // tracks open/closed folders in Explorer // triggers Sandpack remount only when files are truly committed
  
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const mediaRecorderRef = useRef(null);
  const [audioStream, setAudioStream] = useState(null);
  
  const [attachedFiles, setAttachedFiles] = useState([]);
  const [useStreaming, setUseStreaming] = useState(true);
  const [lastError, setLastError] = useState(null);
  const [currentPhase, setCurrentPhase] = useState('');
  const [buildPhases, setBuildPhases] = useState([]);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [agentsPanelOpen, setAgentsPanelOpen] = useState(false);
  const [agentsActivity, setAgentsActivity] = useState([]);
  const [chatMaximized, setChatMaximized] = useState(false);
  const [fileSearchOpen, setFileSearchOpen] = useState(false);
  const [lastTokensUsed, setLastTokensUsed] = useState(0);
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(true); // open by default
  const [showFirstRunBanner, setShowFirstRunBanner] = useState(() => !localStorage.getItem('crucibai_first_run'));
  const [rightSidebarOpen, setRightSidebarOpen] = useState(() => {
    try {
      const v = localStorage.getItem('crucibai_workspace_right_panel');
      return v !== 'false';
    } catch { return true; }
  });
  const setRightSidebarOpenPersisted = useCallback((value) => {
    setRightSidebarOpen(value);
    try { localStorage.setItem('crucibai_workspace_right_panel', String(value)); } catch (_) {}
  }, []);
  const resetLayout = useCallback(() => {
    setLeftSidebarOpen(true);
    setRightSidebarOpenPersisted(true);
    setActivePanel('preview');
  }, [setRightSidebarOpenPersisted]);
  const [splitEditor, setSplitEditor] = useState(false);
  const [buildCardExpanded, setBuildCardExpanded] = useState(false);
  const [menuAnchor, setMenuAnchor] = useState(null); // 'file' | 'edit' | 'view' | 'go' | 'run' | 'terminal' | 'help' | null
  const [toolsReport, setToolsReport] = useState(null); // { type: 'validate'|'security'|'a11y', data }
  const [toolsLoading, setToolsLoading] = useState(false);
  const [buildHistoryList, setBuildHistoryList] = useState([]);
  const [buildHistoryLoading, setBuildHistoryLoading] = useState(false);
  const [buildTimelineEvents, setBuildTimelineEvents] = useState([]);
  const [buildEventsErr, setBuildEventsErr] = useState(null);
  const [serverDbSnapshots, setServerDbSnapshots] = useState([]);
  const [serverDbLoading, setServerDbLoading] = useState(false);
  const [serverDbErr, setServerDbErr] = useState(null);
  const [serverDocSnapshots, setServerDocSnapshots] = useState([]);
  const [serverDocsLoading, setServerDocsLoading] = useState(false);
  const [serverDocsErr, setServerDocsErr] = useState(null);
  const [docsSelectedPath, setDocsSelectedPath] = useState(null);
  const [analyticsData, setAnalyticsData] = useState(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analyticsErr, setAnalyticsErr] = useState(null);
  const [agentApiStatuses, setAgentApiStatuses] = useState([]);
  const [projectSandboxLogs, setProjectSandboxLogs] = useState([]);
  const [projectSandboxLoading, setProjectSandboxLoading] = useState(false);
  const [projectSandboxErr, setProjectSandboxErr] = useState(null);
  const [apiHealth, setApiHealth] = useState('unknown');
  const [jobsChip, setJobsChip] = useState({ total: 0, active: 0 });
  const [consoleFilter, setConsoleFilter] = useState('all');
  const [workspaceTheme, setWorkspaceTheme] = useState(() => {
    try {
      return document.documentElement.getAttribute('data-theme') || localStorage.getItem('crucibai-theme') || 'dark';
    } catch {
      return 'dark';
    }
  });
  const toggleWorkspaceTheme = useCallback(() => {
    try {
      const cur = document.documentElement.getAttribute('data-theme') || localStorage.getItem('crucibai-theme') || 'dark';
      const next = cur === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('crucibai-theme', next);
      setWorkspaceTheme(next);
    } catch (_) {}
  }, []);
  const [nextSuggestions, setNextSuggestions] = useState([]);
  const [buildMode, setBuildMode] = useState('agent'); // 'quick' | 'plan' | 'agent' | 'thinking' | 'swarm'
  const { user: authUser, refreshUser } = useAuth();
  const { mode: layoutMode, setMode: setLayoutMode, isDev: devMode } = useLayoutStore();
  const toggleDevMode = async () => {
    const next = devMode ? 'simple' : 'dev';
    const backendMode = next === 'dev' ? 'developer' : 'simple';
    setLayoutMode(next);
    try {
      const token = localStorage.getItem('token');
      if (token) {
        await axios.post(`${API}/user/workspace-mode`, { mode: backendMode }, { headers: { Authorization: `Bearer ${token}` } });
        if (refreshUser) await refreshUser();
      }
    } catch (_) {}
  };
  const { addTask, updateTask, tasks: storeTasks } = useTaskStore();

  // Section 06: parseMultiFileOutput — extract fenced code blocks with file paths
  const parseMultiFileOutput = (responseText) => {
    const filePattern = /```(?:jsx?|tsx?|css|html)?:([\w./\-]+)\n([\s\S]*?)```/g;
    const parsedFiles = {};
    let match;
    while ((match = filePattern.exec(responseText)) !== null) {
      const filePath = match[1].startsWith('/') ? match[1] : `/${match[1]}`;
      parsedFiles[filePath] = { code: match[2] };
    }
    // Fallback: if no file markers, put everything in /App.js
    if (Object.keys(parsedFiles).length === 0) {
      const cleaned = responseText.replace(/```jsx?/g, '').replace(/```/g, '').trim();
      parsedFiles['/App.js'] = { code: cleaned };
    }
    return parsedFiles;
  };
  const [qualityGateResult, setQualityGateResult] = useState(null); // { passed, score, verdict } after build
  const [tokensPerStep, setTokensPerStep] = useState({ plan: 0, generate: 0 });
  const [showDeployModal, setShowDeployModal] = useState(false);
  const [projectLiveUrl, setProjectLiveUrl] = useState(null);
  const [deployTokensHint, setDeployTokensHint] = useState({ has_vercel: false, has_netlify: false });
  const [deployZipBusy, setDeployZipBusy] = useState(false);
  const [deployOneClickBusy, setDeployOneClickBusy] = useState(null);
  const [publishCustomDomain, setPublishCustomDomain] = useState('');
  const [publishRailwayUrl, setPublishRailwayUrl] = useState('');
  const [publishSaveBusy, setPublishSaveBusy] = useState(false);
  const [deployRailwayBusy, setDeployRailwayBusy] = useState(false);
  const [deployRailwaySteps, setDeployRailwaySteps] = useState(null);
  const [deployRailwayDashboard, setDeployRailwayDashboard] = useState(null);
  const [deployRailwayErr, setDeployRailwayErr] = useState(null);
  const [mobileView, setMobileView] = useState(false);
  const [showVibeInput, setShowVibeInput] = useState(false);
  const projectIdFromUrl = searchParams.get('projectId');
  const taskIdFromUrl = searchParams.get('taskId');
  const [projectBuildProgress, setProjectBuildProgress] = useState({ phase: 0, agent: '', progress: 0, status: '', tokens_used: 0 });

  const localMdDocs = useMemo(
    () =>
      Object.entries(files)
        .filter(([k]) => isWorkspaceDocPath(k))
        .map(([path, f]) => ({
          path: path.startsWith('/') ? path.slice(1) : path,
          content: f?.code || '',
          source: 'editor',
        })),
    [files],
  );

  const mergedDocFiles = useMemo(() => {
    const sortFn = (a, b) => docSortKey(a.path) - docSortKey(b.path) || String(a.path).localeCompare(String(b.path));
    const editor = localMdDocs.map((d) => ({ ...d, source: 'editor' })).sort(sortFn);
    if (!projectIdFromUrl) return editor;
    const serv = serverDocSnapshots.map((d) => ({ path: d.path, content: d.content || '', source: 'server' })).sort(sortFn);
    const sn = new Set(serv.map((d) => normalizeWorkspacePath(d.path)));
    const uniqEditor = editor.filter((d) => !sn.has(normalizeWorkspacePath(d.path)));
    return [...serv, ...uniqEditor].sort(sortFn);
  }, [projectIdFromUrl, serverDocSnapshots, localMdDocs]);

  const localDbEntries = useMemo(
    () =>
      Object.entries(files)
        .filter(([k]) => isWorkspaceDbPath(k))
        .map(([k, f]) => ({
          path: k.startsWith('/') ? k.slice(1) : k,
          displayKey: k.startsWith('/') ? k : `/${k}`,
          content: f?.code || '',
          source: 'editor',
        })),
    [files],
  );

  const dbPanelMerge = useMemo(() => {
    const serverNorm = new Set(serverDbSnapshots.map((s) => normalizeWorkspacePath(s.path)));
    const editorOnly = localDbEntries.filter((e) => !serverNorm.has(normalizeWorkspacePath(e.path)));
    const sqlBlob = [...serverDbSnapshots, ...editorOnly.map((e) => ({ content: e.content }))]
      .map((x) => x.content)
      .join('\n');
    return {
      editorOnly,
      inferredTables: [...new Set(extractSqlTableNames(sqlBlob))],
      hasRows: serverDbSnapshots.length > 0 || localDbEntries.length > 0,
    };
  }, [serverDbSnapshots, localDbEntries]);

  /** Guided: core workbench only. Pro: database, docs, analytics, agents, passes. */
  const workbenchTabs = useMemo(() => {
    const base = [
      { id: 'preview', label: 'Preview', icon: Eye },
      { id: 'code', label: 'Code', icon: FileCode },
      { id: 'console', label: 'Console', icon: Terminal },
      { id: 'dashboard', label: 'Dashboard', icon: Activity },
      { id: 'database', label: 'Database', icon: Database },
      { id: 'docs', label: 'Docs', icon: BookOpen },
      { id: 'analytics', label: 'Analytics', icon: BarChart3 },
      { id: 'agents', label: 'Agents', icon: Network },
      { id: 'passes', label: 'Passes', icon: Layers },
      { id: 'sandbox', label: 'Sandbox', icon: Globe2 },
      ...(projectIdFromUrl ? [{ id: 'history', label: 'History', icon: History }] : []),
    ];
    const proOnly = new Set(['database', 'docs', 'analytics', 'agents', 'passes', 'sandbox']);
    if (devMode) return base;
    return base.filter((t) => !proOnly.has(t.id));
  }, [projectIdFromUrl, devMode]);

  const filteredConsoleLogs = useMemo(() => {
    if (consoleFilter === 'all') return logs;
    return logs.filter((log) => {
      const t = log.type || 'info';
      const a = (log.agent || '').toLowerCase();
      if (consoleFilter === 'error') return t === 'error';
      if (consoleFilter === 'build') return a === 'build';
      if (consoleFilter === 'system') return a === 'system' || !log.agent;
      return true;
    });
  }, [logs, consoleFilter]);

  const fileInputRef = useRef(null);
  const folderInputRef = useRef(null);
  const zipInputRef = useRef(null);
  const chatInputRef = useRef(null);
  const chatEndRef = useRef(null);

  // Zone 3: resize textarea 48px–120px, collapse on send
  const resizeChatInput = useCallback(() => {
    const el = chatInputRef.current;
    if (!el) return;
    el.style.height = '48px';
    el.style.height = `${Math.min(Math.max(el.scrollHeight, 48), 120)}px`;
  }, []);
  useEffect(() => {
    if (!input) {
      const el = chatInputRef.current;
      if (el) el.style.height = '48px';
    } else resizeChatInput();
  }, [input, resizeChatInput]);
  const workspaceFilesLoadedForProject = useRef(null);
  const [workspacePullKey, setWorkspacePullKey] = useState(0);
  const reloadWorkspaceFromServer = useCallback(() => {
    workspaceFilesLoadedForProject.current = null;
    setWorkspacePullKey((k) => k + 1);
  }, []);
  const prevIsBuildingRef = useRef(false);

  useEffect(() => {
    axios.get(`${API}/build/phases`).then(r => setBuildPhases(r.data.phases || [])).catch(() => {});
  }, []);

  useEffect(() => {
    if (!API) return undefined;
    const ping = () => {
      axios.get(`${API}/health`, { timeout: 8000 }).then(() => setApiHealth('ok')).catch(() => setApiHealth('down'));
    };
    ping();
    const id = setInterval(ping, 25000);
    return () => clearInterval(id);
  }, [API]);

  useEffect(() => {
    if (!token || !API) {
      setJobsChip({ total: 0, active: 0 });
      return undefined;
    }
    const headers = { Authorization: `Bearer ${token}` };
    const run = () => {
      axios
        .get(`${API}/jobs`, { headers, timeout: 12000 })
        .then((r) => {
          const jobs = r.data?.jobs || [];
          const active = jobs.filter((j) => j.status === 'running' || j.status === 'queued').length;
          setJobsChip({ total: jobs.length, active });
        })
        .catch(() => {});
    };
    run();
    const id = setInterval(run, 12000);
    return () => clearInterval(id);
  }, [token, API]);

  // Initial terminal message so panel isn't empty
  useEffect(() => {
    addLog('Workspace ready. Use the chat to build or update your app. Build output will appear here.', 'info', 'system');
  }, []);

  useEffect(() => {
    const stateFiles = location.state?.initialFiles;
    if (stateFiles && typeof stateFiles === 'object' && Object.keys(stateFiles).length > 0) {
      setFiles(stateFiles);
    }
  }, [location.state]);

  // Item 17: Fetch build history when workspace is opened with a project
  useEffect(() => {
    if (!projectIdFromUrl || !token || !API) return;
    setBuildHistoryLoading(true);
    axios.get(`${API}/projects/${projectIdFromUrl}/build-history`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => setBuildHistoryList(r.data?.build_history || []))
      .catch(() => setBuildHistoryList([]))
      .finally(() => setBuildHistoryLoading(false));
  }, [projectIdFromUrl, token, API]);

  useEffect(() => {
    if (!projectIdFromUrl || !token || !API) {
      setProjectLiveUrl(null);
      setPublishCustomDomain('');
      setPublishRailwayUrl('');
      return;
    }
    axios
      .get(`${API}/projects/${projectIdFromUrl}`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => {
        const p = r.data?.project;
        setProjectLiveUrl(p?.live_url || null);
        setPublishCustomDomain(typeof p?.custom_domain === 'string' ? p.custom_domain : '');
        setPublishRailwayUrl(typeof p?.railway_project_url === 'string' ? p.railway_project_url : '');
      })
      .catch(() => {
        setProjectLiveUrl(null);
        setPublishCustomDomain('');
        setPublishRailwayUrl('');
      });
  }, [projectIdFromUrl, token, API]);

  useEffect(() => {
    if (prevIsBuildingRef.current && !isBuilding && projectIdFromUrl && token && API) {
      const headers = { Authorization: `Bearer ${token}` };
      axios
        .get(`${API}/projects/${projectIdFromUrl}`, { headers })
        .then((r) => {
          const p = r.data?.project;
          setProjectLiveUrl(p?.live_url || null);
          setPublishCustomDomain(typeof p?.custom_domain === 'string' ? p.custom_domain : '');
          setPublishRailwayUrl(typeof p?.railway_project_url === 'string' ? p.railway_project_url : '');
        })
        .catch(() => {});
      axios
        .get(`${API}/projects/${projectIdFromUrl}/build-history`, { headers })
        .then((r) => setBuildHistoryList(r.data?.build_history || []))
        .catch(() => {});
    }
    prevIsBuildingRef.current = isBuilding;
  }, [isBuilding, projectIdFromUrl, token, API]);

  useEffect(() => {
    if (!showDeployModal || !token || !API) return;
    axios
      .get(`${API}/users/me/deploy-tokens`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => setDeployTokensHint({ has_vercel: !!r.data?.has_vercel, has_netlify: !!r.data?.has_netlify }))
      .catch(() => setDeployTokensHint({ has_vercel: false, has_netlify: false }));
  }, [showDeployModal, token, API]);

  useEffect(() => {
    if (!showDeployModal) {
      setDeployRailwaySteps(null);
      setDeployRailwayDashboard(null);
      setDeployRailwayErr(null);
    }
  }, [showDeployModal]);

  // Orchestration timeline: snapshot + SSE (access_token query; EventSource has no Bearer). Poll fallback if SSE fails.
  useEffect(() => {
    if (!projectIdFromUrl || !token || !API) {
      setBuildTimelineEvents([]);
      setBuildEventsErr(null);
      return undefined;
    }
    let cancelled = false;
    let es = null;
    let pollId = null;

    const clearPoll = () => {
      if (pollId != null) {
        clearInterval(pollId);
        pollId = null;
      }
    };

    const fetchSnapshot = () => {
      axios
        .get(`${API}/projects/${projectIdFromUrl}/events/snapshot`, {
          headers: { Authorization: `Bearer ${token}` },
          timeout: 12000,
        })
        .then((r) => {
          if (cancelled) return;
          const list = r.data?.events;
          setBuildTimelineEvents(Array.isArray(list) ? list : []);
          setBuildEventsErr(null);
        })
        .catch((e) => {
          if (cancelled) return;
          const st = e?.response?.status;
          setBuildEventsErr(st === 404 ? 'Project not found or no access.' : 'Could not load build events.');
        });
    };

    const startPolling = (ms) => {
      clearPoll();
      fetchSnapshot();
      pollId = setInterval(fetchSnapshot, ms);
    };

    axios
      .get(`${API}/projects/${projectIdFromUrl}/events/snapshot`, {
        headers: { Authorization: `Bearer ${token}` },
        timeout: 12000,
      })
      .then((r) => {
        if (cancelled) return;
        const list = Array.isArray(r.data?.events) ? r.data.events : [];
        setBuildTimelineEvents(list);
        setBuildEventsErr(null);
        const maxId = list.length ? Math.max(...list.map((e) => Number(e?.id) || 0)) : -1;
        const lastId = maxId + 1;
        const base = API.replace(/\/$/, '');
        const url = `${base}/projects/${encodeURIComponent(projectIdFromUrl)}/events?last_id=${lastId}&access_token=${encodeURIComponent(token)}`;
        try {
          es = new EventSource(url);
          es.onmessage = (event) => {
            if (cancelled) return;
            try {
              const ev = JSON.parse(event.data);
              if (ev?.type === 'stream_end') {
                es?.close();
                return;
              }
              if (ev == null || typeof ev.id !== 'number') return;
              setBuildTimelineEvents((prev) => {
                if (prev.some((x) => x.id === ev.id)) return prev;
                return [...prev, ev];
              });
            } catch (_) {
              /* ignore parse */
            }
          };
          es.onerror = () => {
            if (cancelled) return;
            try {
              es?.close();
            } catch (_) {
              /* ignore */
            }
            es = null;
            startPolling(isBuilding ? 3000 : 8000);
          };
        } catch (_) {
          startPolling(isBuilding ? 2000 : 5000);
        }
      })
      .catch((e) => {
        if (cancelled) return;
        const st = e?.response?.status;
        setBuildEventsErr(st === 404 ? 'Project not found or no access.' : 'Could not load build events.');
        startPolling(isBuilding ? 2000 : 5000);
      });

    return () => {
      cancelled = true;
      clearPoll();
      try {
        es?.close();
      } catch (_) {
        /* ignore */
      }
    };
  }, [projectIdFromUrl, token, API, isBuilding]);

  useEffect(() => {
    setServerDbSnapshots([]);
    setServerDbErr(null);
    setServerDocSnapshots([]);
    setServerDocsErr(null);
    setDocsSelectedPath(null);
    setAnalyticsData(null);
    setAnalyticsErr(null);
  }, [projectIdFromUrl]);

  useEffect(() => {
    if (activePanel !== 'database' || !projectIdFromUrl || !token || !API) return undefined;
    let cancelled = false;
    setServerDbLoading(true);
    setServerDbErr(null);
    const headers = { Authorization: `Bearer ${token}` };
    axios
      .get(`${API}/projects/${projectIdFromUrl}/workspace/files`, { headers, timeout: 15000 })
      .then(async (r) => {
        const paths = (r.data?.files || []).filter(isWorkspaceDbPath).slice(0, 30);
        const chunks = await Promise.all(
          paths.map((path) =>
            axios
              .get(`${API}/projects/${projectIdFromUrl}/workspace/file`, { params: { path }, headers, timeout: 12000 })
              .then((res) => ({ path: res.data.path, content: res.data.content || '', source: 'server' }))
              .catch(() => null),
          ),
        );
        if (!cancelled) setServerDbSnapshots(chunks.filter(Boolean));
      })
      .catch((e) => {
        if (!cancelled) setServerDbErr(typeof e?.response?.data?.detail === 'string' ? e.response.data.detail : e?.message || 'Load failed');
      })
      .finally(() => {
        if (!cancelled) setServerDbLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activePanel, projectIdFromUrl, token, API]);

  useEffect(() => {
    if (activePanel !== 'docs' || !projectIdFromUrl || !token || !API) return undefined;
    let cancelled = false;
    setServerDocsLoading(true);
    setServerDocsErr(null);
    const headers = { Authorization: `Bearer ${token}` };
    axios
      .get(`${API}/projects/${projectIdFromUrl}/workspace/files`, { headers, timeout: 15000 })
      .then(async (r) => {
        const paths = (r.data?.files || []).filter(isWorkspaceDocPath).slice(0, 35);
        const sorted = [...paths].sort((a, b) => docSortKey(a) - docSortKey(b) || a.localeCompare(b));
        const chunks = await Promise.all(
          sorted.map((path) =>
            axios
              .get(`${API}/projects/${projectIdFromUrl}/workspace/file`, { params: { path }, headers, timeout: 12000 })
              .then((res) => ({ path: res.data.path, content: res.data.content || '', source: 'server' }))
              .catch(() => null),
          ),
        );
        if (!cancelled) setServerDocSnapshots(chunks.filter(Boolean));
      })
      .catch((e) => {
        if (!cancelled) setServerDocsErr(typeof e?.response?.data?.detail === 'string' ? e.response.data.detail : e?.message || 'Load failed');
      })
      .finally(() => {
        if (!cancelled) setServerDocsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activePanel, projectIdFromUrl, token, API]);

  useEffect(() => {
    if (activePanel !== 'analytics' || !token || !API) return undefined;
    let cancelled = false;
    setAnalyticsLoading(true);
    setAnalyticsErr(null);
    const headers = { Authorization: `Bearer ${token}` };
    Promise.all([
      axios.get(`${API}/jobs`, { headers, timeout: 12000 }),
      axios.get(`${API}/tokens/usage`, { headers, timeout: 12000 }),
    ])
      .then(([jobsRes, tokRes]) => {
        if (!cancelled) {
          setAnalyticsData({
            jobs: jobsRes.data?.jobs || [],
            tokens: tokRes.data || null,
          });
        }
      })
      .catch((e) => {
        if (!cancelled) setAnalyticsErr(e?.message || 'Failed to load analytics');
      })
      .finally(() => {
        if (!cancelled) setAnalyticsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activePanel, token, API]);

  useEffect(() => {
    if (activePanel !== 'docs' || mergedDocFiles.length === 0) return;
    setDocsSelectedPath((prev) => {
      if (!prev) return mergedDocFiles[0].path;
      const np = normalizeWorkspacePath(prev);
      const hit = mergedDocFiles.find((d) => normalizeWorkspacePath(d.path) === np);
      return hit ? hit.path : mergedDocFiles[0].path;
    });
  }, [activePanel, mergedDocFiles]);

  useEffect(() => {
    if (devMode) return;
    const proOnly = new Set(['database', 'docs', 'analytics', 'agents', 'passes', 'sandbox']);
    if (proOnly.has(activePanel)) setActivePanel('preview');
  }, [devMode, activePanel]);

  useEffect(() => {
    const agentsPoll = activePanel === 'agents' || isBuilding;
    if (!agentsPoll || !projectIdFromUrl || !token || !API) return undefined;
    let cancelled = false;
    const headers = { Authorization: `Bearer ${token}` };
    const run = () => {
      axios
        .get(`${API}/agents/status/${projectIdFromUrl}`, { headers, timeout: 12000 })
        .then((r) => {
          if (!cancelled) setAgentApiStatuses(Array.isArray(r.data?.statuses) ? r.data.statuses : []);
        })
        .catch(() => {
          if (!cancelled) setAgentApiStatuses([]);
        });
    };
    run();
    const id = setInterval(run, 4000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [activePanel, isBuilding, projectIdFromUrl, token, API]);

  useEffect(() => {
    if (activePanel !== 'sandbox' || !projectIdFromUrl || !token || !API) return undefined;
    let cancelled = false;
    setProjectSandboxLoading(true);
    setProjectSandboxErr(null);
    const headers = { Authorization: `Bearer ${token}` };
    const run = () => {
      axios
        .get(`${API}/projects/${projectIdFromUrl}/logs`, { headers, timeout: 15000 })
        .then((r) => {
          if (!cancelled) setProjectSandboxLogs(Array.isArray(r.data?.logs) ? r.data.logs : []);
        })
        .catch((e) => {
          if (!cancelled) {
            setProjectSandboxLogs([]);
            setProjectSandboxErr(typeof e?.response?.data?.detail === 'string' ? e.response.data.detail : e?.message || 'Failed to load logs');
          }
        })
        .finally(() => {
          if (!cancelled) setProjectSandboxLoading(false);
        });
    };
    run();
    const id = setInterval(run, 8000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [activePanel, projectIdFromUrl, token, API]);

  // Reconnect recovery — check for in-progress builds when workspace loads
  useEffect(() => {
    if (!token || !API) return;
    axios.get(`${API}/jobs`, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => {
        const jobs = res.data?.jobs || [];
        const running = jobs.find(j => j.status === 'running' || j.status === 'queued');
        if (running) {
          setIsBuilding(true);
          setBuildProgress(running.progress || 0);
          addLog(`Reconnected to in-progress build: ${running.message || running.name}`, 'info', 'build');
          const sessionId = running.payload?.session_id;
          pollJobStatus(running.id, sessionId);
        }
      })
      .catch(() => {});
  }, [token, API]);

  // Load task files when opening with taskId (returning users - Q122 FIX)
  useEffect(() => {
    if (!taskIdFromUrl || !token || !API) return;
    axios.get(`${API}/tasks/${taskIdFromUrl}`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => {
        const task = r.data?.task || r.data;
        const taskFiles = task?.files || task?.doc?.files;
        if (!taskFiles || Object.keys(taskFiles).length === 0) return;
        // Convert stored format to Sandpack format
        const loaded = Object.entries(taskFiles).reduce((acc, [path, content]) => {
          const key = path.startsWith('/') ? path : `/${path}`;
          acc[key] = { code: typeof content === 'string' ? content : (content?.code || '') };
          return acc;
        }, {});
        if (Object.keys(loaded).length > 0) {
          setFiles(loaded);
          setActiveFile(Object.keys(loaded).sort().find(k => k.includes('App')) || Object.keys(loaded).sort()[0]);
          // Trigger Sandpack remount so preview loads — THE CRITICAL FIX for Q122
          setTimeout(() => {
            const vId = `task_${taskIdFromUrl}_${Date.now()}`;
            setCurrentVersion(vId);
            setFilesReadyKey(`fk_${vId}`);
            setActivePanel('preview');
          }, 500);
        }
      })
      .catch(() => {});
  }, [taskIdFromUrl, token, API]);

  // Load imported project files from workspace when opening with projectId (e.g. after Import)
  useEffect(() => {
    if (!projectIdFromUrl || !token || !API || workspaceFilesLoadedForProject.current === projectIdFromUrl) return;
    const headers = { Authorization: `Bearer ${token}` };
    axios.get(`${API}/projects/${projectIdFromUrl}/workspace/files`, { headers })
      .then((r) => {
        const list = r.data?.files || [];
        if (list.length === 0) return;
        workspaceFilesLoadedForProject.current = projectIdFromUrl;
        return Promise.all(
          list.map((path) =>
            axios.get(`${API}/projects/${projectIdFromUrl}/workspace/file`, { params: { path }, headers })
              .then((f) => ({ path: f.data.path, content: f.data.content }))
              .catch(() => null)
          )
        ).then((results) => {
          const loaded = results.filter(Boolean).reduce((acc, { path, content }) => {
            const key = path.startsWith('/') ? path : `/${path}`;
            acc[key] = { code: content };
            return acc;
          }, {});
          if (Object.keys(loaded).length > 0) {
            setFiles(loaded);
            setActiveFile((current) => (current && loaded[current] ? current : Object.keys(loaded).sort()[0]));
            // FIX Q122: trigger Sandpack remount after workspace reload so preview works on return
            setTimeout(() => {
              const vId = `reload_${projectIdFromUrl}_${Date.now()}`;
              setCurrentVersion(vId);
              setFilesReadyKey(`fk_${vId}`);
              setActivePanel('preview');
            }, 500);
          }
        });
      })
      .catch(() => {});
  }, [projectIdFromUrl, token, API, workspacePullKey]);

  useEffect(() => {
    if (token) {
      axios.get(`${API}/agents/activity`, { headers: { Authorization: `Bearer ${token}` } })
        .then(r => setAgentsActivity(r.data.activities || []))
        .catch(() => {});
    }
  }, [token, messages.length]);

  // Wire real build progress when opened with projectId (from AgentMonitor "Open in Workspace")
  // Phase 3: Auto-reconnect on disconnect with exponential backoff
  useEffect(() => {
    if (!projectIdFromUrl || !API) return;
    const wsBase = (API || '').replace(/^http/, 'ws').replace(/\/api\/?$/, '');
    const wsUrl = `${wsBase}/ws/projects/${projectIdFromUrl}/progress`;
    let ws;
    let reconnectTimeout;
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 10;
    const baseDelay = 1000;

    const connect = () => {
      try {
        ws = new WebSocket(wsUrl);
        ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setProjectBuildProgress({
            phase: data.phase ?? 0,
            agent: data.agent ?? '',
            progress: data.progress ?? 0,
            status: data.status ?? '',
            tokens_used: data.tokens_used ?? 0
          });
          // AUTO-WIRE: Update agent activity for InlineAgentMonitor
          if (data.agent && data.status) {
            setAgentsActivity(prev => {
              const existing = prev.findIndex(a => a.name === data.agent);
              const entry = { name: data.agent, status: data.status, phase: data.phase, progress: data.progress, updated: Date.now() };
              if (existing >= 0) {
                const next = [...prev];
                next[existing] = entry;
                return next;
              }
              return [...prev, entry];
            });
          }
          // AUTO-WIRE: When build completes, load deploy_files into Sandpack preview
          if (data.type === 'build_completed' && data.status === 'completed') {
            const deployFiles = data.deploy_files;
            if (deployFiles && Object.keys(deployFiles).length > 0) {
              const sandpackFiles = {};
              for (const [filePath, content] of Object.entries(deployFiles)) {
                const key = filePath.startsWith('/') ? filePath : `/${filePath}`;
                sandpackFiles[key] = { code: content };
              }
              setFiles(prev => ({ ...prev, ...sandpackFiles }));
              const mainFile = sandpackFiles['/src/App.jsx'] || sandpackFiles['/App.js'] || sandpackFiles['/App.jsx'];
              if (mainFile) {
                setActiveFile(sandpackFiles['/src/App.jsx'] ? '/src/App.jsx' : sandpackFiles['/App.js'] ? '/App.js' : '/App.jsx');
              }
              setVersions(v => [{ id: `v_${Date.now()}`, prompt: 'Orchestration build', files: { ...sandpackFiles }, time: new Date().toLocaleTimeString() }, ...v]);
              setCurrentVersion(`v_${Date.now()}`);
              addLog('Build completed! Files loaded into preview.', 'success', 'deploy');
              setActivePanel('preview'); // Auto-switch to preview
              setBuildProgress(100);
              setIsBuilding(false);
              if (refreshUser) refreshUser(); // refresh credit balance
            } else {
              // Fallback: fetch deploy_files from API
              const headers = token ? { Authorization: `Bearer ${token}` } : {};
              axios.get(`${API}/projects/${projectIdFromUrl}/deploy/files`, { headers })
                .then(r => {
                  const files = r.data?.files || {};
                  if (Object.keys(files).length > 0) {
                    const sandpackFiles = {};
                    for (const [filePath, content] of Object.entries(files)) {
                      const key = filePath.startsWith('/') ? filePath : `/${filePath}`;
                      sandpackFiles[key] = { code: content };
                    }
                    setFiles(prev => ({ ...prev, ...sandpackFiles }));
                    setVersions(v => [{ id: `v_${Date.now()}`, prompt: 'Orchestration build', files: { ...sandpackFiles }, time: new Date().toLocaleTimeString() }, ...v]);
                    setCurrentVersion(`v_${Date.now()}`);
                    setActivePanel('preview');
                    addLog('Build completed! Files loaded from server.', 'success', 'deploy');
                  }
                  if (r.data?.quality_score) setQualityGateResult({ score: r.data.quality_score });
                })
                .catch(() => {});
              setBuildProgress(100);
              setIsBuilding(false);
            }
          }
        } catch (_) {}
      };
        ws.onclose = () => {
          if (reconnectAttempts < maxReconnectAttempts) {
            const delay = Math.min(baseDelay * Math.pow(2, reconnectAttempts), 30000);
            reconnectAttempts++;
            reconnectTimeout = setTimeout(connect, delay);
          }
        };
        ws.onerror = () => { try { ws?.close(); } catch (_) {} };
        reconnectAttempts = 0;
      } catch (_) {}
    };
    connect();
    return () => {
      clearTimeout(reconnectTimeout);
      try { if (ws) ws.close(); } catch (_) {}
    };
  }, [projectIdFromUrl, API]);

  // Wire GET /ai/chat/history so session history can be loaded (e.g. on "New Agent" we keep sessionId; history loads for current session)
  useEffect(() => {
    if (!sessionId) return;
    axios.get(`${API}/ai/chat/history/${encodeURIComponent(sessionId)}`)
      .then(r => {
        const list = r.data?.history || [];
        if (list.length > 0 && messages.length === 0) {
          const asMessages = list.map(h => ({ role: h.role || 'assistant', content: h.message || h.content || '' }));
          setMessages(asMessages);
        }
      })
      .catch(() => {});
  }, [sessionId]);

  useEffect(() => {
    const onKey = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setCommandPaletteOpen(prev => !prev);
      }
      if ((e.ctrlKey || e.metaKey) && e.altKey && e.key === 'e') {
        e.preventDefault();
        setChatMaximized(prev => !prev);
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'j') {
        e.preventDefault();
        setActivePanel('console');
        setRightSidebarOpen(true);
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'p') {
        e.preventDefault();
        setFileSearchOpen(prev => !prev);
      }
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'B') {
        e.preventDefault();
        window.open('/app/workspace', '_blank');
      }
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'L') {
        e.preventDefault();
        navigate('/app', { state: { newAgent: Date.now() } });
      }
      if (e.key === 'Escape') {
        setCommandPaletteOpen(false);
        setFileSearchOpen(false);
        setMenuAnchor(null);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [navigate]);

  // Restore existing task workspace when opening by taskId — load files + messages.
  // Pre-fill input with task.prompt when task has no build yet so user can click Submit/Go to run.
  const taskRestoredRef = useRef(null);
  useEffect(() => {
    if (!taskIdFromUrl || !storeTasks?.length) return;
    const task = storeTasks.find(t => t.id === taskIdFromUrl);
    if (!task) return;
    if (taskRestoredRef.current === taskIdFromUrl) return;
    taskRestoredRef.current = taskIdFromUrl;
    if (task.files && typeof task.files === 'object' && Object.keys(task.files).length > 0) {
      setFiles(task.files);
      const firstKey = Object.keys(task.files).sort()[0];
      if (firstKey) setActiveFile(firstKey);
    }
    if (task.messages && Array.isArray(task.messages) && task.messages.length > 0) {
      setMessages(task.messages);
    } else if (task.prompt && (!task.files || Object.keys(task.files || {}).length === 0)) {
      setInput(task.prompt);
    }
    if (task.versions?.length) {
      setVersions(task.versions);
      setCurrentVersion(task.versions[0]?.id);
    }
  }, [taskIdFromUrl, storeTasks]);

  // Pending prompt from landing (user said "build me X" then signed up) — restore and start building
  const PENDING_PROMPT_KEY = 'crucibai_pending_prompt';
  const pendingPromptAppliedRef = useRef(false);
  useEffect(() => {
    if (pendingPromptAppliedRef.current) return;
    const hasStatePrompt = location.state?.initialPrompt || searchParams.get('prompt');
    if (hasStatePrompt) return; // URL/state already has a prompt; let the auto-start effect handle it
    const fromStorage = typeof sessionStorage !== 'undefined' ? sessionStorage.getItem(PENDING_PROMPT_KEY) : null;
    if (!fromStorage?.trim()) return;
    pendingPromptAppliedRef.current = true;
    sessionStorage.removeItem(PENDING_PROMPT_KEY);
    sessionStorage.removeItem(PENDING_PROMPT_KEY + '_hasFiles');
    setInput(fromStorage);
    handleBuild(fromStorage);
  }, [location.state, searchParams]);

  // Auto-start build when user explicitly clicks "Start Building" / "Go" (Dashboard or Landing with auth)
  const autoStartedRef = useRef(null);
  useEffect(() => {
    const statePrompt = location.state?.initialPrompt || searchParams.get('prompt');
    const stateAutoStart = location.state?.autoStart || searchParams.get('autoStart') === '1';
    const initialFiles = location.state?.initialAttachedFiles;
    if (!stateAutoStart || !statePrompt) return;
    if (autoStartedRef.current === `${location.key}-${taskIdFromUrl}`) return;
    autoStartedRef.current = `${location.key}-${taskIdFromUrl}`;
    if (initialFiles?.length) setAttachedFiles(initialFiles);
    setInput(statePrompt);
    handleBuild(statePrompt, initialFiles || undefined);
  }, [location.key, location.state, taskIdFromUrl]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ── Async job polling (Q121 fix — build survives browser close) ──────────
  const pollJobStatus = async (jobId, sessionId) => {
    const maxPolls = 180;
    let polls = 0;
    const interval = setInterval(async () => {
      try {
        polls++;
        if (polls > maxPolls) { clearInterval(interval); return; }
        const res = await axios.get(`${API}/jobs/${jobId}`,
          token ? { headers: { Authorization: `Bearer ${token}` } } : {});
        const job = res.data;
        if (job.progress) setBuildProgress(job.progress);
        if (job.message) addLog(job.message, 'info', 'build');
        if (job.status === 'complete') {
          clearInterval(interval);
          if (sessionId && token) {
            try {
              const taskRes = await axios.get(`${API}/tasks/${sessionId}`,
                { headers: { Authorization: `Bearer ${token}` } });
              const taskFiles = taskRes.data?.task?.files || taskRes.data?.files || taskRes.data?.doc?.files;
              if (taskFiles && Object.keys(taskFiles).length > 0) {
                const fileEntries = Object.fromEntries(
                  Object.entries(taskFiles).map(([k, v]) => [k, { code: typeof v === 'string' ? v : v?.code || '' }])
                );
                setFiles(prev => ({ ...prev, ...fileEntries }));
                setTimeout(() => {
                  const vId = `async_${Date.now()}`;
                  setCurrentVersion(vId); setFilesReadyKey(`fk_${vId}`); setActivePanel('preview');
                }, 500);
                addLog(`Build complete: ${Object.keys(fileEntries).length} files`, 'success', 'deploy');
                if (refreshUser) refreshUser();
                const newUrl = new URL(window.location.href);
                newUrl.searchParams.set('taskId', sessionId);
                window.history.replaceState({}, '', newUrl.toString());
              }
            } catch (_) {}
          }
          setIsBuilding(false); setBuildProgress(100);
        }
        if (job.status === 'failed') {
          clearInterval(interval);
          addLog(`Build failed: ${job.error}`, 'error', 'deploy');
          setIsBuilding(false);
        }
      } catch (_) { clearInterval(interval); setIsBuilding(false); }
    }, 1000);
  };

  const addLog = (message, type = 'info', agent = null) => {
    const now = new Date();
    const time = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
    setLogs(prev => [...prev, { message, type, time, agent }]);
  };

  // ── Voice: Web Speech API (Chrome/Edge/Safari) or fallback to record + backend /voice/transcribe ──
  const speechRecognitionRef = useRef(null);
  const voiceChunksRef = useRef([]);

  const startRecording = async () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      try {
        const recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';
        recognition.maxAlternatives = 1;
        recognition.onstart = () => { setIsRecording(true); addLog('Listening...', 'info', 'voice'); };
        recognition.onresult = (e) => {
          const transcript = e.results[0][0].transcript.trim();
          setInput(prev => (prev ? prev + ' ' + transcript : transcript));
          setIsRecording(false);
          addLog(`Voice: "${transcript}"`, 'success', 'voice');
        };
        recognition.onerror = (e) => {
          setIsRecording(false);
          const msg = e.error === 'not-allowed'
            ? 'Microphone access denied. Allow mic in your browser, then try again.'
            : e.error === 'no-speech'
            ? 'No speech detected. Try again.'
            : `Voice error: ${e.error}`;
          addLog(msg, 'error', 'voice');
        };
        recognition.onend = () => { setIsRecording(false); speechRecognitionRef.current = null; };
        speechRecognitionRef.current = recognition;
        recognition.start();
        return;
      } catch (err) {
        addLog(`Voice failed: ${err.message}`, 'error', 'voice');
      }
    }
    // Fallback: record with MediaRecorder, then send to backend /voice/transcribe (works in all browsers)
    if (!navigator.mediaDevices?.getUserMedia) {
      addLog('Microphone not supported in this browser.', 'error', 'voice');
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      const mimeType = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'].find(m => MediaRecorder.isTypeSupported(m)) || 'audio/webm';
      const recorder = new MediaRecorder(stream, { mimeType });
      voiceChunksRef.current = [];
      recorder.ondataavailable = (e) => { if (e.data.size > 0) voiceChunksRef.current.push(e.data); };
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        setAudioStream(null);
        mediaRecorderRef.current = null;
        setIsRecording(false);
        const blob = new Blob(voiceChunksRef.current, { type: recorder.mimeType || 'audio/webm' });
        if (blob.size < 100) { addLog('Recording too short. Speak longer.', 'error', 'voice'); return; }
        setIsTranscribing(true);
        addLog('Transcribing...', 'info', 'voice');
        try {
          const formData = new FormData();
          formData.append('audio', blob, 'recording.webm');
          const headers = token ? { Authorization: `Bearer ${token}` } : {};
          const res = await axios.post(`${API}/voice/transcribe`, formData, { headers, timeout: 60000 });
          const text = (res.data?.text || '').trim();
          if (text) {
            setInput(prev => (prev ? prev + ' ' + text : text));
            addLog(`Voice: "${text.slice(0, 60)}${text.length > 60 ? '...' : ''}"`, 'success', 'voice');
          } else addLog('No text from transcription.', 'error', 'voice');
        } catch (err) {
          const msg = err?.response?.status === 503
            ? 'Voice needs OPENAI_API_KEY on the server. Add it in Railway or .env.'
            : err?.code === 'ERR_NETWORK' || err?.response?.status >= 500
            ? 'Backend not available. Start the CrucibAI backend for voice transcription.'
            : (err?.response?.data?.detail || err?.message) || 'Transcription failed.';
          addLog(msg, 'error', 'voice');
        } finally {
          setIsTranscribing(false);
        }
      };
      recorder.start(500);
      mediaRecorderRef.current = { recorder, stream };
      setAudioStream(stream);
      setIsRecording(true);
      addLog('Recording... (stop to transcribe)', 'info', 'voice');
    } catch (err) {
      const msg = err?.name === 'NotAllowedError'
        ? 'Microphone access denied. Allow mic in your browser settings and refresh.'
        : err?.message || 'Could not start recording.';
      addLog(msg, 'error', 'voice');
    }
  };

  const stopRecording = () => {
    if (speechRecognitionRef.current) {
      speechRecognitionRef.current.stop();
      speechRecognitionRef.current = null;
    }
    const ref = mediaRecorderRef.current;
    if (ref?.recorder?.state === 'recording') ref.recorder.stop();
    else if (ref?.stream) ref.stream.getTracks().forEach(t => t.stop());
    if (ref && !ref.recorder?.state || ref?.recorder?.state === 'inactive') {
      mediaRecorderRef.current = null;
      setAudioStream(null);
    }
    setIsRecording(false);
  };

  const confirmRecording = () => {
    stopRecording();
  };

  const transcribeAudio = async () => {
    // Used for attached audio files; keep for compatibility
  };

  const handleFileSelect = async (e) => {
    const selectedFiles = Array.from(e.target.files || []);
    for (const file of selectedFiles) {
      const isZip = file.type === 'application/zip' || file.name.toLowerCase().endsWith('.zip');
      if (isZip) {
        try {
          const zip = await JSZip.loadAsync(file);
          const CODE_EXTS = /\.(jsx?|tsx?|css|html|json|py|c|cpp|h|hpp|md|txt|env\.example|gitignore)$/i;
          const newFiles = {};
          const entries = Object.keys(zip.files).filter((name) => !zip.files[name].dir && CODE_EXTS.test(name));
          for (const name of entries) {
            const entry = zip.files[name];
            const content = await entry.async('string');
            const path = name.startsWith('/') ? name : `/${name}`;
            newFiles[path] = { code: content };
          }
          if (Object.keys(newFiles).length > 0) {
            setFiles(prev => ({ ...prev, ...newFiles }));
            const first = Object.keys(newFiles).sort()[0];
            if (first) setActiveFile(first);
            addLog(`Loaded ${Object.keys(newFiles).length} files from ${file.name}`, 'success', 'files');
          } else {
            addLog('No code files in ZIP', 'warning', 'files');
          }
        } catch (err) {
          addLog(`ZIP error: ${err.message || 'Failed to read'}`, 'error', 'files');
        }
        continue;
      }
      const valid =
        file.type.startsWith('image/') ||
        file.type === 'application/pdf' ||
        file.type.startsWith('text/') ||
        file.type.startsWith('audio/') ||
        /\.(js|jsx|ts|tsx|css|html|json|py|md)$/i.test(file.name);
      if (!valid) continue;
      const reader = new FileReader();
      reader.onload = (ev) => {
        setAttachedFiles(prev => [...prev, {
          name: file.name,
          type: file.type,
          data: ev.target.result,
          size: file.size
        }]);
        addLog(`Attached: ${file.name}`, 'info', 'files');
      };
      if (file.type.startsWith('image/') || file.type === 'application/pdf' || file.type.startsWith('audio/')) {
        reader.readAsDataURL(file);
      } else {
        reader.readAsText(file);
      }
    }
    e.target.value = '';
  };

  const removeFile = (index) => {
    setAttachedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleBuild = async (promptOverride = null, filesOverride = null) => {
    let prompt = (promptOverride ?? input).trim();
    let filesToUse = filesOverride && filesOverride.length > 0 ? filesOverride : [...attachedFiles];
    // Transcribe attached audio and append to prompt (voice notes)
    const audioAttachments = filesToUse.filter(f => f.type?.startsWith?.('audio/'));
    if (audioAttachments.length > 0) {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      for (const att of audioAttachments) {
        try {
          const blob = await (await fetch(att.data)).blob();
          const formData = new FormData();
          formData.append('audio', blob, att.name || 'audio.webm');
          const res = await axios.post(`${API}/voice/transcribe`, formData, { headers, timeout: 30000 });
          const text = res.data?.text?.trim();
          if (text) {
            prompt = (prompt ? prompt + ' ' : '') + text;
            addLog(`Voice note: "${text.slice(0, 60)}..."`, 'info', 'voice');
          }
        } catch (_) {}
      }
      filesToUse = filesToUse.filter(f => !f.type?.startsWith?.('audio/'));
    }
    const hasImageOnly = filesToUse.length >= 1 && filesToUse.every(f => f.type?.startsWith?.('image/'));
    const useImageToCode = hasImageOnly && (!prompt || /screenshot|image|convert|turn into code|build from/i.test(prompt));

    if ((!prompt && !useImageToCode) || isBuilding) return;

    setInput('');
    setNextSuggestions([]);
    setIsBuilding(true);
    setBuildProgress(0);
    setLastError(null);
    setQualityGateResult(null);
    setTokensPerStep({ plan: 0, generate: 0 });
    // Auto-open right panel and switch to Preview per Section 06
    setRightSidebarOpen(true);
    setActivePanel('preview');
    if (!filesOverride?.length) setAttachedFiles([]);

    const userMessage = { role: 'user', content: useImageToCode ? 'Convert image to code' : prompt, attachments: filesToUse.length ? [...filesToUse] : undefined };
    setMessages(prev => [...prev, userMessage]);
    const imagesToSend = [...filesToUse];

    const promptIsBig = /build\s+(me\s+)?(a\s+)?(bank|software|app|platform|dashboard|application|system|tool|website)/i.test(prompt);
    const isBigBuild = !useImageToCode && buildMode !== 'quick' && (buildMode === 'plan' || buildMode === 'agent' || buildMode === 'thinking' || buildMode === 'swarm') && (promptIsBig || prompt.length > 80);
    const initialAssistantContent = useImageToCode ? 'Converting image to code...' : (isBigBuild ? 'Planning...' : 'Building...');
    setMessages(prev => [...prev, { role: 'assistant', content: initialAssistantContent, isBuilding: true }]);

    addLog(useImageToCode ? 'Screenshot to code...' : isBigBuild ? 'Creating plan...' : 'Starting build process...', 'info', 'planner');

    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};

      let planSuggestions = [];
      if (isBigBuild) {
        try {
          const useSwarm = buildMode === 'swarm' && !!token;
          const p = (prompt || '').toLowerCase();
          const buildKind = /mobile|react native|flutter|ios app|android app|build me a mobile/i.test(p) ? 'mobile'
            : /build me an agent|automation|cron|webhook agent|build agent/i.test(p) ? 'ai_agent'
            : /landing page|one-page|marketing page/i.test(p) ? 'landing'
            : /website|build me a web/i.test(p) ? 'fullstack'
            : /saas|subscription|stripe|billing/i.test(p) ? 'saas'
            : /slack bot|discord bot|telegram bot|chatbot/i.test(p) ? 'bot'
            : /game|2d game|3d game|browser game/i.test(p) ? 'game'
            : /trading|stock|crypto|forex|order book/i.test(p) ? 'trading'
            : 'fullstack';
          const planRes = await axios.post(`${API}/build/plan`, { prompt, swarm: useSwarm, build_kind: buildKind }, { headers, timeout: 45000 });
          const planText = (planRes.data.plan_text || '').trim();
          planSuggestions = planRes.data.suggestions || [];
          const planTokens = planRes.data.plan_tokens ?? planRes.data.tokens_estimate ?? 0;
          setTokensPerStep(prev => ({ ...prev, plan: planTokens }));
          setMessages(prev => {
            const next = [...prev];
            const lastIdx = next.length - 1;
            if (lastIdx >= 0 && next[lastIdx].role === 'assistant' && next[lastIdx].isBuilding) {
              next[lastIdx] = { role: 'assistant', content: planText || 'Plan ready.', planSuggestions };
            }
            return next;
          });
          addLog('Plan ready. Starting build...', 'info', 'planner');
          setMessages(prev => [...prev, { role: 'assistant', content: 'Building...', isBuilding: true }]);
        } catch (planErr) {
          const is404 = planErr.response?.status === 404 || planErr.response?.status === 405;
          addLog(is404 ? 'Plan endpoint not available, building without plan.' : `Plan failed: ${planErr.message}, building directly`, 'info', 'planner');
          setMessages(prev => prev.map((msg, i) => i === prev.length - 1 ? { ...msg, content: 'Building...' } : msg));
        }
      }

      if (useImageToCode && imagesToSend[0]) {
        const img = imagesToSend[0];
        const blob = await (await fetch(img.data)).blob();
        const formData = new FormData();
        formData.append('file', blob, img.name || 'screenshot.png');
        if (prompt) formData.append('prompt', prompt);
        const res = await axios.post(`${API}/ai/image-to-code`, formData, { headers, timeout: 60000 });
        let code = (res.data.code || '').trim();
        code = code.replace(/```jsx?/g, '').replace(/```/g, '').trim();
        setBuildProgress(100);
        addLog('Image-to-code completed', 'success', 'deploy');
        const newFiles = { ...files, '/App.js': { code } };
        setFiles(newFiles);
        setVersions(prev => [{ id: `v_${Date.now()}`, prompt: 'Image to code', files: newFiles, time: new Date().toLocaleTimeString() }, ...prev]);
        setCurrentVersion(`v_${Date.now()}`);
        const doneMsg = { role: 'assistant', content: 'Done! Your app is ready.', hasCode: true };
        setMessages(prev => prev.map((msg, i) => i === prev.length - 1 ? doneMsg : msg));
        if (taskIdFromUrl) {
          const vId = `v_${Date.now()}`;
          const v = { id: vId, prompt: 'Image to code', files: newFiles, time: new Date().toLocaleTimeString() };
          updateTask(taskIdFromUrl, { files: newFiles, messages: [{ role: 'user', content: prompt || 'Convert image to code' }, doneMsg], versions: [v], status: 'completed' });
        } else {
          addTask({ name: prompt ? prompt.slice(0, 120) : 'Image to code', prompt: prompt || 'Image to code', status: 'completed', createdAt: Date.now() });
        }
        setIsBuilding(false);
        setTimeout(() => fetchSuggestNext(), 400);
        return;
      }

      const phaseLabels = buildPhases.length ? buildPhases : [
        { id: 'planning', name: 'Planning' },
        { id: 'generating', name: 'Generating' },
        { id: 'validating', name: 'Validating' },
        { id: 'deployment', name: 'Deployment' }
      ];
      // ── Detect if the request is for native code (C, Python, algorithm, CLI) ──
      const nativeLangMap = {
        python: /\bpython\b/i,
        c:      /\b(c\s+program|in\s+c\b|\.c\b|c\s+code|write\s+c\b)/i,
        cpp:    /\b(c\+\+|cpp)\b/i,
        bash:   /\b(bash|shell\s+script|sh\b)\b/i,
        java:   /\bjava\b/i,
      };
      let nativeLang = null;
      for (const [lang, rx] of Object.entries(nativeLangMap)) {
        if (rx.test(prompt)) { nativeLang = lang; break; }
      }
      // Also treat algorithm/data-structure requests as native code
      const isAlgorithm = /\b(algorithm|sort|binary search|linked list|stack|queue|graph|tree|dynamic programming|compile|compiler|assembler|interpreter)\b/i.test(prompt);
      if (!nativeLang && isAlgorithm) nativeLang = 'c'; // default to C for algorithm tasks

      const isNativeCode = !!nativeLang;
      const langExt = { python: 'py', c: 'c', cpp: 'cpp', bash: 'sh', java: 'java' };
      const ext = langExt[nativeLang] || 'c';

      // ── Choose agent set based on request type ──
      const agents = isNativeCode ? [
        { name: 'Planner',   delay: 200, phase: phaseLabels[0]?.name || 'Planning',   desc: `Analyzing ${nativeLang} requirements...` },
        { name: 'Coder',     delay: 350, phase: phaseLabels[1]?.name || 'Generating', desc: `Writing ${nativeLang} source code...` },
        { name: 'Compiler',  delay: 300, phase: phaseLabels[1]?.name || 'Generating', desc: `Compiling and checking for errors...` },
        { name: 'Tester',    delay: 250, phase: phaseLabels[2]?.name || 'Validating', desc: 'Running test cases and verifying output...' },
        { name: 'Optimizer', delay: 150, phase: phaseLabels[3]?.name || 'Deployment', desc: 'Reviewing code quality and edge cases...' },
      ] : [
        { name: 'Planner',     delay: 250, phase: phaseLabels[0]?.name || 'Planning',    desc: 'Analyzing requirements and breaking into tasks...' },
        { name: 'Architect',   delay: 200, phase: phaseLabels[0]?.name || 'Planning',    desc: 'Designing component structure and data flow...' },
        { name: 'Frontend',    delay: 300, phase: phaseLabels[1]?.name || 'Generating',  desc: 'Building React components with hooks...' },
        { name: 'Styling',     delay: 250, phase: phaseLabels[1]?.name || 'Generating',  desc: 'Applying Tailwind CSS and responsive layout...' },
        { name: 'Logic',       delay: 200, phase: phaseLabels[1]?.name || 'Generating',  desc: 'Implementing business logic and state management...' },
        { name: 'Validator',   delay: 200, phase: phaseLabels[2]?.name || 'Validating',  desc: 'Checking for syntax errors and best practices...' },
        { name: 'Optimizer',   delay: 150, phase: phaseLabels[3]?.name || 'Deployment',  desc: 'Optimizing bundle and adding deployment config...' },
      ];
      let progress = 0;
      setAgentsActivity([]);
      for (const agent of agents) {
        setCurrentPhase(agent.phase);
        addLog(`[${agent.name}] ${agent.desc}`, 'info', agent.name.toLowerCase());
        setAgentsActivity(prev => [
          ...prev.filter(a => a.name !== agent.name),
          { name: agent.name, status: 'running', phase: agent.phase, progress: Math.round(progress), updated: Date.now() }
        ]);
        await new Promise(r => setTimeout(r, agent.delay));
        progress += 100 / agents.length;
        setBuildProgress(Math.min(Math.round(progress * 0.9), 90));
        setAgentsActivity(prev => prev.map(a => a.name === agent.name ? { ...a, status: 'done' } : a));
      }
      setCurrentPhase('');

      // ── Build generation prompt ──
      let messageContent;

      if (isNativeCode) {
        messageContent = `You are CrucibAI, an expert ${nativeLang} developer.

Create a complete, working ${nativeLang} program for: "${prompt}"

OUTPUT FORMAT — generate ONLY these files:

1. The main source file:
\`\`\`${nativeLang}:/main.${ext}
// complete ${nativeLang} source code here — NO placeholders
\`\`\`

2. If more source files are needed, add them:
\`\`\`${nativeLang}:/helpers.${ext}
// additional code
\`\`\`

3. A simple React viewer App.js that displays the source code and run instructions:
\`\`\`jsx:/App.js
import React, { useState } from 'react';

const SOURCE = \`[the exact source code]\`;

export default function App() {
  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6 font-mono">
      <h1 className="text-2xl font-bold text-green-400 mb-4">${prompt}</h1>
      <div className="bg-gray-800 rounded-lg p-4 overflow-auto">
        <pre className="text-sm text-green-300 whitespace-pre-wrap">{SOURCE}</pre>
      </div>
      <p className="mt-4 text-gray-400 text-sm">Click Run ▶ in the terminal below to execute this program.</p>
    </div>
  );
}
\`\`\`

RULES:
- Write COMPLETE, compilable/runnable code — no placeholders, no "// TODO"
- Include all necessary headers/imports
- Add comments explaining the algorithm
- Handle edge cases`;
      } else {
        messageContent = `You are CrucibAI. Build a COMPLETE, PRODUCTION-QUALITY, MULTI-FILE React application for: "${prompt}"

OUTPUT ALL FILES IN THIS EXACT ORDER — do not skip any:

\`\`\`jsx:/App.js
import { MemoryRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import Home from './pages/Home';
// import all pages...
export default function App() {
  return (
    <Router>
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        {/* all routes */}
      </Routes>
      <Footer />
    </Router>
  );
}
\`\`\`

\`\`\`css:/styles.css
/* Global styles, fonts, CSS variables */
\`\`\`

\`\`\`jsx:/components/Navbar.js
/* Full responsive navigation with logo, links, mobile menu */
\`\`\`

\`\`\`jsx:/components/Footer.js
/* Full footer with links, socials, copyright */
\`\`\`

\`\`\`jsx:/pages/Home.js
/* Hero section, features grid, CTA — full content, NO placeholders */
\`\`\`

Then add ALL other relevant pages (About, Services, Pricing, Contact, etc.) — one \`\`\`jsx:/pages/PageName.js\`\`\` block each.

RULES:
- MemoryRouter only (NOT BrowserRouter — breaks in preview iframe)
- Tailwind CSS classes for ALL styling (loaded via CDN)
- lucide-react for icons, framer-motion for animations
- Real hardcoded data — NO "Lorem ipsum", NO placeholder text
- NO backend code, NO fetch(), NO require(), NO Node.js
- COMPLETE code in every file — no "// TODO", no "// add here", no truncation
- Every component fully implemented with real content

Allowed imports: react, react-router-dom, lucide-react, framer-motion, recharts, date-fns, clsx

BUILD IT NOW — output every file completely:`;
      }

      if (imagesToSend.length > 0) {
        messageContent += `\n\n- The user attached ${imagesToSend.length} image(s) as design reference. Match the style closely.`;
      }
      const wantsPayments = /payment|stripe|subscription|checkout|pay|billing/i.test(prompt);
      if (wantsPayments) {
        messageContent += `\n\n- Include Stripe Checkout integration with a working payment button and STRIPE_PUBLISHABLE_KEY placeholder.`;
      }
      const wantsAuth = /login|auth|sign.?in|register|user|account/i.test(prompt);
      if (wantsAuth) {
        messageContent += `\n\n- Include a working login/register UI with form validation and localStorage-based session simulation.`;
      }
      const wantsDB = /database|db|data|crud|list|todo|tasks?|store/i.test(prompt);
      if (wantsDB) {
        messageContent += `\n\n- Include localStorage-based data persistence with full CRUD operations.`;
      }

      // Clear stale default files before new build — Explorer should show ONLY built files
      setFiles({});
      setExpandedFolders({});

      // ── ITERATIVE BUILD (multi-turn, 15-30 files) ──────────────────
      const iterativeBuildKinds = ['fullstack','saas','landing','ai_agent','game','mobile'];
      const shouldUseIterative = !isNativeCode && !useImageToCode && !!token;
      // Detect build kind for preview routing
      const detectedBuildKind = /mobile|react native|expo|ios app|android/i.test(prompt) ? 'mobile'
        : /saas|dashboard|admin/i.test(prompt) ? 'saas'
        : /landing page|one.?page|marketing/i.test(prompt) ? 'landing'
        : /agent|automation|chatbot/i.test(prompt) ? 'ai_agent'
        : /game|2d game/i.test(prompt) ? 'game'
        : 'fullstack';
      setLastBuildKind(detectedBuildKind);

      if (shouldUseIterative) {
        addLog('Starting iterative multi-file build...', 'info', 'planner');
        try {
          const iterRes = await fetch(`${API}/ai/build/iterative`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...headers },
            body: JSON.stringify({ message: messageContent, session_id: sessionId }),
          });
          if (!iterRes.ok) throw new Error(`Iterative build failed: ${iterRes.status}`);
          const reader2 = iterRes.body.getReader();
          const decoder2 = new TextDecoder();
          let iterDone = false;
          while (!iterDone) {
            const { done, value } = await reader2.read();
            if (done) break;
            const lines = decoder2.decode(value, { stream: true }).split('\n').filter(Boolean);
            for (const line of lines) {
              try {
                const ev = JSON.parse(line);
                if (ev.type === 'start') {
                  addLog(`Building ${ev.build_kind} app in ${ev.total_steps} passes...`, 'info', 'planner');
                  setBuildProgress(10);
                }
                if (ev.type === 'step_complete') {
                  const stepFiles = ev.files || {};
                  const count = Object.keys(stepFiles).length;
                  addLog(`✓ ${ev.step}: ${count} files generated`, 'success', ev.step);
                  setFiles(prev => ({ ...prev, ...Object.fromEntries(Object.entries(stepFiles).map(([k, v]) => [k, { code: v }])) }));
                  setBuildProgress(prev => Math.min(prev + 20, 90));
                }
                if (ev.type === 'done') {
                  iterDone = true;
                  const allFiles = ev.files || {};
                  const fileEntries = Object.fromEntries(Object.entries(allFiles).map(([k, v]) => [k, { code: v }]));
                  const totalCount = Object.keys(fileEntries).length;
                  addLog(`Build complete: ${totalCount} files`, 'success', 'deploy');
                  setBuildProgress(100);
                  if (refreshUser) refreshUser();
                  const vId = `v_${Date.now()}`;
                  setFiles(prev => ({ ...prev, ...fileEntries }));
                  setVersions(prev => [{ id: vId, prompt, files: { ...files, ...fileEntries }, time: new Date().toLocaleTimeString() }, ...prev]);
                  setMessages(m => m.map((msg, i) => i === m.length - 1 ? { role: 'assistant', content: `Done! Built ${totalCount} files.`, hasCode: true, planSuggestions } : msg));
                  setTimeout(() => { setCurrentVersion(vId); setFilesReadyKey(`fk_${vId}`); setActivePanel('preview'); }, 500);
                  setIsBuilding(false);
                  setAgentsActivity([]);
                  // PERSISTENCE FIX (Q122): store taskId in URL so returning users reload their workspace
                  const savedTaskId = ev.task_id || sessionId;
                  if (savedTaskId && !window.location.search.includes('taskId=')) {
                    const newUrl = new URL(window.location.href);
                    newUrl.searchParams.set('taskId', savedTaskId);
                    window.history.replaceState({}, '', newUrl.toString());
                  }
                }
                if (ev.type === 'error') {
                  throw new Error(ev.error);
                }
              } catch (_) {}
            }
          }
        } catch (iterErr) {
          addLog(`Iterative build failed: ${iterErr.message} — falling back to single call`, 'warn', 'deploy');
          // Fall through to single-call path below
        }
        if (!isBuilding) return; // iterative build finished
      }

      if (useStreaming) {
        const res = await fetch(`${API}/ai/chat/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...headers },
          body: JSON.stringify({ message: messageContent, session_id: sessionId, model: selectedModel, mode: buildMode === 'thinking' ? 'thinking' : undefined }),
        });
        if (!res.ok) {
          const responseText = await res.text();
          const isStreamMissing = res.status === 404 || res.status === 405 || /Cannot POST|<!DOCTYPE/i.test(responseText);
          if (isStreamMissing) {
            addLog('Stream endpoint not available, using non-streaming build...', 'info', 'deploy');
            const response = await axios.post(`${API}/ai/chat`, {
              message: messageContent,
              session_id: sessionId,
              model: selectedModel,
            }, { headers, timeout: 90000 });
            setBuildProgress(100);
            if (response.data.tokens_used != null) { setLastTokensUsed(response.data.tokens_used); setTokensPerStep(prev => ({ ...prev, generate: response.data.tokens_used })); }
            addLog('Build completed successfully!', 'success', 'deploy');
            if (refreshUser) refreshUser(); // refresh credit balance
            const parsedFiles = parseMultiFileOutput(response.data.response || response.data.message || '');
            const newFiles = { ...files, ...parsedFiles };
            const vId = `v_${Date.now()}`;
            setFiles(newFiles);
            setVersions(prev => [{ id: vId, prompt, files: newFiles, time: new Date().toLocaleTimeString() }, ...prev]);
            setTimeout(() => {
            setCurrentVersion(vId);
            setFilesReadyKey(`fk_${vId}`);
            setActivePanel("preview");
          }, 500);
            setMessages(prev => prev.map((msg, i) => i === prev.length - 1 ? { role: 'assistant', content: 'Done! Your app is ready.', hasCode: true, planSuggestions } : msg));
            setTimeout(() => fetchSuggestNext(), 400);
            const mainCode = parsedFiles['/App.js']?.code || parsedFiles['/src/App.jsx']?.code || parsedFiles['/App.jsx']?.code || Object.values(parsedFiles)[0]?.code || '';
            const filesForQuality = Object.fromEntries(Object.entries(parsedFiles || {}).map(([k, v]) => [k, (v && v.code) || '']));
            const qgHeaders = token ? { Authorization: `Bearer ${token}` } : {};
            axios.post(`${API}/ai/quality-gate`, { code: mainCode, files: Object.keys(filesForQuality).length ? filesForQuality : undefined }, { headers: qgHeaders }).then(r => setQualityGateResult(r.data)).catch(() => setQualityGateResult(null));
            setActivePanel('preview');
            if (taskIdFromUrl) {
              const finalMsgs = [{ role: 'user', content: prompt }, { role: 'assistant', content: 'Done! Your app is ready.', hasCode: true, planSuggestions }];
              const vId = `v_${Date.now()}`;
              updateTask(taskIdFromUrl, { files: newFiles, messages: finalMsgs, versions: [{ id: vId, prompt, files: newFiles, time: new Date().toLocaleTimeString() }], status: 'completed' });
            } else {
              addTask({ name: prompt.slice(0, 120), prompt, status: 'completed', createdAt: Date.now() });
            }
            if (token) {
              axios.post(`${API}/tasks`, { name: prompt.slice(0, 120), prompt, session_id: sessionId, status: 'completed', files: Object.keys(parsedFiles) }, { headers: { Authorization: `Bearer ${token}` } }).catch(() => {});
            }
            if (projectIdFromUrl) {
              const hdr = token ? { Authorization: `Bearer ${token}` } : {};
              axios.get(`${API}/projects/${projectIdFromUrl}/deploy/files`, { headers: hdr })
                .then(r => {
                  const df = r.data?.files || {};
                  if (Object.keys(df).length > 0) {
                    const spFiles = {};
                    for (const [fp, content] of Object.entries(df)) {
                      spFiles[fp.startsWith('/') ? fp : `/${fp}`] = { code: content };
                    }
                    setFiles(prev => ({ ...prev, ...spFiles }));
                    addLog(`Loaded ${Object.keys(df).length} files from orchestration.`, 'info', 'deploy');
                  }
                  if (r.data?.quality_score) setQualityGateResult({ score: r.data.quality_score });
                }).catch(() => {});
            }
          } else {
            throw new Error(responseText);
          }
        } else {
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let accumulated = '';
        let streamDone = false;
        while (!streamDone) {
          const { done, value } = await reader.read();
          if (done) break;
          const text = decoder.decode(value, { stream: true });
          const lines = text.split('\n').filter(Boolean);
          for (const line of lines) {
            try {
              const obj = JSON.parse(line);
              if (obj.error) {
                const errMsg = obj.error;
                if (errMsg.includes('rate limit') || errMsg.includes('Rate limit') || errMsg.includes('RATE_LIMITED') || errMsg.includes('429')) {
                  throw new Error('⏱ AI rate limit reached — wait 60 seconds and try again.');
                }
                throw new Error(errMsg);
              }
              if (obj.chunk) {
                accumulated += obj.chunk;
                // Don't update files mid-stream with raw text - wait for parse at done
              }
              if (obj.done) {
                streamDone = true;
                setBuildProgress(100);
                if (obj.tokens_used != null) { setLastTokensUsed(obj.tokens_used); setTokensPerStep(prev => ({ ...prev, generate: obj.tokens_used })); }
                addLog('Build completed successfully!', 'success', 'deploy');
                if (refreshUser) refreshUser(); // refresh credit balance in sidebar
                const parsedFiles = parseMultiFileOutput(accumulated);
                const versionId = `v_${Date.now()}`;
                setFiles(prev => {
                  const next = { ...prev, ...parsedFiles };
                  setVersions(v => [{ id: versionId, prompt, files: next, time: new Date().toLocaleTimeString() }, ...v]);
                  setMessages(m => m.map((msg, i) => i === m.length - 1 ? { role: 'assistant', content: 'Done! Your app is ready.', hasCode: true, planSuggestions: planSuggestions } : msg));
                  setTimeout(() => fetchSuggestNext(), 400);
                  const mainCode = parsedFiles['/App.js']?.code || parsedFiles['/src/App.jsx']?.code || parsedFiles['/App.jsx']?.code || Object.values(parsedFiles)[0]?.code || '';
                  const filesForQuality = Object.fromEntries(Object.entries(parsedFiles || {}).map(([k, v]) => [k, (v && v.code) || '']));
                  const qgHeaders = token ? { Authorization: `Bearer ${token}` } : {};
                  axios.post(`${API}/ai/quality-gate`, { code: mainCode, files: Object.keys(filesForQuality).length ? filesForQuality : undefined }, { headers: qgHeaders }).then(r => setQualityGateResult(r.data)).catch(() => setQualityGateResult(null));
                  return next;
                });
                // Set version AFTER files are committed so Sandpack remounts with correct files
                setTimeout(() => {
                  setCurrentVersion(versionId);
                  setFilesReadyKey(`fk_${versionId}`);
                  setActivePanel("preview");
                }, 500);
                // AUTO-RUN: if native code files were generated, compile + run them
                const nativeFileKeys = Object.keys(parsedFiles).filter(p => /\.(c|cpp|py|sh|rb|go|rs|java)$/i.test(p));
                if (nativeFileKeys.length > 0) {
                  const fileToRun = nativeFileKeys[0];
                  const runCode = parsedFiles[fileToRun]?.code || '';
                  const runLang = /\.py$/.test(fileToRun) ? 'python'
                               : /\.cpp$/.test(fileToRun) ? 'cpp'
                               : /\.sh$/.test(fileToRun) ? 'bash'
                               : /\.java$/.test(fileToRun) ? 'java'
                               : 'c';
                  setActiveFile(fileToRun);
                  setActiveBottomPanel('terminal');
                  addLog(`[Compiler] Compiling and running ${fileToRun}...`, 'info', 'compiler');
                  axios.post(`${API}/code/run`, { code: runCode, language: runLang, filename: fileToRun }, { timeout: 20000 })
                    .then(r => {
                      if (r.data.stdout) addLog(`[Output]\n${r.data.stdout}`, r.data.exit_code === 0 ? 'success' : 'info', 'run');
                      if (r.data.stderr && r.data.exit_code !== 0) addLog(`[Error]\n${r.data.stderr}`, 'error', 'run');
                      else if (r.data.stderr) addLog(`[Warnings]\n${r.data.stderr}`, 'warning', 'run');
                      addLog(`Exited with code ${r.data.exit_code}`, r.data.exit_code === 0 ? 'success' : 'error', 'run');
                    })
                    .catch(e => addLog(`Auto-run failed: ${e.message}`, 'error', 'run'));
                } else {
                  setActivePanel('preview'); // AUTO-WIRE: switch to preview on build complete
                }
                // PHASE 7: Single task authority — update existing task or add new
                if (taskIdFromUrl) {
                  const merged = { ...files, ...parsedFiles };
                  const finalMsgs = [{ role: 'user', content: prompt }, { role: 'assistant', content: 'Done! Your app is ready.', hasCode: true, planSuggestions: planSuggestions }];
                  const vId = `v_${Date.now()}`;
                  updateTask(taskIdFromUrl, { files: merged, messages: finalMsgs, versions: [{ id: vId, prompt, files: merged, time: new Date().toLocaleTimeString() }], status: 'completed' });
                } else {
                  addTask({ name: prompt.slice(0, 120), prompt, status: 'completed', createdAt: Date.now() });
                }
                if (token) {
                  axios.post(`${API}/tasks`, {
                    name: prompt.slice(0, 120),
                    prompt,
                    session_id: sessionId,
                    status: 'completed',
                    files: Object.keys(parsedFiles),
                  }, { headers: { Authorization: `Bearer ${token}` } }).catch(() => {});
                }
                // AUTO-WIRE: Also try to fetch multi-file deploy output if project exists
                if (projectIdFromUrl) {
                  const hdr = token ? { Authorization: `Bearer ${token}` } : {};
                  axios.get(`${API}/projects/${projectIdFromUrl}/deploy/files`, { headers: hdr })
                    .then(r => {
                      const df = r.data?.files || {};
                      if (Object.keys(df).length > 0) {
                        const spFiles = {};
                        for (const [fp, content] of Object.entries(df)) {
                          spFiles[fp.startsWith('/') ? fp : `/${fp}`] = { code: content };
                        }
                        setFiles(prev => ({ ...prev, ...spFiles }));
                        addLog(`Loaded ${Object.keys(df).length} files from orchestration.`, 'info', 'deploy');
                      }
                      if (r.data?.quality_score) setQualityGateResult({ score: r.data.quality_score });
                    }).catch(() => {});
                }
                break;
              }
            } catch (_) {}
          }
        }
      }
    } else {
        const response = await axios.post(`${API}/ai/chat`, {
          message: messageContent,
          session_id: sessionId,
          model: selectedModel
        }, { headers, timeout: 90000 });
        setBuildProgress(100);
        if (response.data.tokens_used != null) { setLastTokensUsed(response.data.tokens_used); setTokensPerStep(prev => ({ ...prev, generate: response.data.tokens_used })); }
        addLog('Build completed successfully!', 'success', 'deploy');
        const parsedFiles = parseMultiFileOutput(response.data.response);
        const newFiles = { ...files, ...parsedFiles };
        setFiles(newFiles);
        setVersions(prev => [{ id: `v_${Date.now()}`, prompt, files: newFiles, time: new Date().toLocaleTimeString() }, ...prev]);
        setCurrentVersion(`v_${Date.now()}`);
        setMessages(prev => prev.map((msg, i) => i === prev.length - 1 ? { role: 'assistant', content: 'Done! Your app is ready.', hasCode: true, planSuggestions } : msg));
        setTimeout(() => fetchSuggestNext(), 400);
        const mainCode = parsedFiles['/App.js']?.code || parsedFiles['/src/App.jsx']?.code || parsedFiles['/App.jsx']?.code || Object.values(parsedFiles)[0]?.code || '';
        const filesForQuality = Object.fromEntries(Object.entries(parsedFiles || {}).map(([k, v]) => [k, (v && v.code) || '']));
        const qgHdrs = token ? { Authorization: `Bearer ${token}` } : {};
        axios.post(`${API}/ai/quality-gate`, { code: mainCode, files: Object.keys(filesForQuality).length ? filesForQuality : undefined }, { headers: qgHdrs }).then(r => setQualityGateResult(r.data)).catch(() => setQualityGateResult(null));
        setActivePanel('preview'); // AUTO-WIRE: switch to preview on build complete
        // PHASE 7: Single task authority — update existing task or add new
        if (taskIdFromUrl) {
          const finalMsgs = [{ role: 'user', content: prompt }, { role: 'assistant', content: 'Done! Your app is ready.', hasCode: true, planSuggestions }];
          const vId = `v_${Date.now()}`;
          updateTask(taskIdFromUrl, { files: newFiles, messages: finalMsgs, versions: [{ id: vId, prompt, files: newFiles, time: new Date().toLocaleTimeString() }], status: 'completed' });
        } else {
          addTask({ name: prompt.slice(0, 120), prompt, status: 'completed', createdAt: Date.now() });
        }
        if (token) {
          axios.post(`${API}/tasks`, {
            name: prompt.slice(0, 120),
            prompt,
            session_id: sessionId,
            status: 'completed',
            files: Object.keys(parsedFiles),
          }, { headers: { Authorization: `Bearer ${token}` } }).catch(() => {});
        }
        // AUTO-WIRE: Also try to fetch multi-file deploy output if project exists
        if (projectIdFromUrl) {
          const hdr = token ? { Authorization: `Bearer ${token}` } : {};
          axios.get(`${API}/projects/${projectIdFromUrl}/deploy/files`, { headers: hdr })
            .then(r => {
              const df = r.data?.files || {};
              if (Object.keys(df).length > 0) {
                const spFiles = {};
                for (const [fp, content] of Object.entries(df)) {
                  spFiles[fp.startsWith('/') ? fp : `/${fp}`] = { code: content };
                }
                setFiles(prev => ({ ...prev, ...spFiles }));
                addLog(`Loaded ${Object.keys(df).length} files from orchestration.`, 'info', 'deploy');
              }
              if (r.data?.quality_score) setQualityGateResult({ score: r.data.quality_score });
            }).catch(() => {});
        }
      }
    } catch (error) {
      const rawMsg = error.message || '';
      const is404 = error.response?.status === 404 || error.response?.status === 405;
      const isHtmlError = /<!DOCTYPE|Cannot POST|<\/?(html|body|pre)>/i.test(rawMsg);
      const backendUnavailable = "Backend not available. Start the CrucibAI backend to use AI build (see BACKEND_SETUP.md). If the backend is running, ensure it exposes POST /api/ai/chat and optionally /api/build/plan and /api/ai/chat/stream.";
      addLog(`Build failed: ${is404 || isHtmlError ? 'Backend endpoint unavailable' : rawMsg.slice(0, 200)}`, 'error', 'system');
      setLastError(is404 || isHtmlError ? 'Backend endpoint unavailable' : error.message);
      const detail = String(error.response?.data?.detail || '');
      const is402 = error.response?.status === 402;
      const is429 = error.response?.status === 429 || rawMsg.includes('Rate limit') || rawMsg.includes('rate limit') || rawMsg.includes('RATE_LIMITED');
      const isKeyError = error.response?.status === 401 || detail.toLowerCase().includes('api key') || detail.toLowerCase().includes('no api key') || (error.message && error.message.toLowerCase().includes('key'));
      let friendlyMessage;
      if (is429) {
        friendlyMessage = '⏱ AI rate limit reached — wait 60 seconds and try again. This happens when too many builds run at once.';
      } else if (is402) {
        friendlyMessage = detail || 'Insufficient tokens. Buy more in Token Center to keep building.';
      } else if (is404 || isHtmlError || (error.message && (error.message.includes('Cannot POST') || error.message.includes('<!DOCTYPE') || error.message.includes('status code 404')))) {
        friendlyMessage = backendUnavailable;
      } else if (error.code === 'ERR_NETWORK' || (error.message && (error.message.includes('Network') || error.message.includes('Failed to fetch')))) {
        friendlyMessage = "Connection lost. Make sure the backend server is running (e.g. port 8000) and try again. See BACKEND_SETUP.md.";
      } else if (isKeyError) {
        friendlyMessage = "AI service error. Make sure CEREBRAS_API_KEY is set in backend/.env and the server is running.";
      } else {
        friendlyMessage = `Build failed: ${detail || (isHtmlError ? "Backend returned an error. See BACKEND_SETUP.md." : rawMsg) || 'Unknown error. Please try again.'}`;
      }
      setMessages(prev => {
        const next = prev.map((msg, i) => i === prev.length - 1 ? { role: 'assistant', content: friendlyMessage, error: true } : msg);
        if (friendlyMessage === backendUnavailable || friendlyMessage.startsWith('Backend not available.')) {
          const dupIndices = next.map((m, i) => i).filter(i => next[i].role === 'assistant' && next[i].content?.startsWith?.('Backend not available.'));
          const keepLastOnly = dupIndices.length > 1 ? dupIndices[dupIndices.length - 1] : null;
          if (keepLastOnly != null) return next.filter((m, i) => m.role !== 'assistant' || !m.content?.startsWith?.('Backend not available.') || i === keepLastOnly);
        }
        return next;
      });
    } finally {
      setIsBuilding(false);
    }
  };

  const handleModify = async () => {
    if (!input.trim() || isBuilding) return;

    const request = input.trim();
    setInput('');
    setNextSuggestions([]);
    setIsBuilding(true);
    setRightSidebarOpen(true);
    setActivePanel('preview');
    
    setMessages(prev => [...prev, { role: 'user', content: request }]);
    setMessages(prev => [...prev, { role: 'assistant', content: 'Updating...', isBuilding: true }]);
    
    addLog('Processing modification request...', 'info', 'planner');

    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      
      // Build context from all files for multi-file awareness
      const fileContext = Object.entries(files).map(([fp, f]) => `--- ${fp} ---\n${f.code || ''}`).join('\n\n');
      const response = await axios.post(`${API}/ai/chat`, {
        message: `Current files:\n\n${fileContext}\n\nModify to: "${request}"\n\nRespond with the complete updated code. If multiple files, use \`\`\`jsx:filename.js format.`,
        session_id: sessionId,
        model: selectedModel,
        mode: buildMode === 'thinking' ? 'thinking' : undefined
      }, { headers, timeout: 90000 });

      if (response.data.tokens_used != null) setLastTokensUsed(response.data.tokens_used);
      const parsedModFiles = parseMultiFileOutput(response.data.response);
      const hasCode = Object.values(parsedModFiles).some(f => f.code && (f.code.includes('import') || f.code.includes('function') || f.code.includes('const')));

      if (hasCode) {
        const newFiles = { ...files, ...parsedModFiles };
        setFiles(newFiles);
        
        const newVersion = {
          id: `v_${Date.now()}`,
          prompt: request,
          files: newFiles,
          time: new Date().toLocaleTimeString()
        };
        setVersions(prev => [newVersion, ...prev]);
        setCurrentVersion(newVersion.id);
        
        addLog('Modification applied successfully!', 'success', 'frontend');
        setTimeout(() => fetchSuggestNext(), 400);
        setMessages(prev => prev.map((msg, i) => 
          i === prev.length - 1 ? { role: 'assistant', content: 'Updated! What else would you like to change?', hasCode: true } : msg
        ));
      } else {
        setMessages(prev => prev.map((msg, i) => 
          i === prev.length - 1 ? { role: 'assistant', content: response.data.response } : msg
        ));
      }
    } catch (error) {
      const is404 = error.response?.status === 404 || error.response?.status === 405;
      const backendUnavailable = "Backend not available. Start the CrucibAI backend to use AI build (see BACKEND_SETUP.md).";
      addLog(`Modification failed: ${is404 ? 'Backend endpoint unavailable' : error.message}`, 'error', 'system');
      const friendlyMessage = is404 ? backendUnavailable : (error.response?.data?.detail || 'Error updating. Try again.');
      setMessages(prev => {
        const next = prev.map((msg, i) => i === prev.length - 1 ? { role: 'assistant', content: friendlyMessage, error: true } : msg);
        if (friendlyMessage.startsWith('Backend not available.')) {
          const dupIndices = next.map((m, i) => i).filter(i => next[i].role === 'assistant' && next[i].content?.startsWith?.('Backend not available.'));
          const keepLastOnly = dupIndices.length > 1 ? dupIndices[dupIndices.length - 1] : null;
          if (keepLastOnly != null) return next.filter((m, i) => m.role !== 'assistant' || !m.content?.startsWith?.('Backend not available.') || i === keepLastOnly);
        }
        return next;
      });
    } finally {
      setIsBuilding(false);
    }
  };

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (!input.trim()) {
      // Section 07 Test E-1: Show error for empty prompt
      if (input === '' || input.trim() === '') {
        setMessages(prev => [...prev, { role: 'assistant', content: 'Please describe what you want to build.', error: true }]);
      }
      return;
    }
    
    if (versions.length > 0) {
      handleModify();
    } else {
      handleBuild();
    }
  };

  const restoreVersion = (version) => {
    setFiles(version.files);
    setCurrentVersion(version.id);
    addLog(`Restored to version from ${version.time}`, 'info', 'history');
  };

  const addNewFileToProject = () => {
    const name = window.prompt('File name (e.g. Button.jsx):');
    if (!name) return;
    const path = name.startsWith('/') ? name : `/${name}`;
    if (files[path]) { addLog(`File ${path} already exists`, 'warning', 'files'); return; }
    const isReact = /\.(jsx?|tsx?)$/.test(name);
    const code = isReact
      ? `import React from 'react';\n\nexport default function ${name.replace(/\.[^.]+$/, '').replace(/[^a-zA-Z0-9]/g, '')}() {\n  return <div>New component</div>;\n}\n`
      : '';
    setFiles(prev => ({ ...prev, [path]: { code } }));
    setActiveFile(path);
    addLog(`Created ${path}`, 'success', 'files');
  };

  const addNewFolderToProject = () => {
    const name = window.prompt('Folder name:');
    if (!name) return;
    const folder = name.replace(/^\//, '').replace(/\/$/, '');
    const placeholder = `/${folder}/.gitkeep`;
    setFiles(prev => ({ ...prev, [placeholder]: { code: '' } }));
    addLog(`Created folder /${folder}`, 'success', 'files');
  };

  const deleteFileFromProject = (path) => {
    if (!window.confirm(`Delete ${path}?`)) return;
    setFiles(prev => {
      const next = { ...prev };
      delete next[path];
      return next;
    });
    if (activeFile === path) setActiveFile(Object.keys(files).find(f => f !== path) || '/App.js');
    addLog(`Deleted ${path}`, 'info', 'files');
  };

  const handleFolderOpen = (e) => {
    const items = Array.from(e.target.files);
    if (!items.length) return;
    const CODE_EXTS = /\.(jsx?|tsx?|css|html|json|py|c|cpp|h|hpp|md|txt|env\.example|gitignore)$/i;
    const eligible = items.filter(f => CODE_EXTS.test(f.name));
    if (!eligible.length) { addLog('No code files found in folder', 'warning', 'files'); return; }
    let loaded = 0;
    const newFiles = {};
    eligible.forEach(file => {
      const rel = file.webkitRelativePath || file.name;
      // Strip the top folder name so paths start from "/"
      const path = '/' + rel.split('/').slice(1).join('/');
      const reader = new FileReader();
      reader.onload = ev => {
        newFiles[path] = { code: ev.target.result };
        loaded++;
        if (loaded === eligible.length) {
          setFiles(prev => ({ ...prev, ...newFiles }));
          const first = Object.keys(newFiles)[0];
          if (first) setActiveFile(first);
          addLog(`Loaded ${loaded} files from local folder`, 'success', 'files');
        }
      };
      reader.readAsText(file);
    });
    e.target.value = '';
  };

  // Item 31 — Bring your code: ZIP upload → parse and setFiles()
  const handleZipUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !file.name.toLowerCase().endsWith('.zip')) {
      addLog('Please select a .zip file', 'warning', 'files');
      e.target.value = '';
      return;
    }
    try {
      const zip = await JSZip.loadAsync(file);
      const CODE_EXTS = /\.(jsx?|tsx?|css|html|json|py|c|cpp|h|hpp|md|txt|env\.example|gitignore)$/i;
      const newFiles = {};
      const entries = Object.keys(zip.files).filter((name) => !zip.files[name].dir && CODE_EXTS.test(name));
      for (const name of entries) {
        const entry = zip.files[name];
        const content = await entry.async('string');
        const path = name.startsWith('/') ? name : `/${name}`;
        newFiles[path] = { code: content };
      }
      if (Object.keys(newFiles).length === 0) {
        addLog('No code files found in ZIP', 'warning', 'files');
      } else {
        setFiles(prev => ({ ...prev, ...newFiles }));
        const first = Object.keys(newFiles).sort()[0];
        if (first) setActiveFile(first);
        addLog(`Loaded ${Object.keys(newFiles).length} files from ZIP`, 'success', 'files');
      }
    } catch (err) {
      addLog(`ZIP error: ${err.message || 'Failed to read ZIP'}`, 'error', 'files');
    }
    e.target.value = '';
  };

  const runCurrentCode = async () => {
    const code = files[activeFile]?.code ?? '';
    if (!code.trim()) { addLog('No code to run — open a file first', 'warning', 'system'); return; }
    const lang = /\.py$/.test(activeFile) ? 'python'
               : /\.(c)$/.test(activeFile) ? 'c'
               : /\.cpp$/.test(activeFile) ? 'cpp'
               : /\.sh$/.test(activeFile) ? 'bash'
               : 'javascript';
    addLog(`Running ${activeFile} as ${lang}...`, 'info', 'system');
    setActiveBottomPanel('terminal');
    try {
      const res = await axios.post(`${API}/code/run`, {
        code, language: lang, filename: activeFile,
      }, { timeout: 20000 });
      const { stdout, stderr, exit_code } = res.data;
      if (stdout) addLog(`[stdout]\n${stdout}`, exit_code === 0 ? 'success' : 'info', 'run');
      if (stderr) addLog(`[stderr]\n${stderr}`, 'error', 'run');
      if (!stdout && !stderr) addLog(`Exited with code ${exit_code}`, exit_code === 0 ? 'success' : 'error', 'run');
    } catch (e) {
      addLog(`Run failed: ${e.message}`, 'error', 'run');
    }
  };

  const runValidate = async () => {
    const code = files[activeFile]?.code ?? '';
    if (!code.trim()) { addLog('No file selected or empty file', 'warning', 'system'); return; }
    setToolsLoading(true);
    setToolsReport(null);
    try {
      const lang = activeFile.endsWith('.css') ? 'css' : 'javascript';
      const res = await axios.post(`${API}/ai/validate-and-fix`, { code, language: lang }, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
      setToolsReport({ type: 'validate', data: res.data });
      addLog(res.data.valid ? 'Validation: no issues' : 'Validation: issues found, fix available', res.data.valid ? 'success' : 'warning', 'system');
    } catch (e) {
      addLog(`Validate failed: ${e.response?.data?.detail || e.message}`, 'error', 'system');
      setToolsReport({ type: 'validate', data: { error: e.response?.data?.detail || e.message } });
    } finally {
      setToolsLoading(false);
    }
  };

  const runSecurityScan = async () => {
    const payload = Object.fromEntries(Object.entries(files).map(([k, v]) => [k, v?.code ?? '']));
    setToolsLoading(true);
    setToolsReport(null);
    try {
      const body = { files: payload };
      if (projectIdFromUrl && token) body.project_id = projectIdFromUrl;
      const res = await axios.post(`${API}/ai/security-scan`, body, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
      setToolsReport({ type: 'security', data: res.data });
      addLog('Security scan completed', 'info', 'system');
    } catch (e) {
      addLog(`Security scan failed: ${e.response?.data?.detail || e.message}`, 'error', 'system');
      setToolsReport({ type: 'security', data: { error: e.response?.data?.detail || e.message } });
    } finally {
      setToolsLoading(false);
    }
  };

  const runA11yCheck = async () => {
    const code = files[activeFile]?.code ?? '';
    if (!code.trim()) { addLog('No file selected or empty file', 'warning', 'system'); return; }
    setToolsLoading(true);
    setToolsReport(null);
    try {
      const res = await axios.post(`${API}/ai/accessibility-check`, { code }, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
      setToolsReport({ type: 'a11y', data: res.data });
      addLog('Accessibility check completed', 'info', 'system');
    } catch (e) {
      addLog(`A11y check failed: ${e.response?.data?.detail || e.message}`, 'error', 'system');
      setToolsReport({ type: 'a11y', data: { error: e.response?.data?.detail || e.message } });
    } finally {
      setToolsLoading(false);
    }
  };

  const fetchSuggestNext = async (filesOverride = null, lastPromptOverride = null) => {
    const f = filesOverride || files;
    const payload = Object.fromEntries(Object.entries(f).map(([k, v]) => [k, (v && typeof v === 'object' && v.code !== undefined) ? v.code : (v || '')]));
    const lastPrompt = lastPromptOverride ?? (messages.length > 0 ? (messages[messages.length - 1].content || '').slice(0, 200) : '');
    try {
      const res = await axios.post(`${API}/ai/suggest-next`, { files: payload, last_prompt: lastPrompt }, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
      setNextSuggestions(Array.isArray(res.data?.suggestions) ? res.data.suggestions : []);
    } catch {
      setNextSuggestions([]);
    }
  };

  const applyValidateFix = () => {
    if (toolsReport?.type === 'validate' && toolsReport.data?.fixed_code) {
      setFiles(prev => ({ ...prev, [activeFile]: { code: toolsReport.data.fixed_code } }));
      addLog('Applied validation fix', 'success', 'system');
      setToolsReport(null);
    }
  };

  const downloadCode = () => {
    Object.entries(files).forEach(([name, { code }]) => {
      const blob = new Blob([code], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = name.replace('/', '');
      a.click();
    });
    addLog('Files downloaded', 'success', 'export');
  };

  const exportFilesPayload = () => {
    const out = {};
    Object.entries(files).forEach(([name, { code }]) => { out[name] = code || ''; });
    return out;
  };

  const handleExportGitHub = async () => {
    try {
      const res = await axios.post(`${API}/export/github`, { files: exportFilesPayload() }, { responseType: 'blob' });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'crucibai-github.zip';
      a.click();
      URL.revokeObjectURL(url);
      addLog('GitHub ZIP downloaded. Create a repo and upload contents.', 'success', 'export');
    } catch (e) {
      addLog(`Export failed: ${e.message}`, 'error', 'export');
    }
  };

  const handleExportDeploy = async () => {
    try {
      const res = await axios.post(`${API}/export/deploy`, { files: exportFilesPayload() }, { responseType: 'blob' });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'crucibai-deploy.zip';
      a.click();
      URL.revokeObjectURL(url);
      addLog('Deploy ZIP downloaded. Use Vercel or Netlify to deploy.', 'success', 'export');
    } catch (e) {
      addLog(`Export failed: ${e.message}`, 'error', 'export');
    }
  };

  const handleExportZip = async () => {
    try {
      const res = await axios.post(`${API}/export/zip`, { files: exportFilesPayload() }, { responseType: 'blob' });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'crucibai-project.zip';
      a.click();
      URL.revokeObjectURL(url);
      addLog('Project ZIP downloaded. For live URL: upload to Vercel (vercel.com/new) or Netlify.', 'success', 'export');
    } catch (e) {
      addLog(`Export ZIP failed: ${e.message}`, 'error', 'export');
    }
  };

  const formatDeployErr = (e) => {
    const d = e.response?.data?.detail;
    if (typeof d === 'string') return d;
    if (d && typeof d === 'object') return d.message || JSON.stringify(d);
    return e.message;
  };

  const downloadServerDeployZip = async () => {
    if (!projectIdFromUrl || !token) {
      addLog('Open a saved project to download the server deploy package.', 'warning', 'export');
      return;
    }
    setDeployZipBusy(true);
    try {
      const res = await axios.get(`${API}/projects/${projectIdFromUrl}/deploy/zip`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob',
        timeout: 120000,
      });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'crucibai-deploy.zip';
      a.click();
      URL.revokeObjectURL(url);
      addLog('Deploy ZIP downloaded from project (orchestration snapshot).', 'success', 'export');
    } catch (e) {
      addLog(`Server deploy ZIP: ${formatDeployErr(e)}`, 'error', 'export');
    } finally {
      setDeployZipBusy(false);
    }
  };

  const oneClickDeployPlatform = async (platform) => {
    if (!projectIdFromUrl || !token) {
      addLog('Save as a project first, then deploy.', 'warning', 'export');
      return;
    }
    setDeployOneClickBusy(platform);
    try {
      const res = await axios.post(
        `${API}/projects/${projectIdFromUrl}/deploy/${platform}`,
        {},
        { headers: { Authorization: `Bearer ${token}` }, timeout: 120000 },
      );
      const u = res.data?.url;
      if (u) {
        setProjectLiveUrl(u);
        addLog(`Live: ${u}`, 'success', 'export');
      } else {
        addLog(`${platform} deploy finished — check your dashboard for the URL.`, 'info', 'export');
      }
    } catch (e) {
      addLog(`${platform}: ${formatDeployErr(e)}`, 'error', 'export');
    } finally {
      setDeployOneClickBusy(null);
    }
  };

  const savePublishSettings = async () => {
    if (!projectIdFromUrl || !token) {
      addLog('Open a saved project to save publish settings.', 'warning', 'export');
      return;
    }
    setPublishSaveBusy(true);
    try {
      await axios.patch(
        `${API}/projects/${projectIdFromUrl}/publish-settings`,
        { custom_domain: publishCustomDomain.trim(), railway_project_url: publishRailwayUrl.trim() },
        { headers: { Authorization: `Bearer ${token}` } },
      );
      addLog('Publish settings saved (custom domain + Railway link).', 'success', 'export');
    } catch (e) {
      addLog(`Publish settings: ${formatDeployErr(e)}`, 'error', 'export');
    } finally {
      setPublishSaveBusy(false);
    }
  };

  const prepareRailwayDeploy = async () => {
    if (!projectIdFromUrl || !token) {
      addLog('Save as a project first.', 'warning', 'export');
      return;
    }
    setDeployRailwayBusy(true);
    setDeployRailwayErr(null);
    setDeployRailwaySteps(null);
    setDeployRailwayDashboard(null);
    try {
      const res = await axios.post(
        `${API}/projects/${projectIdFromUrl}/deploy/railway`,
        {},
        { headers: { Authorization: `Bearer ${token}` }, timeout: 120000 },
      );
      setDeployRailwaySteps(Array.isArray(res.data?.steps) ? res.data.steps : []);
      setDeployRailwayDashboard(typeof res.data?.dashboard_url === 'string' ? res.data.dashboard_url : null);
      addLog('Railway package validated. Follow the steps below.', 'success', 'export');
    } catch (e) {
      setDeployRailwayErr(formatDeployErr(e));
      addLog(`Railway: ${formatDeployErr(e)}`, 'error', 'export');
    } finally {
      setDeployRailwayBusy(false);
    }
  };

  const runOptimize = async () => {
    const code = files[activeFile]?.code ?? '';
    if (!code.trim()) { addLog('No file selected or empty file', 'warning', 'system'); return; }
    setToolsLoading(true);
    setToolsReport(null);
    try {
      const lang = activeFile.endsWith('.css') ? 'css' : 'javascript';
      const res = await axios.post(`${API}/ai/optimize`, { code, language: lang }, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
      setToolsReport({ type: 'optimize', data: res.data });
      addLog('Optimize completed', 'info', 'system');
    } catch (e) {
      addLog(`Optimize failed: ${e.response?.data?.detail || e.message}`, 'error', 'system');
      setToolsReport({ type: 'optimize', data: { error: e.response?.data?.detail || e.message } });
    } finally {
      setToolsLoading(false);
    }
  };

  const runExplainError = async () => {
    const code = files[activeFile]?.code ?? '';
    const err = lastError || 'Syntax or runtime error';
    if (!code.trim()) { addLog('No file selected or empty file', 'warning', 'system'); return; }
    setToolsLoading(true);
    setToolsReport(null);
    try {
      const res = await axios.post(`${API}/ai/explain-error`, { error: err, code }, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
      setToolsReport({ type: 'explain', data: res.data });
      addLog('Explain error completed', 'info', 'system');
    } catch (e) {
      addLog(`Explain error failed: ${e.response?.data?.detail || e.message}`, 'error', 'system');
      setToolsReport({ type: 'explain', data: { error: e.response?.data?.detail || e.message } });
    } finally {
      setToolsLoading(false);
    }
  };

  const runAnalyze = async () => {
    const code = files[activeFile]?.code ?? '';
    if (!code.trim()) { addLog('No file selected or empty file', 'warning', 'system'); return; }
    setToolsLoading(true);
    setToolsReport(null);
    try {
      const res = await axios.post(`${API}/ai/analyze`, { content: code, task: 'analyze' }, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
      setToolsReport({ type: 'analyze', data: res.data });
      addLog('Analyze completed', 'info', 'system');
    } catch (e) {
      addLog(`Analyze failed: ${e.response?.data?.detail || e.message}`, 'error', 'system');
      setToolsReport({ type: 'analyze', data: { error: e.response?.data?.detail || e.message } });
    } finally {
      setToolsLoading(false);
    }
  };

  const runFilesAnalyze = async () => {
    const code = files[activeFile]?.code ?? '';
    if (!code.trim()) { addLog('No file selected or empty file', 'warning', 'system'); return; }
    setToolsLoading(true);
    setToolsReport(null);
    try {
      const formData = new FormData();
      formData.append('file', new Blob([code], { type: 'text/plain' }), (activeFile || 'file.txt').replace('/', ''));
      formData.append('analysis_type', 'code');
      const res = await axios.post(`${API}/files/analyze`, formData, { headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), 'Content-Type': 'multipart/form-data' } });
      setToolsReport({ type: 'files', data: res.data });
      addLog('Files analyze completed', 'info', 'system');
    } catch (e) {
      addLog(`Files analyze failed: ${e.response?.data?.detail || e.message}`, 'error', 'system');
      setToolsReport({ type: 'files', data: { error: e.response?.data?.detail || e.message } });
    } finally {
      setToolsLoading(false);
    }
  };

  const runDesignFromUrl = async () => {
    const url = window.prompt('Enter image URL to design from (must be an image):', 'https://example.com/image.png');
    if (!url?.trim()) return;
    setToolsLoading(true);
    setToolsReport(null);
    try {
      const formData = new FormData();
      formData.append('url', url.trim());
      const res = await axios.post(`${API}/ai/design-from-url`, formData, { headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) }, timeout: 60000 });
      setToolsReport({ type: 'design', data: res.data });
      if (res.data?.code) {
        setFiles(prev => ({ ...prev, '/App.js': { code: res.data.code } }));
        setActiveFile('/App.js');
        addLog('Design from URL applied to App.js', 'success', 'system');
      } else {
        addLog('Design from URL completed', 'info', 'system');
      }
    } catch (e) {
      addLog(`Design from URL failed: ${e.response?.data?.detail || e.message}`, 'error', 'system');
      setToolsReport({ type: 'design', data: { error: e.response?.data?.detail || e.message } });
    } finally {
      setToolsLoading(false);
    }
  };

  const handleAutoFix = async () => {
    const mainCode = files[activeFile]?.code || files['/App.js']?.code;
    if (!mainCode || isBuilding) return;
    setIsBuilding(true);
    setRightSidebarOpen(true);
    setActivePanel('preview');
    setMessages(prev => [...prev, { role: 'assistant', content: 'Auto-fixing errors...', isBuilding: true }]);
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const fileContext = Object.entries(files).map(([fp, f]) => `--- ${fp} ---\n${f.code || ''}`).join('\n\n');
      const res = await axios.post(`${API}/ai/chat`, {
        message: `Fix any syntax or runtime errors in these React files. If multiple files, use \`\`\`jsx:filename.js format.\n\n${fileContext}`,
        session_id: sessionId,
        model: selectedModel
      }, { headers, timeout: 60000 });
      const fixedFiles = parseMultiFileOutput(res.data.response || '');
      const hasCode = Object.values(fixedFiles).some(f => f.code && (f.code.includes('import') || f.code.includes('function') || f.code.includes('const')));
      if (hasCode) {
        setFiles(prev => ({ ...prev, ...fixedFiles }));
        setLastError(null);
        addLog('Auto-fix applied', 'success', 'system');
      }
      setMessages(prev => prev.map((msg, i) => i === prev.length - 1 ? { role: 'assistant', content: 'Done. Check the preview.', hasCode: true } : msg));
    } catch (e) {
      setMessages(prev => prev.map((msg, i) => i === prev.length - 1 ? { role: 'assistant', content: `Fix failed: ${e.message}`, error: true } : msg));
    } finally {
      setIsBuilding(false);
    }
  };

  const copyCode = () => {
    navigator.clipboard.writeText(files[activeFile].code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleCodeChange = (value) => {
    setFiles(prev => ({
      ...prev,
      [activeFile]: { code: value }
    }));
  };

  const runCommand = (cmd) => {
    setCommandPaletteOpen(false);
    if (cmd === 'deploy') { handleExportDeploy(); setShowDeployModal(true); }
    else if (cmd === 'export') downloadCode();
    else if (cmd === 'zip') handleExportZip();
    else if (cmd === 'github') handleExportGitHub();
    else if (cmd === 'autofix' && lastError) handleAutoFix();
    else if (cmd === 'tokens') navigate('/app/tokens');
    else if (cmd === 'settings') navigate('/app/settings');
    else if (cmd === 'newAgent') navigate('/app', { state: { newAgent: Date.now() } });
    else if (cmd === 'terminal') { setActivePanel('console'); setRightSidebarOpen(true); }
    else if (cmd === 'maximizeChat') setChatMaximized(prev => !prev);
    else if (cmd === 'searchFiles') setFileSearchOpen(prev => !prev);
    else if (cmd === 'openBrowser') window.open('/app/workspace', '_blank');
    else if (cmd === 'shortcuts') navigate('/app/shortcuts');
    else if (cmd === 'templates') navigate('/app/templates');
    else if (cmd === 'prompts') navigate('/app/prompts');
    else if (cmd === 'payments') navigate('/app/payments-wizard');
  };


  return (
    <div className="h-full min-h-0 flex flex-col overflow-hidden font-sans text-[13px] antialiased" style={{ background: 'var(--theme-bg, #111113)', color: 'white' }}>

      {/* ── Command Palette (Ctrl+K) ── */}
      {commandPaletteOpen && (
        <div className="fixed inset-0 z-[200] flex items-start justify-center pt-[15vh]" style={{ background: 'rgba(0,0,0,0.75)' }} onClick={() => setCommandPaletteOpen(false)}>
          <div className="w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden border" style={{ background: 'var(--theme-surface, #1C1C1E)', borderColor: 'var(--theme-border, rgba(255,255,255,0.1))' }} onClick={e => e.stopPropagation()}>
            <div className="px-4 py-2.5 border-b text-xs" style={{ borderColor: 'var(--theme-border, rgba(255,255,255,0.08))', color: 'var(--theme-muted, #71717a)' }}>Command palette</div>
            <div className="max-h-80 overflow-y-auto py-1">
              {[
                { id: 'newAgent', label: 'New chat (Ctrl+Shift+L)', icon: Plus },
                { id: 'searchFiles', label: 'Open file (Ctrl+P)', icon: Search },
                { id: 'terminal', label: 'Show Console', icon: Terminal },
                { id: 'deploy', label: 'Deploy (ZIP → Vercel/Netlify)', icon: ExternalLink },
                { id: 'export', label: 'Download code', icon: Download },
                { id: 'github', label: 'Push to GitHub', icon: Github },
                ...(lastError ? [{ id: 'autofix', label: 'Auto-fix errors', icon: RefreshCw }] : []),
                { id: 'tokens', label: 'Token Center', icon: Zap },
                { id: 'settings', label: 'Settings', icon: Settings },
              ].map(({ id, label, icon: Icon }) => (
                <button key={id} onClick={() => runCommand(id)} className="w-full flex items-center gap-3 px-4 py-3 text-left transition hover:bg-white/5">
                  <Icon className="w-4 h-4" style={{ color: 'var(--theme-muted, #71717a)' }} />
                  <span style={{ color: 'var(--theme-text, #e4e4e7)' }}>{label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── File Search (Ctrl+P) ── */}
      {fileSearchOpen && (
        <div className="fixed inset-0 z-[200] flex items-start justify-center pt-[20vh]" style={{ background: 'rgba(0,0,0,0.75)' }} onClick={() => setFileSearchOpen(false)}>
          <div className="w-full max-w-md rounded-2xl shadow-2xl overflow-hidden border" style={{ background: 'var(--theme-surface, #1C1C1E)', borderColor: 'var(--theme-border, rgba(255,255,255,0.1))' }} onClick={e => e.stopPropagation()}>
            <div className="px-4 py-2.5 border-b text-xs" style={{ borderColor: 'var(--theme-border, rgba(255,255,255,0.08))', color: 'var(--theme-muted, #71717a)' }}>Open file</div>
            <div className="max-h-64 overflow-y-auto py-1">
              {Object.keys(files).sort().map((filename) => (
                <button key={filename} onClick={() => { setActiveFile(filename); setActivePanel('code'); setFileSearchOpen(false); }} className="w-full flex items-center gap-2.5 px-4 py-2.5 text-left transition hover:bg-white/5">
                  <FileCode className="w-4 h-4" style={{ color: '#eab308' }} />
                  <span style={{ color: 'var(--theme-text, #d4d4d8)' }}>{filename.replace(/^\//, '')}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Header ── */}
      <header className="h-12 flex items-center px-4 gap-3 shrink-0 border-b" style={{ background: 'var(--theme-surface, #18181B)', borderColor: 'var(--theme-border, rgba(255,255,255,0.08))' }}>
        <button onClick={() => navigate('/app')} className="p-1.5 rounded-lg transition hover:bg-white/10" style={{ color: 'var(--theme-muted, #71717a)' }} title="Back">
          <ArrowLeft className="w-4 h-4" />
        </button>
        <Logo variant="mark" height={22} href="/app" className="shrink-0" />
        <div className="h-4 w-px shrink-0" style={{ background: 'rgba(255,255,255,0.1)' }} />
        <span className="text-sm truncate max-w-xs" style={{ color: 'var(--theme-muted, #a1a1aa)' }}>
          {messages.find(m => m.role === 'user')?.content?.toString().slice(0, 55) || 'New project'}
        </span>
        {isBuilding && (
          <div className="flex items-center gap-2 ml-1">
            <div className="w-1.5 h-1.5 rounded-full bg-orange-400 animate-pulse" />
            <span className="text-xs">{currentPhase || 'Building'}... {Math.round(buildProgress)}%</span>
          </div>
        )}
        {devMode && qualityGateResult && !isBuilding && (
          <div className="flex items-center gap-1.5 ml-1 text-xs" style={{ color: qualityGateResult.score >= 70 ? '#86efac' : '#fbbf24' }}>
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>{qualityGateResult.score}%</span>
          </div>
        )}
        <div className="ml-auto flex items-center gap-2">
          <div className="flex items-center gap-1.5 text-[10px] shrink-0" style={{ color: 'var(--theme-muted)' }} title={apiHealth === 'ok' ? 'API reachable (GET /api/health)' : apiHealth === 'down' ? 'API unreachable' : 'Checking API…'}>
            <span className="w-2 h-2 rounded-full shrink-0" style={{ background: apiHealth === 'ok' ? '#4ade80' : apiHealth === 'down' ? '#f87171' : '#71717a' }} />
            <span className="hidden sm:inline font-mono">API</span>
          </div>
          {token && jobsChip.active > 0 && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full font-medium shrink-0" style={{ background: 'rgba(251,146,60,0.15)', color: '#fb923c' }} title="Jobs running or queued (GET /api/jobs)">
              {jobsChip.active} job{jobsChip.active !== 1 ? 's' : ''}
            </span>
          )}
          {lastError && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full max-w-[140px] truncate shrink-0" style={{ background: 'rgba(248,113,113,0.15)', color: '#fca5a5' }} title={lastError}>
              Error
            </span>
          )}
          <button
            type="button"
            onClick={toggleWorkspaceTheme}
            className="p-1.5 rounded-lg transition hover:bg-white/10 shrink-0"
            style={{ color: 'var(--theme-muted, #71717a)' }}
            title={workspaceTheme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
            aria-label={workspaceTheme === 'dark' ? 'Light theme' : 'Dark theme'}
          >
            {workspaceTheme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
          <button
            onClick={resetLayout}
            className="p-1.5 rounded-lg transition hover:bg-white/10"
            style={{ color: 'var(--theme-muted, #71717a)' }}
            title="Reset layout (show Explorer, Preview panel, default view)"
            aria-label="Reset layout"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
          {/* Simple / Code toggle */}
          <button
            onClick={toggleDevMode}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition border"
            style={{
              background: devMode ? 'rgba(255,255,255,0.1)' : 'transparent',
              color: devMode ? 'var(--theme-text, #e4e4e7)' : 'var(--theme-muted, #71717a)',
              borderColor: 'var(--theme-border, rgba(255,255,255,0.1))',
            }}
            title={devMode ? 'Switch to Guided — fewer technical panels' : 'Switch to Pro — database, docs, analytics, agents, passes, sandbox logs'}
          >
            <FileCode className="w-3.5 h-3.5" />
            {devMode ? 'Pro' : 'Guided'}
          </button>
          <button
            onClick={() => setCommandPaletteOpen(true)}
            className="p-1.5 rounded-lg transition hover:bg-white/10"
            style={{ color: 'var(--theme-muted, #71717a)' }}
            title="Command palette (Ctrl+K)"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* ── Token low banner ── */}
      {user && user.token_balance === 0 && (
        <div className="shrink-0 px-4 py-2 flex items-center justify-between" style={{ background: 'var(--theme-surface2)', borderBottom: '1px solid var(--theme-border)' }}>
          <span className="text-sm" style={{ color: 'var(--theme-accent)' }}>Out of tokens — get more to keep building.</span>
          <button onClick={() => navigate('/app/tokens')} className="text-sm font-medium underline" style={{ color: 'var(--theme-accent)' }}>Buy tokens</button>
        </div>
      )}

      {/* ── Main 3-panel layout ── */}
      <div className="flex-1 flex overflow-hidden">

        {/* ── Left: File Explorer ── */}
        {leftSidebarOpen ? (
          <div className="w-52 flex flex-col shrink-0 border-r" style={{ background: 'var(--theme-surface, #18181B)', borderColor: 'var(--theme-border, rgba(255,255,255,0.07))' }}>
            <input ref={folderInputRef} type="file" webkitdirectory="" multiple onChange={handleFolderOpen} className="hidden" />
            <input ref={zipInputRef} type="file" accept=".zip" onChange={handleZipUpload} className="hidden" />
            {/* Explorer header */}
            <div className="flex items-center justify-between px-3 py-2 border-b" style={{ borderColor: 'var(--theme-border, rgba(255,255,255,0.07))' }}>
              <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: 'var(--theme-muted, #52525b)' }}>Explorer</span>
              <div className="flex items-center gap-0.5">
                {projectIdFromUrl && token && (
                  <button
                    type="button"
                    onClick={reloadWorkspaceFromServer}
                    className="p-1 rounded transition hover:bg-white/10"
                    style={{ color: 'var(--theme-muted, #52525b)' }}
                    title="Reload file tree from server workspace (GET /projects/{id}/workspace/files)"
                  >
                    <RefreshCw className="w-3 h-3" />
                  </button>
                )}
                {devMode && (
                  <>
                    <button onClick={() => zipInputRef.current?.click()} className="p-1 rounded transition hover:bg-white/10" style={{ color: 'var(--theme-muted, #52525b)' }} title="Upload ZIP (bring your code)"><Upload className="w-3 h-3" /></button>
                    <button onClick={addNewFileToProject} className="p-1 rounded transition hover:bg-white/10" style={{ color: 'var(--theme-muted, #52525b)' }} title="New file"><Plus className="w-3 h-3" /></button>
                  </>
                )}
                <button onClick={() => setLeftSidebarOpen(false)} className="p-1 rounded transition hover:bg-white/10" style={{ color: 'var(--theme-muted, #52525b)' }} title="Collapse sidebar"><PanelLeftClose className="w-3 h-3" /></button>
              </div>
            </div>
            {/* Project name */}
            <div className="px-3 py-2 border-b" style={{ borderColor: 'var(--theme-border, rgba(255,255,255,0.05))' }}>
              <span className="text-xs truncate block" style={{ color: 'var(--theme-muted, #3f3f46)' }}>
                {messages.find(m => m.role === 'user')?.content?.toString().slice(0, 30) || 'project'}
              </span>
            </div>
            {/* File list — Manus-style nested tree (src/, public/, server/, shared/, etc.) */}
            <div className="flex-1 overflow-y-auto py-1">
              {(() => {
                // Build nested tree from all file paths (any depth)
                const tree = {};
                const addPath = (path) => {
                  const clean = path.replace(/^\//, '');
                  const parts = clean.split('/').filter(Boolean);
                  let current = tree;
                  for (let i = 0; i < parts.length; i++) {
                    const seg = parts[i];
                    const isLast = i === parts.length - 1;
                    if (isLast) {
                      current[seg] = { type: 'file', path: path.startsWith('/') ? path : `/${path}` };
                    } else {
                      if (!current[seg] || current[seg].type !== 'folder') {
                        current[seg] = { type: 'folder', pathPrefix: parts.slice(0, i + 1).join('/'), children: {} };
                      }
                      current = current[seg].children;
                    }
                  }
                };
                Object.keys(files).sort().forEach(addPath);

                const getIcon = (name) => {
                  const ext = (name || '').split('.').pop();
                  const color = ext === 'jsx' || ext === 'js' || ext === 'tsx' || ext === 'ts' ? '#eab308'
                    : ext === 'css' ? '#ec4899' : ext === 'html' ? 'var(--theme-accent)'
                    : ext === 'json' ? '#a78bfa' : ext === 'py' ? '#60a5fa' : ext === 'md' ? '#94a3b8' : ext === 'yml' || ext === 'yaml' ? '#64748b' : 'var(--theme-muted)';
                  return <FileCode className="w-3 h-3 shrink-0" style={{ color }} />;
                };

                const renderNode = (key, node, depth) => {
                  const indent = 12 + depth * 14;
                  if (node.type === 'file') {
                    const path = node.path;
                    const name = key;
                    const isActive = activeFile === path;
                    return (
                      <div key={path} className="group flex items-center">
                        <button
                          onClick={() => { setActiveFile(path); setActivePanel('code'); }}
                          className="flex-1 flex items-center gap-1.5 py-1 text-left text-xs transition hover:bg-white/5 min-w-0"
                          style={{ paddingLeft: `${indent}px`, background: isActive ? 'rgba(255,255,255,0.09)' : 'transparent', color: isActive ? 'var(--theme-text)' : 'var(--theme-muted)' }}
                        >
                          {getIcon(name)}
                          <span className="truncate">{name}</span>
                        </button>
                        {devMode && (
                          <button onClick={(e) => { e.stopPropagation(); deleteFileFromProject(path); }} className="opacity-0 group-hover:opacity-100 p-1 shrink-0" style={{ color: 'var(--theme-muted)' }} title="Delete"><X className="w-3 h-3" /></button>
                        )}
                      </div>
                    );
                  }
                  // folder
                  const pathPrefix = node.pathPrefix || key;
                  const folderKey = `folder_${pathPrefix}`;
                  const isOpen = expandedFolders[folderKey] !== false;
                  const childKeys = Object.keys(node.children || {}).sort();
                  const count = childKeys.length;
                  return (
                    <div key={folderKey}>
                      <button
                        onClick={() => setExpandedFolders(prev => ({ ...prev, [folderKey]: !isOpen }))}
                        className="w-full flex items-center gap-1.5 py-1 text-xs hover:bg-white/5 transition min-w-0"
                        style={{ paddingLeft: `${indent}px`, color: 'var(--theme-muted)' }}
                      >
                        {isOpen ? <ChevronDown className="w-3 h-3 shrink-0" /> : <ChevronRight className="w-3 h-3 shrink-0" />}
                        <Folder className="w-3 h-3 shrink-0" style={{ color: '#60a5fa' }} />
                        <span className="font-medium truncate">{key}</span>
                        {count > 0 && <span className="ml-auto text-[10px] opacity-50 shrink-0">{count}</span>}
                      </button>
                      {isOpen && childKeys.map(childKey => renderNode(childKey, node.children[childKey], depth + 1))}
                    </div>
                  );
                };

                const rootKeys = Object.keys(tree).sort();
                if (rootKeys.length === 0) {
                  return isBuilding ? (
                    <div className="px-3 py-4 space-y-2">
                      <div className="text-[10px] uppercase tracking-wider mb-2 font-semibold" style={{ color: 'var(--theme-muted)' }}>Generating files...</div>
                      {['src/', 'components/', 'api/', 'styles/'].map((f, i) => (
                        <div key={f} className="flex items-center gap-2 py-1 animate-pulse" style={{ animationDelay: `${i * 150}ms` }}>
                          <Folder className="w-3 h-3 shrink-0" style={{ color: '#60a5fa', opacity: 0.5 }} />
                          <span className="text-xs" style={{ color: 'var(--theme-muted)', opacity: 0.5 }}>{f}</span>
                        </div>
                      ))}
                      {['App.tsx', 'server.ts', 'schema.sql'].map((f, i) => (
                        <div key={f} className="flex items-center gap-2 py-1 pl-3 animate-pulse" style={{ animationDelay: `${(i + 4) * 150}ms` }}>
                          <FileCode className="w-3 h-3 shrink-0" style={{ color: '#4ade80', opacity: 0.4 }} />
                          <span className="text-xs" style={{ color: 'var(--theme-muted)', opacity: 0.4 }}>{f}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="px-3 py-4 text-center text-xs" style={{ color: 'var(--theme-muted)' }}>
                      Build something to see files
                    </div>
                  );
                }
                return rootKeys.map(key => renderNode(key, tree[key], 0));
              })()}
            </div>
            {/* Versions */}
            {versions.length > 0 && (
              <div className="border-t px-3 py-2" style={{ borderColor: 'var(--theme-border, rgba(255,255,255,0.07))' }}>
                <div className="text-[10px] font-semibold uppercase tracking-wider mb-1.5" style={{ color: 'var(--theme-muted, #52525b)' }}>History</div>
                {versions.slice(0, 4).map((v, i) => (
                  <button key={v.id} onClick={() => restoreVersion(v)} className="w-full flex items-center gap-2 py-1 text-left text-xs transition hover:bg-white/5 rounded px-1" style={{ color: currentVersion === v.id ? 'var(--theme-text, #e4e4e7)' : 'var(--theme-muted, #71717a)' }}>
                    <History className="w-3 h-3 shrink-0" />
                    <span className="truncate">v{versions.length - i} — {v.time}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div
            onClick={() => setLeftSidebarOpen(true)}
            className="flex flex-col items-center pt-3 shrink-0 border-r cursor-pointer transition hover:bg-white/5"
            style={{ width: 28, background: 'var(--theme-surface, #18181B)', borderColor: 'var(--theme-border, rgba(255,255,255,0.07))', color: 'var(--theme-muted, #52525b)' }}
            title="Open explorer"
          >
            <PanelRightOpen className="w-3.5 h-3.5" />
          </div>
        )}

        {/* ── Center: Chat / Build Steps ── */}
        <div className="flex-1 flex flex-col min-w-0" style={{ background: 'var(--theme-bg, #111113)' }}>

          {/* ── Manus-style task header ── */}
          {(isBuilding || messages.length > 0) && (
            <div className="shrink-0 px-4 py-2.5 border-b flex items-center gap-3" style={{ borderColor: 'var(--theme-border, rgba(255,255,255,0.08))', background: 'var(--theme-surface, #18181B)' }}>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-medium truncate" style={{ color: 'var(--theme-text)' }}>
                  {messages.find(m => m.role === 'user')?.content?.toString().slice(0, 60) || 'New task'}
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  {isBuilding ? (
                    <>
                      <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: 'var(--theme-accent)' }} />
                      <span className="text-[11px]" style={{ color: 'var(--theme-muted)' }}>{currentPhase || 'Building'}... {Math.round(buildProgress)}%</span>
                    </>
                  ) : versions.length > 0 ? (
                    <>
                      <div className="w-1.5 h-1.5 rounded-full" style={{ background: '#4ade80' }} />
                      <span className="text-[11px]" style={{ color: 'var(--theme-muted)' }}>Complete · {Object.keys(files).length} files · v{versions.length}</span>
                    </>
                  ) : null}
                </div>
              </div>
              {/* Progress bar */}
              {(isBuilding || buildProgress > 0) && (
                <div className="w-20 h-1 rounded-full overflow-hidden shrink-0" style={{ background: 'var(--theme-input)' }}>
                  <div className="h-full rounded-full transition-all duration-700" style={{ width: `${buildProgress}%`, background: buildProgress === 100 ? '#4ade80' : 'var(--theme-accent)' }} />
                </div>
              )}
              {/* Mode badge */}
              <div className="text-[10px] px-2 py-0.5 rounded-full font-medium shrink-0" style={{ background: 'rgba(255,255,255,0.07)', color: 'var(--theme-muted)' }}>
                {devMode ? '⚙ Pro' : '✦ Guided'}
              </div>
            </div>
          )}

          {/* Messages area */}
          <div className="flex-1 overflow-y-auto px-5 py-6 space-y-4 min-h-0">
            {messages.length === 0 && !isBuilding && (
              <div
                className={`flex flex-col items-center justify-center gap-4 ${projectIdFromUrl ? 'py-8' : 'h-full'}`}
                style={{ color: 'var(--theme-muted, #3f3f46)' }}
              >
                <Sparkles className="w-10 h-10" style={{ color: 'var(--theme-input, #27272a)' }} />
                <p className="text-sm">Describe what you want to build...</p>
              </div>
            )}

            {/* Server-sourced build timeline (typed events from orchestration) */}
            {projectIdFromUrl && token && (
              <div
                className="rounded-2xl border overflow-hidden"
                style={{ background: 'var(--theme-surface, #1C1C1E)', borderColor: 'var(--theme-border, rgba(255,255,255,0.08))' }}
              >
                <div className="flex items-center gap-2 px-3 py-2 border-b" style={{ borderColor: 'var(--theme-border, rgba(255,255,255,0.06))', background: 'rgba(0,0,0,0.15)' }}>
                  <Activity className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--theme-accent)' }} />
                  <span className="text-xs font-semibold" style={{ color: 'var(--theme-text)' }}>{devMode ? 'Orchestration timeline' : 'Build activity'}</span>
                  <span className="text-[10px] ml-auto font-mono" style={{ color: 'var(--theme-muted)' }}>{devMode ? 'live' : 'summary'}</span>
                </div>
                {devMode ? (
                  <div className="max-h-56 overflow-y-auto px-2 py-2 space-y-1">
                    {buildEventsErr && (
                      <p className="text-xs px-2 py-1" style={{ color: '#f87171' }}>{buildEventsErr}</p>
                    )}
                    {!buildEventsErr && buildTimelineEvents.length === 0 && (
                      <p className="text-xs px-2 py-2" style={{ color: 'var(--theme-muted)' }}>
                        No server events yet. They appear here when this project runs a build.
                      </p>
                    )}
                    {buildTimelineEvents.slice(-40).map((ev) => {
                      const { Icon, color, title } = getBuildEventPresentation(ev);
                      const sub =
                        ev.message
                        || (ev.agent ? `${ev.agent}` : '')
                        || (ev.phase != null ? `Phase ${Number(ev.phase) + 1}` : '')
                        || (ev.count != null ? `${ev.count} checkpoint(s)` : '');
                      const timeStr = ev.ts
                        ? new Date(ev.ts).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' })
                        : '';
                      return (
                        <div
                          key={`${ev.id}-${ev.ts}-${ev.type}`}
                          className="workspace-orchestration-event-card flex items-start gap-2 rounded-xl px-2.5 py-2 text-xs border"
                          style={{ background: 'rgba(255,255,255,0.03)', borderColor: 'var(--theme-border, rgba(255,255,255,0.06))', boxShadow: '0 1px 2px rgba(0,0,0,0.2)' }}
                        >
                          <div className="w-6 h-6 rounded-md flex items-center justify-center shrink-0 mt-0.5" style={{ background: 'rgba(255,255,255,0.06)' }}>
                            <Icon className="w-3.5 h-3.5" style={{ color }} />
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="font-medium" style={{ color: 'var(--theme-text)' }}>
                              {title}
                              {ev.type === 'phase_started' && ev.agents?.length ? ` · ${ev.agents.join(', ')}` : ''}
                              {ev.type === 'agent_completed' && ev.tokens != null ? ` · ${Number(ev.tokens).toLocaleString()} tok` : ''}
                            </div>
                            {sub && <div className="truncate opacity-70" style={{ color: 'var(--theme-muted)' }}>{sub}</div>}
                          </div>
                          {timeStr && (
                            <span className="shrink-0 text-[10px] font-mono mt-0.5" style={{ color: 'var(--theme-muted)' }}>{timeStr}</span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="px-3 py-3">
                    {buildEventsErr && (
                      <p className="text-xs" style={{ color: '#f87171' }}>{buildEventsErr}</p>
                    )}
                    {!buildEventsErr && buildTimelineEvents.length === 0 && (
                      <p className="text-xs" style={{ color: 'var(--theme-muted)' }}>Activity will show here when a build runs on this project.</p>
                    )}
                    {!buildEventsErr && buildTimelineEvents.length > 0 && (() => {
                      const ev = buildTimelineEvents[buildTimelineEvents.length - 1];
                      const { title } = getBuildEventPresentation(ev);
                      const sub = ev.message || (ev.agent ? String(ev.agent) : '') || '';
                      return (
                        <div>
                          <p className="text-sm font-medium" style={{ color: 'var(--theme-text)' }}>{title}</p>
                          {sub && <p className="text-xs mt-1 line-clamp-2" style={{ color: 'var(--theme-muted)' }}>{sub}</p>}
                          {buildTimelineEvents.length > 1 && (
                            <p className="text-[10px] mt-2" style={{ color: 'var(--theme-muted)' }}>{buildTimelineEvents.length} updates · use Pro for the full timeline</p>
                          )}
                        </div>
                      );
                    })()}
                  </div>
                )}
              </div>
            )}

            {/* ── Manus-style grouped execution cards ── */}
            {isBuilding && (
              <div className="space-y-2">
                {/* Main progress card */}
                <div className="rounded-2xl p-4 border" style={{ background: 'var(--theme-surface, #1C1C1E)', borderColor: 'var(--theme-border, rgba(255,255,255,0.08))' }}>
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: 'var(--theme-accent)' }} />
                    <span className="text-sm font-medium" style={{ color: 'var(--theme-text, #ffffff)' }}>{currentPhase || 'Building your app...'}</span>
                    <span className="ml-auto text-xs font-mono" style={{ color: 'var(--theme-muted, #52525b)' }}>{Math.round(buildProgress)}%</span>
                  </div>
                  {/* Segmented progress */}
                  {devMode ? (
                    <div className="flex gap-0.5 h-1 rounded-full overflow-hidden mb-3">
                      {['Planning', 'Architecture', 'Frontend', 'Backend', 'Validation', 'Deploy'].map((phase, i) => (
                        <div key={phase} className="flex-1 rounded-sm transition-all duration-500" style={{
                          background: buildProgress > (i * 17) ? (buildProgress === 100 ? '#4ade80' : 'var(--theme-accent)') : 'rgba(255,255,255,0.08)'
                        }} />
                      ))}
                    </div>
                  ) : (
                    <div className="flex gap-1 h-1.5 rounded-full overflow-hidden mb-3">
                      {['Plan', 'Build', 'Polish'].map((phase, i) => (
                        <div key={phase} className="flex-1 rounded-sm transition-all duration-500" style={{
                          background: buildProgress > (i * 34) ? (buildProgress === 100 ? '#4ade80' : 'var(--theme-accent)') : 'rgba(255,255,255,0.08)'
                        }} />
                      ))}
                    </div>
                  )}
                  {/* Agent steps — Pro only */}
                  {devMode ? (
                    <div className="space-y-1.5">
                      {agentsActivity.length > 0 ? agentsActivity.map((a, i) => (
                        <div key={i} className="flex items-center gap-2.5 text-xs py-1">
                          {a.status === 'done' ? (
                            <div className="w-4 h-4 rounded-full flex items-center justify-center shrink-0" style={{ background: 'rgba(74,222,128,0.15)' }}>
                              <Check className="w-2.5 h-2.5 text-green-400" />
                            </div>
                          ) : a.status === 'running' ? (
                            <div className="w-4 h-4 flex items-center justify-center shrink-0">
                              <Loader2 className="w-3.5 h-3.5 animate-spin" style={{ color: 'var(--theme-accent)' }} />
                            </div>
                          ) : (
                            <div className="w-4 h-4 rounded-full border shrink-0" style={{ borderColor: 'rgba(255,255,255,0.12)' }} />
                          )}
                          <span className="font-medium" style={{ color: a.status === 'done' ? '#86efac' : a.status === 'running' ? '#fb923c' : 'var(--theme-muted, #52525b)' }}>
                            {a.name}
                          </span>
                          <span className="truncate opacity-60" style={{ color: 'var(--theme-muted, #3f3f46)' }}>{a.phase}</span>
                          {a.status === 'done' && <span className="ml-auto shrink-0 text-[10px]" style={{ color: '#4ade80' }}>✓</span>}
                          {a.status === 'running' && <span className="ml-auto shrink-0 text-[10px] animate-pulse" style={{ color: 'var(--theme-accent)' }}>●</span>}
                        </div>
                      )) : (
                        ['Planner', 'Architect', 'Frontend', 'Styling', 'Logic', 'Validator', 'Optimizer'].map((name, i) => (
                          <div key={name} className="flex items-center gap-2.5 text-xs py-1">
                            <div className="w-4 h-4 flex items-center justify-center shrink-0">
                              {i === 0 ? <Loader2 className="w-3.5 h-3.5 animate-spin" style={{ color: 'var(--theme-accent)' }} /> : <div className="w-3 h-3 rounded-full border" style={{ borderColor: 'rgba(255,255,255,0.12)' }} />}
                            </div>
                            <span style={{ color: i === 0 ? '#fb923c' : 'var(--theme-muted, #52525b)' }}>{name}</span>
                            <span className="opacity-50 text-[10px]" style={{ color: 'var(--theme-muted)' }}>
                              {i === 0 ? 'Planning' : i <= 2 ? 'Generating' : i === 5 ? 'Validating' : 'Queued'}
                            </span>
                          </div>
                        ))
                      )}
                    </div>
                  ) : (
                    <p className="text-[11px] leading-relaxed" style={{ color: 'var(--theme-muted)' }}>
                      We&apos;re generating and checking your app. Turn on <span className="font-medium" style={{ color: 'var(--theme-text)' }}>Pro</span> in the header to see every agent step.
                    </p>
                  )}
                </div>

                {/* Step count badge */}
                {devMode && agentsActivity.length > 0 && (
                  <div className="flex items-center gap-2 px-2 text-xs" style={{ color: 'var(--theme-muted)' }}>
                    <span>{agentsActivity.filter(a => a.status === 'done').length}/{agentsActivity.length} steps complete</span>
                    <div className="flex-1 h-px" style={{ background: 'var(--theme-border)' }} />
                  </div>
                )}
              </div>
            )}

            {/* Chat messages */}
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {msg.role === 'assistant' && (
                  <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 mr-2 mt-0.5" style={{ background: 'var(--theme-input, #27272a)' }}>
                    <Sparkles className="w-3.5 h-3.5" style={{ color: 'var(--theme-muted, #a1a1aa)' }} />
                  </div>
                )}
                <div
                  className="max-w-[75%] rounded-2xl px-4 py-2.5 text-sm"
                  style={{
                    background: msg.role === 'user' ? 'var(--chat-user-bg)' : 'var(--chat-ai-bg)',
                    border: msg.role === 'user' ? 'none' : '1px solid var(--theme-border)',
                    color: msg.error ? 'var(--chat-error)' : 'var(--chat-text)',
                  }}
                >
                  {msg.isBuilding ? (
                    <div className="flex items-center gap-2">
                      <Loader2 className="w-3.5 h-3.5 animate-spin" style={{ color: 'var(--theme-accent)' }} />
                      <span style={{ color: 'var(--theme-muted, #a1a1aa)' }}>{formatMsgContent(msg.content)}</span>
                    </div>
                  ) : (
                    <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed">{formatMsgContent(msg.content)}</pre>
                  )}
                  {msg.hasCode && (
                    <div className="mt-2.5 flex items-center gap-2">
                      <button onClick={() => setActivePanel('preview')} className="flex items-center gap-1.5 text-xs px-3 py-1 rounded-lg transition hover:bg-white/10" style={{ background: 'var(--theme-surface2, rgba(255,255,255,0.08))', color: 'var(--theme-muted, #a1a1aa)' }}>
                        <Eye className="w-3 h-3" /> Preview
                      </button>
                      <button onClick={() => setActivePanel('code')} className="flex items-center gap-1.5 text-xs px-3 py-1 rounded-lg transition hover:bg-white/10" style={{ background: 'var(--theme-surface2, rgba(255,255,255,0.08))', color: 'var(--theme-muted, #a1a1aa)' }}>
                        <FileCode className="w-3 h-3" /> Code
                      </button>
                      <button onClick={downloadCode} className="flex items-center gap-1.5 text-xs px-3 py-1 rounded-lg transition hover:bg-white/10" style={{ background: 'var(--theme-surface2, rgba(255,255,255,0.08))', color: 'var(--theme-muted, #a1a1aa)' }}>
                        <Download className="w-3 h-3" /> Export
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Next suggestions */}
            {nextSuggestions.length > 0 && !isBuilding && (
              <div className="flex flex-wrap gap-2 pl-9">
                {nextSuggestions.slice(0, 4).map((s, i) => (
                  <button key={i} onClick={() => setInput(s)} className="text-xs px-3 py-1.5 rounded-full border transition hover:bg-white/5" style={{ borderColor: 'var(--theme-border, rgba(255,255,255,0.1))', color: 'var(--theme-muted, #71717a)' }}>
                    {s}
                  </button>
                ))}
              </div>
            )}

            <div ref={chatEndRef} />
          </div>

          {/* ── Input bar ── */}
          <div className="px-4 pb-4 shrink-0">
            {/* Attached files preview */}
            {attachedFiles.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-2">
                {attachedFiles.map((f, i) => (
                  <span key={i} className="flex items-center gap-1 text-xs px-2.5 py-1 rounded-full" style={{ background: 'var(--theme-surface2, #3f3f46)', color: 'var(--theme-text, #d4d4d8)' }}>
                    {f.type?.startsWith('image/') ? <Image className="w-3 h-3" /> : f.type?.startsWith('audio/') ? <Mic className="w-3 h-3" /> : <FileText className="w-3 h-3" />}
                    {f.name}
                    <button onClick={() => setAttachedFiles(p => p.filter((_, j) => j !== i))} style={{ color: 'var(--theme-muted, #71717a)' }}><X className="w-3 h-3" /></button>
                  </span>
                ))}
              </div>
            )}

            <div className="rounded-2xl border" style={{ background: 'var(--theme-surface, #1C1C1E)', borderColor: 'var(--theme-border, rgba(255,255,255,0.1))' }}>
              <form onSubmit={handleSubmit}>
                <textarea
                  ref={chatInputRef}
                  value={input}
                  onChange={(e) => { setInput(e.target.value); resizeChatInput(); }}
                  onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(e); } }}
                  placeholder={isBuilding ? 'Building your app...' : (versions.length > 0 ? 'Describe changes, fix bugs, add features...' : 'Describe what you want to build...')}
                  rows={1}
                  disabled={isBuilding}
                  className="w-full bg-transparent outline-none text-sm resize-none px-4 pt-3.5 pb-1 workspace-chat-input"
                  style={{ minHeight: 52, maxHeight: 140, color: 'var(--theme-text)', caretColor: 'var(--theme-text)' }}
                />
                <div className="flex items-center gap-2 px-3 pb-3">
                  <input ref={fileInputRef} type="file" multiple accept="image/*,.pdf,.txt,.md,.zip,audio/*,.js,.jsx,.ts,.tsx,.css,.html,.json,.py" onChange={handleFileSelect} className="hidden" />
                  <button type="button" onClick={() => fileInputRef.current?.click()} className="p-1.5 rounded-lg transition hover:bg-white/10" style={{ color: 'var(--theme-muted, #52525b)' }} title="Attach file">
                    <Paperclip className="w-4 h-4" />
                  </button>
                  <button
                    type="button"
                    onClick={isTranscribing ? undefined : (isRecording ? stopRecording : startRecording)}
                    disabled={isTranscribing}
                    className="p-1.5 rounded-lg transition hover:bg-white/10"
                    style={{ color: isRecording ? '#f87171' : 'var(--theme-muted, #52525b)' }}
                    title={isTranscribing ? 'Transcribing...' : (isRecording ? 'Stop voice' : 'Voice input (dictate or record → transcribe)')}
                  >
                    {isTranscribing ? <Loader2 className="w-4 h-4 animate-spin" /> : isRecording ? <MicOff className="w-4 h-4 animate-pulse" /> : <Mic className="w-4 h-4" />}
                  </button>
                  <div className="ml-auto flex items-center gap-2">
                    <select
                      value={buildMode}
                      onChange={(e) => setBuildMode(e.target.value)}
                      className="text-xs rounded-lg px-2.5 py-1.5 outline-none cursor-pointer"
                      style={{ background: 'var(--theme-surface2, #3f3f46)', color: 'var(--theme-text, #d4d4d8)', border: 'none' }}
                    >
                      <option value="agent">Auto</option>
                      <option value="quick">Quick</option>
                      <option value="plan">Plan</option>
                      <option value="swarm">Swarm</option>
                    </select>
                    <button
                      type="submit"
                      disabled={(!input.trim() && attachedFiles.length === 0) || isBuilding}
                      className="flex items-center gap-1.5 px-4 py-1.5 rounded-xl text-sm font-semibold transition disabled:opacity-40"
                      style={{ background: 'white', color: 'black' }}
                    >
                      {isBuilding
                        ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        : <Send className="w-3.5 h-3.5" />}
                      {isBuilding ? 'Building...' : versions.length > 0 ? 'Update' : 'Build'}
                    </button>
                  </div>
                </div>
              </form>
            </div>
          </div>
        </div>

        {/* ── Right: Preview + Code Editor (collapsible) ── */}
        {rightSidebarOpen ? (
        <div className="workspace-right-panel flex flex-col shrink-0 border-l" style={{ width: '46%', background: 'var(--theme-surface, #18181B)', borderColor: 'var(--theme-border, rgba(255,255,255,0.08))' }}>
          {/* Manus-style tab bar */}
          <div className="h-11 flex items-center px-2 border-b shrink-0 gap-0.5 overflow-x-auto" style={{ borderColor: 'var(--theme-border, rgba(255,255,255,0.08))', scrollbarWidth: 'none' }}>
            {workbenchTabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActivePanel(tab.id)}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition shrink-0"
                style={{
                  background: activePanel === tab.id ? 'rgba(255,255,255,0.1)' : 'transparent',
                  color: activePanel === tab.id ? 'var(--theme-text, #e4e4e7)' : 'var(--theme-muted, #52525b)',
                  borderBottom: activePanel === tab.id ? '1.5px solid var(--theme-accent, #3b82f6)' : '1.5px solid transparent',
                  borderRadius: activePanel === tab.id ? '8px 8px 0 0' : '8px',
                }}
              >
                <tab.icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            ))}
            <div className="ml-auto flex items-center gap-1">
              {activePanel === 'preview' && (
                <>
                  {devMode && (
                    <button onClick={() => setMobileView(v => !v)} className="p-1.5 rounded-lg transition hover:bg-white/10" style={{ color: 'var(--theme-muted, #52525b)' }} title={mobileView ? 'Desktop view' : 'Mobile view'}>
                      {mobileView ? <Monitor className="w-3.5 h-3.5" /> : <Smartphone className="w-3.5 h-3.5" />}
                    </button>
                  )}
                  <button onClick={() => { const c = { ...files }; setFiles({}); setTimeout(() => setFiles(c), 50); }} className="p-1.5 rounded-lg transition hover:bg-white/10" style={{ color: 'var(--theme-muted, #52525b)' }} title="Refresh preview">
                    <RefreshCw className="w-3.5 h-3.5" />
                  </button>
                </>
              )}
              {activePanel === 'code' && (
                <button onClick={copyCode} className="p-1.5 rounded-lg transition hover:bg-white/10" style={{ color: copied ? '#86efac' : 'var(--theme-muted, #52525b)' }} title="Copy">
                  {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              )}
              <button onClick={downloadCode} className="p-1.5 rounded-lg transition hover:bg-white/10" style={{ color: 'var(--theme-muted, #52525b)' }} title="Download">
                <Download className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={async () => {
                  try {
                    const shareUrl = `${window.location.origin}/share/${projectIdFromUrl || 'demo'}`;
                    await navigator.clipboard.writeText(shareUrl);
                    addLog('Share link copied to clipboard!', 'success', 'system');
                  } catch {
                    addLog('Could not copy share link', 'warning', 'system');
                  }
                }}
                className="p-1.5 rounded-lg transition hover:bg-white/10"
                style={{ color: 'var(--theme-muted, #52525b)' }}
                title="Copy share link"
              >
                <Share2 className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setShowDeployModal(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold ml-1 transition"
                style={{ background: 'rgba(255,255,255,0.1)', color: 'var(--theme-text, #e4e4e7)' }}
              >
                <Rocket className="w-3 h-3" />
                Deploy
              </button>
              <button
                onClick={() => setRightSidebarOpenPersisted(false)}
                className="p-1.5 rounded-lg transition hover:bg-white/10"
                style={{ color: 'var(--theme-muted, #52525b)' }}
                title="Hide panel (Preview / Code / Console)"
                aria-label="Hide right panel"
              >
                <PanelRightOpen className="w-3.5 h-3.5 rotate-180" />
              </button>
            </div>
          </div>

          {/* Panel content */}
          <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
            {/* Preview — always mounted so Sandpack never loses files on tab switch */}
            <div style={{ display: activePanel === 'preview' ? 'flex' : 'none', flexDirection: 'column', height: '100%' }}>
              {/* Show placeholder when no build yet */}
              {(currentVersion === null || filesReadyKey === 'default') && !isBuilding ? (
                <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--theme-bg)', color: 'var(--theme-muted)', flexDirection: 'column', gap: 12 }}>
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 9h6M9 12h6M9 15h4"/></svg>
                  <p style={{ fontSize: 13 }}>Build something to see the preview</p>
                </div>
              ) : (currentVersion === null || filesReadyKey === 'default') && isBuilding ? (
                /* ── BUILDING SKELETON — Manus-style live preview placeholder ── */
                <div style={{ flex: 1, background: 'var(--theme-bg)', padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div style={{ height: 48, borderRadius: 8, background: 'rgba(255,255,255,0.04)', animation: 'pulse 1.5s ease-in-out infinite' }} />
                  <div style={{ display: 'flex', gap: 12, flex: 1 }}>
                    <div style={{ width: 180, borderRadius: 8, background: 'rgba(255,255,255,0.03)', animation: 'pulse 1.5s ease-in-out infinite', animationDelay: '0.2s' }} />
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 10 }}>
                      <div style={{ height: 120, borderRadius: 8, background: 'rgba(255,255,255,0.04)', animation: 'pulse 1.5s ease-in-out infinite', animationDelay: '0.1s' }} />
                      <div style={{ height: 80, borderRadius: 8, background: 'rgba(255,255,255,0.03)', animation: 'pulse 1.5s ease-in-out infinite', animationDelay: '0.3s' }} />
                      <div style={{ height: 60, borderRadius: 8, background: 'rgba(255,255,255,0.02)', animation: 'pulse 1.5s ease-in-out infinite', animationDelay: '0.5s' }} />
                    </div>
                  </div>
                  <div style={{ textAlign: 'center', fontSize: 12, color: 'var(--theme-muted)', paddingTop: 8 }}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--theme-accent)', display: 'inline-block', animation: 'pulse 1s ease-in-out infinite' }} />
                      Building your app — preview loads when complete
                    </span>
                  </div>
                </div>
              ) : lastBuildKind === 'mobile' ? (
                /* ── MOBILE PREVIEW: Expo Snack iframe ── */
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: 'var(--theme-bg)' }}>
                  <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--theme-border)', display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#22c55e' }} />
                    <span style={{ fontSize: 11, color: 'var(--theme-muted)' }}>Mobile Preview — Expo Snack</span>
                    <a
                      href={`https://snack.expo.dev/?code=${encodeURIComponent(files['/App.tsx']?.code || files['/App.jsx']?.code || files['/App.js']?.code || '')}&platform=ios&supportedPlatforms=ios,android,web&name=CrucibAI+Build&description=Built+with+CrucibAI`}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--theme-accent)', textDecoration: 'underline' }}
                    >
                      Open in Expo Snack ↗
                    </a>
                  </div>
                  <iframe
                    src={`https://snack.expo.dev/embedded?code=${encodeURIComponent(files['/App.tsx']?.code || files['/App.jsx']?.code || files['/App.js']?.code || '')}&platform=ios&preview=true&theme=dark`}
                    style={{ flex: 1, border: 'none', width: '100%' }}
                    allow="accelerometer; camera; geolocation; gyroscope; microphone"
                    title="Mobile Preview"
                  />
                </div>
              ) : (
              <SandpackProvider
                key={filesReadyKey || 'default'}
                files={sandpackFiles}
                theme={document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark'}
                template="react"
                customSetup={{ dependencies: sandpackDeps }}
                options={{
                  externalResources: [
                    'https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css',
                    'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap',
                  ],
                  autoReload: true,
                  recompileMode: 'delayed',
                  recompileDelay: 500,
                }}
              >
                <SandpackErrorBoundary onError={(e) => { setLastError(e); addLog(`Preview error: ${e}`, 'error', 'preview'); }}>
                  <div style={{ flex: 1, minHeight: 320, display: 'flex', flexDirection: 'column', background: 'var(--theme-surface2)' }}>
                    <SandpackPreview
                      showOpenInCodeSandbox={false}
                      style={{
                        flex: 1,
                        minHeight: 300,
                        width: mobileView ? '390px' : '100%',
                        margin: mobileView ? '0 auto' : '0',
                      }}
                    />
                  </div>
                </SandpackErrorBoundary>
              </SandpackProvider>
              )}
            </div>

            {activePanel === 'code' && (
              <div className="flex flex-col h-full">
                {/* File tabs */}
                <div className="flex overflow-x-auto shrink-0 border-b" style={{ background: 'var(--theme-surface, #18181B)', borderColor: 'var(--theme-border, rgba(255,255,255,0.07))' }}>
                  {Object.keys(files).map(fp => (
                    <button
                      key={fp}
                      onClick={() => setActiveFile(fp)}
                      className="px-3 py-2 text-xs whitespace-nowrap shrink-0 border-r transition"
                      style={{
                        background: activeFile === fp ? 'var(--theme-bg, #111113)' : 'transparent',
                        color: activeFile === fp ? 'var(--theme-text, #e4e4e7)' : 'var(--theme-muted, #71717a)',
                        borderColor: 'var(--theme-border, rgba(255,255,255,0.06))',
                      }}
                    >
                      {fp.replace(/^\//, '')}
                    </button>
                  ))}
                </div>
                {/* Monaco editor */}
                <Editor
                  height="100%"
                  language={
                    activeFile.endsWith('.css') ? 'css'
                    : activeFile.endsWith('.html') ? 'html'
                    : activeFile.endsWith('.json') ? 'json'
                    : activeFile.endsWith('.py') ? 'python'
                    : activeFile.endsWith('.c') || activeFile.endsWith('.h') ? 'c'
                    : activeFile.endsWith('.cpp') ? 'cpp'
                    : 'javascript'
                  }
                  value={files[activeFile]?.code || ''}
                  onChange={handleCodeChange}
                  theme={workspaceTheme === 'light' ? 'vs' : 'vs-dark'}
                  options={{
                    minimap: { enabled: false },
                    fontSize: 13,
                    lineNumbers: 'on',
                    scrollBeyondLastLine: false,
                    wordWrap: 'on',
                    tabSize: 2,
                    padding: { top: 12 },
                    fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
                  }}
                />
              </div>
            )}

            {activePanel === 'console' && (
              <div className="flex flex-col h-full min-h-0">
                <div className="shrink-0 flex flex-wrap items-center gap-1.5 px-3 py-2 border-b" style={{ borderColor: 'var(--theme-border, rgba(255,255,255,0.07))' }}>
                  <span className="text-[10px] font-semibold uppercase tracking-wider mr-1" style={{ color: 'var(--theme-muted)' }}>Filter</span>
                  {[
                    { id: 'all', label: 'All' },
                    { id: 'error', label: 'Errors' },
                    { id: 'build', label: 'Build' },
                    { id: 'system', label: 'System' },
                  ].map((f) => (
                    <button
                      key={f.id}
                      type="button"
                      onClick={() => setConsoleFilter(f.id)}
                      className="text-[10px] px-2 py-0.5 rounded-md font-medium transition"
                      style={{
                        background: consoleFilter === f.id ? 'rgba(255,255,255,0.12)' : 'transparent',
                        color: consoleFilter === f.id ? 'var(--theme-text)' : 'var(--theme-muted)',
                        border: `1px solid ${consoleFilter === f.id ? 'var(--theme-border)' : 'transparent'}`,
                      }}
                    >
                      {f.label}
                    </button>
                  ))}
                </div>
                <div className="flex-1 min-h-0">
                  <ConsolePanel logs={filteredConsoleLogs} placeholder="Build logs appear here. Press Build to start." />
                </div>
              </div>
            )}
            {activePanel === 'history' && projectIdFromUrl && (
              <BuildHistoryPanel buildHistory={buildHistoryList} projectId={projectIdFromUrl} loading={buildHistoryLoading} />
            )}

            {/* ── Dashboard tab (Manus-style project ops) ── */}
            {activePanel === 'dashboard' && (
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {/* Project header */}
                <div className="rounded-xl p-4 border" style={{ background: 'var(--theme-surface2, #111)', borderColor: 'var(--theme-border, rgba(255,255,255,0.08))' }}>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--theme-muted)' }}>Project</div>
                      <div className="font-semibold text-sm" style={{ color: 'var(--theme-text)' }}>
                        {messages.find(m => m.role === 'user')?.content?.toString().slice(0, 40) || 'Untitled build'}
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium" style={{
                      background: versions.length > 0 ? 'rgba(74,222,128,0.12)' : 'rgba(255,255,255,0.06)',
                      color: versions.length > 0 ? '#86efac' : 'var(--theme-muted)'
                    }}>
                      <div className="w-1.5 h-1.5 rounded-full" style={{ background: versions.length > 0 ? '#86efac' : 'var(--theme-muted)' }} />
                      {versions.length > 0 ? 'Built' : 'Not built'}
                    </div>
                  </div>
                  <div className="mt-3 pt-3 border-t flex gap-4 text-xs" style={{ borderColor: 'var(--theme-border)' }}>
                    <div><span style={{ color: 'var(--theme-muted)' }}>Files</span><span className="ml-2 font-medium" style={{ color: 'var(--theme-text)' }}>{Object.keys(files).length}</span></div>
                    <div><span style={{ color: 'var(--theme-muted)' }}>Versions</span><span className="ml-2 font-medium" style={{ color: 'var(--theme-text)' }}>{versions.length}</span></div>
                    <div><span style={{ color: 'var(--theme-muted)' }}>Progress</span><span className="ml-2 font-medium" style={{ color: 'var(--theme-text)' }}>{Math.round(buildProgress)}%</span></div>
                  </div>
                </div>

                {/* Feature badges — Pro */}
                {devMode && versions.length > 0 && (
                  <div className="rounded-xl p-4 border" style={{ background: 'var(--theme-surface2)', borderColor: 'var(--theme-border)' }}>
                    <div className="text-xs font-semibold uppercase tracking-wider mb-2.5" style={{ color: 'var(--theme-muted)' }}>Features Detected</div>
                    <div className="flex flex-wrap gap-2">
                      {[
                        { label: 'Frontend', check: Object.keys(files).some(f => f.includes('App') || f.includes('.jsx') || f.includes('.tsx')) },
                        { label: 'Backend', check: Object.keys(files).some(f => f.includes('server') || f.includes('api') || f.includes('routes')) },
                        { label: 'Database', check: Object.keys(files).some(f => f.includes('schema') || f.includes('db') || f.includes('migration')) },
                        { label: 'Auth', check: Object.keys(files).some(f => f.includes('auth') || f.includes('login')) },
                        { label: 'TypeScript', check: Object.keys(files).some(f => f.endsWith('.ts') || f.endsWith('.tsx')) },
                        { label: 'Docker', check: Object.keys(files).some(f => f.includes('Dockerfile') || f.includes('docker-compose')) },
                        { label: 'CI/CD', check: Object.keys(files).some(f => f.includes('.github') || f.includes('deploy.yml')) },
                      ].filter(f => f.check).map(({ label }) => (
                        <span key={label} className="px-2 py-0.5 rounded-full text-xs font-medium" style={{ background: 'rgba(59,130,246,0.15)', color: '#93c5fd' }}>{label}</span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Quality score — Pro */}
                {devMode && qualityGateResult && (
                  <div className="rounded-xl p-4 border" style={{ background: 'var(--theme-surface2)', borderColor: 'var(--theme-border)' }}>
                    <div className="text-xs font-semibold uppercase tracking-wider mb-2.5" style={{ color: 'var(--theme-muted)' }}>Quality Score</div>
                    <div className="flex items-center gap-3">
                      <div className="text-3xl font-bold" style={{ color: qualityGateResult.score >= 70 ? '#86efac' : '#fbbf24' }}>{qualityGateResult.score}%</div>
                      <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: 'var(--theme-input)' }}>
                        <div className="h-full rounded-full transition-all duration-700" style={{ width: `${qualityGateResult.score}%`, background: qualityGateResult.score >= 70 ? '#4ade80' : '#f59e0b' }} />
                      </div>
                    </div>
                  </div>
                )}

                {/* Deploy actions */}
                <div className="rounded-xl p-4 border" style={{ background: 'var(--theme-surface2)', borderColor: 'var(--theme-border)' }}>
                  <div className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--theme-muted)' }}>Publish & Deploy</div>
                  {projectLiveUrl && (
                    <a
                      href={projectLiveUrl.startsWith('http') ? projectLiveUrl : `https://${projectLiveUrl}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold mb-2 transition hover:bg-white/5 border"
                      style={{ borderColor: 'rgba(74,222,128,0.35)', color: '#86efac' }}
                    >
                      <Globe className="w-3.5 h-3.5 shrink-0" /> Live site
                    </a>
                  )}
                  <div className="space-y-2">
                    <button onClick={downloadCode} disabled={Object.keys(files).length === 0} className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-xs font-medium transition hover:bg-white/5 border disabled:opacity-40" style={{ borderColor: 'var(--theme-border)', color: 'var(--theme-text)' }}>
                      <Download className="w-3.5 h-3.5" /> Download ZIP
                    </button>
                    <button onClick={() => setShowDeployModal(true)} disabled={Object.keys(files).length === 0} className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-xs font-semibold transition disabled:opacity-40" style={{ background: 'var(--theme-accent)', color: 'white' }}>
                      <Rocket className="w-3.5 h-3.5" /> Deploy App
                    </button>
                  </div>
                </div>

                {/* Version history */}
                {versions.length > 0 && (
                  <div className="rounded-xl p-4 border" style={{ background: 'var(--theme-surface2)', borderColor: 'var(--theme-border)' }}>
                    <div className="text-xs font-semibold uppercase tracking-wider mb-2.5" style={{ color: 'var(--theme-muted)' }}>Version History</div>
                    <div className="space-y-1.5">
                      {versions.slice(0, 5).map((v, i) => (
                        <button key={v.id} onClick={() => restoreVersion(v)} className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs transition hover:bg-white/5 text-left" style={{ color: currentVersion === v.id ? 'var(--theme-text)' : 'var(--theme-muted)' }}>
                          <History className="w-3 h-3 shrink-0" />
                          <span className="truncate">v{versions.length - i} — {v.prompt?.slice(0, 30) || 'Build'}</span>
                          <span className="ml-auto shrink-0 opacity-60">{v.time}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            <WorkspaceProPanels
              activePanel={activePanel}
              projectIdFromUrl={projectIdFromUrl}
              token={token}
              serverDbErr={serverDbErr}
              serverDbLoading={serverDbLoading}
              serverDbSnapshots={serverDbSnapshots}
              dbPanelMerge={dbPanelMerge}
              setFiles={setFiles}
              setActiveFile={setActiveFile}
              setActivePanel={setActivePanel}
              serverDocsErr={serverDocsErr}
              serverDocsLoading={serverDocsLoading}
              mergedDocFiles={mergedDocFiles}
              docsSelectedPath={docsSelectedPath}
              setDocsSelectedPath={setDocsSelectedPath}
              analyticsErr={analyticsErr}
              analyticsLoading={analyticsLoading}
              analyticsData={analyticsData}
              buildHistoryList={buildHistoryList}
              buildTimelineEvents={buildTimelineEvents}
              agentsActivity={agentsActivity}
              agentApiStatuses={agentApiStatuses}
              projectSandboxErr={projectSandboxErr}
              projectSandboxLoading={projectSandboxLoading}
              projectSandboxLogs={projectSandboxLogs}
              files={files}
              versions={versions}
              buildHistoryLoading={buildHistoryLoading}
              isBuilding={isBuilding}
              sandpackFiles={sandpackFiles}
              projectBuildProgress={projectBuildProgress}
              currentPhase={currentPhase}
            />
          </div>
        </div>
        ) : (
          <button
            onClick={() => setRightSidebarOpenPersisted(true)}
            className="flex flex-col items-center justify-center shrink-0 w-10 border-l transition hover:bg-white/5 self-stretch"
            style={{ background: 'var(--theme-surface, #18181B)', borderColor: 'var(--theme-border, rgba(255,255,255,0.08))', color: 'var(--theme-muted, #52525b)' }}
            title="Show Preview / Code / Console"
            aria-label="Show right panel"
          >
            <PanelRightOpen className="w-4 h-4" />
            <span className="text-[10px] mt-1">Panel</span>
          </button>
        )}
      </div>

      {/* ── Deploy modal ── */}
      {showDeployModal && (
        <div className="fixed inset-0 z-[300] flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.75)' }} onClick={() => setShowDeployModal(false)}>
          <div className="rounded-2xl shadow-2xl max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto p-6 border" style={{ background: 'var(--theme-surface, #1C1C1E)', borderColor: 'var(--theme-border, rgba(255,255,255,0.1))' }} onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-white mb-1">Deploy your app</h3>
            <p className="text-sm mb-4" style={{ color: 'var(--theme-muted, #71717a)' }}>Use your saved project for server packages and one-click deploy, or export from the editor.</p>

            {projectLiveUrl && (
              <a
                href={projectLiveUrl.startsWith('http') ? projectLiveUrl : `https://${projectLiveUrl}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-semibold mb-4 transition hover:opacity-90"
                style={{ background: 'rgba(74,222,128,0.15)', color: '#86efac', border: '1px solid rgba(74,222,128,0.35)' }}
              >
                <Globe className="w-4 h-4" /> Open live site
              </a>
            )}

            {projectIdFromUrl && token && (
              <div className="mb-4 space-y-2">
                <div className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: 'var(--theme-muted)' }}>This project (API)</div>
                <button
                  type="button"
                  onClick={downloadServerDeployZip}
                  disabled={deployZipBusy}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-medium transition hover:bg-white/5 border disabled:opacity-50"
                  style={{ borderColor: 'var(--theme-border, rgba(255,255,255,0.1))', color: 'var(--theme-text, #e4e4e7)' }}
                >
                  {deployZipBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                  Download deploy ZIP (server build)
                </button>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => oneClickDeployPlatform('vercel')}
                    disabled={!!deployOneClickBusy}
                    className="flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-semibold text-white hover:opacity-90 transition disabled:opacity-50"
                    style={{ background: '#000' }}
                  >
                    {deployOneClickBusy === 'vercel' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
                    Vercel
                  </button>
                  <button
                    type="button"
                    onClick={() => oneClickDeployPlatform('netlify')}
                    disabled={!!deployOneClickBusy}
                    className="flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-semibold text-white hover:opacity-90 transition disabled:opacity-50"
                    style={{ background: '#00AD9F' }}
                  >
                    {deployOneClickBusy === 'netlify' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
                    Netlify
                  </button>
                </div>
                <div className="pt-2 border-t space-y-2" style={{ borderColor: 'var(--theme-border, rgba(255,255,255,0.08))' }}>
                  <div className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: 'var(--theme-muted)' }}>Railway &amp; custom domain</div>
                  <p className="text-[11px] leading-snug" style={{ color: 'var(--theme-muted)' }}>
                    Save the hostname you will use with your host (DNS stays at your registrar). Optional: paste your Railway project URL for reference.
                  </p>
                  <input
                    type="text"
                    value={publishCustomDomain}
                    onChange={(e) => setPublishCustomDomain(e.target.value)}
                    placeholder="app.example.com"
                    autoComplete="off"
                    className="w-full px-3 py-2 rounded-lg text-sm border bg-transparent"
                    style={{ borderColor: 'var(--theme-border, rgba(255,255,255,0.12))', color: 'var(--theme-text)' }}
                  />
                  <input
                    type="url"
                    value={publishRailwayUrl}
                    onChange={(e) => setPublishRailwayUrl(e.target.value)}
                    placeholder="https://railway.app/project/…"
                    autoComplete="off"
                    className="w-full px-3 py-2 rounded-lg text-sm border bg-transparent"
                    style={{ borderColor: 'var(--theme-border, rgba(255,255,255,0.12))', color: 'var(--theme-text)' }}
                  />
                  <button
                    type="button"
                    onClick={savePublishSettings}
                    disabled={publishSaveBusy}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold transition hover:bg-white/5 border disabled:opacity-50"
                    style={{ borderColor: 'var(--theme-border)', color: 'var(--theme-text)' }}
                  >
                    {publishSaveBusy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
                    Save publish settings
                  </button>
                  <button
                    type="button"
                    onClick={prepareRailwayDeploy}
                    disabled={deployRailwayBusy}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold text-white transition disabled:opacity-50"
                    style={{ background: '#0B0D0E', border: '1px solid rgba(255,255,255,0.15)' }}
                  >
                    {deployRailwayBusy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Rocket className="w-3.5 h-3.5" />}
                    Validate for Railway (ZIP + CLI steps)
                  </button>
                  {deployRailwayErr && (
                    <div className="text-[11px] px-2 py-1.5 rounded-lg" style={{ background: 'rgba(248,113,113,0.12)', color: '#fca5a5' }}>{deployRailwayErr}</div>
                  )}
                  {deployRailwaySteps && deployRailwaySteps.length > 0 && (
                    <div className="rounded-lg p-3 border text-[11px] space-y-2" style={{ borderColor: 'var(--theme-border)', color: 'var(--theme-muted)' }}>
                      <div className="font-semibold uppercase tracking-wider text-[10px]" style={{ color: 'var(--theme-muted)' }}>Next steps</div>
                      <ol className="list-decimal pl-4 space-y-1">
                        {deployRailwaySteps.map((s, i) => (
                          <li key={i} style={{ color: 'var(--theme-text)' }}>{s}</li>
                        ))}
                      </ol>
                      <button
                        type="button"
                        onClick={() => window.open(deployRailwayDashboard || 'https://railway.app/new', '_blank', 'noopener,noreferrer')}
                        className="w-full mt-1 py-2 rounded-lg text-xs font-semibold text-white"
                        style={{ background: '#0B0D0E', border: '1px solid rgba(255,255,255,0.15)' }}
                      >
                        Open Railway dashboard
                      </button>
                    </div>
                  )}
                </div>
                {(!deployTokensHint.has_vercel || !deployTokensHint.has_netlify) && (
                  <p className="text-[11px] leading-snug" style={{ color: 'var(--theme-muted)' }}>
                    One-click needs tokens in{' '}
                    <Link to="/app/settings" className="underline font-medium" style={{ color: 'var(--theme-accent)' }}>Settings → Deploy integrations</Link>
                    {(!deployTokensHint.has_vercel && !deployTokensHint.has_netlify) ? ' (Vercel and/or Netlify).' : !deployTokensHint.has_vercel ? ' (add Vercel).' : ' (add Netlify).'}
                  </p>
                )}
              </div>
            )}

            <div className="text-[10px] font-semibold uppercase tracking-wider mb-2 pt-1 border-t" style={{ color: 'var(--theme-muted)', borderColor: 'var(--theme-border, rgba(255,255,255,0.08))' }}>Editor export & hosts</div>
            <div className="flex flex-col gap-2">
              <button type="button" onClick={downloadCode} className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-medium transition hover:bg-white/5 border" style={{ borderColor: 'var(--theme-border, rgba(255,255,255,0.1))', color: 'var(--theme-text, #e4e4e7)' }}>
                <Download className="w-4 h-4" /> Download ZIP (current editor)
              </button>
              <button type="button" onClick={handleExportDeploy} className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-medium transition hover:bg-white/5 border" style={{ borderColor: 'var(--theme-border, rgba(255,255,255,0.1))', color: 'var(--theme-text, #e4e4e7)' }}>
                <Rocket className="w-4 h-4" /> Deploy-ready ZIP (API from editor)
              </button>
              <a href="https://vercel.com/new" target="_blank" rel="noopener noreferrer" className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-medium text-white hover:opacity-90 transition" style={{ background: '#000' }}>
                Vercel (upload)
              </a>
              <a href="https://app.netlify.com/drop" target="_blank" rel="noopener noreferrer" className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-medium text-white hover:opacity-90 transition" style={{ background: '#00AD9F' }}>
                Netlify Drop
              </a>
              <a href="https://railway.app/new" target="_blank" rel="noopener noreferrer" className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-medium text-white hover:opacity-90 transition" style={{ background: '#0B0D0E', border: '1px solid rgba(255,255,255,0.15)' }}>
                Railway
              </a>
            </div>
            <button type="button" onClick={() => setShowDeployModal(false)} className="mt-4 w-full py-2 text-sm rounded-xl border transition hover:bg-white/5" style={{ color: 'var(--theme-muted, #71717a)', borderColor: 'var(--theme-border, rgba(255,255,255,0.1))' }}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Workspace;

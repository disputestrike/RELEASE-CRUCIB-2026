import { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
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
import {
  ChevronDown,
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
  File,
  Coffee,
  Zap,
  RefreshCw,
  ExternalLink,
  Github,
  History,
  Undo2,
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
} from 'lucide-react';
import { useAuth, API } from '../App';
import { useLayoutStore } from '../stores/useLayoutStore';
import { useTaskStore } from '../stores/useTaskStore';
import axios from 'axios';
import ManusComputer from '../components/ManusComputer';
import InlineAgentMonitor from '../components/InlineAgentMonitor';

// Default React app template
const DEFAULT_FILES = {
  '/App.js': {
    code: `import React from 'react';

export default function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-[#1A1A1A] mb-4">
          Welcome to CrucibAI
        </h1>
        <p className="text-slate-400 text-lg">
          Describe what you want to build in the chat...
        </p>
      </div>
    </div>
  );
}`,
  },
  '/index.js': {
    code: `import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles.css';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);`,
  },
  '/styles.css': {
    code: `@import url('https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css');

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}`,
  },
};

// File tree component
const FileTree = ({ files, activeFile, onSelectFile, onAddFile }) => {
  const getFileIcon = (filename) => {
    if (filename.endsWith('.js') || filename.endsWith('.jsx')) return <FileCode className="w-4 h-4 text-yellow-400" />;
    if (filename.endsWith('.css')) return <FileText className="w-4 h-4 text-gray-800" />;
    if (filename.endsWith('.html')) return <FileText className="w-4 h-4 text-gray-800" />;
    return <File className="w-4 h-4 text-gray-500" />;
  };

  const fileList = Object.keys(files).sort();

  return (
    <div className="text-sm">
      <div className="flex items-center justify-between gap-2 px-3 py-2 text-gray-500 text-xs uppercase tracking-wider">
        <div className="flex items-center gap-2">
          <FolderOpen className="w-4 h-4" />
          <span>Files</span>
        </div>
        {onAddFile && (
          <button type="button" onClick={onAddFile} className="flex items-center gap-1 text-gray-500 hover:text-gray-900" title="New file">
            <Plus className="w-3.5 h-3.5" /> New file
          </button>
        )}
      </div>
      {fileList.map((filename) => (
        <button
          key={filename}
          onClick={() => onSelectFile(filename)}
          data-testid={`file-${filename.replace('/', '')}`}
          className={`w-full flex items-center gap-2 px-4 py-1.5 text-left transition ${
            activeFile === filename
              ? 'bg-gray-200 text-gray-900'
              : 'text-gray-600 hover:bg-gray-100 hover:text-gray-800'
          }`}
        >
          {getFileIcon(filename)}
          <span className="truncate">{filename.replace('/', '')}</span>
        </button>
      ))}
    </div>
  );
};

// Console/Logs component (Terminal)
const ConsolePanel = ({ logs, placeholder = "Terminal output will appear here. Run a build to see logs." }) => {
  const consoleRef = useRef(null);

  useEffect(() => {
    if (consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div ref={consoleRef} className="h-full overflow-auto font-mono text-xs p-3 space-y-1 bg-white text-gray-800">
      {logs.length === 0 ? (
        <div className="text-gray-500">{placeholder}</div>
      ) : (
        logs.map((log, i) => (
          <div
            key={i}
            className={`flex items-start gap-2 ${
              log.type === 'error' ? 'text-red-600' :
              log.type === 'success' ? 'text-green-700' :
              log.type === 'warning' ? 'text-amber-700' :
              'text-gray-600'
            }`}
          >
            <span className="text-[#666666]">[{log.time}]</span>
            <span className="text-gray-500">{log.agent || 'system'}:</span>
            <span className="flex-1">{log.message}</span>
          </div>
        ))
      )}
    </div>
  );
};

// LLM Selector dropdown – Cursor-style: next to chat, opens upward
const ModelSelector = ({ selectedModel, onSelectModel, variant = 'default' }) => {
  const [isOpen, setIsOpen] = useState(false);
  const isChat = variant === 'chat';

  const models = [
    { id: 'auto', name: 'Auto', icon: Sparkles, desc: 'Best model for the task' },
    { id: 'gpt-4o', name: 'GPT-4o', icon: Zap, desc: 'OpenAI latest' },
    { id: 'claude', name: 'Claude 3.5', icon: Coffee, desc: 'Anthropic Sonnet' },
    { id: 'gemini', name: 'Gemini Flash', icon: RefreshCw, desc: 'Google fast model' },
  ];

  const selected = models.find(m => m.id === selectedModel) || models[0];

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        data-testid="model-selector"
        className={`flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white text-gray-800 hover:bg-gray-50 transition ${
          isChat ? 'h-[42px] px-3 py-2 text-sm' : 'px-3 py-1.5 text-sm'
        }`}
      >
        <selected.icon className="w-4 h-4 shrink-0" />
        <span className="truncate max-w-[100px]">{isChat ? selected.name : selected.name}</span>
        <ChevronDown className={`w-3.5 h-3.5 shrink-0 transition ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      <AnimatePresence>
        {isOpen && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} aria-hidden />
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 6 }}
              className="absolute left-0 bottom-full mb-1.5 w-56 bg-white border border-gray-200 rounded-lg shadow-xl overflow-hidden z-50"
            >
              <div className="py-1">
                {models.map((model) => (
                  <button
                    key={model.id}
                    type="button"
                    onClick={() => { onSelectModel(model.id); setIsOpen(false); }}
                    data-testid={`model-option-${model.id}`}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 text-left text-sm transition ${
                      selectedModel === model.id ? 'bg-gray-100 text-gray-900' : 'text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    <model.icon className="w-4 h-4 shrink-0" />
                    <div className="min-w-0 flex-1">
                      <div className="font-medium">{model.name}</div>
                      <div className="text-xs text-gray-500 truncate">{model.desc}</div>
                    </div>
                    {selectedModel === model.id && <Check className="w-4 h-4 shrink-0 text-green-600" />}
                  </button>
                ))}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
};

// Version History Panel
const VersionHistory = ({ versions, onRestore, currentVersion }) => {
  return (
    <div className="p-3 space-y-2 overflow-y-auto h-full">
      <div className="text-xs text-gray-500 uppercase tracking-wider mb-3">Version History</div>
      {versions.length === 0 ? (
        <div className="text-sm text-gray-500">No versions yet</div>
      ) : (
        versions.map((version, i) => (
          <div
            key={version.id}
            className={`p-3 rounded-lg cursor-pointer transition ${
              currentVersion === version.id ? 'bg-gray-200 border border-gray-300' : 'bg-gray-50 hover:bg-gray-100 border border-transparent'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium text-gray-800">v{versions.length - i}</span>
              <span className="text-xs text-gray-500">{version.time}</span>
            </div>
            <p className="text-xs text-gray-600 mb-2 line-clamp-2">{version.prompt}</p>
            {currentVersion !== version.id && (
              <button
                onClick={() => onRestore(version)}
                className="flex items-center gap-1 text-xs text-gray-800 hover:text-gray-900"
              >
                <Undo2 className="w-3 h-3" />
                Restore
              </button>
            )}
          </div>
        ))
      )}
    </div>
  );
};

// Main Workspace Component
const Workspace = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const { user, token } = useAuth();
  
  const [files, setFiles] = useState(DEFAULT_FILES);
  const [activeFile, setActiveFile] = useState('/App.js');
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
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [versions, setVersions] = useState([]);
  const [currentVersion, setCurrentVersion] = useState(null);
  
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
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(false); // collapsed by default; View → "Show code / files" for devs
  const [showFirstRunBanner, setShowFirstRunBanner] = useState(() => !localStorage.getItem('crucibai_first_run'));
  const [rightSidebarOpen, setRightSidebarOpen] = useState(false);
  const [splitEditor, setSplitEditor] = useState(false);
  const [menuAnchor, setMenuAnchor] = useState(null); // 'file' | 'edit' | 'view' | 'go' | 'run' | 'terminal' | 'help' | null
  const [toolsReport, setToolsReport] = useState(null); // { type: 'validate'|'security'|'a11y', data }
  const [toolsLoading, setToolsLoading] = useState(false);
  const [nextSuggestions, setNextSuggestions] = useState([]);
  const [buildMode, setBuildMode] = useState('agent'); // 'quick' | 'plan' | 'agent' | 'thinking' | 'swarm'
  const { mode: layoutMode, setMode: setLayoutMode, isDev: devMode } = useLayoutStore();
  const toggleDevMode = () => setLayoutMode(prev => (prev === 'dev' ? 'simple' : 'dev'));
  const { addTask } = useTaskStore();

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
  const [mobileView, setMobileView] = useState(false);
  const projectIdFromUrl = searchParams.get('projectId');
  const [projectBuildProgress, setProjectBuildProgress] = useState({ phase: 0, agent: '', progress: 0, status: '', tokens_used: 0 });
  const fileInputRef = useRef(null);
  const chatEndRef = useRef(null);
  const workspaceFilesLoadedForProject = useRef(null);

  useEffect(() => {
    axios.get(`${API}/build/phases`).then(r => setBuildPhases(r.data.phases || [])).catch(() => {});
  }, []);

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
          }
        });
      })
      .catch(() => {});
  }, [projectIdFromUrl, token, API]);

  useEffect(() => {
    if (token) {
      axios.get(`${API}/agents/activity`, { headers: { Authorization: `Bearer ${token}` } })
        .then(r => setAgentsActivity(r.data.activities || []))
        .catch(() => {});
    }
  }, [token, messages.length]);

  // Wire real build progress when opened with projectId (from AgentMonitor "Open in Workspace")
  useEffect(() => {
    if (!projectIdFromUrl || !API) return;
    const wsBase = (API || '').replace(/^http/, 'ws').replace(/\/api\/?$/, '');
    const wsUrl = `${wsBase}/ws/projects/${projectIdFromUrl}/progress`;
    let ws;
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
    } catch (_) {}
    return () => { try { if (ws) ws.close(); } catch (_) {} };
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
        window.open('/workspace', '_blank');
      }
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'L') {
        e.preventDefault();
        setSessionId(`session_${Date.now()}`);
        setMessages([]);
        setMenuAnchor(null);
      }
      if (e.key === 'Escape') {
        setCommandPaletteOpen(false);
        setFileSearchOpen(false);
        setMenuAnchor(null);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // PHASE 4: Build only from form submit — never from useEffect. Pre-fill input only.
  useEffect(() => {
    const statePrompt = location.state?.initialPrompt;
    const initialPrompt = statePrompt || searchParams.get('prompt');
    const initialFiles = location.state?.initialAttachedFiles;
    if (initialPrompt) {
      setInput(initialPrompt);
      if (initialFiles?.length) setAttachedFiles(initialFiles);
    } else if (initialFiles?.length && initialFiles.every(f => f.type?.startsWith?.('image/'))) {
      setAttachedFiles(initialFiles);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps -- run once on mount to prefill from navigation
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const addLog = (message, type = 'info', agent = null) => {
    const now = new Date();
    const time = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
    setLogs(prev => [...prev, { message, type, time, agent }]);
  };

  const startRecording = async () => {
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        addLog('Microphone not supported in this browser.', 'error', 'voice');
        return;
      }
      if (typeof MediaRecorder === 'undefined') {
        addLog('Voice recording not supported. Try Chrome or Firefox.', 'error', 'voice');
        return;
      }
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeTypes = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus'];
      const mimeType = mimeTypes.find(mt => MediaRecorder.isTypeSupported(mt)) || 'audio/webm';
      const recorder = new MediaRecorder(stream, { mimeType });
      const chunks = [];
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        setIsRecording(false);
        const blob = new Blob(chunks, { type: mimeType.split(';')[0] });
        if (blob.size < 100) {
          addLog('Recording too short. Speak for at least a second.', 'error', 'voice');
          return;
        }
        const ext = mimeType.includes('mp4') ? 'm4a' : 'webm';
        setIsTranscribing(true);
        addLog('Transcribing...', 'info', 'voice');
        try {
          await transcribeAudio(blob, ext);
        } finally {
          setIsTranscribing(false);
        }
      };
      recorder.start(1000);
      mediaRecorderRef.current = { recorder, stream };
      setAudioStream(stream);
      setIsRecording(true);
      addLog('Listening...', 'info', 'voice');
    } catch (err) {
      setIsRecording(false);
      const micMsg = err?.name === 'NotAllowedError'
        ? 'Microphone access denied. Allow it in browser settings.'
        : 'Could not start microphone. Check browser permissions.';
      addLog(micMsg, 'error', 'voice');
      setMessages(prev => [...prev, { role: 'assistant', content: micMsg, error: true }]);
    }
  };

  const stopRecording = () => {
    // ISSUE 7: Cancel recording — stop without transcribing, fully release mic
    const ref = mediaRecorderRef.current;
    if (ref?.recorder) {
      ref.recorder.onstop = () => {
        // Stop ALL tracks on the stream to fully release microphone
        if (ref.stream) ref.stream.getTracks().forEach(t => t.stop());
      };
      if (ref.recorder.state !== 'inactive') ref.recorder.stop();
    }
    // Also stop stream directly in case recorder didn't clean up
    if (ref?.stream) {
      ref.stream.getTracks().forEach(t => t.stop());
    }
    mediaRecorderRef.current = null;
    setAudioStream(null);
    setIsRecording(false);
    addLog('Recording cancelled.', 'info', 'voice');
  };

  const confirmRecording = () => {
    // Stop recording and send to Whisper for transcription
    const ref = mediaRecorderRef.current;
    if (ref?.recorder?.state === 'recording') {
      ref.recorder.stop(); // onstop handler will call transcribeAudio
    }
    setAudioStream(null);
  };

  const transcribeAudio = async (blob, ext = 'webm') => {
    try {
      const formData = new FormData();
      formData.append('audio', blob, `recording.${ext}`);
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const response = await axios.post(`${API}/voice/transcribe`, formData, {
        headers: { ...headers },
        timeout: 30000,
        maxContentLength: Infinity,
        maxBodyLength: Infinity,
      });
      if (response.data?.text) {
        setInput(response.data.text);
        addLog(`Transcribed: "${response.data.text}"`, 'success', 'voice');
      } else {
        addLog('No text in response. Try speaking clearly.', 'error', 'voice');
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Transcription failed.';
      addLog(msg, 'error', 'voice');
      setLastError(msg);
    }
  };

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files);
    const validFiles = selectedFiles.filter(f => 
      f.type.startsWith('image/') || 
      f.type === 'application/pdf' ||
      f.type.startsWith('text/')
    );
    
    validFiles.forEach(file => {
      const reader = new FileReader();
      reader.onload = (e) => {
        setAttachedFiles(prev => [...prev, {
          name: file.name,
          type: file.type,
          data: e.target.result,
          size: file.size
        }]);
        addLog(`Attached: ${file.name}`, 'info', 'files');
      };
      if (file.type.startsWith('image/')) {
        reader.readAsDataURL(file);
      } else {
        reader.readAsText(file);
      }
    });
  };

  const removeFile = (index) => {
    setAttachedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleBuild = async (promptOverride = null, filesOverride = null) => {
    const prompt = (promptOverride ?? input).trim();
    const filesToUse = filesOverride && filesOverride.length > 0 ? filesOverride : attachedFiles;
    const hasImageOnly = filesToUse.length >= 1 && filesToUse.every(f => f.type?.startsWith?.('image/'));
    const useImageToCode = hasImageOnly && (!prompt || /screenshot|image|convert|turn into code|build from/i.test(prompt));

    if ((!prompt && !useImageToCode) || isBuilding) return;

    setInput('');
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
const planRes = await axios.post(`${API}/build/plan`, { prompt, swarm: useSwarm }, { headers, timeout: 45000 });
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
          addLog(`Plan failed: ${planErr.message}, building directly`, 'info', 'planner');
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
        setMessages(prev => prev.map((msg, i) => i === prev.length - 1 ? { role: 'assistant', content: 'Done! Your app is ready.', hasCode: true } : msg));
        addTask({ name: prompt ? prompt.slice(0, 120) : 'Image to code', prompt: prompt || 'Image to code', status: 'completed', createdAt: Date.now() });
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
      const agents = [
        { name: 'Planner', delay: 300, phase: phaseLabels[0]?.name || 'Planning' },
        { name: 'Frontend', delay: 500, phase: phaseLabels[1]?.name || 'Generating' },
        { name: 'Styling', delay: 400, phase: phaseLabels[1]?.name || 'Generating' },
        { name: 'Testing', delay: 300, phase: phaseLabels[2]?.name || 'Validating' },
        { name: 'Finalizing', delay: 200, phase: phaseLabels[3]?.name || 'Deployment' }
      ];
      let progress = 0;
      for (const agent of agents) {
        setCurrentPhase(agent.phase);
        addLog(`${agent.name} agent processing...`, 'info', agent.name.toLowerCase());
        await new Promise(r => setTimeout(r, agent.delay));
        progress += 20;
        setBuildProgress(Math.min(progress, 90));
      }
      setCurrentPhase('');

      let messageContent = `Create a complete, production-ready React application for: "${prompt}". 
Use React hooks and Tailwind CSS. Make it modern, responsive, and functional.
Include all necessary components and styling.
Respond with ONLY the complete App.js code, nothing else.`;
      if (imagesToSend.length > 0) {
        messageContent += `\n\nThe user has attached ${imagesToSend.length} image(s) as reference. Try to match the design style.`;
      }
      const wantsPayments = /payment|stripe|subscription|checkout|pay|billing/i.test(prompt);
      if (wantsPayments) {
        messageContent += `\n\nIMPORTANT: Include Stripe Checkout integration. Use @stripe/react-stripe-js or Stripe.js. Add a checkout/pay button and handle payment success. Include placeholder for STRIPE_PUBLISHABLE_KEY.`;
      }

      if (useStreaming) {
        const res = await fetch(`${API}/ai/chat/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...headers },
          body: JSON.stringify({ message: messageContent, session_id: sessionId, model: selectedModel, mode: buildMode === 'thinking' ? 'thinking' : undefined }),
        });
        if (!res.ok) throw new Error(await res.text());
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
              if (obj.error) throw new Error(obj.error);
              if (obj.chunk) {
                accumulated += obj.chunk;
                setFiles(prev => ({ ...prev, '/App.js': { code: accumulated } }));
              }
              if (obj.done) {
                streamDone = true;
                setBuildProgress(100);
                if (obj.tokens_used != null) { setLastTokensUsed(obj.tokens_used); setTokensPerStep(prev => ({ ...prev, generate: obj.tokens_used })); }
                addLog('Build completed successfully!', 'success', 'deploy');
                const parsedFiles = parseMultiFileOutput(accumulated);
                setFiles(prev => {
                  const next = { ...prev, ...parsedFiles };
                  setVersions(v => [{ id: `v_${Date.now()}`, prompt, files: next, time: new Date().toLocaleTimeString() }, ...v]);
                  setCurrentVersion(`v_${Date.now()}`);
                  setMessages(m => m.map((msg, i) => i === m.length - 1 ? { role: 'assistant', content: 'Done! Your app is ready.', hasCode: true, planSuggestions: planSuggestions } : msg));
                  setTimeout(() => fetchSuggestNext(), 400);
                  const mainCode = parsedFiles['/App.js']?.code || Object.values(parsedFiles)[0]?.code || '';
                  axios.post(`${API}/ai/quality-gate`, { code: mainCode }).then(r => setQualityGateResult(r.data)).catch(() => setQualityGateResult(null));
                  return next;
                });
                setActivePanel('preview'); // AUTO-WIRE: switch to preview on build complete
                // PHASE 7: Single task authority — write to store (persists to localStorage)
                addTask({ name: prompt.slice(0, 120), prompt, status: 'completed', createdAt: Date.now() });
                if (token) {
                  axios.post(`${API}/api/tasks`, {
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
        const mainCode = parsedFiles['/App.js']?.code || Object.values(parsedFiles)[0]?.code || '';
        axios.post(`${API}/ai/quality-gate`, { code: mainCode }).then(r => setQualityGateResult(r.data)).catch(() => setQualityGateResult(null));
        setActivePanel('preview'); // AUTO-WIRE: switch to preview on build complete
        // PHASE 7: Single task authority — write to store (persists to localStorage)
        addTask({ name: prompt.slice(0, 120), prompt, status: 'completed', createdAt: Date.now() });
        if (token) {
          axios.post(`${API}/api/tasks`, {
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
      addLog(`Build failed: ${error.message}`, 'error', 'system');
      setLastError(error.message);
      const detail = String(error.response?.data?.detail || '');
      const is402 = error.response?.status === 402;
      const isKeyError = error.response?.status === 401 || detail.toLowerCase().includes('api key') || detail.toLowerCase().includes('no api key') || error.message?.toLowerCase().includes('key');
      const friendlyMessage = is402
        ? (detail || 'Insufficient tokens. Buy more in Token Center to keep building.')
        : error.code === 'ERR_NETWORK' || error.message?.includes('Network') || error.message?.includes('Failed to fetch')
          ? "Connection lost. Check your connection and try again."
          : isKeyError
            ? "AI couldn't run. Check Settings → API & Environment: add and save your OpenAI or Anthropic key, then try again."
            : "The build didn't complete. Try again or check Settings if you use your own API keys.";
      setMessages(prev => prev.map((msg, i) => i === prev.length - 1 ? { role: 'assistant', content: friendlyMessage, error: true } : msg));
    } finally {
      setIsBuilding(false);
    }
  };

  const handleModify = async () => {
    if (!input.trim() || isBuilding) return;

    const request = input.trim();
    setInput('');
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
      addLog(`Modification failed: ${error.message}`, 'error', 'system');
      setMessages(prev => prev.map((msg, i) => 
        i === prev.length - 1 ? { role: 'assistant', content: 'Error updating. Try again.', error: true } : msg
      ));
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
    const base = '/NewFile';
    const ext = '.jsx';
    let path = base + ext;
    let n = 0;
    while (files[path]) {
      n += 1;
      path = base + n + ext;
    }
    const code = `// ${path}\nimport React from 'react';\n\nexport default function Component() {\n  return <div>New component</div>;\n}\n`;
    setFiles(prev => ({ ...prev, [path]: { code } }));
    setActiveFile(path);
    addLog(`Added file ${path}`, 'info', 'files');
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
    else if (cmd === 'newAgent') { setSessionId(`session_${Date.now()}`); setMessages([]); }
    else if (cmd === 'terminal') { setActivePanel('console'); setRightSidebarOpen(true); }
    else if (cmd === 'maximizeChat') setChatMaximized(prev => !prev);
    else if (cmd === 'searchFiles') setFileSearchOpen(prev => !prev);
    else if (cmd === 'openBrowser') window.open('/workspace', '_blank');
    else if (cmd === 'shortcuts') navigate('/app/shortcuts');
    else if (cmd === 'templates') navigate('/app/templates');
    else if (cmd === 'prompts') navigate('/app/prompts');
    else if (cmd === 'payments') navigate('/app/payments-wizard');
  };

  return (
    <div className="h-full min-h-0 flex flex-col overflow-hidden bg-[#FAF9F7] text-gray-900 font-sans text-[13px] antialiased">
      {/* Manus Computer Widget — wired to real build when projectId in URL (from AgentMonitor Open in Workspace) */}
      <ManusComputer 
        currentStep={projectIdFromUrl ? (projectBuildProgress.phase + 1) : (versions.length > 0 ? Math.min(versions.length, 7) : 0)}
        totalSteps={projectIdFromUrl ? 12 : 7}
        thinking={projectIdFromUrl ? (projectBuildProgress.agent || 'Building...') : (isBuilding ? 'Analyzing your request and generating code...' : '')}
        tokensUsed={projectIdFromUrl ? projectBuildProgress.tokens_used : (versions.length * 1000)}
        tokensTotal={projectIdFromUrl ? 100000 : 50000}
        isActive={projectIdFromUrl ? (projectBuildProgress.status === 'running' || (projectBuildProgress.progress > 0 && projectBuildProgress.progress < 100)) : (isBuilding || versions.length > 0)}
      />
      {/* Command palette (Ctrl+K / Cmd+K) */}
      {commandPaletteOpen && (
        <div className="fixed inset-0 z-[200] flex items-start justify-center pt-[15vh] bg-zinc-900/40 backdrop-blur-sm" onClick={() => setCommandPaletteOpen(false)}>
          <div className="w-full max-w-lg bg-white border border-gray-200 rounded-xl shadow-2xl overflow-hidden" onClick={e => e.stopPropagation()}>
            <div className="px-4 py-2 border-b border-gray-200 text-xs text-gray-500">Command palette</div>
            <div className="max-h-80 overflow-y-auto">
              {[
                { id: 'newAgent', label: 'New Agent / New chat (Ctrl+Shift+L)', icon: Plus },
                { id: 'searchFiles', label: 'Search / Open file (Ctrl+P)', icon: Search },
                { id: 'terminal', label: 'Show Terminal (Ctrl+J)', icon: Terminal },
                { id: 'maximizeChat', label: 'Maximize Chat (Ctrl+Alt+E)', icon: Maximize2 },
                { id: 'openBrowser', label: 'Open preview in browser (Ctrl+Shift+B)', icon: Globe },
                { id: 'deploy', label: 'Deploy (download ZIP for Vercel/Netlify)', icon: ExternalLink },
                { id: 'export', label: 'Export / Download code', icon: Download },
                { id: 'github', label: 'Push to GitHub (download ZIP)', icon: Github },
                ...(lastError ? [{ id: 'autofix', label: 'Auto-fix errors', icon: RefreshCw }] : []),
                { id: 'templates', label: 'Templates gallery', icon: FileCode },
                { id: 'prompts', label: 'Prompt Library', icon: FileText },
                { id: 'shortcuts', label: 'Shortcut cheat sheet (?)', icon: HelpCircle },
                { id: 'payments', label: 'Add payments (Stripe) wizard', icon: CreditCard },
                { id: 'tokens', label: 'Token Center', icon: Zap },
                { id: 'settings', label: 'Settings', icon: Settings },
              ].map(({ id, label, icon: Icon }) => (
                <button key={id} onClick={() => runCommand(id)} className="w-full flex items-center gap-3 px-4 py-3 text-left text-gray-800 hover:bg-gray-100 transition">
                  <Icon className="w-4 h-4 text-gray-500" />
                  <span>{label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* File search (Ctrl+P) */}
      {fileSearchOpen && (
        <div className="fixed inset-0 z-[200] flex items-start justify-center pt-[20vh] bg-zinc-900/40 backdrop-blur-sm" onClick={() => setFileSearchOpen(false)}>
          <div className="w-full max-w-md bg-white border border-gray-200 rounded-xl shadow-2xl overflow-hidden" onClick={e => e.stopPropagation()}>
            <div className="px-4 py-2 border-b border-gray-200 text-xs text-gray-500">Open file (Ctrl+P)</div>
            <div className="max-h-60 overflow-y-auto">
              {Object.keys(files).sort().map((filename) => (
                <button key={filename} onClick={() => { setActiveFile(filename); setFileSearchOpen(false); }} className="w-full flex items-center gap-2 px-4 py-2.5 text-left hover:bg-gray-100 text-sm text-gray-800">
                  <FileCode className="w-4 h-4 text-gray-500" />
                  {filename.replace('/', '')}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Paywall banner when low/zero tokens */}
      {user && (user.token_balance === 0 || (user.token_balance < 10000 && user.token_balance > 0)) && (
        <div className="flex-shrink-0 px-4 py-2 bg-amber-500/10 border-b border-amber-500/20 flex items-center justify-between">
          <span className="text-sm text-amber-700">
            {user.token_balance === 0 ? 'Out of tokens.' : 'Running low on tokens.'} Get more to keep building.
          </span>
          <button onClick={() => navigate('/app/tokens')} className="text-sm font-medium text-amber-700 hover:text-amber-800">
            Buy tokens
          </button>
        </div>
      )}

      {/* Click outside to close menu */}
      {menuAnchor && <div className="fixed inset-0 z-40" onClick={() => setMenuAnchor(null)} aria-hidden />}
      {/* Menu bar – File, Edit, Selection, View, Go, Run, Terminal, Help (Developer mode only) */}
      {devMode && (
      <div className="h-9 border-b border-stone-200 flex items-center px-2 gap-0 flex-shrink-0 text-[13px] relative z-50 bg-[#FAF9F7]">
        {['File', 'Edit', 'Selection', 'View', 'Go', 'Run', 'Terminal', 'Help'].map((name) => (
          <div key={name} className="relative">
            <button
              onClick={() => setMenuAnchor(menuAnchor === name.toLowerCase() ? null : name.toLowerCase())}
              className="px-3 py-1.5 rounded text-gray-600 hover:text-gray-900 hover:bg-gray-200"
            >
              {name}
            </button>
            {menuAnchor === name.toLowerCase() && (
              <div className="absolute left-0 top-full mt-0.5 w-48 py-1 bg-white border border-gray-200 rounded-lg shadow-xl z-50">
                {name === 'File' && (
                  <>
                    <button onClick={() => setFileSearchOpen(true)} className="w-full px-3 py-2 text-left text-gray-700 hover:bg-gray-100 text-xs">Open File... (Ctrl+P)</button>
                    <button onClick={() => { setSessionId(`session_${Date.now()}`); setMessages([]); setMenuAnchor(null); }} className="w-full px-3 py-2 text-left text-gray-700 hover:bg-gray-100 text-xs">New Agent (Ctrl+Shift+L)</button>
                    <div className="h-px bg-gray-200 my-1" />
                    <button onClick={downloadCode} className="w-full px-3 py-2 text-left text-gray-700 hover:bg-gray-100 text-xs">Export</button>
                    <button onClick={() => { handleExportZip(); setMenuAnchor(null); }} className="w-full px-3 py-2 text-left text-gray-700 hover:bg-gray-100 text-xs">Download ZIP</button>
                    <button onClick={() => { handleExportGitHub(); setMenuAnchor(null); }} className="w-full px-3 py-2 text-left text-gray-700 hover:bg-gray-100 text-xs">Push to GitHub</button>
                    <button onClick={() => setMenuAnchor(null)} className="w-full px-3 py-2 text-left text-gray-700 hover:bg-gray-100 text-xs">Close</button>
                  </>
                )}
                {name === 'Edit' && (
                  <>
                    <button onClick={copyCode} className="w-full px-3 py-2 text-left text-gray-700 hover:bg-gray-100 text-xs">Copy</button>
                    <button onClick={() => { versions.length > 1 && restoreVersion(versions[1]); setMenuAnchor(null); }} className="w-full px-3 py-2 text-left text-gray-700 hover:bg-gray-100 text-xs">Undo</button>
                    <button onClick={() => { runCommand('autofix'); setMenuAnchor(null); }} className="w-full px-3 py-2 text-left text-gray-700 hover:bg-gray-100 text-xs">Auto-fix</button>
                  </>
                )}
                {name === 'View' && (
                  <>
                    <button onClick={() => { setActivePanel('preview'); setMenuAnchor(null); }} className="w-full px-3 py-2 text-left text-gray-700 hover:bg-gray-100 text-xs">Preview</button>
                    <button onClick={() => { setActivePanel('console'); setMenuAnchor(null); }} className="w-full px-3 py-2 text-left text-gray-700 hover:bg-gray-100 text-xs">Terminal (Ctrl+J)</button>
                    <button onClick={() => setChatMaximized(prev => !prev)} className="w-full px-3 py-2 text-left text-gray-700 hover:bg-gray-100 text-xs">Maximize Chat (Ctrl+Alt+E)</button>
                    <button onClick={() => setAgentsPanelOpen(prev => !prev)} className="w-full px-3 py-2 text-left text-gray-700 hover:bg-gray-100 text-xs">Agents Panel</button>
                    <div className="h-px bg-gray-200 my-1" />
                    <div className="px-3 py-1.5 text-xs text-gray-500">Build level</div>
                    {['quick', 'balanced', 'deep'].map((level) => (
                      <button key={level} onClick={() => { setAutoLevel(level); setMenuAnchor(null); }} className={`w-full px-3 py-2 text-left text-xs capitalize ${autoLevel === level ? 'text-gray-900 bg-gray-200' : 'text-gray-700 hover:bg-gray-100'}`}>{level}</button>
                    ))}
                    <div className="h-px bg-gray-200 my-1" />
                    <button onClick={() => setLeftSidebarOpen(prev => !prev)} className="w-full px-3 py-2 text-left text-gray-700 hover:bg-gray-100 text-xs">Show code / files</button>
                    <button onClick={() => setRightSidebarOpen(prev => !prev)} className="w-full px-3 py-2 text-left text-gray-700 hover:bg-gray-100 text-xs">Toggle Right Sidebar</button>
                  </>
                )}
                {name === 'Go' && (
                  <>
                    <button onClick={() => versions.length > 1 && restoreVersion(versions[1])} className="w-full px-3 py-2 text-left text-gray-700 hover:bg-gray-100 text-xs">Back (previous version)</button>
                    <button onClick={() => setFileSearchOpen(true)} className="w-full px-3 py-2 text-left text-gray-700 hover:bg-gray-100 text-xs">Go to File... (Ctrl+P)</button>
                  </>
                )}
                {name === 'Run' && (
                  <>
                    <button onClick={() => { setActivePanel('preview'); setMenuAnchor(null); }} className="w-full px-3 py-2 text-left text-gray-700 hover:bg-gray-100 text-xs">Run Preview</button>
                    <button onClick={() => { handleExportDeploy(); setMenuAnchor(null); }} className="w-full px-3 py-2 text-left text-gray-700 hover:bg-gray-100 text-xs">Deploy</button>
                  </>
                )}
                {name === 'Terminal' && (
                  <>
                    <button onClick={() => { setActivePanel('console'); setRightSidebarOpen(true); setMenuAnchor(null); }} className="w-full px-3 py-2 text-left text-gray-700 hover:bg-gray-100 text-xs">Show Terminal (Ctrl+J)</button>
                  </>
                )}
                {name === 'Help' && (
                  <>
                    <button onClick={() => navigate('/app/shortcuts')} className="w-full px-3 py-2 text-left text-gray-700 hover:bg-gray-100 text-xs">Shortcuts (?)</button>
                    <button onClick={() => navigate('/app/learn')} className="w-full px-3 py-2 text-left text-gray-700 hover:bg-gray-100 text-xs">Learn</button>
                    <button onClick={() => setCommandPaletteOpen(true)} className="w-full px-3 py-2 text-left text-gray-700 hover:bg-gray-100 text-xs">Command Palette (Ctrl+K)</button>
                  </>
                )}
                {(name === 'Selection' && (
                  <>
                    <button onClick={copyCode} className="w-full px-3 py-2 text-left text-gray-700 hover:bg-gray-100 text-xs">Copy</button>
                  </>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      )}

      {/* Header – branding + Settings */}
      <header className="h-11 border-b border-stone-200 flex items-center justify-between px-3 flex-shrink-0 bg-[#FAF9F7]">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={() => navigate('/')}
            data-testid="back-button"
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition shrink-0"
          >
            <ArrowLeft className="w-4 h-4 shrink-0" />
            <span className="text-sm font-medium text-gray-800 truncate">CrucibAI</span>
          </button>
          <div className="h-4 w-px bg-gray-200 shrink-0" />
          <span className="text-xs text-gray-500 truncate">
            {versions.length > 0 ? `v${versions.length}` : 'New Project'}
          </span>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={toggleDevMode}
            className={`dev-toggle-btn ${devMode ? 'active' : ''}`}
            title={devMode ? 'Switch to Simple view' : 'Switch to Developer view'}
          >
            {devMode ? '\u25FB Simple' : '< > Code'}
          </button>
          <button
            onClick={() => navigate('/app/settings')}
            data-testid="settings-button"
            className="p-2 rounded-md text-gray-500 hover:text-gray-900 hover:bg-gray-100 transition"
            title="Settings – add API keys to build with AI"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* First-run banner (one-time) */}
      {showFirstRunBanner && (
        <div className="flex-shrink-0 px-3 py-2 bg-gray-100 border-b border-gray-200 flex items-center justify-between gap-3" data-testid="first-run-banner">
          <p className="text-sm text-gray-900">
            Describe your app in the chat and we&apos;ll build it with 120 specialized agents. Plan, code, test, and deploy in one flow.
          </p>
          <button
            type="button"
            onClick={() => {
              localStorage.setItem('crucibai_first_run', '1');
              setShowFirstRunBanner(false);
            }}
            className="shrink-0 px-2 py-1 text-xs font-medium text-gray-800 hover:bg-gray-200 rounded transition"
            aria-label="Dismiss"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Agents panel (optional) */}
        {agentsPanelOpen && (
          <div className="w-64 border-r border-stone-200 flex-shrink-0 overflow-y-auto bg-[#FAF9F7]">
            <div className="p-3 border-b border-gray-200 flex items-center justify-between">
              <span className="text-xs font-medium text-gray-600">Agents</span>
              <button onClick={() => setAgentsPanelOpen(false)} className="text-gray-500 hover:text-gray-900">×</button>
            </div>
            <div className="p-2 space-y-2">
              {agentsActivity.length === 0 ? (
                <p className="text-xs text-gray-500 p-2">When you build, activity will appear here.</p>
              ) : (
                agentsActivity.slice(0, 10).map((a, i) => (
                  <div key={i} className="p-2 rounded-lg bg-white border border-gray-200 text-xs">
                    <p className="text-gray-800 line-clamp-2">{a.message}</p>
                    <div className="flex justify-between mt-1 text-gray-500">
                      <span>{a.model || 'auto'}</span>
                      <span>{a.tokens_used ? `~${a.tokens_used}` : ''}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
        {/* === DEVELOPER MODE: Left Sidebar + Code Editor === */}
        {devMode && (
          <>
            {/* Left Sidebar – Code / Files */}
            {leftSidebarOpen && (
              <div className="w-56 border-r border-stone-200 flex-shrink-0 overflow-y-auto flex flex-col bg-[#FAF9F7]">
                <div className="flex items-center justify-between px-2 py-1 border-b border-gray-200">
                  <span className="text-xs text-gray-500">Files</span>
                  <div className="flex items-center gap-1">
                    <button onClick={() => fileInputRef.current?.click()} className="p-1 text-gray-500 hover:text-gray-900" title="Attach file to chat"><Paperclip className="w-3.5 h-3.5" /></button>
                    <button onClick={() => setLeftSidebarOpen(false)} className="p-1 text-gray-500 hover:text-gray-900" title="Hide code"><PanelLeftClose className="w-3.5 h-3.5" /></button>
                  </div>
                </div>
                <FileTree 
                  files={files} 
                  activeFile={activeFile} 
                  onSelectFile={setActiveFile}
                  onAddFile={addNewFileToProject}
                />
              </div>
            )}
            {!leftSidebarOpen && (
              <button onClick={() => setLeftSidebarOpen(true)} className="w-8 border-r border-gray-200 flex-shrink-0 flex items-center justify-center text-gray-500 hover:text-gray-900 bg-gray-50" title="Show code / files"><PanelRightOpen className="w-4 h-4" /></button>
            )}

            {/* Code Editor */}
            <div className="flex-1 flex flex-col min-w-0 bg-white">
              {/* Editor Tabs */}
              <div className="h-10 border-b border-stone-200 flex items-center px-2 gap-1 flex-shrink-0 bg-[#FAF9F7]">
                {Object.keys(files).map(filename => (
                  <button
                    key={filename}
                    onClick={() => setActiveFile(filename)}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded text-sm transition ${
                      activeFile === filename 
                        ? 'bg-white text-gray-900 border border-gray-200 border-b-white -mb-px' 
                        : 'text-gray-500 hover:text-gray-800'
                    }`}
                  >
                    <FileCode className="w-3.5 h-3.5" />
                    {filename.replace('/', '')}
                  </button>
                ))}
                
                <div className="ml-auto flex items-center gap-2">
                  <button
                    onClick={copyCode}
                    className="p-1.5 text-gray-500 hover:text-gray-900 transition"
                    title="Copy code"
                  >
                    {copied ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Monaco Editor OR InlineAgentMonitor during BUILD */}
              <div className="flex-1">
                {isBuilding ? (
                  <InlineAgentMonitor
                    isBuilding={isBuilding}
                    buildProgress={buildProgress}
                    currentPhase={currentPhase}
                    agentsActivity={agentsActivity}
                    buildEvents={[]}
                    tokensUsed={lastTokensUsed}
                    projectBuildProgress={projectBuildProgress}
                    qualityScore={qualityGateResult?.score ?? null}
                  />
                ) : (
                  <Editor
                    height="100%"
                    language={activeFile.endsWith('.css') ? 'css' : 'javascript'}
                    value={files[activeFile]?.code || ''}
                    onChange={handleCodeChange}
                    theme="light"
                    options={{
                      minimap: { enabled: false },
                      fontSize: 13,
                      lineNumbers: 'on',
                      scrollBeyondLastLine: false,
                      wordWrap: 'on',
                      tabSize: 2,
                      padding: { top: 16 },
                    }}
                  />
                )}
              </div>
            </div>
          </>
        )}

        {/* === SIMPLE MODE: AgentMonitor during build, Chat/Prompt otherwise === */}
        {!devMode && (
          <div className="flex-1 flex flex-col min-w-0 bg-white">
            {isBuilding ? (
              <InlineAgentMonitor
                isBuilding={isBuilding}
                buildProgress={buildProgress}
                currentPhase={currentPhase}
                agentsActivity={agentsActivity}
                buildEvents={[]}
                tokensUsed={lastTokensUsed}
                projectBuildProgress={projectBuildProgress}
                qualityScore={qualityGateResult?.score ?? null}
              />
            ) : (
              <div className="flex-1 flex flex-col overflow-y-auto">
                {/* Chat history */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                  {messages.length === 0 ? (
                    <div className="flex items-center justify-center h-full text-gray-400 text-sm">
                      Describe what you want to build...
                    </div>
                  ) : (
                    messages.map((msg, i) => (
                      <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[80%] rounded-xl px-4 py-3 text-sm ${
                          msg.role === 'user'
                            ? 'bg-gray-100 text-gray-900'
                            : 'bg-white border border-gray-200 text-gray-800'
                        }`}>
                          <pre className="whitespace-pre-wrap font-sans">{msg.content}</pre>
                        </div>
                      </div>
                    ))
                  )}
                  <div ref={chatEndRef} />
                </div>
              </div>
            )}
          </div>
        )}

        {/* Right Panel - Manus-Style Preview / Code / Terminal / History / Tools */}
        {rightSidebarOpen && (
        <div className="w-[42%] min-w-[320px] max-w-[560px] border-l border-stone-200 flex flex-col flex-shrink-0 bg-white" style={{ transition: 'width 0.3s ease' }}>
          {/* Manus-Style Panel Header — Section 06 */}
          <div className="h-10 border-b border-stone-200 flex items-center px-2 gap-1 flex-shrink-0 bg-[#FAF9F7]">
            {/* Tab selectors — PHASE 6: Simple mode shows only Preview */}
            <div className="flex items-center gap-1">
              {(devMode
                ? [
                    { id: 'preview', label: 'Preview', icon: Eye },
                    { id: 'console', label: 'Terminal', icon: Terminal },
                    { id: 'history', label: 'History', icon: History },
                    { id: 'review', label: 'Code', icon: FileCode },
                    { id: 'tools', label: 'Tools', icon: Wrench },
                  ]
                : [{ id: 'preview', label: 'Preview', icon: Eye }]
              ).map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActivePanel(tab.id)}
                  data-testid={`${tab.id}-tab`}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-sm transition ${
                    activePanel === tab.id ? 'bg-white text-gray-900 border border-stone-200 border-b-white -mb-px shadow-sm' : 'text-stone-600 hover:text-gray-900'
                  }`}
                >
                  <tab.icon className="w-3.5 h-3.5" />
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Preview controls — only visible when Preview tab active */}
            {activePanel === 'preview' && (
              <div className="flex items-center gap-1 ml-2">
                <button
                  className={`p-1.5 rounded transition ${mobileView ? 'bg-gray-200 text-gray-900' : 'text-stone-500 hover:text-gray-900'}`}
                  onClick={() => setMobileView(v => !v)}
                  title={mobileView ? 'Switch to desktop view' : 'Switch to mobile view'}
                >
                  {mobileView ? <Monitor className="w-4 h-4" /> : <Smartphone className="w-4 h-4" />}
                </button>
                <button
                  className="p-1.5 text-stone-500 hover:text-gray-900 transition rounded"
                  onClick={() => {
                    const current = { ...files };
                    setFiles({});
                    setTimeout(() => setFiles(current), 50);
                  }}
                  title="Refresh preview"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
                <button
                  className="p-1.5 text-stone-500 hover:text-gray-900 transition rounded"
                  onClick={() => {
                    const iframe = document.querySelector('.sp-preview-iframe');
                    if (iframe?.src) window.open(iframe.src, '_blank');
                  }}
                  title="Open in new tab"
                >
                  <ExternalLink className="w-4 h-4" />
                </button>
              </div>
            )}

            {devMode && (
            <button
              className="ml-auto mr-1 px-3 py-1 rounded text-sm font-semibold transition"
              style={{ background: 'var(--accent)', color: 'white' }}
              onMouseEnter={e => { e.target.style.background = 'var(--accent-hover)'; }}
              onMouseLeave={e => { e.target.style.background = 'var(--accent)'; }}
              onClick={() => setShowDeployModal(true)}
            >
              Deploy
            </button>
            )}

            <div className="flex items-center gap-1">
              <button
                onClick={() => setIsFullscreen(!isFullscreen)}
                className="p-1.5 text-stone-500 hover:text-gray-900 transition"
              >
                {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
              </button>
              <button
                onClick={() => setRightSidebarOpen(false)}
                className="p-1.5 text-stone-500 hover:text-gray-900 transition"
                title="Close panel"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Panel Content — PHASE 6: Simple mode only shows Preview */}
          <div className="flex-1 overflow-hidden">
            {(activePanel === 'preview' || !devMode) && (
              <div className={`flex-1 h-full overflow-hidden transition-all duration-300 relative ${mobileView ? 'flex justify-center' : ''}`}>
              <div className={mobileView ? 'w-[375px] h-full border-l border-r border-gray-200' : 'w-full h-full'}>
              {/* PHASE 5: Explicit loading state — no ambiguous dark screen */}
              {isBuilding && (
                <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-[#FAF9F7] text-gray-500">
                  <div className="w-8 h-8 border-2 border-stone-300 rounded-full animate-spin" style={{ borderTopColor: 'var(--accent)' }} />
                  <span className="text-sm">Building…</span>
                </div>
              )}
              <SandpackProvider
                template="react"
                files={files}
                theme="light"
                options={{
                  externalResources: ['https://cdn.tailwindcss.com'],
                }}
              >
                <div style={{ position: 'relative', height: '100%' }}>
                  <SandpackPreview
                    showNavigator={false}
                    showRefreshButton={true}
                    style={{ height: '100%' }}
                  />
                  <SandpackErrorBoundary
                    onAutoFix={async (errorMsg) => {
                      addLog(`Auto-fix triggered: ${errorMsg}`, 'info', 'system');
                      try {
                        const headers = token ? { Authorization: `Bearer ${token}` } : {};
                        const res = await axios.post(`${API}/ai/explain-error`, {
                          error: errorMsg,
                          code: files[activeFile]?.code || files['/App.js']?.code || ''
                        }, { headers, timeout: 30000 });
                        if (res.data.fixed_code) {
                          setFiles(prev => ({ ...prev, [activeFile || '/App.js']: { code: res.data.fixed_code } }));
                          addLog('Auto-fix applied successfully', 'success', 'system');
                          setLastError(null);
                        }
                      } catch (e) {
                        addLog(`Auto-fix failed: ${e.message}`, 'error', 'system');
                      }
                    }}
                    onError={(err) => {
                      setLastError(err);
                      addLog(`Preview error: ${err}`, 'error', 'preview');
                    }}
                    maxRetries={3}
                    autoFixEnabled={true}
                  />
                </div>
              </SandpackProvider>
              </div>
              </div>
            )}
            
            {devMode && activePanel === 'console' && (
              <ConsolePanel logs={logs} placeholder="Build and agent output appears here. Use View → Terminal or Ctrl+J to focus." />
            )}
            
            {devMode && activePanel === 'history' && (
              <VersionHistory 
                versions={versions} 
                onRestore={restoreVersion}
                currentVersion={currentVersion}
              />
            )}
            {devMode && activePanel === 'review' && (
              <div className="p-4 h-full overflow-auto">
                <div className="text-xs text-gray-500 uppercase tracking-wider mb-3">Review changes</div>
                <p className="text-sm text-gray-600 mb-4">{Object.keys(files).length} file(s) in current version.</p>
                <div className="flex flex-col gap-2">
                  {Object.keys(files).sort().map((filename) => (
                    <div key={filename} className="flex items-center gap-2 py-2 border-b border-gray-200 text-sm">
                      <FileCode className="w-4 h-4 text-gray-500" />
                      <span className="text-gray-800">{filename.replace('/', '')}</span>
                    </div>
                  ))}
                </div>
                <div className="flex gap-2 mt-6">
                  <button onClick={() => versions.length > 1 && restoreVersion(versions[1])} className="px-4 py-2 rounded-lg bg-gray-200 text-gray-800 hover:bg-gray-300 text-sm">Undo All</button>
                  <button onClick={() => setActivePanel('preview')} className="px-4 py-2 rounded-lg bg-gray-200 text-gray-900 hover:bg-gray-300 text-sm">Keep All</button>
                </div>
              </div>
            )}
            {devMode && activePanel === 'tools' && (
              <div className="p-4 h-full overflow-auto">
                <div className="text-xs text-gray-500 uppercase tracking-wider mb-3">Quality & checks</div>
                <div className="flex flex-wrap gap-2 mb-4">
                  <button onClick={runValidate} disabled={toolsLoading} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-100 text-gray-800 hover:bg-gray-200 text-sm disabled:opacity-50">
                    <Check className="w-4 h-4" /> Validate current file
                  </button>
                  <button onClick={runSecurityScan} disabled={toolsLoading} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-100 text-gray-800 hover:bg-gray-200 text-sm disabled:opacity-50">
                    <ShieldCheck className="w-4 h-4" /> Security scan
                  </button>
                  <button onClick={runA11yCheck} disabled={toolsLoading} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-100 text-gray-800 hover:bg-gray-200 text-sm disabled:opacity-50">
                    <Eye className="w-4 h-4" /> Accessibility check
                  </button>
                  <button onClick={runOptimize} disabled={toolsLoading} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-100 text-gray-800 hover:bg-gray-200 text-sm disabled:opacity-50">
                    <Zap className="w-4 h-4" /> Optimize
                  </button>
                  <button onClick={runExplainError} disabled={toolsLoading} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-100 text-gray-800 hover:bg-gray-200 text-sm disabled:opacity-50">
                    <HelpCircle className="w-4 h-4" /> Explain error
                  </button>
                  <button onClick={runAnalyze} disabled={toolsLoading} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-100 text-gray-800 hover:bg-gray-200 text-sm disabled:opacity-50">
                    <FileCode className="w-4 h-4" /> Analyze code
                  </button>
                  <button onClick={runFilesAnalyze} disabled={toolsLoading} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-100 text-gray-800 hover:bg-gray-200 text-sm disabled:opacity-50">
                    <FileText className="w-4 h-4" /> Analyze files
                  </button>
                  <button onClick={runDesignFromUrl} disabled={toolsLoading} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-100 text-gray-800 hover:bg-gray-200 text-sm disabled:opacity-50">
                    <Globe className="w-4 h-4" /> Design from URL
                  </button>
                </div>
                {toolsLoading && <p className="text-sm text-gray-500 mb-2">Running…</p>}
                {toolsReport && (
                  <div className="mt-3 p-3 rounded-lg bg-gray-50 border border-gray-200 text-sm">
                    {toolsReport.type === 'validate' && (
                      <>
                        {toolsReport.data.error ? (
                          <p className="text-red-600">{toolsReport.data.error}</p>
                        ) : (
                          <>
                            <p className={toolsReport.data.valid ? 'text-green-700' : 'text-amber-700'}>
                              {toolsReport.data.valid ? 'No issues found.' : 'Issues found. Fix available below.'}
                            </p>
                            {!toolsReport.data.valid && toolsReport.data.fixed_code && (
                              <button onClick={applyValidateFix} className="mt-2 px-3 py-1.5 rounded bg-gray-200 text-gray-900 hover:bg-gray-300 text-xs">Apply fix</button>
                            )}
                          </>
                        )}
                      </>
                    )}
                    {toolsReport.type === 'security' && (
                      <pre className="whitespace-pre-wrap text-gray-700 font-mono text-xs">{toolsReport.data.error || toolsReport.data.report || (toolsReport.data.checklist || []).join('\n')}</pre>
                    )}
                    {toolsReport.type === 'a11y' && (
                      <pre className="whitespace-pre-wrap text-gray-700 font-mono text-xs">{toolsReport.data.error || toolsReport.data.report}</pre>
                    )}
                    {toolsReport.type === 'optimize' && (
                      <pre className="whitespace-pre-wrap text-gray-700 font-mono text-xs">{toolsReport.data.error || toolsReport.data.optimized_code || toolsReport.data.report || JSON.stringify(toolsReport.data)}</pre>
                    )}
                    {toolsReport.type === 'explain' && (
                      <pre className="whitespace-pre-wrap text-gray-700 font-mono text-xs">{toolsReport.data.error || toolsReport.data.explanation || toolsReport.data.report}</pre>
                    )}
                    {toolsReport.type === 'analyze' && (
                      <pre className="whitespace-pre-wrap text-gray-700 font-mono text-xs">{toolsReport.data.error || toolsReport.data.result || toolsReport.data.report}</pre>
                    )}
                    {toolsReport.type === 'files' && (
                      <pre className="whitespace-pre-wrap text-gray-700 font-mono text-xs">{toolsReport.data.error || toolsReport.data.report || JSON.stringify(toolsReport.data)}</pre>
                    )}
                    {toolsReport.type === 'design' && (
                      <pre className="whitespace-pre-wrap text-gray-700 font-mono text-xs">{toolsReport.data.error || (toolsReport.data.files ? 'Design applied to editor.' : toolsReport.data.report) || JSON.stringify(toolsReport.data)}</pre>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
        )}
      </div>

      {/* Status bar — PHASE 6: Dev only (no token counter / errors in Simple) */}
      {devMode && (
      <div className="h-6 border-t border-stone-200 flex items-center justify-between px-3 text-xs text-stone-600 flex-shrink-0 bg-[#FAF9F7]">
        <div className="flex items-center gap-4">
          <span>{versions.length > 0 ? `Project · v${versions.length}` : 'New Project'}</span>
          <span>{currentVersion ? 'main' : '—'}</span>
          {lastError && <span className="text-red-600">1 error</span>}
          {!lastError && <span className="text-stone-500">0 errors</span>}
          <span className="text-stone-500">0 warnings</span>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          {(tokensPerStep.plan > 0 || tokensPerStep.generate > 0) && (
            <span className="text-stone-500" title="Per-step token usage">
              {tokensPerStep.plan > 0 && <>Plan: ~{(tokensPerStep.plan / 1000).toFixed(1)}k</>}
              {tokensPerStep.plan > 0 && tokensPerStep.generate > 0 && ' · '}
              {tokensPerStep.generate > 0 && <>Generate: ~{(tokensPerStep.generate / 1000).toFixed(1)}k</>}
            </span>
          )}
          {qualityGateResult != null && (
            <span className={qualityGateResult.passed ? 'text-green-600' : 'text-amber-600'} title="Quality gate">
              Quality: {qualityGateResult.score}% {qualityGateResult.passed ? '✓' : '(review)'}
            </span>
          )}
          <button onClick={() => setFileSearchOpen(true)} className="hover:text-gray-800">Ctrl+P</button>
          <button onClick={() => setCommandPaletteOpen(true)} className="hover:text-gray-800">Ctrl+K</button>
          {user && <span>Tokens: {user.token_balance?.toLocaleString() ?? 0}</span>}
        </div>
      </div>
      )}

      {/* Bottom Chat Panel – Agent dropdown + input + Send */}
      <div className="border-t border-stone-200 bg-[#FAF9F7] p-3 flex-shrink-0 relative z-[100] isolate">
        {isBuilding && (
          <div className="mb-3">
            {currentPhase && (
              <div className="text-xs text-gray-600 mb-1 flex items-center gap-2">
                <span className="inline-block w-2 h-2 rounded-full animate-pulse" style={{ background: '#1A1A1A' }} />
                {currentPhase}
              </div>
            )}
            <div className="h-1 bg-gray-200 rounded-full overflow-hidden">
              <motion.div 
                className="h-full rounded-full"
                style={{ background: '#1A1A1A' }}
                initial={{ width: 0 }}
                animate={{ width: `${buildProgress}%` }}
              />
            </div>
          </div>
        )}

        {/* Add API key banner when last message is key/network error */}
        {messages.some(m => m.error && (m.content || '').toLowerCase().includes('api key')) && (
          <div className="mb-3 flex items-center justify-between gap-3 px-4 py-2.5 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-sm">
            <span>Check Settings → API & Environment: your saved keys are used for builds. If you see errors, re-save your OpenAI or Anthropic key and try again.</span>
            <button type="button" onClick={() => navigate('/app/settings')} className="shrink-0 px-3 py-1.5 rounded-lg bg-amber-200 hover:bg-amber-300 font-medium text-amber-900">Open Settings</button>
          </div>
        )}

        {/* Try these prompts when no messages yet */}
        {messages.length === 0 && (
          <div className="mb-3">
            <p className="text-xs text-gray-500 mb-2">First time? Add your API keys in <button type="button" onClick={() => navigate('/app/settings')} className="underline hover:text-gray-700">Settings</button> to build with AI.</p>
            <span className="text-xs text-gray-500">Try these:</span>
            <div className="flex flex-wrap gap-2 mt-1">
              {['Build a todo app', 'Create a landing page', 'Add a contact form', 'Make a counter component'].map((prompt) => (
                <button key={prompt} type="button" onClick={() => setInput(prompt)} className="px-3 py-1.5 rounded-lg bg-white text-gray-700 hover:bg-gray-100 text-sm border border-gray-200">{prompt}</button>
              ))}
            </div>
          </div>
        )}

        {messages.length > 0 && (
          <div className="max-h-32 overflow-y-auto mb-3 space-y-2">
            {messages.slice(-4).map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] px-3 py-2 rounded-lg text-sm ${
                  msg.role === 'user' 
                    ? 'bg-gray-100 text-gray-900' 
                    : msg.error 
                      ? 'bg-red-50 text-red-700 border border-red-200'
                      : 'bg-white border border-gray-200 text-gray-800'
                }`}>
                  {msg.isBuilding ? (
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 border-2 border-gray-300 rounded-full animate-spin" style={{ borderTopColor: '#1A1A1A' }} />
                      <span>{msg.content}</span>
                    </div>
                  ) : (
                    <>
                      <span className={msg.content && msg.content.includes('\n') ? 'whitespace-pre-wrap block text-left max-h-48 overflow-y-auto' : ''}>{msg.content}</span>
                      {msg.planSuggestions?.length > 0 && (
                        <div className="mt-2 pt-2 border-t border-gray-200">
                          <p className="text-xs text-gray-500 mb-1">Suggestions</p>
                          <div className="flex flex-wrap gap-1">
                            {msg.planSuggestions.map((s, j) => (
                              <button key={j} type="button" onClick={() => setInput(String(s))} className="px-2 py-1 rounded bg-gray-100 hover:bg-gray-200 text-xs text-gray-700">{String(s)}</button>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>
        )}

        {attachedFiles.length > 0 && (
          <div className="flex gap-2 mb-3 flex-wrap">
            {attachedFiles.map((file, i) => (
              <div key={i} className="flex items-center gap-2 px-3 py-1.5 bg-white border border-gray-200 rounded-lg text-sm">
                {file.type.startsWith('image/') ? (
                  <Image className="w-4 h-4 text-orange-600" />
                ) : (
                  <FileText className="w-4 h-4 text-green-600" />
                )}
                <span className="text-gray-700 max-w-[150px] truncate">{file.name}</span>
                <button onClick={() => removeFile(i)} className="text-gray-500 hover:text-gray-900">
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        )}

        {nextSuggestions.length > 0 && (
          <div className="mb-3">
            <span className="text-xs text-gray-500 mr-2">What next?</span>
            <div className="flex flex-wrap gap-2 mt-1">
              {nextSuggestions.map((s, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => { setInput(String(s)); setNextSuggestions([]); }}
                  className="px-3 py-1.5 rounded-lg bg-white text-gray-700 hover:bg-gray-100 text-sm border border-gray-200"
                >
                  {String(s)}
                </button>
              ))}
            </div>
          </div>
        )}

        {devMode && (
        <div className="text-xs text-gray-500 mb-1.5 flex items-center justify-between flex-wrap gap-2">
          <select
            value={buildMode}
            onChange={(e) => setBuildMode(e.target.value)}
            className="px-2 py-1 rounded border border-gray-200 bg-white text-gray-700 text-xs cursor-pointer outline-none"
          >
            <option value="agent">Auto</option>
            <option value="quick">Quick</option>
            <option value="plan">Plan</option>
            <option value="thinking">Thinking</option>
            <option value="swarm">Swarm</option>
          </select>
          <span><kbd className="px-1 py-0.5 rounded bg-gray-200 text-gray-600">Ctrl+K</kbd></span>
        </div>
        )}
        <form onSubmit={handleSubmit} className="flex gap-2 items-stretch">
          <div className="flex shrink-0">
            <ModelSelector selectedModel={selectedModel} onSelectModel={setSelectedModel} variant="chat" />
          </div>
          <div className="flex-1 flex items-center gap-2 px-3 py-2.5 bg-white rounded-lg border border-gray-300 min-w-0 shadow-sm">
            {isRecording ? (
              <VoiceWaveform
                stream={audioStream}
                onStop={stopRecording}
                onConfirm={confirmRecording}
                isRecording={isRecording}
              />
            ) : (
              <button
                type="button"
                onClick={isTranscribing ? undefined : startRecording}
                disabled={isTranscribing}
                data-testid="voice-input-button"
                className={`p-2 rounded-md transition ${
                  isTranscribing ? 'text-[#666666] cursor-wait' : 'text-gray-500 hover:text-gray-900 hover:bg-gray-200'
                }`}
                title={isTranscribing ? 'Transcribing...' : 'Voice input'}
              >
                {isTranscribing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Mic className="w-4 h-4" />}
              </button>
            )}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              data-testid="file-attach-button"
              className="p-2 rounded-md text-gray-500 hover:text-gray-900 hover:bg-gray-200 transition"
              title="Add file (image, PDF, text)"
            >
              <Paperclip className="w-4 h-4" />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/*,.pdf,.txt,.md"
              onChange={handleFileSelect}
              className="hidden"
            />
            
            <div className="h-4 w-px bg-gray-300" />
            
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              data-testid="chat-input"
              placeholder={versions.length > 0 ? "Describe changes... (@ file, / fix)" : "Describe what you want to build..."}
              className="flex-1 bg-transparent text-gray-900 placeholder-gray-400 outline-none text-sm min-w-0"
              disabled={isBuilding}
            />
          </div>
          
          <button
            type="submit"
            disabled={!input.trim() || isBuilding}
            data-testid="submit-button"
            className="relative z-10 px-4 py-2.5 rounded-lg text-sm font-medium disabled:opacity-30 disabled:cursor-not-allowed transition flex items-center gap-2 shrink-0"
            style={{ background: '#1A1A1A', color: '#FFFFFF' }}
            onMouseEnter={e => { if (!e.target.disabled) e.target.style.background = '#E05A25'; }}
            onMouseLeave={e => { if (!e.target.disabled) e.target.style.background = '#1A1A1A'; }}
            title={versions.length > 0 ? 'Send update' : 'Send & build'}
          >
            {isBuilding ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                <Send className="w-4 h-4" />
                <span>{versions.length > 0 ? 'Update' : 'Build'}</span>
              </>
            )}
          </button>
        </form>
      </div>

      {/* One-click deploy modal */}
      {showDeployModal && (
        <div className="fixed inset-0 z-[300] flex items-center justify-center bg-zinc-900/50 backdrop-blur-sm" onClick={() => setShowDeployModal(false)}>
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4 p-6 border border-gray-200" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Deploy your app</h3>
            <p className="text-sm text-gray-600 mb-4">Your deploy ZIP has been downloaded (or use the download again from Ctrl+K → Deploy). Upload it to one of these platforms:</p>
            <div className="flex flex-col gap-2">
              <a href="https://vercel.com/new" target="_blank" rel="noopener noreferrer" className="flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-zinc-900 text-white text-sm font-medium hover:bg-gray-800">
                Deploy with Vercel
              </a>
              <a href="https://app.netlify.com/drop" target="_blank" rel="noopener noreferrer" className="flex items-center justify-center gap-2 px-4 py-3 rounded-lg text-sm font-medium text-white" style={{ background: '#1A1A1A' }}>
                Deploy with Netlify
              </a>
              <a href="https://railway.app/new" target="_blank" rel="noopener noreferrer" className="flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-[#0B0D0E] text-white text-sm font-medium hover:bg-[#1a1d1f] border border-gray-600">
                Deploy with Railway
              </a>
            </div>
            <button type="button" onClick={() => setShowDeployModal(false)} className="mt-4 w-full py-2 text-sm text-gray-600 hover:text-gray-900 border border-gray-200 rounded-lg">Close</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Workspace;

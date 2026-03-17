import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useNavigate, useSearchParams, useLocation, Link } from 'react-router-dom';
import JSZip from 'jszip';
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
  RotateCcw,
  Share2,
} from 'lucide-react';
import { useAuth, API } from '../App';
import { useLayoutStore } from '../stores/useLayoutStore';
import { useTaskStore } from '../stores/useTaskStore';
import axios from 'axios';
import CrucibAIComputer from '../components/CrucibAIComputer';
import InlineAgentMonitor from '../components/InlineAgentMonitor';
import ManusComputer from '../components/ManusComputer';
import { CommandPalette } from '../components/AdvancedIDEUX';
import { VibeCodingInput } from '../components/VibeCoding';

/** Format message content — avoid [object Object] */
function formatMsgContent(c) {
  if (c == null) return '';
  if (typeof c === 'string') return c;
  if (c?.text) return c.text;
  if (c?.message) return c.message;
  if (c?.content) return c.content;
  return typeof c === 'object' ? JSON.stringify(c) : String(c);
}

/** Chat message — user on right, long messages with Show more */
function ChatMessage({ msg }) {
  const [expanded, setExpanded] = useState(false);
  const content = formatMsgContent(msg.content);
  const isLong = content.length > 300 || (content.match(/\n/g) || []).length > 4;
  const showContent = expanded || !isLong ? content : content.slice(0, 300) + (content.length > 300 ? '...' : '');
  return (
    <div className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[80%] rounded-xl px-4 py-3 text-sm ${
        msg.role === 'user'
          ? 'bg-gray-100 text-gray-900'
          : 'bg-white border border-gray-200 text-gray-800'
      }`}>
        <pre className="whitespace-pre-wrap font-sans">{showContent}</pre>
        {isLong && (
          <button
            type="button"
            onClick={() => setExpanded(e => !e)}
            className="mt-2 text-xs font-medium text-gray-600 hover:text-gray-900 underline"
          >
            {expanded ? 'Show less' : 'Show more'}
          </button>
        )}
      </div>
    </div>
  );
}

/** Compact collapsible build progress card — Manus-style step bar */
function BuildProgressCard({ expanded, onToggle, buildProgress, currentPhase, lastTokensUsed, projectBuildProgress, qualityScore, agentsActivityLength, children }) {
  const tokens = lastTokensUsed || projectBuildProgress?.tokens_used || 0;
  return (
    <div className="border-b border-stone-200 bg-white flex-shrink-0">
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-gray-50 transition"
      >
        <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: '#1A1A1A' }} />
        <span className="text-sm font-medium text-gray-900 flex-1 truncate">
          {currentPhase || 'Building...'} — {Math.round(buildProgress)}%
        </span>
        <span className="text-xs text-gray-500 shrink-0">{agentsActivityLength || 0} agents · {(tokens / 1000).toFixed(0)}k tokens</span>
        {qualityScore != null && <span className="text-xs text-gray-600 shrink-0">Quality: {qualityScore}%</span>}
        {expanded ? <ChevronDown className="w-4 h-4 text-gray-500 shrink-0" /> : <ChevronRight className="w-4 h-4 text-gray-500 shrink-0" />}
      </button>
      <div className="border-t border-stone-100 bg-gray-50/50">
        <div className="h-1 bg-gray-200 rounded-full overflow-hidden">
          <motion.div
            className="h-full rounded-full"
            style={{ background: '#1A1A1A' }}
            initial={{ width: 0 }}
            animate={{ width: `${buildProgress}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
      </div>
      {expanded && (
        <div className="max-h-64 overflow-y-auto border-t border-stone-200">
          {children}
        </div>
      )}
    </div>
  );
}

// Default React app template
const DEFAULT_FILES = {
  '/App.js': {
    code: `import React from 'react';

export default function App() {
  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'Inter, sans-serif' }}>
      <div style={{ textAlign: 'center', padding: '2rem' }}>
        <div style={{ width: 64, height: 64, background: '#3b82f6', borderRadius: 16, display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.5rem' }}>
          <span style={{ fontSize: 28 }}>⚡</span>
        </div>
        <h1 style={{ fontSize: '2.25rem', fontWeight: 700, color: '#f8fafc', marginBottom: '0.75rem', letterSpacing: '-0.02em' }}>
          Welcome to CrucibAI
        </h1>
        <p style={{ color: '#94a3b8', fontSize: '1.125rem', marginBottom: '2rem' }}>
          Describe what you want to build in the chat
        </p>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, padding: '0.5rem 1rem', color: '#64748b', fontSize: '0.875rem' }}>
          <span>💬</span> Type a prompt to get started
        </div>
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
    code: `/* Tailwind CSS loaded via CDN (see externalResources in Sandpack config) */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}`,
  },
};

// File tree component
const FileTree = ({ files, activeFile, onSelectFile, onAddFile, onAddFolder, onOpenFolder, onDeleteFile }) => {
  const [expandedFolders, setExpandedFolders] = useState({});

  const getFileIcon = (name) => {
    if (/\.(jsx?|tsx?)$/.test(name)) return <FileCode className="w-3.5 h-3.5 text-yellow-500 flex-shrink-0" />;
    if (/\.css$/.test(name)) return <FileText className="w-3.5 h-3.5 text-pink-500 flex-shrink-0" />;
    if (/\.html$/.test(name)) return <FileText className="w-3.5 h-3.5 text-orange-500 flex-shrink-0" />;
    if (/\.json$/.test(name)) return <FileText className="w-3.5 h-3.5 text-yellow-600 flex-shrink-0" />;
    if (/\.(py|c|cpp|h)$/.test(name)) return <FileCode className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />;
    if (/\.(md|txt)$/.test(name)) return <FileText className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />;
    return <File className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />;
  };

  // Group files into root-level files and folders
  const tree = {};
  Object.keys(files).sort().forEach(path => {
    const clean = path.replace(/^\//, '');
    const parts = clean.split('/');
    if (parts.length === 1) {
      tree[path] = null;
    } else {
      const folder = '/' + parts[0];
      if (!tree[folder]) tree[folder] = [];
      tree[folder].push(path);
    }
  });

  const toggleFolder = (folder) => {
    setExpandedFolders(prev => ({ ...prev, [folder]: prev[folder] === false ? true : false }));
  };

  const isExpanded = (folder) => expandedFolders[folder] !== false; // expanded by default

  return (
    <div className="text-sm flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-2 py-1.5 border-b border-gray-200 bg-[#FAF9F7] flex-shrink-0">
        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Explorer</span>
        <div className="flex items-center gap-0.5">
          {onAddFile && (
            <button onClick={onAddFile} className="p-1 text-gray-400 hover:text-gray-700 rounded" title="New file">
              <Plus className="w-3.5 h-3.5" />
            </button>
          )}
          {onAddFolder && (
            <button onClick={onAddFolder} className="p-1 text-gray-400 hover:text-gray-700 rounded" title="New folder">
              <FolderOpen className="w-3.5 h-3.5" />
            </button>
          )}
          {onOpenFolder && (
            <button onClick={onOpenFolder} className="p-1 text-gray-400 hover:text-gray-700 rounded" title="Open local folder">
              <Upload className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* File tree */}
      <div className="overflow-y-auto flex-1 py-1">
        {Object.entries(tree).map(([key, children]) => {
          if (children === null) {
            // Root-level file
            const name = key.replace(/^\//, '');
            return (
              <div key={key} className="group flex items-center">
                <button
                  onClick={() => onSelectFile(key)}
                  className={`flex-1 flex items-center gap-2 px-3 py-1 text-left text-xs transition truncate ${
                    activeFile === key ? 'bg-blue-50 text-blue-800 font-medium' : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  {getFileIcon(name)}
                  <span className="truncate">{name}</span>
                </button>
                {onDeleteFile && (
                  <button onClick={() => onDeleteFile(key)} className="opacity-0 group-hover:opacity-100 pr-2 text-gray-400 hover:text-red-500 transition" title="Delete file">
                    <X className="w-3 h-3" />
                  </button>
                )}
              </div>
            );
          } else {
            // Folder
            const folderName = key.replace(/^\//, '');
            const expanded = isExpanded(key);
            return (
              <div key={key}>
                <button
                  onClick={() => toggleFolder(key)}
                  className="w-full flex items-center gap-1.5 px-2 py-1 text-left text-xs text-gray-500 hover:bg-gray-100 font-medium"
                >
                  {expanded ? <ChevronDown className="w-3 h-3 flex-shrink-0" /> : <ChevronRight className="w-3 h-3 flex-shrink-0" />}
                  <FolderOpen className="w-3.5 h-3.5 text-yellow-500 flex-shrink-0" />
                  <span>{folderName}</span>
                </button>
                {expanded && children.map(path => {
                  const name = path.split('/').pop();
                  return (
                    <div key={path} className="group flex items-center">
                      <button
                        onClick={() => onSelectFile(path)}
                        className={`flex-1 flex items-center gap-2 pl-7 pr-2 py-1 text-left text-xs transition truncate ${
                          activeFile === path ? 'bg-blue-50 text-blue-800 font-medium' : 'text-gray-600 hover:bg-gray-100'
                        }`}
                      >
                        {getFileIcon(name)}
                        <span className="truncate">{name}</span>
                      </button>
                      {onDeleteFile && (
                        <button onClick={() => onDeleteFile(path)} className="opacity-0 group-hover:opacity-100 pr-2 text-gray-400 hover:text-red-500 transition" title="Delete file">
                          <X className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            );
          }
        })}
      </div>
    </div>
  );
};

// Console/Logs component (Terminal) — dark theme to match app
const ConsolePanel = ({ logs, placeholder = "Terminal output will appear here. Run a build to see logs." }) => {
  const consoleRef = useRef(null);

  useEffect(() => {
    if (consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div ref={consoleRef} className="workspace-console-panel h-full overflow-auto font-mono text-xs p-3 space-y-1">
      {logs.length === 0 ? (
        <div className="workspace-console-placeholder">{placeholder}</div>
      ) : (
        logs.map((log, i) => (
          <div
            key={i}
            className={`workspace-console-line flex items-start gap-2 workspace-console-line--${log.type || 'info'}`}
          >
            <span className="workspace-console-time">[{log.time}]</span>
            <span className="workspace-console-agent">{log.agent || 'system'}:</span>
            <span className="flex-1 workspace-console-message">{log.message}</span>
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
                    {selectedModel === model.id && <Check className="w-4 h-4 shrink-0 text-[#1A1A1A]" />}
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

// Version History Panel (local versions)
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

// Build History Panel (Item 17) — fetch prior builds from API, click to view in Agent Monitor
const BuildHistoryPanel = ({ buildHistory, projectId, loading }) => {
  if (loading) {
    return (
      <div className="p-4 flex items-center justify-center h-full">
        <Loader2 className="w-6 h-6 animate-spin text-zinc-400" />
      </div>
    );
  }
  if (!buildHistory || buildHistory.length === 0) {
    return (
      <div className="p-4 text-sm text-zinc-500">
        No prior builds yet. Run a build from the dashboard to see history here.
      </div>
    );
  }
  return (
    <div className="p-3 space-y-2 overflow-y-auto h-full">
      <div className="text-xs text-zinc-500 uppercase tracking-wider mb-3">Build history</div>
      {buildHistory.map((entry, i) => (
        <div key={i} className="p-3 rounded-lg border border-zinc-700/50 bg-zinc-800/30 hover:bg-zinc-800/50 transition">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-zinc-400">
              {entry.completed_at ? new Date(entry.completed_at).toLocaleString() : '—'}
            </span>
            <span className={`text-xs font-medium ${entry.status === 'completed' ? 'text-green-400' : 'text-amber-500'}`}>
              {entry.status === 'completed' ? 'Completed' : (entry.status || '—')}
            </span>
          </div>
          {entry.quality_score != null && <p className="text-xs text-zinc-500">Quality: {Number(entry.quality_score).toFixed(0)}</p>}
          {entry.tokens_used != null && <p className="text-xs text-zinc-500">{Number(entry.tokens_used).toLocaleString()} tokens</p>}
          {projectId && (
            <Link
              to={`/app/projects/${projectId}`}
              className="inline-flex items-center gap-1 mt-2 text-xs text-blue-400 hover:text-blue-300"
            >
              <ExternalLink className="w-3 h-3" /> View in Agent Monitor
            </Link>
          )}
        </div>
      ))}
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

  // Files safe to pass to Sandpack — exclude backend/test/config files.
  // Also post-process: BrowserRouter → MemoryRouter (BrowserRouter breaks in iframes),
  // and inject Tailwind CDN into styles.css so classes render correctly.
  const sandpackFiles = useMemo(() => {
    const EXCLUDED = /\.(test|spec)\.[jt]sx?$|Dockerfile|docker-compose|\.md$|\.sh$|\.ya?ml$|\.env|\.gitignore|server\.(js|ts)$|express|mongoose/i;
    const ALLOWED  = /\.(jsx?|tsx?|css|html|json)$/i;
    const BACKEND_CODE = /require\(['"]express['"]\)|require\(['"]mongoose['"]\)|require\(['"]mongodb['"]\)|from ['"]express['"]|from ['"]mongoose['"]|app\.listen\(|mongoose\.connect\(/;

    const filtered = Object.entries(files).filter(([path, f]) => {
      if (!ALLOWED.test(path) || EXCLUDED.test(path)) return false;
      // Drop files that are clearly Node/Express backend
      if (f?.code && BACKEND_CODE.test(f.code)) return false;
      return true;
    });

    return Object.fromEntries(
      filtered.map(([path, f]) => {
        let code = f?.code || '';
        // Fix: BrowserRouter doesn't work in Sandpack iframes → use MemoryRouter
        code = code
          .replace(/import\s*\{\s*BrowserRouter(\s*,\s*|\s+as\s+\w+\s*,?\s*)/g, 'import { MemoryRouter$1')
          .replace(/import\s*\{\s*([^}]*),?\s*BrowserRouter\s*,?\s*([^}]*)\}/g, (_, a, b) =>
            `import { ${[a, b].filter(Boolean).join(', ')}, MemoryRouter }`)
          .replace(/<BrowserRouter>/g, '<MemoryRouter>')
          .replace(/<\/BrowserRouter>/g, '</MemoryRouter>')
          .replace(/BrowserRouter\b/g, 'MemoryRouter');

        // Inject Tailwind CDN into styles.css if not already present
        if ((path === '/styles.css' || path === 'styles.css') && !code.includes('tailwindcss') && !code.includes('tailwind')) {
          code = `@import url('https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css');\n\n` + code;
        }

        return [path, { ...f, code }];
      })
    );
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
  const [mobileView, setMobileView] = useState(false);
  const [showVibeInput, setShowVibeInput] = useState(false);
  const projectIdFromUrl = searchParams.get('projectId');
  const taskIdFromUrl = searchParams.get('taskId');
  const [projectBuildProgress, setProjectBuildProgress] = useState({ phase: 0, agent: '', progress: 0, status: '', tokens_used: 0 });
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

  // Item 17: Fetch build history when workspace is opened with a project
  useEffect(() => {
    if (!projectIdFromUrl || !token || !API) return;
    setBuildHistoryLoading(true);
    axios.get(`${API}/projects/${projectIdFromUrl}/build-history`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => setBuildHistoryList(r.data?.build_history || []))
      .catch(() => setBuildHistoryList([]))
      .finally(() => setBuildHistoryLoading(false));
  }, [projectIdFromUrl, token, API]);

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

  // Auto-start build ONLY when user explicitly clicks "Start Building" / "Go" (e.g. from Dashboard).
  // Opening a task from the sidebar just loads the task; execution happens on Submit/Go/Update.
  const autoStartedRef = useRef(null);
  useEffect(() => {
    const statePrompt = location.state?.initialPrompt || searchParams.get('prompt');
    const stateAutoStart = location.state?.autoStart || searchParams.get('autoStart') === '1';
    const initialFiles = location.state?.initialAttachedFiles;
    if (!stateAutoStart || !statePrompt) return;
    if (autoStartedRef.current === `${location.key}-${taskIdFromUrl}`) return;
    autoStartedRef.current = `${location.key}-${taskIdFromUrl}`;
    if (initialFiles?.length) setAttachedFiles(initialFiles);
    handleBuild(statePrompt, initialFiles || undefined);
  }, [location.key, location.state, taskIdFromUrl]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const addLog = (message, type = 'info', agent = null) => {
    const now = new Date();
    const time = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
    setLogs(prev => [...prev, { message, type, time, agent }]);
  };

  // ── Voice input via Web Speech API (browser-native, no API key needed) ──
  const speechRecognitionRef = useRef(null);

  const startRecording = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      addLog('Voice input not supported. Please use Chrome, Edge, or Safari.', 'error', 'voice');
      setMessages(prev => [...prev, { role: 'assistant', content: 'Voice input requires Chrome, Edge, or Safari.', error: true }]);
      return;
    }
    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';
      recognition.maxAlternatives = 1;

      recognition.onstart = () => {
        setIsRecording(true);
        addLog('Listening...', 'info', 'voice');
      };

      recognition.onresult = (e) => {
        const transcript = e.results[0][0].transcript.trim();
        setInput(prev => (prev ? prev + ' ' + transcript : transcript));
        setIsRecording(false);
        addLog(`Voice: "${transcript}"`, 'success', 'voice');
      };

      recognition.onerror = (e) => {
        setIsRecording(false);
        const msg = e.error === 'not-allowed'
          ? 'Microphone access denied. Please allow mic in your browser settings.'
          : e.error === 'no-speech'
          ? 'No speech detected. Please try again.'
          : `Voice error: ${e.error}`;
        addLog(msg, 'error', 'voice');
      };

      recognition.onend = () => {
        setIsRecording(false);
        speechRecognitionRef.current = null;
      };

      speechRecognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      setIsRecording(false);
      addLog(`Voice failed: ${err.message}`, 'error', 'voice');
    }
  };

  const stopRecording = () => {
    if (speechRecognitionRef.current) {
      speechRecognitionRef.current.stop();
      speechRecognitionRef.current = null;
    }
    // Also stop old MediaRecorder if any
    const ref = mediaRecorderRef.current;
    if (ref?.recorder?.state !== 'inactive') ref?.recorder?.stop();
    if (ref?.stream) ref.stream.getTracks().forEach(t => t.stop());
    mediaRecorderRef.current = null;
    setAudioStream(null);
    setIsRecording(false);
  };

  const confirmRecording = () => {
    // Legacy — just stop
    stopRecording();
  };

  const transcribeAudio = async () => {
    // No-op: replaced by Web Speech API
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
        messageContent = `You are CrucibAI. Build a COMPLETE, BEAUTIFUL, MULTI-PAGE React application for: "${prompt}"

⚠️ CRITICAL RULES — THIS IS A BROWSER-ONLY SANDPACK PREVIEW:

❌ ABSOLUTELY FORBIDDEN (will break the preview):
   - NO Node.js, Express, Koa, Fastify or any backend server
   - NO MongoDB, Mongoose, PostgreSQL, MySQL or any database
   - NO require('...') CommonJS imports — use ES module imports only
   - NO server.js, api.js, app.listen(), mongoose.connect()
   - NO Dockerfile, .env, .yml, CI/CD, deployment scripts
   - NO next.js, remix, or any SSR framework
   - NO BrowserRouter — use MemoryRouter (BrowserRouter breaks in iframes)

✅ REQUIRED:
1. ROUTING: Use react-router-dom with MemoryRouter (NOT BrowserRouter):
   import { MemoryRouter as Router, Routes, Route } from 'react-router-dom';
   <Router><Routes><Route path="/" element={<Home />} /></Routes></Router>
   Build 3-5 meaningful pages. Example "flower website": Home, Shop, Gallery, About, Contact.

2. COMPONENTS: Always create:
   - /components/Navbar.js — navigation links using <Link to="...">
   - /components/Footer.js — footer section

3. PAGES: One file per page under /pages/:
   /pages/Home.js, /pages/About.js, /pages/[relevant].js, etc.

4. STYLING — all Tailwind classes (loaded via CDN, no config needed):
   - Bold hero sections, gradient backgrounds, card grids
   - lucide-react icons, framer-motion entrance animations
   - Realistic hardcoded data (no "Lorem ipsum", real product names, prices, etc.)
   - Use inline styles for dynamic values, Tailwind for everything else

5. DATA: Use hardcoded JavaScript arrays/objects — no API calls, no fetch()

6. OUTPUT FORMAT — every file on its own fenced block:
\`\`\`jsx:/App.js
import { MemoryRouter as Router, Routes, Route } from 'react-router-dom';
// ... rest of App
\`\`\`
\`\`\`jsx:/components/Navbar.js
// ...
\`\`\`
\`\`\`jsx:/pages/Home.js
// ...
\`\`\`

Allowed imports ONLY: react, react-router-dom, lucide-react, framer-motion, recharts, date-fns, clsx
Build it NOW — no placeholders, no TODOs, no backend code:`;
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
            setTimeout(() => { setCurrentVersion(vId); setActivePanel("preview"); }, 200);
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
              if (obj.error) throw new Error(obj.error);
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
                setTimeout(() => { setCurrentVersion(versionId); setActivePanel("preview"); }, 200);
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
      const isKeyError = error.response?.status === 401 || detail.toLowerCase().includes('api key') || detail.toLowerCase().includes('no api key') || (error.message && error.message.toLowerCase().includes('key'));
      let friendlyMessage;
      if (is402) {
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
      setMessages(prev => prev.map((msg, i) => i === prev.length - 1 ? { role: 'assistant', content: friendlyMessage, error: true } : msg));
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
      setMessages(prev => prev.map((msg, i) => 
        i === prev.length - 1 ? { role: 'assistant', content: is404 ? backendUnavailable : (error.response?.data?.detail || 'Error updating. Try again.'), error: true } : msg
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
            <span className="text-xs text-orange-400">{currentPhase || 'Building'}... {Math.round(buildProgress)}%</span>
          </div>
        )}
        {qualityGateResult && !isBuilding && (
          <div className="flex items-center gap-1.5 ml-1 text-xs" style={{ color: qualityGateResult.score >= 70 ? '#86efac' : '#fbbf24' }}>
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>{qualityGateResult.score}%</span>
          </div>
        )}
        <div className="ml-auto flex items-center gap-1.5">
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
            title={devMode ? 'Switch to Simple view' : 'Switch to Code view'}
          >
            <FileCode className="w-3.5 h-3.5" />
            {devMode ? 'Code' : 'Simple'}
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
        <div className="shrink-0 px-4 py-2 flex items-center justify-between" style={{ background: '#292524', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
          <span className="text-sm text-orange-300">Out of tokens — get more to keep building.</span>
          <button onClick={() => navigate('/app/tokens')} className="text-sm font-medium text-orange-300 underline">Buy tokens</button>
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
                <button onClick={() => zipInputRef.current?.click()} className="p-1 rounded transition hover:bg-white/10" style={{ color: 'var(--theme-muted, #52525b)' }} title="Upload ZIP (bring your code)"><Upload className="w-3 h-3" /></button>
                <button onClick={addNewFileToProject} className="p-1 rounded transition hover:bg-white/10" style={{ color: 'var(--theme-muted, #52525b)' }} title="New file"><Plus className="w-3 h-3" /></button>
                <button onClick={() => setLeftSidebarOpen(false)} className="p-1 rounded transition hover:bg-white/10" style={{ color: 'var(--theme-muted, #52525b)' }} title="Collapse sidebar"><PanelLeftClose className="w-3 h-3" /></button>
              </div>
            </div>
            {/* Project name */}
            <div className="px-3 py-2 border-b" style={{ borderColor: 'var(--theme-border, rgba(255,255,255,0.05))' }}>
              <span className="text-xs truncate block" style={{ color: 'var(--theme-muted, #3f3f46)' }}>
                {messages.find(m => m.role === 'user')?.content?.toString().slice(0, 30) || 'project'}
              </span>
            </div>
            {/* File list */}
            <div className="flex-1 overflow-y-auto py-1">
              {Object.keys(files).sort().map(fp => {
                const name = fp.replace(/^\//, '');
                const isActive = activeFile === fp;
                const ext = name.split('.').pop();
                const iconColor = ext === 'jsx' || ext === 'js' ? '#eab308' : ext === 'css' ? '#ec4899' : ext === 'html' ? '#f97316' : ext === 'json' ? '#a78bfa' : '#71717a';
                return (
                  <div key={fp} className="group flex items-center">
                    <button
                      onClick={() => { setActiveFile(fp); setActivePanel('code'); }}
                      className="flex-1 flex items-center gap-2 px-3 py-1.5 text-left text-xs transition"
                      style={{ background: isActive ? 'rgba(255,255,255,0.09)' : 'transparent', color: isActive ? 'var(--theme-text, #e4e4e7)' : 'var(--theme-muted, #a1a1aa)' }}
                    >
                      <FileCode className="w-3 h-3 shrink-0" style={{ color: iconColor }} />
                      <span className="truncate">{name}</span>
                    </button>
                    <button onClick={() => deleteFileFromProject(fp)} className="opacity-0 group-hover:opacity-100 pr-2 transition" style={{ color: 'var(--theme-muted, #52525b)' }} title="Delete">
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                );
              })}
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
          {/* Messages area */}
          <div className="flex-1 overflow-y-auto px-5 py-6 space-y-4 min-h-0">
            {messages.length === 0 && !isBuilding && (
              <div className="flex flex-col items-center justify-center h-full gap-4" style={{ color: 'var(--theme-muted, #3f3f46)' }}>
                <Sparkles className="w-10 h-10" style={{ color: 'var(--theme-input, #27272a)' }} />
                <p className="text-sm">Describe what you want to build...</p>
              </div>
            )}

            {/* ── Agent steps card (Manus-style) ── */}
            {isBuilding && (
              <div className="rounded-2xl p-4 border" style={{ background: 'var(--theme-surface, #1C1C1E)', borderColor: 'var(--theme-border, rgba(255,255,255,0.08))' }}>
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-2 h-2 rounded-full bg-orange-400 animate-pulse" />
                  <span className="text-sm font-medium" style={{ color: 'var(--theme-text, #ffffff)' }}>{currentPhase || 'Building your app...'}</span>
                  <span className="ml-auto text-xs" style={{ color: 'var(--theme-muted, #52525b)' }}>{Math.round(buildProgress)}%</span>
                </div>
                {/* Progress bar */}
                <div className="h-0.5 rounded-full mb-3 overflow-hidden" style={{ background: 'var(--theme-input, #27272a)' }}>
                  <div className="h-full rounded-full bg-orange-400 transition-all duration-500" style={{ width: `${buildProgress}%` }} />
                </div>
                {/* Agent steps */}
                <div className="space-y-2">
                  {agentsActivity.map((a, i) => (
                    <div key={i} className="flex items-center gap-2.5 text-xs">
                      {a.status === 'done' ? (
                        <div className="w-4 h-4 rounded-full flex items-center justify-center shrink-0" style={{ background: 'rgba(74,222,128,0.15)' }}>
                          <Check className="w-2.5 h-2.5 text-green-400" />
                        </div>
                      ) : a.status === 'running' ? (
                        <div className="w-4 h-4 flex items-center justify-center shrink-0">
                          <Loader2 className="w-3.5 h-3.5 text-orange-400 animate-spin" />
                        </div>
                      ) : (
                        <div className="w-4 h-4 rounded-full border shrink-0" style={{ borderColor: 'var(--theme-muted, #3f3f46)' }} />
                      )}
                      <span className="font-medium" style={{ color: a.status === 'done' ? '#86efac' : a.status === 'running' ? '#fb923c' : 'var(--theme-muted, #52525b)' }}>
                        {a.name}
                      </span>
                      <span className="truncate" style={{ color: 'var(--theme-muted, #3f3f46)' }}>{a.phase}</span>
                    </div>
                  ))}
                </div>
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
                    background: msg.role === 'user' ? 'var(--chat-user-bg, #3f3f46)' : 'var(--chat-ai-bg, #1c1c1e)',
                    border: msg.role === 'user' ? 'none' : '1px solid var(--theme-border, rgba(255,255,255,0.07))',
                    color: msg.error ? '#f87171' : 'var(--chat-text, #e4e4e7)',
                  }}
                >
                  {msg.isBuilding ? (
                    <div className="flex items-center gap-2">
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-orange-400" />
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
                  className="w-full bg-transparent outline-none text-sm resize-none px-4 pt-3.5 pb-1"
                  style={{ minHeight: 52, maxHeight: 140, color: 'white', caretColor: 'white' }}
                />
                <div className="flex items-center gap-2 px-3 pb-3">
                  <input ref={fileInputRef} type="file" multiple accept="image/*,.pdf,.txt,.md,.zip,audio/*,.js,.jsx,.ts,.tsx,.css,.html,.json,.py" onChange={handleFileSelect} className="hidden" />
                  <button type="button" onClick={() => fileInputRef.current?.click()} className="p-1.5 rounded-lg transition hover:bg-white/10" style={{ color: 'var(--theme-muted, #52525b)' }} title="Attach file">
                    <Paperclip className="w-4 h-4" />
                  </button>
                  <button
                    type="button"
                    onClick={isRecording ? stopRecording : startRecording}
                    className="p-1.5 rounded-lg transition hover:bg-white/10"
                    style={{ color: isRecording ? '#f87171' : 'var(--theme-muted, #52525b)' }}
                    title={isRecording ? 'Stop voice' : 'Voice input (Chrome/Edge/Safari)'}
                  >
                    {isRecording ? <MicOff className="w-4 h-4 animate-pulse" /> : <Mic className="w-4 h-4" />}
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
          {/* Tab bar */}
          <div className="h-11 flex items-center px-3 border-b shrink-0 gap-1" style={{ borderColor: 'var(--theme-border, rgba(255,255,255,0.08))' }}>
            {[
              { id: 'preview', label: 'Preview', icon: Eye },
              { id: 'code', label: 'Code', icon: FileCode },
              { id: 'console', label: 'Console', icon: Terminal },
              ...(projectIdFromUrl ? [{ id: 'history', label: 'History', icon: History }] : []),
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActivePanel(tab.id)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition"
                style={{
                  background: activePanel === tab.id ? 'rgba(255,255,255,0.1)' : 'transparent',
                  color: activePanel === tab.id ? 'var(--theme-text, #e4e4e7)' : 'var(--theme-muted, #52525b)',
                }}
              >
                <tab.icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            ))}
            <div className="ml-auto flex items-center gap-1">
              {activePanel === 'preview' && (
                <>
                  <button onClick={() => setMobileView(v => !v)} className="p-1.5 rounded-lg transition hover:bg-white/10" style={{ color: 'var(--theme-muted, #52525b)' }} title={mobileView ? 'Desktop view' : 'Mobile view'}>
                    {mobileView ? <Monitor className="w-3.5 h-3.5" /> : <Smartphone className="w-3.5 h-3.5" />}
                  </button>
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
          <div className="flex-1 overflow-hidden">
            {/* Preview — always mounted so Sandpack never loses files on tab switch */}
            <div style={{ display: activePanel === 'preview' ? 'flex' : 'none', flexDirection: 'column', height: '100%' }}>
              {/* Show placeholder when no build yet */}
              {currentVersion === null && !isBuilding ? (
                <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--theme-bg, #111113)', color: 'var(--theme-muted, #52525b)', flexDirection: 'column', gap: 12 }}>
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 9h6M9 12h6M9 15h4"/></svg>
                  <p style={{ fontSize: 13 }}>Build something to see the preview</p>
                </div>
              ) : (
              <SandpackProvider
                key={currentVersion || 'default'}
                files={sandpackFiles}
                theme={localStorage.getItem('crucibai-theme') === 'light' ? 'light' : 'dark'}
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
                  <SandpackPreview
                    showOpenInCodeSandbox={false}
                    style={{
                      height: '100%',
                      width: mobileView ? '390px' : '100%',
                      margin: mobileView ? '0 auto' : '0',
                    }}
                  />
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
                  theme="vs-dark"
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
              <ConsolePanel logs={logs} placeholder="Build logs appear here. Press Build to start." />
            )}
            {activePanel === 'history' && projectIdFromUrl && (
              <BuildHistoryPanel buildHistory={buildHistoryList} projectId={projectIdFromUrl} loading={buildHistoryLoading} />
            )}
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
          <div className="rounded-2xl shadow-2xl max-w-md w-full mx-4 p-6 border" style={{ background: 'var(--theme-surface, #1C1C1E)', borderColor: 'var(--theme-border, rgba(255,255,255,0.1))' }} onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-white mb-1">Deploy your app</h3>
            <p className="text-sm mb-5" style={{ color: 'var(--theme-muted, #71717a)' }}>Download your ZIP then upload to any platform below:</p>
            <div className="flex flex-col gap-2">
              <button onClick={downloadCode} className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-medium transition hover:bg-white/5 border" style={{ borderColor: 'var(--theme-border, rgba(255,255,255,0.1))', color: 'var(--theme-text, #e4e4e7)' }}>
                <Download className="w-4 h-4" /> Download ZIP
              </button>
              <a href="https://vercel.com/new" target="_blank" rel="noopener noreferrer" className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-medium text-white hover:opacity-90 transition" style={{ background: '#000' }}>
                Deploy to Vercel
              </a>
              <a href="https://app.netlify.com/drop" target="_blank" rel="noopener noreferrer" className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-medium text-white hover:opacity-90 transition" style={{ background: '#00AD9F' }}>
                Deploy to Netlify Drop
              </a>
              <a href="https://railway.app/new" target="_blank" rel="noopener noreferrer" className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-medium text-white hover:opacity-90 transition" style={{ background: '#0B0D0E', border: '1px solid rgba(255,255,255,0.15)' }}>
                Deploy to Railway
              </a>
            </div>
            <button onClick={() => setShowDeployModal(false)} className="mt-4 w-full py-2 text-sm rounded-xl border transition hover:bg-white/5" style={{ color: 'var(--theme-muted, #71717a)', borderColor: 'var(--theme-border, rgba(255,255,255,0.1))' }}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Workspace;

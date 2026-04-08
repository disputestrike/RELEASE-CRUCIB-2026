import { useState, useEffect, useRef } from 'react';
import { flushSync } from 'react-dom';
import { useNavigate, useLocation, useSearchParams, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Mic, MicOff, Paperclip, Loader2,
  Sparkles, ArrowRight, Upload, X, Github,
  Layout, Smartphone, Code, Zap, Globe,
  Copy, Check, Pencil, Play, CheckCircle, Clock, AlertCircle,
  BarChart3, ExternalLink
} from 'lucide-react';
import Logo from '../components/Logo';
import { useAuth, API } from '../App';
import { useTaskStore } from '../stores/useTaskStore';
import axios from 'axios';
import VoiceWaveform from '../components/VoiceWaveform';
import '../components/VoiceWaveform.css';
import './Dashboard.css';

/**
 * Dashboard — New Task / Home screen
 * AI intent classification → build / agent / chat
 */

// Rule-based: greetings and short conversational messages ALWAYS → chat (no API call)
const CHAT_ONLY_PATTERNS = [
  /^(hi|hello|hey|howdy|yo|sup|greetings?|good\s*(morning|afternoon|evening)|hi\s+there|hey\s+there|what'?s\s*up)\s*[!.?]*$/i,
  /^(thanks?|thank\s*you|thx|ok|okay|sure|yes|no|nope|yep|yeah)\s*[!.?]*$/i,
  /^(how\s+are\s+you|what'?s\s+going\s+on|how\s+is\s+it\s+going)\s*[!.?]*$/i,
  /^(bye|goodbye|see\s*ya|later)\s*[!.?]*$/i,
];
const BUILD_KEYWORDS = /\b(build|create|make|develop|design|generate|produce|build\s+me|create\s+(a|an)|make\s+me|develop\s+(a|an)|generate\s+(a|an))\b.*\b(app|application|website|web\s*app|landing\s*page|dashboard|saas|mvp|api|backend|frontend|tool|platform|product)\b/i;
const AGENT_KEYWORDS = /\b(automate|schedule|cron|webhook|trigger|run\s+every|run\s+when|run\s+on|agent|automation|workflow)\b/i;

function isDefinitelyChat(prompt) {
  const p = prompt.trim();
  if (p.length < 4) return true; // Single words like "Hi" or "Ok"
  if (CHAT_ONLY_PATTERNS.some(r => r.test(p))) return true;
  return false;
}

const INTENT_SYSTEM = `You classify user intent. Return EXACTLY one word: build, agent, or chat.

STRICT RULES:
- chat: greetings (hi, hello, hey), thanks, questions, opinions, small talk, general conversation, or ANY doubt.
- build: when the user asks to create/build/develop/generate a software app, website, dashboard, API, tool, or digital product (build verb + target). ALSO return build if the user said they want you to "figure it out", "just build it", "you decide", "don't ask", or "go ahead" and the topic is clearly software/app/website/tool — then assume build.
- agent: when the user EXPLICITLY asks for automation: something to run on a schedule, triggered by an event, recurring, or in the background without manual action.

When the user has told you to use your own judgment or not ask questions, prefer build or agent if the request is at all about making something. DEFAULT TO CHAT only when there is no build/agent intent. One word only.`;

const SPEC_INFER_SYSTEM = `You are a spec summarizer. Given the user's build request, output ONLY one sentence describing exactly what to build. No questions, no clarification, no greeting. Examples:
- "Web-based meeting recorder with audio capture, transcript display, and download."
- "Landing page for a SaaS product with hero, pricing table, and signup form."
- "Todo app with add, complete, and delete; React and Tailwind."
Output nothing but that one sentence.`;

async function inferBuildSpec(userPrompt, API, token) {
  try {
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    const res = await axios.post(`${API}/ai/chat`, {
      message: userPrompt,
      session_id: "spec_infer",
      model: "auto",
      system_message: SPEC_INFER_SYSTEM,
    }, { headers, timeout: 10000 });
    const spec = (res.data?.response || res.data?.message || "").trim();
    return spec || userPrompt.trim();
  } catch {
    return userPrompt.trim();
  }
}

async function detectIntent(prompt, API, token) {
  const p = prompt.trim();
  if (isDefinitelyChat(p)) return "chat";
  const looksBuild = BUILD_KEYWORDS.test(p);
  const looksAgent = AGENT_KEYWORDS.test(p);
  if (!looksBuild && !looksAgent) return "chat";

  try {
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    const res = await axios.post(`${API}/ai/chat`, {
      message: prompt,
      session_id: "intent_classify",
      model: "auto",
      system_message: INTENT_SYSTEM,
    }, { headers, timeout: 10000 });
    const raw = (res.data?.response || "").trim().toLowerCase().replace(/["']/g, "");
    if (raw === "build" || raw === "agent") return raw;
    return "chat";
  } catch {
    // When backend is down (e.g. no Ollama), use keyword fallback so build/agent prompts still work
    if (looksBuild) return "build";
    if (looksAgent) return "agent";
    return "chat";
  }
}

function formatCronShort(cron) {
  if (!cron) return "on a schedule";
  const parts = cron.trim().split(/\s+/);
  if (parts.length >= 5) {
    const [min, hour] = parts;
    if (hour !== "*" && min !== "*") return `every day at ${hour.padStart(2, "0")}:${min.padStart(2, "0")}`;
    if (hour !== "*") return `every day at ${hour}:00`;
  }
  return "on a schedule";
}

const SKILLS = [
  { icon: '🌐', name: 'Web App', skill_name: 'web-app-builder', desc: 'Full-stack React + Node.js with auth, database, and API', prompt: 'Build a full-stack web app with user authentication, dashboard, and REST API' },
  { icon: '📱', name: 'Mobile App', skill_name: 'mobile-app-builder', desc: 'React Native with Expo — iOS and Android ready', prompt: 'Build a mobile app with navigation, screens, and local storage' },
  { icon: '🛒', name: 'E-Commerce', skill_name: 'ecommerce-builder', desc: 'Product catalog, cart, checkout with Stripe payments', prompt: 'Build an e-commerce store with product catalog, cart, and Stripe checkout' },
  { icon: '📊', name: 'SaaS Dashboard', skill_name: 'saas-mvp-builder', desc: 'Auth, subscription billing, user management, metrics', prompt: 'Build a SaaS MVP with Stripe billing, user auth, and admin dashboard' },
  { icon: '🤖', name: 'AI Chatbot', skill_name: 'ai-chatbot-builder', desc: 'Multi-agent chat interface with knowledge base integration', prompt: 'Build an AI chatbot with multi-agent support and document knowledge base' },
  { icon: '🏠', name: 'Landing Page', skill_name: 'landing-page-builder', desc: 'Hero, features, pricing, testimonials, CTA sections', prompt: 'Build a landing page with hero, features grid, pricing table, and FAQ' },
  { icon: '⚡', name: 'Automation', skill_name: 'automation-builder', desc: 'Scheduled agents, webhooks, workflow pipelines', prompt: 'Build an automation that runs daily and sends results to Slack or email' },
  { icon: '🛠️', name: 'Internal Tool', skill_name: 'internal-tool-builder', desc: 'Admin tables, forms, CRUD, approval workflows', prompt: 'Build an internal admin tool with data tables, forms, and user roles' },
  { icon: '🎮', name: 'Game', skill_name: null, desc: 'Browser-based game with canvas, physics, leaderboard', prompt: 'Build a browser-based game with scoring and leaderboard' },
  { icon: '📄', name: 'Blog / CMS', skill_name: null, desc: 'Articles, categories, search, author dashboard', prompt: 'Build a blog with articles, categories, search, and an author dashboard' },
];

const SkillsPanel = ({ onSelect, token: skillToken, API: skillAPI }) => {
  const [showAll, setShowAll] = useState(false);
  const visibleSkills = showAll ? SKILLS : SKILLS.slice(0, 5);
  const navigate = useNavigate();

  const handleSkillClick = (skill) => {
    onSelect(skill.prompt);
    // Activate the skill when clicked (fire-and-forget)
    if (skillToken && skill.skill_name) {
      axios.post(
        `${skillAPI}/skills/${skill.skill_name}/activate`,
        {},
        { headers: { Authorization: `Bearer ${skillToken}` } }
      ).catch(() => {});
    }
  };

  return (
    <div style={{ maxWidth: '720px', width: '100%', margin: '20px auto 0' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <div>
          <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--theme-text, #111827)' }}>What can I build?</span>
          <span style={{ fontSize: '12px', color: '#9ca3af', marginLeft: '8px' }}>Click any skill to start building</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            type="button"
            onClick={() => setShowAll((v) => !v)}
            style={{ fontSize: '12px', color: '#6b7280', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
          >
            {showAll ? 'Show fewer' : 'Show all capabilities'}
          </button>
          <button
            type="button"
            onClick={() => navigate('/app/skills')}
            style={{ fontSize: '12px', color: '#6366f1', background: 'none', border: 'none', cursor: 'pointer', padding: 0, display: 'flex', alignItems: 'center', gap: '3px' }}
          >
            View in Skills <ArrowRight size={11} />
          </button>
        </div>
      </div>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(5, 1fr)',
        gap: '8px',
      }} className="skills-grid">
        {visibleSkills.map((skill) => (
          <button
            key={skill.name}
            type="button"
            onClick={() => handleSkillClick(skill)}
            style={{
              display: 'flex', flexDirection: 'column', alignItems: 'flex-start',
              padding: '12px', background: 'var(--theme-bg, #fff)', border: '1px solid var(--theme-border, #e5e7eb)',
              borderRadius: '12px', cursor: 'pointer', textAlign: 'left',
              transition: 'border-color 0.15s, box-shadow 0.15s',
              gap: '6px',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#d1d5db'; e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.06)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--theme-border, #e5e7eb)'; e.currentTarget.style.boxShadow = 'none'; }}
          >
            <span style={{ fontSize: '20px', lineHeight: 1 }}>{skill.icon}</span>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--theme-text, #111827)' }}>{skill.name}</span>
            <span style={{ fontSize: '11px', color: '#6b7280', lineHeight: 1.4 }}>{skill.desc}</span>
          </button>
        ))}
      </div>
    </div>
  );
};

const QUICK_START_CHIPS = [
  { label: 'Build website', icon: Layout, prompt: 'Build me a stunning multi-page website with hero, features grid, pricing, testimonials, and footer — beautiful modern design' },
  { label: 'Develop app', icon: Code, prompt: 'Build a complete React web app with multiple pages, authentication UI, dashboard, and CRUD data management' },
  { label: 'Design UI', icon: Globe, prompt: 'Design a beautiful modern SaaS product UI with clean design system, multiple pages, components, and responsive layout' },
  { label: 'SaaS MVP', icon: Zap, prompt: 'Build a SaaS MVP with login/register pages, dashboard, subscription pricing table, settings, and admin panel' },
  { label: 'Import code', icon: Upload, prompt: null, action: 'import' },
];

const GOLDEN_PATH_STEPS = [
  'Prompt or import',
  'Approve plan',
  'Watch build',
  'Review proof',
  'Preview app',
  'Publish URL',
  'Continue improving',
];

const Dashboard = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const { user, token } = useAuth();
  const { addTask, updateTask, tasks: storeTasks } = useTaskStore();
  const [prompt, setPrompt] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState([]);
  const [showImportModal, setShowImportModal] = useState(false);
  const [importSource, setImportSource] = useState('paste');
  const [importName, setImportName] = useState('');
  const [pasteFiles, setPasteFiles] = useState([{ path: '/App.js', code: '' }]);
  const [zipFile, setZipFile] = useState(null);
  const [gitUrl, setGitUrl] = useState('');
  const [importLoading, setImportLoading] = useState(false);
  const [importError, setImportError] = useState(null);
  // Chat state for conversational (non-build) messages
  const [chatMessages, setChatMessages] = useState([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [conversationStarted, setConversationStarted] = useState(false);
  const [audioStream, setAudioStream] = useState(null);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [actionFeedback, setActionFeedback] = useState(null); // { type: 'copy', index } | null
  const actionFeedbackTimerRef = useRef(null);
  const inputRef = useRef(null);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const mediaRecorderRef = useRef(null);

  // Live projects — fetched from API, polled every 5s when any are running
  const [liveProjects, setLiveProjects] = useState([]);
  const [projectsLoading, setProjectsLoading] = useState(false);
  const liveProjectsPollRef = useRef(null);

  const fetchLiveProjects = async () => {
    if (!token || !API) return;
    try {
      const res = await axios.get(`${API}/projects`, {
        headers: { Authorization: `Bearer ${token}` },
        params: { limit: 10 },
        timeout: 8000,
      });
      const projects = res.data?.projects || res.data || [];
      setLiveProjects(Array.isArray(projects) ? projects.slice(0, 10) : []);
    } catch (e) {
      // silent — dashboard still works without live projects
    }
  };

  useEffect(() => {
    if (!token) return;
    setProjectsLoading(true);
    fetchLiveProjects().finally(() => setProjectsLoading(false));
  }, [token]);

  // Poll every 4s if any project is running
  useEffect(() => {
    const hasRunning = liveProjects.some(p => p.status === 'running' || p.status === 'pending');
    if (hasRunning) {
      liveProjectsPollRef.current = setInterval(fetchLiveProjects, 4000);
    } else {
      clearInterval(liveProjectsPollRef.current);
    }
    return () => clearInterval(liveProjectsPollRef.current);
  }, [liveProjects, token]);
  const streamRef = useRef(null);

  // Restore chat when opening a chat task from sidebar (state or URL). Stay on task until user navigates away or New Task.
  const chatTaskIdRef = useRef(null);
  const prevChatTaskIdRef = useRef(null);
  useEffect(() => {
    const chatTaskId = location.state?.chatTaskId || searchParams.get('chatTaskId');
    const newAgent = location.state?.newAgent;

    if (newAgent) {
      chatTaskIdRef.current = null;
      prevChatTaskIdRef.current = null;
      setChatMessages([]);
      setConversationStarted(false);
      setPrompt('');
      setAttachedFiles([]);
      inputRef.current?.focus();
      return;
    }

    if (chatTaskId) {
      if (prevChatTaskIdRef.current === chatTaskId) return; // already on this task, don't overwrite
      prevChatTaskIdRef.current = chatTaskId;
      chatTaskIdRef.current = chatTaskId;
      const task = storeTasks?.find(t => t.id === chatTaskId);
      const msgs = task?.messages;
      if (msgs && Array.isArray(msgs) && msgs.length > 0) {
        setChatMessages(msgs);
        setConversationStarted(true);
      } else {
        // No persisted messages yet (e.g. mid-send); don't clear existing chat
        if (chatMessages.length === 0) setConversationStarted(false);
      }
      setPrompt('');
      inputRef.current?.focus();
      return;
    }

    prevChatTaskIdRef.current = null;
    chatTaskIdRef.current = null;
  }, [location.state?.chatTaskId, location.state?.newAgent, searchParams.get('chatTaskId'), storeTasks]);

  // Autofocus prompt on load
  useEffect(() => {
    const timer = setTimeout(() => inputRef.current?.focus(), 300);
    return () => clearTimeout(timer);
  }, []);
  useEffect(() => {
    const { focusPrompt } = location.state || {};
    if (focusPrompt && inputRef.current) {
      inputRef.current.focus();
    }
    if (location.state?.suggestedPrompt) {
      setPrompt(location.state.suggestedPrompt);
      inputRef.current?.focus();
    }
    if (location.state?.openImport) {
      setShowImportModal(true);
    }
  }, [location.state]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, chatLoading]);

  // Auto-expand textarea as user types (wrap + grow upward)
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(Math.max(el.scrollHeight, 28), 240)}px`;
  }, [prompt]);

  const PROMPT_CONVERT_TO_FILE_LIMIT = 3000;

  const attachTextAsFile = (text, filename = 'pasted_content.txt') => {
    const data = text.trim();
    if (!data) return;
    setAttachedFiles(prev => [...prev, {
      name: filename,
      type: 'text/plain',
      data,
      size: new Blob([data]).size
    }]);
    setPrompt('');
    inputRef.current?.focus();
  };

  const handleConvertToFile = () => attachTextAsFile(prompt, 'pasted_content.txt');

  const handleSubmit = async (e) => {
    e?.preventDefault();
    let textParts = [prompt.trim(), ...attachedFiles.filter(f => f.type === 'text/plain').map(f => f.data || '')].filter(Boolean);
    let userPrompt = textParts.join('\n\n');
    let filesToSend = [...attachedFiles];
    if (!userPrompt && filesToSend.length === 0) return;

    // Transcribe attached audio (voice notes) and append to prompt
    const audioFiles = filesToSend.filter(f => f.type?.startsWith?.('audio/'));
    if (audioFiles.length > 0) {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      for (const att of audioFiles) {
        try {
          const blob = await (await fetch(att.data)).blob();
          const formData = new FormData();
          formData.append('audio', blob, att.name || 'audio.webm');
          const res = await axios.post(`${API}/voice/transcribe`, formData, { headers, timeout: 30000 });
          const text = res.data?.text?.trim();
          if (text) userPrompt = (userPrompt ? userPrompt + ' ' : '') + text;
        } catch (_) {}
      }
      filesToSend = filesToSend.filter(f => !f.type?.startsWith?.('audio/'));
    }

    const userMsg = { role: 'user', content: userPrompt || (filesToSend.length ? `[${filesToSend.length} attachment(s)]` : '') };
    setPrompt('');
    setAttachedFiles([]);
    flushSync(() => {
      setChatMessages(prev => [...prev, userMsg]);
      setConversationStarted(true);
      setChatLoading(true);
    });

    // Conversation-only: skip intent API for greetings or when user sent only attachments (images/PDF)
    const intent = (!userPrompt && filesToSend.length > 0) ? 'chat' : (isDefinitelyChat(userPrompt) ? 'chat' : await detectIntent(userPrompt, API, token));

    if (intent === 'build') {
      // Go straight to workspace (like CrucibAI): works with or without backend; spec from AI or fallback to prompt
      setChatLoading(false);
      const spec = await inferBuildSpec(userPrompt, API, token).catch(() => userPrompt.trim());
      const taskName = (spec || userPrompt).slice(0, 60);
      const taskId = addTask({ name: taskName, prompt: spec || userPrompt, status: 'pending', type: 'build' });
      navigate({
        pathname: '/app/workspace',
        search: taskId ? `?taskId=${encodeURIComponent(taskId)}` : '',
        state: {
          initialPrompt: spec || userPrompt,
          autoStart: true,
          initialAttachedFiles: filesToSend.length > 0 ? filesToSend : undefined
        }
      });
      return;
    }

    if (intent === 'agent') {
      addTask({ name: userPrompt.slice(0, 60), prompt: userPrompt, status: 'completed', type: 'agent' });
      try {
        const headers = token ? { Authorization: `Bearer ${token}` } : {};
        const res = await axios.post(`${API}/agents/from-description`, { description: userPrompt }, { headers, timeout: 60000 });
        const agent = res.data;
        const schedule = agent?.trigger_config?.cron_expression
          ? `runs ${formatCronShort(agent.trigger_config.cron_expression)}`
          : agent?.trigger_type === 'webhook'
            ? 'webhook-triggered'
            : 'scheduled';
        setChatMessages(prev => [...prev, {
          role: 'assistant',
          content: `✅ Agent created — ${schedule}. You can manage it in the Agents page.`
        }]);
      } catch (err) {
        setChatMessages(prev => [...prev, {
          role: 'assistant',
          content: err.response?.data?.detail || err.message || 'Could not create agent. Try again or create from the Agents page.'
        }]);
      } finally {
        setChatLoading(false);
      }
      return;
    }

    // chat — add task (first message) or update existing (continued conversation). Stay on task until user navigates.
    const existingTaskId = chatTaskIdRef.current;
    const taskId = existingTaskId || addTask({ name: userPrompt.slice(0, 60), prompt: userPrompt, status: 'completed', type: 'chat' });
    if (!existingTaskId) {
      chatTaskIdRef.current = taskId;
      // Keep URL in sync so task context survives refresh
      navigate(`/app?chatTaskId=${encodeURIComponent(taskId)}`, { replace: true });
    }

    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const attachments = filesToSend.length > 0 ? filesToSend.map((f) => {
        const type = f.type?.startsWith('image/') ? 'image' : (f.type === 'application/pdf' ? 'pdf' : 'text');
        return { type, data: f.data, name: f.name };
      }) : undefined;
      const res = await axios.post(`${API}/ai/chat`, {
        message: userPrompt,
        session_id: `chat_${taskId}`,
        model: 'auto',
        ...(attachments?.length ? { attachments } : {})
      }, { headers, timeout: 60000 });
      const reply = res.data?.response || res.data?.message || "Hey! What are we building today?";
      const assistantMsg = { role: 'assistant', content: reply };
      setChatMessages(prev => [...prev, assistantMsg]);
      // Persist explicitly: include both user and assistant (don't rely on prev)
      const task = storeTasks?.find(t => t.id === taskId);
      const prevMsgs = (task?.messages && Array.isArray(task.messages)) ? task.messages : [];
      updateTask(taskId, { messages: [...prevMsgs, userMsg, assistantMsg], prompt: userPrompt });
    } catch (err) {
      const is404 = err.response?.status === 404 || err.response?.status === 405;
      const detail = err.response?.data?.detail;
      const backendUnavailable = "Backend not available. Start the CrucibAI backend to use AI (see BACKEND_SETUP.md). You can still try \"Build me a landing page\" — it will open the Workspace; the build will need the backend running.";
      const fallback = is404 ? backendUnavailable : "Chat failed. For AI replies, run the backend (e.g. from CrucibAI) with Ollama. See BACKEND_SETUP.md.";
      const assistantMsg = {
        role: 'assistant',
        content: (typeof detail === 'string' && detail && !is404) ? detail : (err.message?.includes('404') ? backendUnavailable : (err.message || fallback))
      };
      setChatMessages(prev => [...prev, assistantMsg]);
      const task = storeTasks?.find(t => t.id === taskId);
      const prevMsgs = (task?.messages && Array.isArray(task.messages)) ? task.messages : [];
      updateTask(taskId, { messages: [...prevMsgs, userMsg, assistantMsg], prompt: userPrompt });
    } finally {
      setChatLoading(false);
    }
  };

  const handleChipClick = (chip) => {
    if (chip.action === 'import') {
      setShowImportModal(true);
      return;
    }
    if (chip.prompt) {
      const p = (chip.prompt || chip.label || '').trim();
      const taskName = p.length <= 60 ? p : (() => {
        const cut = p.slice(0, 60);
        const lastSpace = cut.lastIndexOf(' ');
        return lastSpace > 35 ? cut.slice(0, lastSpace) : cut;
      })();
      const taskId = addTask({ name: taskName, prompt: chip.prompt, status: 'pending', type: 'build' });
      navigate({
        pathname: '/app/workspace',
        search: taskId ? `?taskId=${encodeURIComponent(taskId)}` : '',
        state: { initialPrompt: chip.prompt, autoStart: true }
      });
    }
  };

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files);
    selectedFiles.forEach(file => {
      const isZip = file.type === 'application/zip' || file.name.toLowerCase().endsWith('.zip');
      const isAudio = file.type.startsWith('audio/');
      const reader = new FileReader();
      reader.onload = (ev) => {
        const data = isZip ? btoa(String.fromCharCode(...new Uint8Array(ev.target.result))) : ev.target.result;
        setAttachedFiles(prev => [...prev, { name: file.name, type: file.type, data, size: file.size }]);
      };
      if (file.type.startsWith('image/') || file.type === 'application/pdf' || isAudio) {
        reader.readAsDataURL(file);
      } else if (isZip) {
        reader.readAsArrayBuffer(file);
      } else {
        reader.readAsText(file);
      }
    });
  };

  const removeFile = (index) => {
    setAttachedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const mimeTypes = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'];
      const mimeType = mimeTypes.find(mt => MediaRecorder.isTypeSupported(mt)) || 'audio/webm';
      const recorder = new MediaRecorder(stream, { mimeType });
      const chunks = [];
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };
      recorder.onstop = async () => {
        // Stop ALL tracks on the stream (ISSUE 7)
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop());
          streamRef.current = null;
        }
        setIsRecording(false);
        setAudioStream(null);
        const blob = new Blob(chunks, { type: mimeType.split(';')[0] });
        if (blob.size < 100) return;
        setIsTranscribing(true);
        try {
          const formData = new FormData();
          formData.append('audio', blob, 'recording.webm');
          const headers = token ? { Authorization: `Bearer ${token}` } : {};
          const res = await axios.post(`${API}/voice/transcribe`, formData, { headers, timeout: 30000 });
          if (res.data?.text) setPrompt(res.data.text);
        } catch (err) {
          setActionFeedback({
            type: 'mic_error',
            message: err?.response?.status === 404 || err?.code === 'ERR_NETWORK'
              ? 'Voice needs the backend. Start the CrucibAI backend (see BACKEND_SETUP.md) and retry.'
              : (err?.response?.data?.detail || err?.message) || 'Voice transcription failed. Retry or type instead.'
          });
          setTimeout(() => setActionFeedback(null), 6000);
        }
        setIsTranscribing(false);
      };
      recorder.start(1000);
      mediaRecorderRef.current = { recorder, stream };
      setAudioStream(stream);
      setIsRecording(true);
    } catch (err) {
      setIsRecording(false);
      if (err?.name === 'NotAllowedError') {
        // Show as a UI error, not as a chat message from CrucibAI
        setActionFeedback({ type: 'mic_error', message: 'Microphone blocked. Click the lock icon in your browser address bar → allow Microphone → refresh.' });
        setTimeout(() => setActionFeedback(null), 6000);
      }
    }
  };

  const stopRecording = () => {
    const ref = mediaRecorderRef.current;
    // Cancel — stop without transcribing
    if (ref?.recorder) {
      ref.recorder.onstop = () => {
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(t => t.stop());
          streamRef.current = null;
        }
      };
      if (ref.recorder.state === 'recording') ref.recorder.stop();
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    mediaRecorderRef.current = null;
    setAudioStream(null);
    setIsRecording(false);
  };

  const confirmRecording = () => {
    const ref = mediaRecorderRef.current;
    if (ref?.recorder?.state === 'recording') {
      ref.recorder.stop(); // onstop handler will transcribe
    }
    setAudioStream(null);
  };

  const handleImportSubmit = async (e) => {
    e.preventDefault();
    setImportError(null);
    setImportLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      let body = { source: importSource, name: importName || undefined };
      if (importSource === 'paste') {
        const files = pasteFiles.filter((f) => (f.path || '').trim() && (f.code || '').trim());
        if (files.length === 0) { setImportError('Add at least one file.'); setImportLoading(false); return; }
        body.files = files.map((f) => ({ path: (f.path || '').trim().replace(/^\/+/, '') || 'App.js', code: (f.code || '').trim() }));
      } else if (importSource === 'zip') {
        if (!zipFile) { setImportError('Choose a ZIP file.'); setImportLoading(false); return; }
        const buf = await zipFile.arrayBuffer();
        const base64 = btoa(String.fromCharCode(...new Uint8Array(buf)));
        body.zip_base64 = base64;
      } else {
        const url = (gitUrl || '').trim();
        if (!url) { setImportError('Enter a GitHub URL.'); setImportLoading(false); return; }
        body.git_url = url;
      }
      const { data } = await axios.post(`${API}/projects/import`, body, { headers });
      setShowImportModal(false);
      navigate(`/app/workspace?projectId=${data.project_id}`);
    } catch (err) {
      setImportError(err.response?.data?.detail || err.message || 'Import failed');
    } finally {
      setImportLoading(false);
    }
  };

  const hasChat = chatMessages.length > 0;

  // Copy feedback: clear after 2s
  useEffect(() => {
    if (!actionFeedback) return;
    if (actionFeedbackTimerRef.current) clearTimeout(actionFeedbackTimerRef.current);
    actionFeedbackTimerRef.current = setTimeout(() => {
      setActionFeedback(null);
      actionFeedbackTimerRef.current = null;
    }, 2000);
    return () => { if (actionFeedbackTimerRef.current) clearTimeout(actionFeedbackTimerRef.current); };
  }, [actionFeedback]);

  const handleCopyMessage = (index) => {
    const text = chatMessages[index]?.content;
    if (text == null) return;
    navigator.clipboard?.writeText(text).then(() => setActionFeedback({ type: 'copy', index }));
  };

  const handleEditMessage = (content) => {
    if (content == null) return;
    setPrompt(String(content));
    inputRef.current?.focus();
  };

  const handleStartBuilding = (buildOffer) => {
    if (!buildOffer?.spec) return;
    const spec = buildOffer.spec.trim();
    const taskName = spec.length <= 60 ? spec : (() => {
      const cut = spec.slice(0, 60);
      const lastSpace = cut.lastIndexOf(' ');
      return lastSpace > 35 ? cut.slice(0, lastSpace) : cut;
    })();
    const taskId = addTask({ name: taskName, prompt: spec, status: 'pending', type: 'build' });
    navigate({
      pathname: '/app/workspace',
      search: taskId ? `?taskId=${encodeURIComponent(taskId)}` : '',
      state: {
        initialPrompt: spec,
        autoStart: true,
        initialAttachedFiles: buildOffer.attachedFiles?.length ? buildOffer.attachedFiles : undefined
      }
    });
  };

  const inputForm = (
    <form onSubmit={handleSubmit} className={`dashboard-prompt-form ${hasChat ? 'dashboard-prompt-form--chat' : ''}`}>
      {attachedFiles.length > 0 && (
        <div className="dashboard-attached-files">
          {attachedFiles.map((file, i) => (
            <div key={i} className="dashboard-attached-file">
              <span className="dashboard-attached-name">{file.name}</span>
              <span className="dashboard-attached-size">
                {file.size != null ? (file.size / 1024).toFixed(2) + ' KB' : ''}
              </span>
              <button type="button" onClick={() => removeFile(i)} className="dashboard-attached-remove">
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
      )}
      <div className={`dashboard-prompt-container ${hasChat ? 'dashboard-prompt-container--stacked' : ''}`}>
        <textarea
          ref={inputRef}
          value={prompt}
          onChange={(e) => {
            const next = e.target.value;
            if (next.length >= PROMPT_CONVERT_TO_FILE_LIMIT) {
              attachTextAsFile(next, 'pasted_content.txt');
            } else {
              setPrompt(next);
            }
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e);
            }
          }}
          placeholder={hasChat ? 'Ask a follow-up or describe a new idea...' : (location.state?.newProject ? 'Describe your project (e.g. I need a flower website)...' : 'Describe what you want to build or ask anything...')}
          className="dashboard-prompt-input"
          rows={1}
        />
        <div className="dashboard-prompt-actions">
          <div className="dashboard-model-badge" title="Auto-selects best model">
            <Sparkles size={14} />
          </div>
          <button type="button" onClick={() => fileInputRef.current?.click()} className="dashboard-prompt-btn" title="Attach file">
            <Paperclip size={18} />
          </button>
          <input ref={fileInputRef} type="file" multiple accept="image/*,.pdf,.txt,.md,.zip,audio/*,.js,.jsx,.ts,.tsx,.css,.html,.json,.py" onChange={handleFileSelect} className="hidden" />
          {isRecording ? (
            <VoiceWaveform stream={audioStream} onStop={stopRecording} onConfirm={confirmRecording} isRecording={isRecording} />
          ) : (
            <button type="button" onClick={isTranscribing ? undefined : startRecording} disabled={isTranscribing} className={`dashboard-prompt-btn ${isRecording ? 'recording' : ''}`} title={isTranscribing ? 'Transcribing...' : 'Voice input (9 languages)'}>
              {isTranscribing ? <Loader2 size={18} className="animate-spin" /> : <Mic size={18} />}
            </button>
          )}
          <button type="submit" disabled={(!prompt.trim() && !attachedFiles.length) || chatLoading} className="dashboard-prompt-submit" title="Send">
            {chatLoading ? <Loader2 size={18} className="animate-spin" /> : <ArrowRight size={18} />}
          </button>
        </div>
        {actionFeedback?.type === 'mic_error' && (
          <div style={{ marginTop: '8px', padding: '8px 12px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '8px', fontSize: '12px', color: '#b91c1c', lineHeight: '1.5' }}>
            🎤 {actionFeedback.message}
          </div>
        )}
      </div>
      {hasChat && (
        <div className="dashboard-prompt-convert">
          <span className="dashboard-prompt-convert-count">{prompt.length.toLocaleString()} / {PROMPT_CONVERT_TO_FILE_LIMIT.toLocaleString()}</span>
          {prompt.length > PROMPT_CONVERT_TO_FILE_LIMIT && (
            <button type="button" onClick={handleConvertToFile} className="dashboard-prompt-convert-btn">
              Convert text to file
            </button>
          )}
        </div>
      )}
    </form>
  );

  return (
    <div className="dashboard-redesigned home-screen" data-testid="dashboard">
      <div className={`home-messages ${hasChat ? 'has-chat' : ''}`}>
        {!hasChat && (
          <>
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="dashboard-greeting">
              <h1 className="dashboard-greeting-text">
                <span className="dashboard-greeting-sub">{location.state?.newProject ? 'What\'s your new project?' : 'What do you want to build?'}</span>
              </h1>
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.1 }} className="dashboard-prompt-inline">
              {inputForm}
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.2 }} className="dashboard-chips">
              <span className="dashboard-chips-label">Quick start:</span>
              <div className="dashboard-chips-grid">
                {QUICK_START_CHIPS.map((chip) => (
                  <button key={chip.label} type="button" onClick={() => handleChipClick(chip)} className="dashboard-chip">
                    <chip.icon size={16} className="dashboard-chip-icon" />
                    <span>{chip.label}</span>
                  </button>
                ))}
              </div>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.24 }}
              className="dashboard-golden-path-card"
            >
              <div className="dashboard-golden-path-copy">
                <span className="dashboard-golden-path-eyebrow">Golden path</span>
                <strong>Build, prove, preview, publish, then keep improving.</strong>
              </div>
              <div className="dashboard-golden-path-steps">
                {GOLDEN_PATH_STEPS.map((step, index) => (
                  <span key={step} className="dashboard-golden-path-step">
                    <span>{index + 1}</span>{step}
                  </span>
                ))}
              </div>
            </motion.div>

            {/* Skills / Capabilities Panel */}
            <SkillsPanel onSelect={(prompt) => setPrompt(prompt)} token={token} API={API} />

            {/* Live Builds Panel — real-time build progress, polled every 4s when builds are running */}
            {liveProjects.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.3 }}
                style={{ marginTop: '24px', maxWidth: '720px', width: '100%', margin: '24px auto 0' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                  <span style={{ fontSize: '12px', fontWeight: 500, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Your builds
                  </span>
                  <Link to="/app/projects" style={{ fontSize: '12px', color: '#6b7280', textDecoration: 'none' }}>View all →</Link>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {liveProjects.slice(0, 5).map((project) => {
                    const isRunning = project.status === 'running' || project.status === 'pending';
                    const isCompleted = project.status === 'completed';
                    const isFailed = project.status === 'failed';
                    const progress = project.progress_percent || 0;
                    return (
                      <Link key={project.id} to={`/app/projects/${project.id}`} style={{ textDecoration: 'none' }}>
                        <div style={{
                          padding: '12px 16px', background: '#fff',
                          border: isRunning ? '1px solid #3b82f6' : '1px solid #e5e7eb',
                          borderRadius: '12px', cursor: 'pointer', transition: 'border-color 0.2s',
                        }}>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: isRunning ? '8px' : '0' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
                              {isRunning && <Loader2 size={14} style={{ color: '#3b82f6', flexShrink: 0 }} />}
                              {isCompleted && <CheckCircle size={14} style={{ color: '#10b981', flexShrink: 0 }} />}
                              {isFailed && <AlertCircle size={14} style={{ color: '#ef4444', flexShrink: 0 }} />}
                              {!isRunning && !isCompleted && !isFailed && <Clock size={14} style={{ color: '#9ca3af', flexShrink: 0 }} />}
                              <span style={{ fontSize: '13px', fontWeight: 500, color: '#111827', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {project.name || project.description || 'Untitled build'}
                              </span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
                              {project.quality_score != null && (
                                <span style={{ fontSize: '11px', color: '#10b981', fontWeight: 500 }}>
                                  {Math.round(project.quality_score)}% quality
                                </span>
                              )}
                              <span style={{
                                fontSize: '11px', padding: '2px 8px', borderRadius: '999px', fontWeight: 500,
                                background: isRunning ? '#eff6ff' : isCompleted ? '#f0fdf4' : isFailed ? '#fef2f2' : '#f9fafb',
                                color: isRunning ? '#3b82f6' : isCompleted ? '#10b981' : isFailed ? '#ef4444' : '#9ca3af',
                              }}>
                                {isRunning ? `Building ${progress > 0 ? `· ${progress}%` : ''}` : project.status}
                              </span>
                              <ExternalLink size={12} style={{ color: '#9ca3af' }} />
                            </div>
                          </div>
                          {isRunning && (
                            <>
                              <div style={{ height: '4px', background: '#e5e7eb', borderRadius: '999px', overflow: 'hidden' }}>
                                <div style={{
                                  height: '100%', background: '#3b82f6', borderRadius: '999px',
                                  width: `${Math.max(progress, 6)}%`, transition: 'width 0.6s ease',
                                }} />
                              </div>
                              {project.current_agent && (
                                <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '4px' }}>
                                  Running: {project.current_agent}
                                </div>
                              )}
                            </>
                          )}
                        </div>
                      </Link>
                    );
                  })}
                </div>
              </motion.div>
            )}
          </>
        )}
        {hasChat && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="dashboard-chat-thread">
            {chatMessages.map((msg, i) => (
              <div key={i} className={`dashboard-chat-msg ${msg.role}`}>
                {msg.role === 'assistant' && (
                  <div className="dashboard-chat-identifier">
                    <Logo href={null} showTagline={false} height={18} className="dashboard-chat-logo" />
                  </div>
                )}
                <div className={`dashboard-chat-bubble ${msg.role}`}>
                  {msg.content}
                </div>
                {msg.buildOffer && (
                  <div className="dashboard-chat-build-offer">
                    <button type="button" onClick={() => handleStartBuilding(msg.buildOffer)} className="dashboard-chat-start-building-btn">
                      Start Building →
                    </button>
                  </div>
                )}
                <div className={`dashboard-chat-actions ${msg.role}`}>
                  <button
                    type="button"
                    onClick={() => handleCopyMessage(i)}
                    className="dashboard-chat-action"
                    title={actionFeedback?.type === 'copy' && actionFeedback?.index === i ? 'Copied!' : 'Copy'}
                    aria-label={actionFeedback?.type === 'copy' && actionFeedback?.index === i ? 'Copied!' : 'Copy'}
                  >
                    {actionFeedback?.type === 'copy' && actionFeedback?.index === i ? <Check size={14} /> : <Copy size={14} />}
                  </button>
                  {msg.role === 'user' && (
                    <button type="button" onClick={() => handleEditMessage(msg.content)} className="dashboard-chat-action" title="Edit" aria-label="Edit">
                      <Pencil size={14} />
                    </button>
                  )}
                </div>
              </div>
            ))}
            {chatLoading && (
              <div className="dashboard-chat-msg assistant">
                <div className="dashboard-chat-identifier">
                  <Logo href={null} showTagline={false} height={18} className="dashboard-chat-logo" />
                </div>
                <div className="dashboard-chat-bubble assistant">
                  <Loader2 size={16} className="animate-spin" style={{ display: 'inline-block' }} />
                  <span style={{ marginLeft: 8 }}>Thinking...</span>
                </div>
              </div>
            )}
          </motion.div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {hasChat && (
        <div className="home-input-bar home-input-bar--chat">
          <div className="home-prompt-wrapper">{inputForm}</div>
        </div>
      )}

      {/* Import Modal */}
      <AnimatePresence>
        {showImportModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="dashboard-modal-overlay"
            onClick={() => setShowImportModal(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="dashboard-modal"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="dashboard-modal-header">
                <h2>Import Project</h2>
                <button onClick={() => setShowImportModal(false)} className="dashboard-modal-close">
                  <X size={20} />
                </button>
              </div>

              <div className="dashboard-modal-tabs">
                {['paste', 'zip', 'github'].map((src) => (
                  <button
                    key={src}
                    onClick={() => setImportSource(src)}
                    className={`dashboard-modal-tab ${importSource === src ? 'active' : ''}`}
                  >
                    {src === 'paste' ? 'Paste Code' : src === 'zip' ? 'Upload ZIP' : 'GitHub'}
                  </button>
                ))}
              </div>

              <form onSubmit={handleImportSubmit} className="dashboard-modal-form">
                <input
                  type="text"
                  placeholder="Project name (optional)"
                  value={importName}
                  onChange={(e) => setImportName(e.target.value)}
                  className="dashboard-modal-input"
                />

                {importSource === 'paste' && (
                  <div className="dashboard-modal-paste">
                    {pasteFiles.map((f, i) => (
                      <div key={i} className="dashboard-modal-paste-row">
                        <input
                          placeholder="File path (e.g. App.js)"
                          value={f.path}
                          onChange={(e) => {
                            const next = [...pasteFiles];
                            next[i] = { ...next[i], path: e.target.value };
                            setPasteFiles(next);
                          }}
                          className="dashboard-modal-input-sm"
                        />
                        <textarea
                          placeholder="Paste code here..."
                          value={f.code}
                          onChange={(e) => {
                            const next = [...pasteFiles];
                            next[i] = { ...next[i], code: e.target.value };
                            setPasteFiles(next);
                          }}
                          className="dashboard-modal-textarea"
                          rows={4}
                        />
                      </div>
                    ))}
                    <button
                      type="button"
                      onClick={() => setPasteFiles(prev => [...prev, { path: '', code: '' }])}
                      className="dashboard-modal-add-file"
                    >
                      + Add file
                    </button>
                  </div>
                )}

                {importSource === 'zip' && (
                  <input
                    type="file"
                    accept=".zip"
                    onChange={(e) => setZipFile(e.target.files[0])}
                    className="dashboard-modal-file-input"
                  />
                )}

                {importSource === 'github' && (
                  <div className="dashboard-modal-github">
                    <Github size={18} />
                    <input
                      type="text"
                      placeholder="https://github.com/user/repo"
                      value={gitUrl}
                      onChange={(e) => setGitUrl(e.target.value)}
                      className="dashboard-modal-input"
                    />
                  </div>
                )}

                {importError && (
                  <div className="dashboard-modal-error">{importError}</div>
                )}

                <button
                  type="submit"
                  disabled={importLoading}
                  className="dashboard-modal-submit"
                >
                  {importLoading ? <Loader2 size={16} className="animate-spin" /> : null}
                  {importLoading ? 'Importing...' : 'Import'}
                </button>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default Dashboard;

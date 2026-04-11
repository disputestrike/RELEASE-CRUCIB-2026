import { useState, useEffect, useLayoutEffect, useRef, useCallback } from 'react';
import { flushSync } from 'react-dom';
import { useNavigate, useLocation, useSearchParams, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Mic, MicOff, Paperclip, Loader2,
  Sparkles, ArrowRight, ArrowUp, Upload, X, Github,
  Layout, Code, Zap, Globe, Monitor,
  Copy, Check, Pencil, Play, CheckCircle, Clock, AlertCircle,
  BarChart3, ExternalLink, ChevronDown,
  ThumbsUp, ThumbsDown, Share2, RefreshCw,
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

/** Stringify bubble content so user/assistant lines always render (never [object Object]). */
function formatChatContent(content) {
  if (content == null) return '';
  if (typeof content === 'string') return content;
  if (typeof content === 'number' || typeof content === 'boolean') return String(content);
  if (typeof content === 'object') {
    if (content.text != null) return formatChatContent(content.text);
    if (content.message != null) return formatChatContent(content.message);
    if (content.content != null) return formatChatContent(content.content);
    try {
      return JSON.stringify(content);
    } catch {
      return '';
    }
  }
  return String(content);
}

function genMessageId() {
  return `msg_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`;
}

/** Ensure every message has a stable id (and optional reaction) for UI + persistence. */
function normalizeMessagesForStore(msgs) {
  if (!Array.isArray(msgs)) return [];
  return msgs.map((m) => ({
    ...m,
    id: typeof m?.id === 'string' && m.id ? m.id : genMessageId(),
    ...(m?.reaction === 'up' || m?.reaction === 'down' ? { reaction: m.reaction } : {}),
  }));
}

/** Prior turns for API: all messages before the latest user line (exclusive). */
function buildPriorTurnsFromMessages(msgs) {
  if (!Array.isArray(msgs) || msgs.length < 2) return [];
  return msgs.slice(0, -1).map((m) => ({
    role: m.role === 'assistant' ? 'assistant' : 'user',
    content: formatChatContent(m.content),
  }));
}

function lastUserContentBeforeIndex(messages, assistantIndex) {
  for (let j = assistantIndex - 1; j >= 0; j -= 1) {
    if (messages[j]?.role === 'user') return formatChatContent(messages[j].content);
  }
  return '';
}

const USER_WANTS_CODE_RE = /\b(code|snippet|implement(ation)?|jsx|tsx|python|java(script)?|typescript|react\s+component|write\s+(a\s+)?function|show\s+(me\s+)?(the\s+)?code|npm\s+install|example\s+code|paste\s+(the\s+)?code)\b/i;

function userRequestedCodeBlock(userText) {
  if (!userText || typeof userText !== 'string') return false;
  if (USER_WANTS_CODE_RE.test(userText)) return true;
  if (/```/.test(userText)) return true;
  return false;
}

/** Display-only cleanup when the model still emits markdown/code in prose answers. */
function sanitizeAssistantDisplay(raw, allowCodeFences) {
  if (raw == null || typeof raw !== 'string') return '';
  let t = raw;
  if (!allowCodeFences) {
    t = t.replace(/```[\w.-]*\n[\s\S]*?```/g, '\n\n');
    t = t.replace(/```[\s\S]*?```/g, '\n\n');
  }
  t = t.replace(/\*\*([^*]+)\*\*/g, '$1');
  t = t.replace(/(^|[\s>])\*([^*\n]+)\*(?=[\s<]|$)/gm, '$1$2');
  t = t.replace(/^\s*\*\s+(.+)$/gm, '• $1');
  return t.replace(/\n{3,}/g, '\n\n').trim();
}

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

const QUICK_START_CHIPS = [
  { label: 'Build website', icon: Layout, prompt: 'Build me a stunning multi-page website with hero, features grid, pricing, testimonials, and footer — beautiful modern design' },
  { label: 'Develop app', icon: Code, prompt: 'Build a complete React web app with multiple pages, authentication UI, dashboard, and CRUD data management' },
  { label: 'Design UI', icon: Globe, prompt: 'Design a beautiful modern SaaS product UI with clean design system, multiple pages, components, and responsive layout' },
  { label: 'SaaS MVP', icon: Zap, prompt: 'Build a SaaS MVP with login/register pages, dashboard, subscription pricing table, settings, and admin panel' },
  { label: 'Import code', icon: Upload, prompt: null, action: 'import' },
];

/** First row on home (Manus-style); Import + templates live under “More”. */
const HOME_PRIMARY_CHIPS = QUICK_START_CHIPS.slice(0, 4);

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
  const [moreMenuOpen, setMoreMenuOpen] = useState(false);
  const moreMenuRef = useRef(null);
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
  const homeMessagesRef = useRef(null);
  /** When true, new messages / loading scroll the transcript to the bottom */
  const stickToBottomRef = useRef(true);
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
        setChatMessages(normalizeMessagesForStore(msgs));
        setConversationStarted(true);
      }
      // If task has no messages yet (mid-send), keep in-memory chat — never clear optimistic turns
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

  const NEAR_BOTTOM_PX = 120;

  const scrollTranscriptToBottom = useCallback((behavior = 'smooth') => {
    const root = homeMessagesRef.current;
    if (!root || !stickToBottomRef.current) return;
    requestAnimationFrame(() => {
      root.scrollTo({ top: root.scrollHeight, behavior: behavior === 'instant' ? 'auto' : behavior });
    });
  }, []);

  useLayoutEffect(() => {
    const root = homeMessagesRef.current;
    if (!root || !chatMessages.length) return;
    const onScroll = () => {
      const dist = root.scrollHeight - root.scrollTop - root.clientHeight;
      stickToBottomRef.current = dist < NEAR_BOTTOM_PX;
    };
    root.addEventListener('scroll', onScroll, { passive: true });
    return () => root.removeEventListener('scroll', onScroll);
  }, [chatMessages.length]);

  useLayoutEffect(() => {
    if (!chatMessages.length) return;
    scrollTranscriptToBottom(chatLoading ? 'instant' : 'smooth');
  }, [chatMessages, chatLoading, scrollTranscriptToBottom]);

  /** Composer textarea: grow with content up to 160px, then internal scroll; ~single-line start */
  const adjustComposerHeight = useCallback(() => {
    const el = inputRef.current;
    if (!el) return;
    const maxPx = 160;
    const minPx = 28;
    el.style.height = '0px';
    el.style.overflowY = 'hidden';
    const sh = el.scrollHeight;
    const h = Math.min(Math.max(sh, minPx), maxPx);
    el.style.height = `${h}px`;
    el.style.overflowY = sh > maxPx ? 'auto' : 'hidden';
  }, []);

  useLayoutEffect(() => {
    adjustComposerHeight();
  }, [prompt, attachedFiles.length, chatMessages.length, adjustComposerHeight]);

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

  const requestAssistantReply = useCallback(async (taskId, userText, priorTurns, filesToSend) => {
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    const attachments = filesToSend?.length > 0 ? filesToSend.map((f) => {
      const type = f.type?.startsWith('image/') ? 'image' : (f.type === 'application/pdf' ? 'pdf' : 'text');
      return { type, data: f.data, name: f.name };
    }) : undefined;
    const res = await axios.post(`${API}/ai/chat`, {
      message: userText,
      session_id: `chat_${taskId}`,
      model: 'auto',
      ...(priorTurns?.length ? { prior_turns: priorTurns } : {}),
      ...(attachments?.length ? { attachments } : {}),
    }, { headers, timeout: 120000 });
    return res.data?.response || res.data?.message || '';
  }, [API, token]);

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
    stickToBottomRef.current = true;
    setPrompt('');
    setAttachedFiles([]);
    let messagesAfterUser;
    flushSync(() => {
      setChatMessages((prev) => {
        messagesAfterUser = [...prev, userMsg];
        return messagesAfterUser;
      });
      setConversationStarted(true);
      setChatLoading(true);
    });
    requestAnimationFrame(() => scrollTranscriptToBottom('instant'));

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
          id: genMessageId(),
          role: 'assistant',
          content: `✅ Agent created — ${schedule}. You can manage it in the Agents page.`
        }]);
      } catch (err) {
        setChatMessages(prev => [...prev, {
          id: genMessageId(),
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
    const pidFromUrl = searchParams.get('projectId');
    const taskId = existingTaskId
      || addTask({
        name: userPrompt.slice(0, 60),
        prompt: userPrompt,
        status: 'completed',
        type: 'chat',
        messages: normalizeMessagesForStore([userMsg]),
        ...(pidFromUrl ? { linkedProjectId: pidFromUrl } : {}),
      });
    if (!existingTaskId) {
      chatTaskIdRef.current = taskId;
      // Keep URL in sync so task context survives refresh (preserve project link from sidebar)
      const qs = new URLSearchParams({ chatTaskId: taskId });
      if (pidFromUrl) qs.set('projectId', pidFromUrl);
      navigate(`/app?${qs.toString()}`, { replace: true });
    } else if (messagesAfterUser) {
      updateTask(taskId, { messages: messagesAfterUser, prompt: userPrompt });
    }

    try {
      const priorTurns = buildPriorTurnsFromMessages(messagesAfterUser);
      const reply = await requestAssistantReply(taskId, userPrompt, priorTurns, filesToSend)
        || 'No response from model. Try again.';
      const assistantMsg = { role: 'assistant', content: reply };
      let afterAssistant;
      setChatMessages((prev) => {
        afterAssistant = [...prev, assistantMsg];
        return afterAssistant;
      });
      if (afterAssistant) updateTask(taskId, { messages: afterAssistant, prompt: userPrompt });
    } catch (err) {
      const is404 = err.response?.status === 404 || err.response?.status === 405;
      const detail = err.response?.data?.detail;
      const backendUnavailable = "Backend not available. Start the CrucibAI backend to use AI (see BACKEND_SETUP.md). You can still try \"Build me a landing page\" — it will open the Workspace; the build will need the backend running.";
      const fallback = is404 ? backendUnavailable : "Chat failed. For AI replies, run the backend (e.g. from CrucibAI) with Ollama. See BACKEND_SETUP.md.";
      const assistantMsg = {
        id: genMessageId(),
        role: 'assistant',
        content: (typeof detail === 'string' && detail && !is404) ? detail : (err.message?.includes('404') ? backendUnavailable : (err.message || fallback))
      };
      let afterAssistantErr;
      setChatMessages((prev) => {
        afterAssistantErr = normalizeMessagesForStore([...prev, assistantMsg]);
        return afterAssistantErr;
      });
      if (afterAssistantErr) updateTask(taskId, { messages: afterAssistantErr, prompt: userPrompt });
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

  const activateSkillName = (skillName) => {
    if (!token || !skillName) return;
    axios.post(`${API}/skills/${skillName}/activate`, {}, { headers: { Authorization: `Bearer ${token}` } }).catch(() => {});
  };

  const handleSkillFromMore = (skill) => {
    setMoreMenuOpen(false);
    if (!skill?.prompt) return;
    activateSkillName(skill.skill_name);
    handleChipClick({ label: skill.name, prompt: skill.prompt });
  };

  useEffect(() => {
    if (!moreMenuOpen) return;
    const onDoc = (e) => {
      if (moreMenuRef.current && !moreMenuRef.current.contains(e.target)) setMoreMenuOpen(false);
    };
    document.addEventListener('click', onDoc);
    return () => document.removeEventListener('click', onDoc);
  }, [moreMenuOpen]);

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
    const text = formatChatContent(chatMessages[index]?.content);
    if (!text) return;
    const role = chatMessages[index]?.role || 'user';
    navigator.clipboard?.writeText(text).then(() => setActionFeedback({ type: 'copy', index, role }));
  };

  const handleEditMessage = (content) => {
    if (content == null) return;
    setPrompt(formatChatContent(content));
    inputRef.current?.focus();
    requestAnimationFrame(() => adjustComposerHeight());
  };

  const handleRegenerateAssistant = async (assistantIndex) => {
    if (assistantIndex < 1 || chatLoading) return;
    const userPrev = chatMessages[assistantIndex - 1];
    if (!userPrev || userPrev.role !== 'user') return;
    const taskId = chatTaskIdRef.current;
    if (!taskId) return;
    const kept = normalizeMessagesForStore(chatMessages.slice(0, assistantIndex));
    const userText = formatChatContent(userPrev.content);
    const priorTurns = buildPriorTurnsFromMessages(kept);
    stickToBottomRef.current = true;
    setChatMessages(kept);
    updateTask(taskId, { messages: kept, prompt: userText });
    setChatLoading(true);
    requestAnimationFrame(() => scrollTranscriptToBottom('instant'));
    try {
      const reply = await requestAssistantReply(taskId, userText, priorTurns, [])
        || 'No response from model. Try again.';
      const after = normalizeMessagesForStore([...kept, { id: genMessageId(), role: 'assistant', content: reply }]);
      setChatMessages(after);
      updateTask(taskId, { messages: after, prompt: userText });
    } catch (err) {
      const detail = err.response?.data?.detail;
      const fallback = (typeof detail === 'string' && detail) ? detail : (err.message || 'Regenerate failed. Try again.');
      const after = normalizeMessagesForStore([...kept, { id: genMessageId(), role: 'assistant', content: fallback }]);
      setChatMessages(after);
      updateTask(taskId, { messages: after, prompt: userText });
    } finally {
      setChatLoading(false);
    }
  };

  const handleShareAssistant = async (i) => {
    const text = formatChatContent(chatMessages[i]?.content);
    const base = `${window.location.origin}/app`;
    const tid = chatTaskIdRef.current;
    const url = tid ? `${base}?chatTaskId=${encodeURIComponent(tid)}` : base;
    const payload = text ? `${text}\n\n—\n${url}` : url;
    const done = () => setActionFeedback({ type: 'share', index: i, role: 'assistant' });
    if (navigator.share) {
      try {
        await navigator.share({ title: 'CrucibAI', text: payload });
        done();
        return;
      } catch (e) {
        if (e && e.name === 'AbortError') return;
      }
    }
    try {
      await navigator.clipboard.writeText(payload);
      done();
    } catch (_) {}
  };

  const toggleMsgReaction = (i, dir) => {
    const taskId = chatTaskIdRef.current;
    if (!taskId) return;
    let nextMessages;
    setChatMessages((prev) => {
      const msg = prev[i];
      if (!msg || msg.role !== 'assistant') return prev;
      const cur = msg.reaction;
      const nextVal = cur === dir ? undefined : dir;
      const nextMsg = { ...msg };
      if (nextVal === undefined) delete nextMsg.reaction;
      else nextMsg.reaction = nextVal;
      nextMessages = prev.map((m, idx) => (idx === i ? nextMsg : m));
      return nextMessages;
    });
    if (nextMessages) updateTask(taskId, { messages: nextMessages });
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
      <div className={`dashboard-prompt-container ${hasChat ? 'dashboard-prompt-container--stacked dashboard-prompt-container--chat' : ''}`}>
        <div className="dashboard-prompt-input-wrap">
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
            onInput={() => requestAnimationFrame(() => adjustComposerHeight())}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
            placeholder={hasChat ? 'Ask a follow-up or describe a new idea...' : (location.state?.newProject ? 'Describe your project (e.g. I need a flower website)...' : 'Describe what you want to build or ask anything...')}
            className="dashboard-prompt-input"
            rows={1}
            aria-label="Message"
          />
        </div>
        <div className="dashboard-prompt-footer">
          <div className="dashboard-prompt-footer-left" aria-label="Add context">
            <div className="dashboard-model-badge" title="Auto-selects best model">
              <Sparkles size={14} />
            </div>
            <button type="button" onClick={() => fileInputRef.current?.click()} className="dashboard-prompt-btn" title="Attach file">
              <Paperclip size={18} />
            </button>
            <button
              type="button"
              className="dashboard-prompt-btn"
              title="Open workspace"
              onClick={() => navigate({ pathname: '/app/workspace' })}
            >
              <Monitor size={18} />
            </button>
            <input ref={fileInputRef} type="file" multiple accept="image/*,.pdf,.txt,.md,.zip,audio/*,.js,.jsx,.ts,.tsx,.css,.html,.json,.py" onChange={handleFileSelect} className="hidden" />
          </div>
          <div className={`dashboard-prompt-footer-right ${isRecording ? 'dashboard-prompt-footer-right--recording' : ''}`} aria-label="Send options">
            <Link to="/app/templates" className="dashboard-prompt-btn dashboard-prompt-btn--link" title="Templates & gallery">
              <Globe size={18} />
            </Link>
            {isRecording ? (
              <div className="dashboard-prompt-footer-wave-wrap">
                <VoiceWaveform stream={audioStream} onStop={stopRecording} onConfirm={confirmRecording} isRecording={isRecording} />
              </div>
            ) : (
              <button type="button" onClick={isTranscribing ? undefined : startRecording} disabled={isTranscribing} className={`dashboard-prompt-btn ${isRecording ? 'recording' : ''}`} title={isTranscribing ? 'Transcribing...' : 'Voice input (9 languages)'}>
                {isTranscribing ? <Loader2 size={18} className="animate-spin" /> : <Mic size={18} />}
              </button>
            )}
            <button
              type="submit"
              disabled={(!prompt.trim() && !attachedFiles.length) || chatLoading}
              className={`dashboard-prompt-submit ${!chatLoading && (prompt.trim() || attachedFiles.length) ? 'dashboard-prompt-submit--ready' : ''}`}
              title="Send"
            >
              {chatLoading ? <Loader2 size={18} className="animate-spin" /> : <ArrowUp size={18} strokeWidth={2.25} />}
            </button>
          </div>
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
      <div ref={homeMessagesRef} className={`home-messages ${hasChat ? 'has-chat' : ''}`}>
        {!hasChat && (
          <div className="home-hero-stage">
            <div className="dashboard-home-column">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="dashboard-greeting">
              <h1 className="dashboard-greeting-text">
                <span className="dashboard-greeting-sub">{location.state?.newProject ? 'What\'s your new project?' : 'What do you want to build?'}</span>
              </h1>
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.1 }} className="dashboard-prompt-inline">
              {inputForm}
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.15 }} className="dashboard-chips" ref={moreMenuRef}>
              <div className="dashboard-chips-row">
                <div className="dashboard-chips-grid">
                  {HOME_PRIMARY_CHIPS.map((chip) => (
                    <button key={chip.label} type="button" onClick={() => handleChipClick(chip)} className="dashboard-chip">
                      <chip.icon size={16} className="dashboard-chip-icon" />
                      <span>{chip.label}</span>
                    </button>
                  ))}
                </div>
                <div className="dashboard-more-wrap">
                  <button
                    type="button"
                    className={`dashboard-chip dashboard-chip-more ${moreMenuOpen ? 'open' : ''}`}
                    aria-expanded={moreMenuOpen}
                    onClick={(e) => {
                      e.stopPropagation();
                      setMoreMenuOpen((o) => !o);
                    }}
                  >
                    <span>More</span>
                    <ChevronDown size={16} className="dashboard-chip-more-chevron" />
                  </button>
                  {moreMenuOpen && (
                    <div className="dashboard-more-menu" role="menu">
                      {QUICK_START_CHIPS.slice(4).map((chip) => (
                        <button
                          key={chip.label}
                          type="button"
                          role="menuitem"
                          className="dashboard-more-menu-item"
                          onClick={() => {
                            setMoreMenuOpen(false);
                            handleChipClick(chip);
                          }}
                        >
                          <chip.icon size={14} className="dashboard-chip-icon" />
                          {chip.label}
                        </button>
                      ))}
                      <div className="dashboard-more-menu-divider" />
                      {SKILLS.map((skill) => (
                        <button
                          key={skill.name}
                          type="button"
                          role="menuitem"
                          className="dashboard-more-menu-item dashboard-more-menu-item-skill"
                          onClick={() => handleSkillFromMore(skill)}
                        >
                          <span className="dashboard-more-skill-emoji" aria-hidden>{skill.icon}</span>
                          <span>{skill.name}</span>
                        </button>
                      ))}
                      <button
                        type="button"
                        className="dashboard-more-menu-footer"
                        onClick={() => {
                          setMoreMenuOpen(false);
                          navigate('/app/templates');
                        }}
                      >
                        Browse templates &amp; gallery <ArrowRight size={14} />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
            </div>

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
          </div>
        )}
        {hasChat && (
          <div className="dashboard-chat-shell">
            <div className="dashboard-chat-inner">
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="dashboard-chat-thread">
              {chatMessages.map((msg, i) => {
                const userAskedCode = msg.role === 'assistant' && userRequestedCodeBlock(lastUserContentBeforeIndex(chatMessages, i));
                const bubbleText = msg.role === 'assistant'
                  ? sanitizeAssistantDisplay(formatChatContent(msg.content), userAskedCode)
                  : formatChatContent(msg.content);
                return (
                <div
                  key={msg.id || `row-${i}`}
                  className={`dashboard-chat-row ${msg.role === 'user' ? 'dashboard-chat-row--user' : 'dashboard-chat-row--assistant'}`}
                >
                  <div className="dashboard-chat-cluster">
                    {msg.role === 'assistant' && (
                      <div className="dashboard-chat-identifier">
                        <Logo href={null} showTagline={false} height={18} className="dashboard-chat-logo" />
                        <span className="dashboard-chat-brand">CrucibAI</span>
                      </div>
                    )}
                    <div className={`dashboard-chat-bubble ${msg.role}`}>
                      {bubbleText}
                    </div>
                    {msg.buildOffer && (
                      <div className="dashboard-chat-build-offer">
                        <button type="button" onClick={() => handleStartBuilding(msg.buildOffer)} className="dashboard-chat-start-building-btn">
                          Start Building →
                        </button>
                      </div>
                    )}
                    {msg.role === 'assistant' && (
                      <div className="dashboard-chat-actions dashboard-chat-actions--assistant">
                        <button
                          type="button"
                          onClick={() => handleCopyMessage(i)}
                          className="dashboard-chat-action"
                          title={actionFeedback?.type === 'copy' && actionFeedback?.index === i && actionFeedback?.role === 'assistant' ? 'Copied!' : 'Copy'}
                          aria-label="Copy assistant message"
                        >
                          {actionFeedback?.type === 'copy' && actionFeedback?.index === i && actionFeedback?.role === 'assistant' ? <Check size={14} /> : <Copy size={14} />}
                        </button>
                        <button
                          type="button"
                          className={`dashboard-chat-action${msg.reaction === 'up' ? ' dashboard-chat-action--active' : ''}`}
                          title="Helpful"
                          aria-label="Thumbs up"
                          aria-pressed={msg.reaction === 'up'}
                          onClick={() => toggleMsgReaction(i, 'up')}
                        >
                          <ThumbsUp size={14} />
                        </button>
                        <button
                          type="button"
                          className={`dashboard-chat-action${msg.reaction === 'down' ? ' dashboard-chat-action--active' : ''}`}
                          title="Not helpful"
                          aria-label="Thumbs down"
                          aria-pressed={msg.reaction === 'down'}
                          onClick={() => toggleMsgReaction(i, 'down')}
                        >
                          <ThumbsDown size={14} />
                        </button>
                        <button
                          type="button"
                          className="dashboard-chat-action"
                          title="Share"
                          aria-label="Share"
                          onClick={() => handleShareAssistant(i)}
                        >
                          {actionFeedback?.type === 'share' && actionFeedback?.index === i && actionFeedback?.role === 'assistant' ? <Check size={14} /> : <Share2 size={14} />}
                        </button>
                        <button
                          type="button"
                          className="dashboard-chat-action"
                          title="Regenerate"
                          aria-label="Regenerate"
                          disabled={chatLoading}
                          onClick={() => handleRegenerateAssistant(i)}
                        >
                          <RefreshCw size={14} />
                        </button>
                      </div>
                    )}
                    {msg.role === 'user' && (
                      <div className="dashboard-chat-actions dashboard-chat-actions--user">
                        <button
                          type="button"
                          onClick={() => handleCopyMessage(i)}
                          className="dashboard-chat-action"
                          title={actionFeedback?.type === 'copy' && actionFeedback?.index === i && actionFeedback?.role === 'user' ? 'Copied!' : 'Copy'}
                          aria-label="Copy user message"
                        >
                          {actionFeedback?.type === 'copy' && actionFeedback?.index === i && actionFeedback?.role === 'user' ? <Check size={14} /> : <Copy size={14} />}
                        </button>
                        <button type="button" onClick={() => handleEditMessage(msg.content)} className="dashboard-chat-action" title="Edit" aria-label="Edit">
                          <Pencil size={14} />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
                );
              })}
              {chatLoading && (
                <div className="dashboard-chat-row dashboard-chat-row--assistant">
                  <div className="dashboard-chat-cluster">
                    <div className="dashboard-chat-identifier">
                      <Logo href={null} showTagline={false} height={18} className="dashboard-chat-logo" />
                      <span className="dashboard-chat-brand">CrucibAI</span>
                    </div>
                    <div className="dashboard-chat-bubble assistant">
                      <Loader2 size={16} className="animate-spin" style={{ display: 'inline-block' }} aria-hidden />
                      <span style={{ marginLeft: 8 }}>Thinking...</span>
                    </div>
                  </div>
                </div>
              )}
              </motion.div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {hasChat && (
        <div className="home-input-bar home-input-bar--chat">
          <div className="home-prompt-wrapper home-prompt-wrapper--chat">{inputForm}</div>
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

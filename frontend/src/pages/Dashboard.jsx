import { useState, useEffect, useRef } from 'react';
import { flushSync } from 'react-dom';
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Mic, MicOff, Paperclip, Loader2,
  Sparkles, ArrowRight, Upload, X, Github,
  Layout, Smartphone, Code, Zap, Globe,
  Copy, Pencil
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
  if (!BUILD_KEYWORDS.test(p) && !AGENT_KEYWORDS.test(p)) return "chat";

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

const QUICK_START_CHIPS = [
  { label: 'Landing page', icon: Layout, prompt: 'Build me a modern landing page with hero section, features grid, pricing table, and footer' },
  { label: 'Automation', icon: Zap, prompt: 'Create an automation workflow that monitors a webhook, processes data, and sends notifications' },
  { label: 'Import code', icon: Upload, prompt: null, action: 'import' },
  { label: 'SaaS MVP', icon: Globe, prompt: 'Build a SaaS MVP with user authentication, dashboard, billing integration, and admin panel' },
  { label: 'Mobile app', icon: Smartphone, prompt: 'Build a React Native mobile app with tab navigation, user profile, and push notifications' },
  { label: 'API backend', icon: Code, prompt: 'Create a REST API backend with authentication, CRUD endpoints, database models, and documentation' },
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

  const firstName = user?.name?.split(' ')[0] || 'there';

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
    const textParts = [prompt.trim(), ...attachedFiles.filter(f => f.type === 'text/plain').map(f => f.data || '')].filter(Boolean);
    const userPrompt = textParts.join('\n\n');
    const filesToSend = [...attachedFiles];
    if (!userPrompt && filesToSend.length === 0) return;

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
      const spec = await inferBuildSpec(userPrompt, API, token);
      const oneLiner = spec.endsWith('.') ? spec : `${spec}.`;
      const summary = `Got it — I'll build ${oneLiner.charAt(0).toLowerCase() + oneLiner.slice(1)}`;
      const buildOfferMsg = {
        role: 'assistant',
        content: summary,
        buildOffer: { spec: spec.trim(), attachedFiles: filesToSend.length > 0 ? filesToSend : undefined }
      };
      setChatMessages(prev => [...prev, buildOfferMsg]);
      setChatLoading(false);
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
      const assistantMsg = {
        role: 'assistant',
        content: "I'm CrucibAI — I build apps and automations. Try \"Build me a landing page\" or \"Create an agent that emails me every morning.\""
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
      const reader = new FileReader();
      reader.onload = (ev) => {
        setAttachedFiles(prev => [...prev, {
          name: file.name,
          type: file.type,
          data: ev.target.result,
          size: file.size
        }]);
      };
      if (file.type.startsWith('image/')) {
        reader.readAsDataURL(file);
      } else if (file.type === 'application/pdf') {
        reader.readAsDataURL(file);
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
        } catch (_) {}
        setIsTranscribing(false);
      };
      recorder.start(1000);
      mediaRecorderRef.current = { recorder, stream };
      setAudioStream(stream);
      setIsRecording(true);
    } catch (err) {
      setIsRecording(false);
      if (err?.name === 'NotAllowedError') {
        setChatMessages(prev => [...prev, { role: 'assistant', content: 'Microphone access denied. Allow it in browser settings.' }]);
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
          placeholder={hasChat ? 'Build something or ask anything' : 'Describe your app, automation, or idea...'}
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
          <input ref={fileInputRef} type="file" multiple accept="image/*,.pdf,.txt,.js,.jsx,.ts,.tsx,.css,.html,.json,.py" onChange={handleFileSelect} className="hidden" />
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
                <span className="dashboard-greeting-name">Hi {firstName}.</span>
                <span className="dashboard-greeting-sub">What do you want to build?</span>
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
                  <button type="button" onClick={() => handleCopyMessage(i)} className="dashboard-chat-action" title="Copy">
                    <Copy size={14} />
                    {actionFeedback?.type === 'copy' && actionFeedback?.index === i ? ' Copied!' : ' Copy'}
                  </button>
                  {msg.role === 'user' && (
                    <button type="button" onClick={() => handleEditMessage(msg.content)} className="dashboard-chat-action" title="Edit">
                      <Pencil size={14} /> Edit
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

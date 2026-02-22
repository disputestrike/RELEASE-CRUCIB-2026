import { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Send, Mic, MicOff, Paperclip, Loader2,
  Sparkles, ArrowRight, Upload, X, Github,
  Layout, Smartphone, Bot, Code, Zap, Globe
} from 'lucide-react';
import { useAuth, API } from '../App';
import { useTaskStore } from '../stores/useTaskStore';
import axios from 'axios';
import VoiceWaveform from '../components/VoiceWaveform';
import '../components/VoiceWaveform.css';
import './Dashboard.css';

/**
 * Dashboard — Prompt-first entry point
 * 
 * ISSUE 1: Intent detection — build keywords → workspace, else → chat inline
 * ISSUE 2: Prompt box full width (max-width: 680px)
 * ISSUE 3: Voice waveform on home screen
 */

function detectIntent(prompt) {
  const lower = prompt.toLowerCase();

  const agentKeywords = [
    'every morning', 'every day', 'every week', 'every month',
    'every hour', 'every night', 'every monday', 'every friday',
    'schedule', 'scheduled', 'automatically', 'automatically send',
    'run agent', 'create agent', 'set up agent', 'build agent',
    'make an agent', 'new agent', 'run automatically',
    'remind me', 'reminder', 'alert me', 'alert me when',
    'notify me', 'watch for', 'monitor', 'keep track',
    'send me daily', 'send me weekly', 'send me monthly',
    'weekly digest', 'daily digest', 'daily summary',
    'weekly summary', 'weekly report', 'daily report',
    'automation', 'automate', 'automated', 'auto-send',
    'trigger', 'webhook', 'on schedule', 'recurring',
    'run on', 'run every', 'post to slack', 'email me every',
    'summarize and send', 'digest', 'workflow',
    'whenever', 'each time', 'every time something',
  ];

  const buildKeywords = [
    'build', 'build me', 'build a', 'build an',
    'create', 'create a', 'create an', 'create me',
    'make', 'make a', 'make me', 'make an',
    'develop', 'develop a', 'develop me',
    'design', 'design a', 'design me',
    'generate', 'generate a',
    'code', 'code me', 'write code',
    'landing page', 'landing page for',
    'website', 'web app', 'web application',
    'mobile app', 'ios app', 'android app', 'react native',
    'saas', 'saas app', 'saas platform', 'saas tool',
    'dashboard', 'admin dashboard', 'analytics dashboard',
    'api', 'api backend', 'rest api', 'backend',
    'frontend', 'full stack', 'fullstack',
    'app', 'application', 'platform', 'tool', 'system',
    'portfolio', 'portfolio site',
    'ecommerce', 'e-commerce', 'store', 'shop',
    'blog', 'cms', 'content management',
    'crm', 'customer management',
    'form', 'contact form', 'signup form',
    'component', 'react component', 'ui component',
    'import my code', 'import code', 'upload my code',
    'fix my code', 'review my code', 'continue my project',
    'clone', 'clone this', 'replicate',
    'calculator', 'counter', 'todo', 'to-do',
    'chat app', 'messaging app', 'booking app',
    'marketplace', 'social network', 'community platform',
  ];

  if (agentKeywords.some(kw => lower.includes(kw))) return 'agent';
  if (buildKeywords.some(kw => lower.includes(kw))) return 'build';
  return 'chat';
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
  const { user, token } = useAuth();
  const { addTask } = useTaskStore();
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
  const inputRef = useRef(null);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);

  // Autofocus prompt on load; focus when navigating from "+ New Agent" (placeholder never changes)
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

  const firstName = user?.name?.split(' ')[0] || 'there';

  const handleSubmit = async (e) => {
    e?.preventDefault();
    if (!prompt.trim()) return;

    const intent = detectIntent(prompt);
    const userPrompt = prompt.trim();
    setConversationStarted(true);
    setPrompt('');

    if (intent === 'build') {
      // BUCKET 2: BUILD — save to All Tasks only, then navigate to workspace (taskId in URL so sidebar highlights it)
      const taskId = addTask({ name: userPrompt.slice(0, 120), prompt: userPrompt, status: 'pending' });
      navigate({
        pathname: '/app/workspace',
        search: taskId ? `?taskId=${encodeURIComponent(taskId)}` : '',
        state: {
          initialPrompt: userPrompt,
          autoStart: true,
          initialAttachedFiles: attachedFiles.length > 0 ? attachedFiles : undefined
        }
      });
      return;
    }

    if (intent === 'agent') {
      // BUCKET 3: AGENT — add user message, create agent via API, show confirmation, save to Agents list only (API handles list)
      setChatMessages(prev => [...prev, { role: 'user', content: userPrompt }]);
      setChatLoading(true);
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

    // BUCKET 1: CHAT — respond inline, save nothing
    setChatMessages(prev => [...prev, { role: 'user', content: userPrompt }]);
    setChatLoading(true);
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await axios.post(`${API}/ai/chat`, {
        message: userPrompt,
        session_id: 'home_chat',
        model: 'auto'
      }, { headers, timeout: 30000 });
      const reply = res.data?.response || res.data?.message || "Hey! What are we building today?";
      setChatMessages(prev => [...prev, { role: 'assistant', content: reply }]);
    } catch (err) {
      setChatMessages(prev => [...prev, {
        role: 'assistant',
        content: "I'm CrucibAI — I build apps and automations. Try \"Build me a landing page\" or \"Create an agent that emails me every morning.\""
      }]);
    } finally {
      setChatLoading(false);
    }
  };

  function formatCronShort(cron) {
    if (!cron) return 'on a schedule';
    const parts = cron.trim().split(/\s+/);
    if (parts.length >= 5) {
      const [min, hour, , , dow] = parts;
      if (hour !== '*' && min !== '*') return `every day at ${hour.padStart(2, '0')}:${min.padStart(2, '0')}`;
      if (hour !== '*') return `every day at ${hour}:00`;
    }
    return 'on a schedule';
  }

  const handleChipClick = (chip) => {
    if (chip.action === 'import') {
      setShowImportModal(true);
      return;
    }
    if (chip.prompt) {
      const taskId = addTask({ name: (chip.prompt || chip.label).slice(0, 120), prompt: chip.prompt, status: 'pending' });
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

  return (
    <div className="dashboard-redesigned home-screen" data-testid="dashboard">
      <div className={`home-messages ${conversationStarted || chatMessages.length > 0 ? 'has-chat' : ''}`}>
        {!conversationStarted && (
          <>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className="dashboard-greeting"
            >
              <h1 className="dashboard-greeting-text">
                Hi {firstName}. <span className="dashboard-greeting-sub">What do you want to build?</span>
              </h1>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.1 }}
              className="dashboard-prompt-inline"
            >
              <motion.form onSubmit={handleSubmit} className="dashboard-prompt-form">
                {attachedFiles.length > 0 && (
                  <div className="dashboard-attached-files">
                    {attachedFiles.map((file, i) => (
                      <div key={i} className="dashboard-attached-file">
                        <span className="dashboard-attached-name">{file.name}</span>
                        <button type="button" onClick={() => removeFile(i)} className="dashboard-attached-remove">
                          <X size={14} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                <div className="dashboard-prompt-container">
                  <textarea
                    ref={inputRef}
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSubmit(e);
                      }
                    }}
                    placeholder="Describe your app, automation, or idea..."
                    className="dashboard-prompt-input"
                    rows={1}
                  />
                  <div className="dashboard-prompt-actions">
                    <div className="dashboard-model-badge" title="Auto-selects best model">
                      <Sparkles size={14} />
                    </div>
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="dashboard-prompt-btn"
                      title="Attach file"
                    >
                      <Paperclip size={18} />
                    </button>
                    <input
                      ref={fileInputRef}
                      type="file"
                      multiple
                      accept="image/*,.pdf,.txt,.js,.jsx,.ts,.tsx,.css,.html,.json,.py"
                      onChange={handleFileSelect}
                      className="hidden"
                    />
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
                        className={`dashboard-prompt-btn ${isRecording ? 'recording' : ''}`}
                        title={isTranscribing ? 'Transcribing...' : 'Voice input (9 languages)'}
                      >
                        {isTranscribing ? <Loader2 size={18} className="animate-spin" /> : <Mic size={18} />}
                      </button>
                    )}
                    <button
                      type="submit"
                      disabled={!prompt.trim() || chatLoading}
                      className="dashboard-prompt-submit"
                      title="Send"
                    >
                      {chatLoading ? <Loader2 size={18} className="animate-spin" /> : <ArrowRight size={18} />}
                    </button>
                  </div>
                </div>
              </motion.form>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.2 }}
              className="dashboard-chips"
            >
              <span className="dashboard-chips-label">Quick start:</span>
              <div className="dashboard-chips-grid">
                {QUICK_START_CHIPS.map((chip) => (
                  <button
                    key={chip.label}
                    type="button"
                    onClick={() => handleChipClick(chip)}
                    className="dashboard-chip"
                  >
                    <chip.icon size={16} className="dashboard-chip-icon" />
                    <span>{chip.label}</span>
                  </button>
                ))}
              </div>
            </motion.div>
          </>
        )}
        {chatMessages.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="dashboard-chat-thread"
          >
            {chatMessages.map((msg, i) => (
              <div key={i} className={`dashboard-chat-msg ${msg.role}`}>
                <div className={`dashboard-chat-bubble ${msg.role}`}>
                  {msg.content}
                </div>
              </div>
            ))}
            {chatLoading && (
              <div className="dashboard-chat-msg assistant">
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

      {(conversationStarted || chatMessages.length > 0) && (
        <div className="home-input-bar">
          <div className="home-prompt-wrapper">
            <form onSubmit={handleSubmit} className="dashboard-prompt-form">
              {attachedFiles.length > 0 && (
                <div className="dashboard-attached-files">
                  {attachedFiles.map((file, i) => (
                    <div key={i} className="dashboard-attached-file">
                      <span className="dashboard-attached-name">{file.name}</span>
                      <button type="button" onClick={() => removeFile(i)} className="dashboard-attached-remove">
                        <X size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
              <div className="dashboard-prompt-container">
                <textarea
                  ref={inputRef}
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSubmit(e);
                    }
                  }}
                  placeholder="Build something or ask anything"
                  className="dashboard-prompt-input"
                  rows={1}
                />
                <div className="dashboard-prompt-actions">
                  <div className="dashboard-model-badge" title="Auto-selects best model">
                    <Sparkles size={14} />
                  </div>
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="dashboard-prompt-btn"
                    title="Attach file"
                  >
                    <Paperclip size={18} />
                  </button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept="image/*,.pdf,.txt,.js,.jsx,.ts,.tsx,.css,.html,.json,.py"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
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
                      className={`dashboard-prompt-btn ${isRecording ? 'recording' : ''}`}
                      title={isTranscribing ? 'Transcribing...' : 'Voice input (9 languages)'}
                    >
                      {isTranscribing ? <Loader2 size={18} className="animate-spin" /> : <Mic size={18} />}
                    </button>
                  )}
                  <button
                    type="submit"
                    disabled={!prompt.trim() || chatLoading}
                    className="dashboard-prompt-submit"
                    title="Send"
                  >
                    {chatLoading ? <Loader2 size={18} className="animate-spin" /> : <ArrowRight size={18} />}
                  </button>
                </div>
              </div>
            </form>
          </div>
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

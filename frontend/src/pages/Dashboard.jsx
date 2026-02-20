import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Send, Mic, MicOff, Paperclip, Loader2,
  Sparkles, ArrowRight, Upload, X, Github,
  Layout, Smartphone, Bot, Code, Zap, Globe
} from 'lucide-react';
import { useAuth, API } from '../App';
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

const BUILD_KEYWORDS = [
  'build', 'create', 'make', 'develop', 'design', 'generate',
  'landing page', 'dashboard', 'saas', 'mobile app', 'api',
  'automation', 'website', 'app', 'tool', 'platform', 'system',
  'todo', 'calculator', 'form', 'page', 'component', 'clone',
  'e-commerce', 'ecommerce', 'blog', 'portfolio', 'chat',
];

function detectIntent(prompt) {
  const lower = prompt.toLowerCase();
  return BUILD_KEYWORDS.some(kw => lower.includes(kw)) ? 'build' : 'chat';
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
  const { user, token } = useAuth();
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
  const [audioStream, setAudioStream] = useState(null);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);

  // Autofocus prompt on load
  useEffect(() => {
    const timer = setTimeout(() => inputRef.current?.focus(), 300);
    return () => clearTimeout(timer);
  }, []);

  const firstName = user?.name?.split(' ')[0] || 'there';

  const handleSubmit = async (e) => {
    e?.preventDefault();
    if (!prompt.trim()) return;

    const intent = detectIntent(prompt);

    if (intent === 'build') {
      // Navigate to workspace with prompt and autoStart flag
      navigate('/app/workspace', {
        state: {
          initialPrompt: prompt,
          autoStart: true,
          initialAttachedFiles: attachedFiles.length > 0 ? attachedFiles : undefined
        }
      });
    } else {
      // Conversational — stay on home screen, respond inline
      const userMsg = { role: 'user', content: prompt };
      setChatMessages(prev => [...prev, userMsg]);
      setPrompt('');
      setChatLoading(true);
      try {
        const headers = token ? { Authorization: `Bearer ${token}` } : {};
        const res = await axios.post(`${API}/ai/chat`, {
          message: prompt,
          session_id: 'home_chat',
          model: 'auto'
        }, { headers, timeout: 30000 });
        const reply = res.data?.response || res.data?.message || "I'm here to help! Try asking me to build something, like \"Build me a todo app\".";
        setChatMessages(prev => [...prev, { role: 'assistant', content: reply }]);
      } catch (err) {
        setChatMessages(prev => [...prev, {
          role: 'assistant',
          content: "I'm CrucibAI — I can build apps for you! Try saying \"Build me a landing page\" or \"Create a todo app\"."
        }]);
      } finally {
        setChatLoading(false);
      }
    }
  };

  const handleChipClick = (chip) => {
    if (chip.action === 'import') {
      setShowImportModal(true);
      return;
    }
    if (chip.prompt) {
      navigate('/app/workspace', {
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
    <div className="dashboard-redesigned" data-testid="dashboard">
      <div className="dashboard-center">
        {/* Greeting */}
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

        {/* Prompt Box */}
        <motion.form
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          onSubmit={handleSubmit}
          className="dashboard-prompt-form"
        >
          {/* Attached files preview */}
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
              {/* Model indicator */}
              <div className="dashboard-model-badge" title="Auto-selects best model">
                <Sparkles size={14} />
              </div>

              {/* File attachment */}
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

              {/* Voice input — ISSUE 3: VoiceWaveform on home screen */}
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

              {/* Submit */}
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

        {/* Chat Messages — ISSUE 1: conversational responses inline */}
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

        {/* Quick Start Chips */}
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
      </div>

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

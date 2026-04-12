import React, { useState, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, ArrowRight, Menu, X, Paperclip, Image, FileText, Mic, MicOff } from 'lucide-react';
import { useAuth, API } from '../App';
import axios from 'axios';
import { logApiError } from '../utils/apiError';
import Logo from '../components/Logo';
import SuggestionChips from '../components/SuggestionChips';
import SolutionsNavDropdown, { SOLUTION_LINKS, USE_CASE_LINKS } from '../components/SolutionsNavDropdown';
import { withWorkspaceHandoffNonce } from '../utils/workspaceHandoff';

const PENDING_PROMPT_KEY = 'crucibai_pending_prompt';
const MAX_PROMPT_IN_URL = 1500;

const LandingPage = () => {
  const navigate = useNavigate();
  const { user, token } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [isBuilding, setIsBuilding] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState([]);
  const [voiceLanguage, setVoiceLanguage] = useState('en');
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [voiceError, setVoiceError] = useState(null);
  const chatEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const voiceStreamRef = useRef(null);
  const voiceChunksRef = useRef([]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const startBuild = async (promptOverride = null, filesOverride = null) => {
    const prompt = (promptOverride ?? input).trim();
    if (!prompt || isBuilding) return;
    const state = (filesOverride?.length || attachedFiles?.length) ? { initialAttachedFiles: filesOverride || attachedFiles } : undefined;
    // If user is not signed in, save prompt so after auth we go straight to building (time-to-action)
    if (!user && !token) {
      try {
        sessionStorage.setItem(PENDING_PROMPT_KEY, prompt);
        if (state?.initialAttachedFiles?.length) {
          sessionStorage.setItem(PENDING_PROMPT_KEY + '_hasFiles', '1');
        }
      } catch (_) {}
      navigate(`/auth?redirect=${encodeURIComponent('/app/workspace')}`);
      return;
    }
    const q = `prompt=${encodeURIComponent(prompt)}&autoStart=1`;
    navigate(`/app/workspace?${q}`, { state: withWorkspaceHandoffNonce({ ...state, initialPrompt: prompt, autoStart: true }) });
  };

  const handleLandingFileSelect = (e) => {
    const selected = Array.from(e.target.files || []);
    const valid = selected.filter(f =>
      f.type.startsWith('image/') || f.type === 'application/pdf' || f.type.startsWith('text/') ||
      f.type === 'application/zip' || f.name?.toLowerCase().endsWith('.zip') || f.type.startsWith('audio/')
    );
    valid.forEach(file => {
      const isZip = file.type === 'application/zip' || file.name?.toLowerCase().endsWith('.zip');
      const isAudio = file.type.startsWith('audio/');
      const reader = new FileReader();
      reader.onload = (ev) => {
        const data = isZip ? btoa(String.fromCharCode(...new Uint8Array(ev.target.result))) : ev.target.result;
        setAttachedFiles(prev => [...prev, { name: file.name, type: file.type, data, size: file.size }]);
      };
      if (file.type.startsWith('image/') || file.type === 'application/pdf' || isAudio) reader.readAsDataURL(file);
      else if (isZip) reader.readAsArrayBuffer(file);
      else reader.readAsText(file);
    });
    e.target.value = '';
  };

  const removeLandingFile = (index) => {
    setAttachedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleVoiceTranscribed = (text) => {
    setInput(prev => (prev ? prev + ' ' : '') + text);
  };

  const startVoiceRecording = async () => {
    setVoiceError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      voiceStreamRef.current = stream;
      const mimeType = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'].find(m => MediaRecorder.isTypeSupported(m)) || 'audio/webm';
      const recorder = new MediaRecorder(stream, { mimeType });
      voiceChunksRef.current = [];
      recorder.ondataavailable = (e) => { if (e.data.size > 0) voiceChunksRef.current.push(e.data); };
      recorder.onerror = () => { setVoiceError('Recording error'); setIsRecording(false); };
      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
    } catch (err) {
      setVoiceError(err.name === 'NotAllowedError' ? 'Microphone access denied.' : err.message || 'Could not start recording.');
      setIsRecording(false);
    }
  };

  const stopVoiceRecording = async () => {
    if (!mediaRecorderRef.current || mediaRecorderRef.current.state === 'inactive') return;
    setIsRecording(false);
    setIsTranscribing(true);
    setVoiceError(null);
    mediaRecorderRef.current.onstop = async () => {
      try {
        const blob = new Blob(voiceChunksRef.current, { type: mediaRecorderRef.current.mimeType || 'audio/webm' });
        if (blob.size < 100) {
          setVoiceError('Recording too short. Speak at least 1 second.');
          setIsTranscribing(false);
          return;
        }
        const ext = (mediaRecorderRef.current.mimeType || '').includes('mp4') ? 'm4a' : 'webm';
        const formData = new FormData();
        formData.append('audio', blob, `recording.${ext}`);
        formData.append('language', voiceLanguage);
        const headers = token ? { Authorization: `Bearer ${token}` } : {};
        const res = await axios.post(`${API}/voice/transcribe`, formData, {
          headers: { ...headers, 'Content-Type': 'multipart/form-data' },
          timeout: 60000,
          maxContentLength: Infinity,
          maxBodyLength: Infinity,
        });
        const text = res.data?.text?.trim();
        if (text) handleVoiceTranscribed(text);
        else setVoiceError('No text from transcription.');
      } catch (err) {
        const msg = err?.code === 'ERR_NETWORK' || err?.response?.status >= 500
          ? 'Voice needs the backend. Start the CrucibAI backend to transcribe.'
          : (err.response?.data?.detail || err.message || 'Transcription failed.');
        setVoiceError(msg);
      } finally {
        setIsTranscribing(false);
        if (voiceStreamRef.current) {
          voiceStreamRef.current.getTracks().forEach(t => t.stop());
          voiceStreamRef.current = null;
        }
      }
    };
    mediaRecorderRef.current.stop();
  };

  const handleSubmit = async (e) => {
    e?.preventDefault();
    let hasInput = input.trim();
    const hasImageOnly = attachedFiles.length > 0 && attachedFiles.every(f => f.type?.startsWith('image/'));
    let filesToSend = attachedFiles.length ? [...attachedFiles] : null;
    // Transcribe attached audio (voice notes) and use as prompt if no text
    const audioFiles = (filesToSend || []).filter(f => f.type?.startsWith?.('audio/'));
    if (audioFiles.length > 0) {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      for (const att of audioFiles) {
        try {
          const blob = await (await fetch(att.data)).blob();
          const formData = new FormData();
          formData.append('audio', blob, att.name || 'audio.webm');
          const res = await axios.post(`${API}/voice/transcribe`, formData, { headers, timeout: 30000 });
          const text = res.data?.text?.trim();
          if (text) hasInput = (hasInput ? hasInput + ' ' : '') + text;
        } catch (_) {}
      }
      if (filesToSend) filesToSend = filesToSend.filter(f => !f.type?.startsWith?.('audio/'));
    }
    if (!hasInput && !hasImageOnly) return;
    startBuild(hasInput || 'Convert image to code', filesToSend?.length ? filesToSend : null);
  };

  /** Send enabled when there is text or image/audio attachment (matches submit disabled logic). */
  const hasLandingSendContent =
    Boolean(input.trim()) ||
    attachedFiles.some((f) => f.type?.startsWith('image/') || f.type?.startsWith('audio/'));

  return (
    <div className="marketing-page bg-kimi-bg text-kimi-text grid-pattern-kimi">
      {/* Navigation — 6 items only */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-kimi-bg border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-6 py-5 flex items-center gap-6">
          <Logo variant="full" height={32} href="/" className="shrink-0" />
          <div className="hidden md:flex flex-1 items-center justify-center gap-8 min-w-0">
            <SolutionsNavDropdown />
            <Link to="/pricing" className="text-kimi-nav text-kimi-muted hover:text-kimi-text transition">Pricing</Link>
            <Link to="/our-projects" className="text-kimi-nav text-kimi-muted hover:text-kimi-text transition">Our Project</Link>
          </div>
          <div className="hidden md:flex items-center gap-4 ml-auto shrink-0">
            <button type="button" onClick={() => navigate('/app')} className="text-sm text-kimi-nav text-kimi-muted hover:text-kimi-text transition">
              Dashboard
            </button>
            {!user && (
              <Link to="/auth" className="text-sm text-kimi-nav text-kimi-muted hover:text-kimi-text transition">Log in</Link>
            )}
            <button type="button" onClick={() => navigate('/app/workspace')} className="px-4 py-2 bg-white text-gray-900 text-sm font-medium rounded-lg hover:bg-gray-100 transition">
              Get started
            </button>
          </div>
          <button className="md:hidden text-kimi-text" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </nav>

      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-40 bg-kimi-bg pt-20 px-6 pb-8 overflow-y-auto md:hidden">
            <div className="flex flex-col gap-6 text-kimi-text min-h-min">
              <p className="text-xs font-semibold uppercase tracking-wider text-kimi-muted">Our solution — who it&apos;s for</p>
              <div className="flex flex-col gap-2 pl-1 border-l border-gray-200">
                {SOLUTION_LINKS.map((item) => (
                  <Link key={item.to} to={item.to} className="text-base text-kimi-muted hover:text-kimi-text" onClick={() => setMobileMenuOpen(false)}>{item.label}</Link>
                ))}
              </div>
              <p className="text-xs font-semibold uppercase tracking-wider text-kimi-muted">Use cases</p>
              <div className="flex flex-col gap-2 pl-1 border-l border-gray-200">
                {USE_CASE_LINKS.map((item) => (
                  <Link key={item.to} to={item.to} className="text-base text-kimi-muted hover:text-kimi-text" onClick={() => setMobileMenuOpen(false)}>{item.label}</Link>
                ))}
              </div>
              <Link to="/pricing" className="text-lg" onClick={() => setMobileMenuOpen(false)}>Pricing</Link>
              <Link to="/our-projects" className="text-lg" onClick={() => setMobileMenuOpen(false)}>Our Project</Link>
              {!user && (
                <Link to="/auth" className="text-lg" onClick={() => setMobileMenuOpen(false)}>Log in</Link>
              )}
              <button type="button" onClick={() => { navigate('/app'); setMobileMenuOpen(false); }} className="text-lg text-left text-kimi-muted hover:text-kimi-text py-2">Dashboard</button>
              <button type="button" onClick={() => { navigate('/app/workspace'); setMobileMenuOpen(false); }} className="w-full py-3 bg-white text-gray-900 rounded-lg font-medium mt-2">Get started</button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* First screen only: exactly 100vh so footer is never visible until scroll */}
      <div className="h-screen flex flex-col overflow-hidden">
      {/* Hero — softer typography, smaller input, suggestion chips (Manus-style) */}
      <section className="flex-1 min-h-0 overflow-y-auto pt-32 pb-16 px-6">
        <div className="max-w-[780px] mx-auto">
          <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-[2.5rem] font-semibold tracking-tight text-[#1a1a1a] mb-6 text-center">
            What can I do for you?
          </motion.h1>
          <div className="landing-input-wrap rounded-2xl overflow-hidden bg-white border border-[#d1d5db] shadow-[0_1px_3px_rgba(0,0,0,0.05)] focus-within:border-[#a3a3a3] focus-within:shadow-[0_0_0_3px_rgba(0,0,0,0.06)] transition-all max-w-[720px] mx-auto">
            {messages.length > 0 && (
              <div className="max-h-48 overflow-y-auto p-4 space-y-3">
                {messages.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[85%] px-3 py-2 rounded-xl text-sm ${msg.role === 'user' ? 'bg-white text-gray-900' : 'bg-gray-100 text-gray-700'}`}>
                      {msg.content}
                    </div>
                  </div>
                ))}
                <div ref={chatEndRef} />
              </div>
            )}
            {attachedFiles.length > 0 && (
              <div className="px-4 pb-2 flex flex-wrap gap-2">
                {attachedFiles.map((file, i) => (
                  <div key={i} className="flex items-center gap-2 px-3 py-2 bg-gray-100 rounded-lg text-sm">
                    {file.type?.startsWith('image/') ? <Image className="w-4 h-4 text-kimi-accent shrink-0" /> : file.type?.startsWith('audio/') ? <Mic className="w-4 h-4 text-gray-500 shrink-0" /> : <FileText className="w-4 h-4 text-gray-400 shrink-0" />}
                    <span className="text-gray-500 max-w-[160px] truncate">{file.name}</span>
                    <button type="button" onClick={() => removeLandingFile(i)} className="text-kimi-muted hover:text-kimi-text p-0.5"><X className="w-4 h-4" /></button>
                  </div>
                ))}
              </div>
            )}
            <form onSubmit={handleSubmit} className="p-4">
              <div className="flex gap-2 items-end">
                <div className="flex-1 flex flex-col gap-2 relative">
                  <div className="flex gap-2 items-end min-h-[64px] py-1.5 pr-24">
                    <textarea
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      placeholder="Describe what you want to build..."
                      className="flex-1 bg-transparent text-gray-900 placeholder-gray-400 outline-none resize-none min-h-[40px] max-h-[160px] text-[0.95rem] leading-relaxed py-1.5 pl-2"
                      disabled={isBuilding}
                      rows={2}
                    />
                    <div className="absolute right-2 bottom-3 flex items-center gap-1">
                      <button type="button" onClick={isRecording ? stopVoiceRecording : startVoiceRecording} disabled={isBuilding || isTranscribing} className={`p-2 rounded-lg transition shrink-0 ${isRecording ? 'bg-[#EBE8E2] text-[#1A1A1A] ring-2 ring-black/10' : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'}`} title="Voice input">
                        {isRecording ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
                      </button>
                      <button type="button" onClick={() => fileInputRef.current?.click()} className="p-2 rounded-lg text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition shrink-0" title="Attach file">
                        <Paperclip className="w-5 h-5" />
                      </button>
                      <button
                        type="submit"
                        disabled={!hasLandingSendContent || isBuilding}
                        className={`p-2 rounded-full shrink-0 transition ${
                          isBuilding
                            ? 'bg-neutral-800 text-white cursor-wait'
                            : hasLandingSendContent
                              ? 'bg-neutral-900 text-white hover:bg-black shadow-sm'
                              : 'bg-neutral-100 text-neutral-400 border border-neutral-200 cursor-not-allowed'
                        }`}
                        title={isBuilding ? 'Starting…' : 'Send'}
                      >
                        {isBuilding ? <Loader2 className="w-5 h-5 animate-spin" /> : <ArrowRight className="w-5 h-5" strokeWidth={2} />}
                      </button>
                    </div>
                  </div>
                  <input ref={fileInputRef} type="file" multiple accept="image/*,.pdf,.txt,.md,.zip,audio/*,.js,.jsx,.ts,.tsx,.css,.html,.json,.py" onChange={handleLandingFileSelect} className="hidden" />
                </div>
              </div>
              {(isRecording || isTranscribing || voiceError) && (
                <div className="mt-2 flex items-center gap-2 min-h-[24px] text-sm text-gray-500">
                  {isRecording && <span>Listening…</span>}
                  {isTranscribing && !isRecording && <span>Transcribing…</span>}
                  {voiceError && !isRecording && !isTranscribing && <span>{voiceError}</span>}
                </div>
              )}
            </form>
          </div>
          <SuggestionChips onSelect={(prompt) => setInput(prompt)} disabled={isBuilding} />
        </div>
      </section>

      {/* CTA — single line, last thing visible on first screen */}
      <section className="mt-auto shrink-0 py-10 px-6 border-t border-gray-200">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-xl md:text-2xl font-semibold text-[#111827] mb-2">Your idea is inevitable.</h2>
          <p className="text-sm text-gray-500">Plan, build, and ship — web, mobile, and automation in one workspace.</p>
        </div>
      </section>
      </div>

      {/* Footer — below the fold; only visible when user scrolls */}
      <footer className="py-12 px-6 border-t border-gray-200 bg-kimi-bg">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-4 gap-12 mb-12">
            <div>
              <div className="mb-4">
                <Logo variant="full" height={28} href="/" />
              </div>
              <p className="text-sm text-kimi-muted mb-3">Turn ideas into inevitable outcomes. Plan, build, ship.</p>
              <ul className="space-y-2 text-sm">
                <li><Link to="/about" className="text-kimi-muted hover:text-kimi-text transition">About us</Link></li>
              </ul>
            </div>
            <div>
              <div className="text-xs text-kimi-muted uppercase tracking-wider mb-4">Product</div>
              <ul className="space-y-3 text-sm">
                <li><Link to="/our-projects#solutions" className="text-kimi-muted hover:text-kimi-text transition">Our solution</Link></li>
                <li><Link to="/pricing" className="text-kimi-muted hover:text-kimi-text transition">Pricing</Link></li>
                <li><Link to="/templates" className="text-kimi-muted hover:text-kimi-text transition">Templates</Link></li>
                <li><Link to="/patterns" className="text-kimi-muted hover:text-kimi-text transition">Patterns</Link></li>
                <li><Link to="/enterprise" className="text-kimi-muted hover:text-kimi-text transition">Enterprise</Link></li>
              </ul>
            </div>
            <div>
              <div className="text-xs text-kimi-muted uppercase tracking-wider mb-4">Resources</div>
              <ul className="space-y-3 text-sm">
                <li><Link to="/learn" className="text-kimi-muted hover:text-kimi-text transition">Learn</Link></li>
                <li><Link to="/shortcuts" className="text-kimi-muted hover:text-kimi-text transition">Shortcuts</Link></li>
                <li><Link to="/benchmarks" className="text-kimi-muted hover:text-kimi-text transition">Benchmarks</Link></li>
                <li><Link to="/prompts" className="text-kimi-muted hover:text-kimi-text transition">Prompt Library</Link></li>
                <li><Link to="/security" className="text-kimi-muted hover:text-kimi-text transition">Security &amp; Trust</Link></li>
                <li><Link to="/about" className="text-kimi-muted hover:text-kimi-text transition">Why CrucibAI</Link></li>
              </ul>
            </div>
            <div>
              <div className="text-xs text-kimi-muted uppercase tracking-wider mb-4">Legal</div>
              <ul className="space-y-3 text-sm">
                <li><Link to="/privacy" className="text-kimi-muted hover:text-kimi-text transition">Privacy</Link></li>
                <li><Link to="/terms" className="text-kimi-muted hover:text-kimi-text transition">Terms</Link></li>
                <li><Link to="/aup" className="text-kimi-muted hover:text-kimi-text transition">Acceptable Use</Link></li>
                <li><Link to="/dmca" className="text-kimi-muted hover:text-kimi-text transition">DMCA</Link></li>
                <li><Link to="/cookies" className="text-kimi-muted hover:text-kimi-text transition">Cookies</Link></li>
              </ul>
            </div>
          </div>
          <div className="pt-8 border-t border-gray-200 text-center">
            <p className="text-xs text-kimi-muted">© 2026 CrucibAI. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;

import { useState, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, ArrowRight, Menu, X, Paperclip, Image, FileText, Mic, MicOff } from 'lucide-react';
import { useAuth, API } from '../App';
import axios from 'axios';
import { logApiError } from '../utils/apiError';
import Logo from '../components/Logo';
import SuggestionChips from '../components/SuggestionChips';

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
    const q = `prompt=${encodeURIComponent(prompt)}`;
    navigate(`/app/workspace?${q}`, { state });
  };

  const handleLandingFileSelect = (e) => {
    const selected = Array.from(e.target.files || []);
    const valid = selected.filter(f => f.type.startsWith('image/') || f.type === 'application/pdf' || f.type.startsWith('text/'));
    valid.forEach(file => {
      const reader = new FileReader();
      reader.onload = (ev) => {
        setAttachedFiles(prev => [...prev, { name: file.name, type: file.type, data: ev.target.result, size: file.size }]);
      };
      if (file.type.startsWith('image/')) reader.readAsDataURL(file);
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
        setVoiceError(err.response?.data?.detail || err.message || 'Transcription failed.');
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

  const handleSubmit = (e) => {
    e?.preventDefault();
    const hasInput = input.trim();
    const hasImageOnly = attachedFiles.length > 0 && attachedFiles.every(f => f.type?.startsWith('image/'));
    if (!hasInput && !hasImageOnly) return;
    startBuild(hasInput || 'Convert image to code', attachedFiles.length ? attachedFiles : null);
  };

  return (
    <div className="marketing-page bg-kimi-bg text-kimi-text grid-pattern-kimi">
      {/* Navigation — 6 items only */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-kimi-bg border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between">
          <Logo variant="full" height={32} href="/" className="shrink-0" />
          <div className="hidden md:flex items-center gap-6">
            <Link to="/features" className="text-kimi-nav text-kimi-muted hover:text-kimi-text transition">Features</Link>
            <Link to="/pricing" className="text-kimi-nav text-kimi-muted hover:text-kimi-text transition">Pricing</Link>
            <Link to="/our-projects" className="text-kimi-nav text-kimi-muted hover:text-kimi-text transition">Our Project</Link>
            <Link to="/blog" className="text-kimi-nav text-kimi-muted hover:text-kimi-text transition">Blog</Link>
            <Link to="/auth" className="text-kimi-nav text-kimi-muted hover:text-kimi-text transition">Log in</Link>
            <Link to="/auth?mode=register" className="px-4 py-2 rounded-full bg-black text-white text-sm font-medium hover:bg-black/90 transition">Sign up</Link>
            <button
              onClick={() => navigate('/app')}
              className="px-4 py-2 rounded-full bg-[#1A1A1A]/10 text-[#1A1A1A] text-sm font-medium hover:bg-[#1A1A1A]/20 transition"
            >
              Dashboard
            </button>
            <button onClick={() => navigate('/app/workspace')} className="px-4 py-2 bg-white text-gray-900 text-sm font-medium rounded-lg hover:bg-gray-100 transition">Get Started</button>
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
              <Link to="/features" className="text-lg" onClick={() => setMobileMenuOpen(false)}>Features</Link>
              <Link to="/pricing" className="text-lg" onClick={() => setMobileMenuOpen(false)}>Pricing</Link>
              <Link to="/our-projects" className="text-lg" onClick={() => setMobileMenuOpen(false)}>Our Project</Link>
              <Link to="/blog" className="text-lg" onClick={() => setMobileMenuOpen(false)}>Blog</Link>
              <Link to="/auth" className="text-lg" onClick={() => setMobileMenuOpen(false)}>Log in</Link>
              <Link to="/auth?mode=register" className="w-full py-3 bg-black text-white rounded-lg font-medium text-center mt-2" onClick={() => setMobileMenuOpen(false)}>Sign up</Link>
              <button onClick={() => { navigate('/app'); setMobileMenuOpen(false); }} className="w-full py-3 bg-white text-gray-900 rounded-lg font-medium">Dashboard</button>
              <button onClick={() => { navigate('/app/workspace'); setMobileMenuOpen(false); }} className="w-full py-3 bg-white text-gray-900 rounded-lg font-medium">Get Started</button>
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
          <div className="landing-input-wrap rounded-2xl overflow-hidden bg-white border border-[#d1d5db] shadow-[0_1px_3px_rgba(0,0,0,0.05)] focus-within:border-[#3b82f6] focus-within:shadow-[0_0_0_3px_rgba(59,130,246,0.1)] transition-all max-w-[720px] mx-auto">
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
                    {file.type?.startsWith('image/') ? <Image className="w-4 h-4 text-kimi-accent shrink-0" /> : <FileText className="w-4 h-4 text-gray-400 shrink-0" />}
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
                      <button type="submit" disabled={(!input.trim() && !attachedFiles.some(f => f.type?.startsWith('image/'))) || isBuilding} className="p-2 rounded-lg bg-[#3b82f6] text-white hover:bg-[#2563eb] disabled:opacity-40 disabled:cursor-not-allowed transition shrink-0" title="Send">
                        {isBuilding ? <Loader2 className="w-5 h-5 animate-spin" /> : <ArrowRight className="w-5 h-5" />}
                      </button>
                    </div>
                  </div>
                  <input ref={fileInputRef} type="file" multiple accept="image/*,.pdf,.txt,.md" onChange={handleLandingFileSelect} className="hidden" />
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
      <section className="mt-auto shrink-0 py-12 px-6 border-t border-gray-200">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-xl md:text-2xl font-semibold text-[#111827]">Your idea is inevitable.</h2>
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
                <li><Link to="/features" className="text-kimi-muted hover:text-kimi-text transition">Features</Link></li>
                <li><Link to="/pricing" className="text-kimi-muted hover:text-kimi-text transition">Pricing</Link></li>
                <li><Link to="/templates" className="text-kimi-muted hover:text-kimi-text transition">Templates</Link></li>
                <li><Link to="/patterns" className="text-kimi-muted hover:text-kimi-text transition">Patterns</Link></li>
                <li><Link to="/enterprise" className="text-kimi-muted hover:text-kimi-text transition">Enterprise</Link></li>
              </ul>
            </div>
            <div>
              <div className="text-xs text-kimi-muted uppercase tracking-wider mb-4">Resources</div>
              <ul className="space-y-3 text-sm">
                <li><Link to="/blog" className="text-kimi-muted hover:text-kimi-text transition">Blog</Link></li>
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

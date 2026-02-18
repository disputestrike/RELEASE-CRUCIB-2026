import { useState, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Send, Loader2, ArrowRight, Check, Menu, X, Play, ArrowUpRight, Paperclip, Image, FileText, Mic, MicOff, FileCode, GitFork } from 'lucide-react';
import { useAuth, API } from '../App';
import axios from 'axios';

const LandingPage = () => {
  const navigate = useNavigate();
  const { user, token } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [openFaq, setOpenFaq] = useState(null);
  const [openWhere, setOpenWhere] = useState(null);
  
  // Build state
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [isBuilding, setIsBuilding] = useState(false);
  const [buildProgress, setBuildProgress] = useState(0);
  const [generatedCode, setGeneratedCode] = useState(null);
  const [sessionId] = useState(() => `session_${Date.now()}`);
  const [attachedFiles, setAttachedFiles] = useState([]);
  const [voiceLanguage, setVoiceLanguage] = useState('en');
  const [liveExamples, setLiveExamples] = useState([]);
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [voiceError, setVoiceError] = useState(null);
  const chatEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const voiceStreamRef = useRef(null);
  const voiceChunksRef = useRef([]);

  useEffect(() => {
    axios.get(`${API}/examples`).then((r) => setLiveExamples((r.data.examples || []).slice(0, 3))).catch(() => setLiveExamples([]));
  }, [API]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const startBuild = async (promptOverride = null, filesOverride = null) => {
    const prompt = (promptOverride ?? input).trim();
    if (!prompt || isBuilding) return;
    const q = `prompt=${encodeURIComponent(prompt)}`;
    const workspacePath = `/app/workspace?${q}`;
    const state = (filesOverride?.length || attachedFiles?.length) ? { initialAttachedFiles: filesOverride || attachedFiles } : undefined;
    if (user) {
      navigate(workspacePath, { state });
    } else {
      navigate(`/auth?mode=register&redirect=${encodeURIComponent(workspacePath)}`, { state: state ? { ...state } : undefined });
    }
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
    if (generatedCode) {
      modifyCode(hasInput || 'Convert image to code');
    } else {
      startBuild(hasInput || 'Convert image to code', attachedFiles.length ? attachedFiles : null);
    }
  };

  const modifyCode = async (request) => {
    if (!request.trim() || isBuilding) return;

    setInput('');
    setIsBuilding(true);
    setMessages(prev => [...prev, { role: 'user', content: request }]);
    setMessages(prev => [...prev, { role: 'assistant', content: 'Updating...', isBuilding: true }]);

    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      
      const response = await axios.post(`${API}/ai/chat`, {
        message: `Current code:\n\n${generatedCode.code}\n\nModify it to: "${request}"\n\nRespond with ONLY the complete updated code.`,
        session_id: sessionId,
        model: 'auto'
      }, { headers, timeout: 60000 });

      const newCode = response.data.response.replace(/```jsx?/g, '').replace(/```/g, '').trim();

      if (newCode.includes('import') || newCode.includes('function') || newCode.includes('const')) {
        setGeneratedCode(prev => ({ ...prev, code: newCode }));
        setMessages(prev => prev.map((msg, i) => 
          i === prev.length - 1 ? { role: 'assistant', content: `Updated. What else?`, hasCode: true } : msg
        ));
      } else {
        setMessages(prev => prev.map((msg, i) => 
          i === prev.length - 1 ? { role: 'assistant', content: response.data.response } : msg
        ));
      }
    } catch (error) {
      setMessages(prev => prev.map((msg, i) => 
        i === prev.length - 1 ? { role: 'assistant', content: 'Error. Try again.', error: true } : msg
      ));
    } finally {
      setIsBuilding(false);
    }
  };

  const downloadCode = () => {
    if (!generatedCode) return;
    const blob = new Blob([generatedCode.code], { type: 'text/javascript' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'app.jsx';
    a.click();
  };

  const whatAreYouBuilding = [
    { title: 'Reporting Dashboard', desc: 'Charts, stats, and data views', prompt: 'Create a reporting dashboard with sidebar, stat cards, and chart placeholders. React and Tailwind.' },
    { title: 'Task Manager', desc: 'Add, complete, filter tasks', prompt: 'Create a task manager with add, complete, delete, and filter by status. React and Tailwind.' },
    { title: 'E-commerce Store', desc: 'Product list, cart, checkout', prompt: 'Build a modern e-commerce product list with add-to-cart, cart sidebar, and checkout button. React and Tailwind.' },
    { title: 'Landing + Waitlist', desc: 'Hero, features, email signup', prompt: 'Build a landing page with hero, features section, and email waitlist signup. React and Tailwind.' },
    { title: 'Auth + Dashboard', desc: 'Login and main app shell', prompt: 'Create a login page and a dashboard with sidebar navigation. React, Tailwind, and local state for auth.' },
    { title: 'SaaS Pricing Page', desc: 'Plans and Stripe-ready', prompt: 'Build a SaaS landing page with pricing cards and Stripe Checkout integration for subscription. React and Tailwind.' },
    { title: 'Portfolio Site', desc: 'Projects and contact', prompt: 'Build a personal portfolio with project grid, about section, and contact form. React and Tailwind.' },
    { title: 'Onboarding Portal', desc: 'Steps and progress', prompt: 'Create an onboarding flow with step progress, back/next, and completion screen. React and Tailwind.' },
    { title: 'Blog', desc: 'Post list and detail view', prompt: 'Build a blog with a list of posts and a post detail view. React and Tailwind.' },
    { title: 'Internal Tool', desc: 'Admin table and filters', prompt: 'Build an internal admin tool with a data table, filters, and search. React and Tailwind.' },
    { title: 'Custom Web Tool', desc: 'Calculator, converter, etc.', prompt: 'Build a custom web tool (e.g. calculator or unit converter) with a clean UI. React and Tailwind.' },
    { title: 'Event or Booking', desc: 'Calendar and booking flow', prompt: 'Create an event or booking page with date selection and confirmation. React and Tailwind.' },
  ];

  const faqs = [
    { q: 'What is CrucibAI?', a: 'CrucibAI is Inevitable AI — the platform where intelligence doesn\'t just act, it makes outcomes inevitable. Describe what you need in plain language; we generate production-ready code with plan-first flow and a 120-agent swarm. Full transparency: every phase, every agent, no black boxes.' },
    { q: 'Is CrucibAI free to use?', a: 'Yes. We offer a free tier with 50 credits. Paid plans are monthly (Starter, Builder, Pro, Agency) with more credits per month; add-ons (Light, Dev) are one-time top-ups. Unused credits roll over.' },
    { q: 'Do I need coding experience?', a: 'No. Our platform is designed for everyone. Just describe your idea and our AI handles the technical implementation.' },
    { q: 'What can I build?', a: 'Websites, dashboards, task managers, onboarding portals, pricing pages, e-commerce stores, internal tools, and more. If you can describe it, we can build it.' },
    { q: 'What is design-to-code?', a: 'Upload a UI screenshot or mockup and CrucibAI generates structured, responsive code (HTML/CSS, React, Tailwind). Use the attach button on the landing or in the workspace.' },
    { q: 'What are Quick, Plan, Agent, and Thinking modes?', a: 'Quick: single-shot generation, no plan step. Plan: we create a structured plan first, then build. Agent: full orchestration with our 120-agent swarm (planning, frontend, backend, design, SEO, tests, deploy). Thinking: step-by-step reasoning before code. Swarm runs selected agents in parallel for speed.' },
    { q: 'How do I make changes?', a: 'Just ask in the chat. Say "make it dark mode", "add a sidebar", or "change the colors" and we update the code instantly.' },
    { q: 'How are apps deployed?', a: 'You export your code as a ZIP or push to GitHub. We give you the files; you deploy to Vercel, Netlify, or any host. You own the code.' },
    { q: 'Is my data secure?', a: 'Yes. We use industry-standard practices. Your API keys stay in your environment; we don’t store them. See our Privacy and Terms for details.' },
    { q: 'Do I own what I create?', a: 'Yes. All applications and code you generate belong to you. Use, modify, or sell them however you like.' },
    { q: 'What are the limitations?', a: 'Complex multi-page apps may need multiple iterations. Very large codebases are subject to model context limits. Offline use is not supported. We recommend verifying critical logic and running your own tests.' },
    { q: 'What’s next for CrucibAI?', a: 'We’re expanding API access for developers, adding more structured outputs (README, API docs, FAQ schema), and improving Swarm and Thinking modes. See our roadmap in the footer.' },
    { q: 'Enterprise & compliance?', a: "We're working toward SOC 2 and enterprise-grade compliance. For Enterprise or custom plans, contact sales@crucibai.com." }
  ];

  const faqsExtra = [
    { q: 'Can I use my own API keys?', a: 'Yes. In Settings you can add your preferred AI provider API key. CrucibAI will use your key for AI requests; token usage is billed by the provider according to their terms.' },
    { q: 'What stacks and frameworks are supported?', a: 'We focus on React and Tailwind for web apps. The workspace uses Sandpack for instant preview. You can export and adapt code for other frameworks.' },
    { q: 'How does plan-first work?', a: 'For larger prompts we first call a planning agent that returns a structured plan (features, components, design notes) and optional suggestions. You see the plan, then we generate code. This reduces backtracking and improves quality.' },
    { q: 'What is Swarm mode?', a: "Swarm (Beta) runs selected agents in parallel instead of sequentially, so multi-step builds can complete faster. It's available on paid plans." },
    { q: 'Can I collaborate with my team?', a: 'You can share exported code or push to a shared GitHub repo. Team and org features are on our roadmap.' },
    { q: 'Does CrucibAI support voice input?', a: 'Yes. Use the microphone button on the landing or in the workspace to record; we transcribe and insert your words into the prompt.' },
    { q: 'What file types can I attach?', a: 'Images (screenshots, mockups), PDFs, and text files. Images are used for design-to-code; PDFs and text add context for the AI.' },
    { q: 'How do token bundles work?', a: 'You buy a bundle (e.g. Starter 100K tokens). Each AI request consumes tokens; when you run low you can buy more. Tokens do not expire.' },
    { q: 'Is there an API for developers?', a: 'We offer API access for prompt to plan and prompt to code. See our roadmap and documentation for availability.' },
    { q: 'How do I get help or report a bug?', a: 'Use the Documentation and Support links in the footer. For bugs, include steps to reproduce and your environment (browser, OS).' },
    { q: 'Can I build mobile apps?', a: 'Currently we focus on web apps (React). Mobile and PWA support are on the roadmap.' },
    { q: 'What browsers are supported?', a: 'We recommend Chrome, Firefox, or Edge. Safari is supported; voice input may have limitations on some browsers.' },
    { q: 'How does CrucibAI compare to Kimi?', a: 'Kimi excels at long-context chat and research. CrucibAI is Inevitable AI for app creation: plan-first builds, 120-agent swarm, design-to-code, and one workspace from idea to export. Use CrucibAI when you want inevitable outcomes — ship software, not just promises.' }
  ];
  const allFaqs = [...faqs, ...faqsExtra];

  const whereItems = [
    { title: 'Web app', desc: 'Use CrucibAI in your browser. Describe your idea on the landing page or open the workspace to build, iterate, and export. No setup required.' },
    { title: 'API', desc: 'Integrate via API for prompt → plan and prompt → code. Billing by token usage.' },
    { title: 'Export & deploy', desc: 'Download your project as a ZIP or push to GitHub. Deploy to Vercel, Netlify, or any host. You own the code and can customize anything.' }
  ];

  const comparisonRows = [
    { tool: 'CrucibAI', bestFor: 'Apps + plan-first + design-to-code', strongest: 'Plan-first build, 120-agent swarm, Swarm, design-to-code', pick: 'You want one workspace to go from idea to shipped app with minimal setup' },
    { tool: 'Kimi (Kimi.ai)', bestFor: 'Long-context chat, research', strongest: 'Very long context, summarization', pick: 'You need long-document Q&A or research; less focused on app building' },
    { tool: 'Cursor', bestFor: 'In-IDE coding', strongest: 'Composer, codebase context', pick: 'You code daily in an IDE and want AI inside the editor' },
    { tool: 'Manus / Bolt', bestFor: 'Agentic app building', strongest: 'Natural language to app', pick: 'You want a similar build-from-prompt experience' },
    { tool: 'ChatGPT', bestFor: 'General + file analysis', strongest: 'Flexible assistant, file uploads', pick: 'You need a general-purpose assistant with file analysis' }
  ];

  return (
    <div className="min-h-screen bg-kimi-bg text-kimi-text grid-pattern-kimi">
      {/* Navigation — Kimi-style */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-kimi-bg border-b border-white/10">
        <div className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between">
          <Link to="/" className="text-xl font-semibold tracking-tight text-kimi-text">CrucibAI <span className="text-kimi-muted font-normal text-base">— Inevitable AI</span></Link>
          <div className="hidden md:flex items-center gap-6">
            <Link to="/features" className="text-kimi-nav text-kimi-muted hover:text-kimi-text transition">Features</Link>
            <Link to="/pricing" className="text-kimi-nav text-kimi-muted hover:text-kimi-text transition">Pricing</Link>
            <Link to="/templates" className="text-kimi-nav text-kimi-muted hover:text-kimi-text transition">Templates</Link>
            <a href="#examples" className="text-kimi-nav text-kimi-muted hover:text-kimi-text transition">Examples</a>
            <Link to="/benchmarks" className="text-kimi-nav text-kimi-muted hover:text-kimi-text transition">Benchmarks</Link>
            <a href="#how" className="text-kimi-nav text-kimi-muted hover:text-kimi-text transition">How it works</a>
            <a href="#faq" className="text-kimi-nav text-kimi-muted hover:text-kimi-text transition">FAQ</a>
            <Link to="/learn" className="text-kimi-nav text-kimi-muted hover:text-kimi-text transition">Documentation</Link>
            {user ? (
              <button onClick={() => navigate('/app')} className="text-kimi-nav text-kimi-muted hover:text-kimi-text transition">Dashboard</button>
            ) : (
              <button onClick={() => navigate('/auth')} className="text-kimi-nav text-kimi-muted hover:text-kimi-text transition">Sign in</button>
            )}
            <button onClick={() => navigate(user ? '/app' : '/auth?mode=register')} className="px-4 py-2 bg-white text-black text-sm font-medium rounded-lg hover:bg-zinc-200 transition">Get started</button>
          </div>
          <button className="md:hidden text-kimi-text" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </nav>

      {/* Mobile Menu */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-40 bg-kimi-bg pt-20 px-6 md:hidden">
            <div className="flex flex-col gap-6 text-kimi-text">
              <Link to="/features" className="text-lg" onClick={() => setMobileMenuOpen(false)}>Features</Link>
              <Link to="/pricing" className="text-lg" onClick={() => setMobileMenuOpen(false)}>Pricing</Link>
              <Link to="/templates" className="text-lg" onClick={() => setMobileMenuOpen(false)}>Templates</Link>
              <a href="#examples" className="text-lg" onClick={() => setMobileMenuOpen(false)}>Examples</a>
              <Link to="/benchmarks" className="text-lg" onClick={() => setMobileMenuOpen(false)}>Benchmarks</Link>
              <a href="#how" className="text-lg" onClick={() => setMobileMenuOpen(false)}>How it works</a>
              <a href="#faq" className="text-lg" onClick={() => setMobileMenuOpen(false)}>FAQ</a>
              <Link to="/learn" className="text-lg" onClick={() => setMobileMenuOpen(false)}>Documentation</Link>
              <button onClick={() => { navigate(user ? '/app' : '/auth?mode=register'); setMobileMenuOpen(false); }} className="w-full py-3 bg-white text-black rounded-lg font-medium mt-4">Get started</button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Hero — Kimi-style with NEW badge */}
      <section className="pt-32 pb-20 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 text-kimi-text text-sm font-medium mb-6">
            <span className="w-2 h-2 rounded-full bg-kimi-accent animate-pulse" /> Inevitable AI — 120-agent swarm, 99.2% success, full transparency
          </motion.div>
          <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-kimi-hero font-bold tracking-tight text-kimi-text mb-6">
            Inevitable AI
          </motion.h1>
          <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="text-lg text-kimi-muted mb-12 max-w-xl mx-auto leading-relaxed">
            Intelligence that doesn&apos;t just act. It guarantees. Describe your vision. Watch it become inevitable.
          </motion.p>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.15 }} className="flex flex-col sm:flex-row flex-wrap items-center justify-center gap-3">
            <button onClick={() => navigate(user ? '/app' : '/auth?mode=register')} className="glass-kimi-btn px-6 py-3 text-black font-medium rounded-xl transition">
              Make It Inevitable
            </button>
            <Link to="/workspace" className="px-6 py-3 bg-white/10 text-kimi-text font-medium rounded-xl border border-white/20 hover:bg-white/20 transition">Open Workspace</Link>
            <Link to="/templates" className="px-6 py-3 bg-white/10 text-kimi-text font-medium rounded-xl border border-white/20 hover:bg-white/20 transition">Templates</Link>
            <Link to="/pricing" className="px-6 py-3 bg-white/10 text-kimi-text font-medium rounded-xl border border-white/20 hover:bg-white/20 transition">Pricing</Link>
          </motion.div>
          {!user && (
            <p className="mt-4 text-sm text-kimi-muted">Sign in to save projects and sync across devices.</p>
          )}
        </div>

        {/* Proof strip — 5 items + Not promises. Measured. */}
        <motion.section initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.15 }} className="max-w-4xl mx-auto mt-12 px-6">
          <div className="flex flex-wrap items-center justify-center gap-6 py-5 px-6 rounded-xl border border-white/10 bg-kimi-bg-elevated/50">
            <span className="text-sm font-medium text-kimi-text">120-agent swarm</span>
            <span className="text-kimi-muted">•</span>
            <span className="text-sm font-medium text-kimi-text">99.2% deployment success</span>
            <span className="text-kimi-muted">•</span>
            <span className="text-sm font-medium text-kimi-text">Typically under 72 hours</span>
            <span className="text-kimi-muted">•</span>
            <span className="text-sm font-medium text-kimi-text">Full transparency</span>
            <span className="text-kimi-muted">•</span>
            <span className="text-sm font-medium text-kimi-text">Minimal supervision</span>
          </div>
          <p className="text-center text-xs text-kimi-muted mt-2">Not promises. Measured.</p>
        </motion.section>

        {/* Main Input — extra space + glass */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="max-w-2xl mx-auto mt-16">
          <div className="glass-kimi-panel rounded-2xl overflow-hidden">
            {/* Messages */}
            {messages.length > 0 && (
              <div className="max-h-80 overflow-y-auto p-5 space-y-4">
                {messages.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[80%] px-4 py-3 rounded-xl text-sm ${
                      msg.role === 'user' 
                        ? 'bg-white text-black' 
                        : msg.error 
                          ? 'bg-red-500/10 text-red-400'
                          : 'bg-zinc-800 text-zinc-200'
                    }`}>
                      {msg.isBuilding ? (
                        <div className="flex items-center gap-2">
                          <div className="w-4 h-4 border-2 border-zinc-500 border-t-white rounded-full animate-spin" />
                          <span>{msg.content}</span>
                        </div>
                      ) : (
                        <span>{msg.content}</span>
                      )}
                    </div>
                  </div>
                ))}
                <div ref={chatEndRef} />
              </div>
            )}

            {/* Progress */}
            {isBuilding && (
              <div className="px-5 pb-2">
                <div className="h-0.5 bg-zinc-800 rounded-full overflow-hidden">
                  <motion.div 
                    className="h-full bg-white"
                    initial={{ width: 0 }}
                    animate={{ width: `${buildProgress}%` }}
                  />
                </div>
              </div>
            )}

            {/* Generated Code */}
            {generatedCode && !isBuilding && (
              <div className="px-5 pb-4">
                <div className="bg-kimi-bg rounded-lg overflow-hidden">
                  <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-800">
                    <span className="text-xs text-kimi-muted font-mono">app.jsx</span>
                    <button onClick={downloadCode} className="text-xs text-kimi-muted hover:text-kimi-text transition">
                      Download
                    </button>
                  </div>
                  <pre className="p-4 text-xs text-kimi-muted font-mono overflow-x-auto max-h-48 overflow-y-auto">
                    <code>{generatedCode.code.slice(0, 800)}{generatedCode.code.length > 800 ? '\n...' : ''}</code>
                  </pre>
                </div>
              </div>
            )}

            {/* Attached files */}
            {attachedFiles.length > 0 && (
              <div className="px-4 pb-2 flex flex-wrap gap-2">
                {attachedFiles.map((file, i) => (
                  <div key={i} className="flex items-center gap-2 px-3 py-2 bg-zinc-800 rounded-lg text-sm">
                    {file.type?.startsWith('image/') ? (
                      <Image className="w-4 h-4 text-blue-400 shrink-0" />
                    ) : (
                      <FileText className="w-4 h-4 text-zinc-400 shrink-0" />
                    )}
                    <span className="text-zinc-300 max-w-[180px] truncate">{file.name}</span>
                    <button type="button" onClick={() => removeLandingFile(i)} className="text-kimi-muted hover:text-kimi-text p-0.5">
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Input — same options as workspace: big box, attach, submit */}
            <form onSubmit={handleSubmit} className="p-4">
              <div className="flex gap-2 items-end">
                <div className="flex-1 flex flex-col gap-2">
                  <div className="flex gap-2 px-4 py-3 bg-[#1C1C1E] rounded-xl border border-zinc-800 focus-within:ring-1 focus-within:ring-zinc-600 transition min-h-[160px]">
                    <textarea
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      placeholder={messages.length > 0 ? "Ask for changes..." : "What do you want to build?"}
                      className="flex-1 bg-transparent text-white placeholder-zinc-500 outline-none resize-none min-h-[120px] text-base leading-relaxed"
                      disabled={isBuilding}
                      rows={5}
                    />
                    <button
                      type="button"
                      onClick={isRecording ? stopVoiceRecording : startVoiceRecording}
                      disabled={isBuilding || isTranscribing}
                      className={`p-2.5 rounded-lg transition self-end shrink-0 ${isRecording ? 'bg-red-500/30 text-red-400 ring-2 ring-red-400/50' : 'text-kimi-muted hover:text-kimi-text hover:bg-zinc-700'}`}
                      title={isRecording ? 'Click to stop and transcribe' : 'Voice input — click to speak'}
                    >
                      {isRecording ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
                    </button>
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="p-2.5 rounded-lg text-kimi-muted hover:text-kimi-text hover:bg-zinc-700 transition self-end shrink-0"
                      title="Attach image or file"
                    >
                      <Paperclip className="w-5 h-5" />
                    </button>
                  </div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept="image/*,.pdf,.txt,.md"
                    onChange={handleLandingFileSelect}
                    className="hidden"
                  />
                </div>
                <button
                  type="submit"
                  disabled={(!input.trim() && !attachedFiles.some(f => f.type?.startsWith('image/'))) || isBuilding}
                  className="px-6 py-4 bg-white text-black rounded-xl text-base font-medium disabled:opacity-30 disabled:cursor-not-allowed hover:bg-zinc-200 transition shrink-0"
                >
                  {isBuilding ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <ArrowRight className="w-5 h-5" />
                  )}
                </button>
              </div>

              {/* Voice status: Listening / Transcribing / Error */}
              {(isRecording || isTranscribing || voiceError) && (
                <div className="mt-3 flex items-center gap-2 min-h-[24px]">
                  {isRecording && (
                    <>
                      <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" aria-hidden />
                      <span className="text-sm text-red-400 font-medium">Listening… click the mic again to stop and see your text here.</span>
                    </>
                  )}
                  {isTranscribing && !isRecording && (
                    <>
                      <Loader2 className="w-4 h-4 text-kimi-accent animate-spin shrink-0" />
                      <span className="text-sm text-kimi-muted">Transcribing… your words will appear above when ready.</span>
                    </>
                  )}
                  {voiceError && !isRecording && !isTranscribing && (
                    <span className="text-sm text-red-400">{voiceError}</span>
                  )}
                </div>
              )}
              
              {messages.length === 0 && (
                <div className="mt-4">
                  <p className="text-xs text-kimi-muted mb-2">Not sure where to start? Try one of these:</p>
                  <div className="flex flex-wrap gap-2">
                    {['Reporting Dashboard', 'Task manager', 'E-commerce store', 'Landing + waitlist', 'Auth + Dashboard', 'Portfolio site', 'Pricing page', 'Blog', 'Internal tool'].map(s => (
                      <button
                        key={s}
                        type="button"
                        onClick={() => setInput(s)}
                        className="px-3 py-1.5 text-xs text-kimi-muted bg-zinc-800/50 rounded-lg hover:bg-zinc-800 hover:text-kimi-text transition border border-zinc-800/50"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </form>
          </div>
        </motion.div>
      </section>

      {/* What is CrucibAI — Clarity brand */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">What we do</span>
          <h2 className="text-kimi-section font-bold text-kimi-text mt-2 mb-6">What is CrucibAI?</h2>
          <p className="text-kimi-body text-kimi-secondary mb-6 leading-relaxed">
            CrucibAI is Inevitable AI — the platform where intelligence doesn&apos;t just act, it makes outcomes inevitable. Plan-first flow, structured plan and suggestions, then production-ready code. Full transparency: every phase, every agent, no black boxes. No surprises, no hidden limitations.
          </p>
          <ul className="grid sm:grid-cols-2 gap-3 text-kimi-body text-kimi-muted">
            {['Research & summarization (docs)', 'Coding & debugging', 'Multimodal (text + images + files)', 'Plan-first agentic workflow', 'Templates & patterns', '120-agent swarm (frontend, backend, tests, deploy)', '99.2% success', 'Export to PDF and Excel (reports, spreadsheets, invoices)'].map((item, i) => (
              <li key={i} className="flex items-center gap-2"><span className="text-kimi-accent">•</span> {item}</li>
            ))}
          </ul>
        </div>
      </section>

      {/* Key Features — two-column Kimi-style */}
      <section className="py-20 px-6 bg-kimi-bg-elevated/50">
        <div className="max-w-5xl mx-auto flex flex-col md:flex-row gap-12 items-start">
          <div className="md:w-2/5">
            <span className="text-xs uppercase tracking-wider text-kimi-muted">Benefits</span>
            <h2 className="text-kimi-section font-bold text-kimi-text mt-2">Why it&apos;s inevitable</h2>
            <p className="text-sm text-kimi-muted mt-2">Not just features — the proof behind inevitable outcomes.</p>
          </div>
          <div className="md:w-3/5 space-y-6">
            {[
              { title: 'Plan-first build', desc: 'We create a structured plan (features, design, components) before writing code. Get suggestions and then build in one flow.' },
              { title: '120-agent swarm', desc: 'Planning, frontend, backend, tests, security, deployment—each step powered by dedicated agents. Swarm mode runs agents in parallel for speed.' },
              { title: 'Design-to-code', desc: 'Upload a UI screenshot or mockup; we generate structured, responsive code (React, Tailwind).' },
              { title: 'Multimodal input', desc: 'Text, images, and files. Describe your idea or attach a design—we handle both.' },
              { title: 'Quick, Plan, Agent & Thinking modes', desc: 'Quick for fast single-shot generation; Plan for plan-then-build; Agent for full orchestration; Thinking for deeper step-by-step reasoning.' },
              { title: 'Web + mobile to stores', desc: 'Build websites and mobile apps (Expo/React Native). Export includes a store submission pack and step-by-step guides for Apple App Store and Google Play.' }
            ].map((item, i) => (
              <div key={i}>
                <h3 className="text-kimi-card font-semibold text-kimi-text mb-1">{item.title}</h3>
                <p className="text-sm text-kimi-muted leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Productized sections — CrucibAI for X (D2) */}
      <section className="py-20 px-6">
        <div className="max-w-5xl mx-auto">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Use cases</span>
          <h2 className="text-kimi-section font-bold text-kimi-text mt-2 mb-8">CrucibAI for Every Need</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { title: 'Dashboards', desc: 'Reporting, analytics, and data views with charts and filters. Plan-first keeps structure clear.', cta: 'Build a dashboard' },
              { title: 'Landing pages', desc: 'Hero, features, waitlist, and pricing sections. Design-to-code from a screenshot.', cta: 'Start a landing page' },
              { title: 'Internal tools', desc: 'Admin tables, forms, and workflows. Ship in minutes, not weeks.', cta: 'Build an internal tool' },
              { title: 'Websites & stores', desc: 'Portfolios, e-commerce, and custom web apps. Export to ZIP or GitHub.', cta: 'Build a website' },
              { title: 'Mobile apps', desc: 'iOS and Android with Expo. Get a store submission pack for App Store and Play Store.', cta: 'Build a mobile app' }
            ].map((item, i) => (
              <div key={i} className="p-5 rounded-xl border border-white/10 bg-kimi-bg hover:border-white/20 transition">
                <h3 className="text-lg font-semibold text-kimi-text mb-2">{item.title}</h3>
                <p className="text-sm text-kimi-muted mb-4">{item.desc}</p>
                <button onClick={() => startBuild(item.cta)} className="text-sm font-medium text-kimi-accent hover:text-kimi-text transition">{item.cta} →</button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How CrucibAI works — key modules (D9) */}
      <section id="how-works" className="py-20 px-6 bg-kimi-bg-elevated/50">
        <div className="max-w-4xl mx-auto">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Under the hood</span>
          <h2 className="text-kimi-section font-bold text-kimi-text mt-2 mb-6 text-center">How CrucibAI Works</h2>
          <p className="text-kimi-muted text-center mb-12 max-w-xl mx-auto">Plan-first, 120-agent swarm, full transparency. From description to reality.</p>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              { step: '1', title: 'Plan first', desc: 'For bigger prompts we generate a structured plan (features, components, design) and optional suggestions before writing code. You see the plan, then we build.' },
              { step: '2', title: '120-agent swarm', desc: 'Planning, frontend, backend, styling, testing, and deployment—each step handled by dedicated agents. Swarm mode runs them in parallel.' },
              { step: '3', title: 'Design-to-code & iterate', desc: 'Attach a screenshot for pixel-accurate code. Use Quick, Plan, Agent, or Thinking mode. Iterate in chat and export when ready — inevitable.' }
            ].map((item, i) => (
              <div key={i} className="text-center">
                <div className="text-2xl font-mono text-kimi-accent mb-2">{item.step}</div>
                <h3 className="text-lg font-semibold text-kimi-text mb-2">{item.title}</h3>
                <p className="text-sm text-kimi-muted">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Live Examples — See What CrucibAI Built (10/10 proof) */}
      <section id="examples" className="py-20 px-6 bg-kimi-bg-elevated/50">
        <div className="max-w-5xl mx-auto">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Live Examples</span>
          <h2 className="text-kimi-section font-bold text-kimi-text mt-2 mb-2">See What CrucibAI Built</h2>
          <p className="text-kimi-muted mb-8">Real apps from our 120-agent swarm. Inevitable outcomes — fork any example to open it in your workspace.</p>
          <div className="grid sm:grid-cols-3 gap-6">
            {liveExamples.length > 0 ? liveExamples.map((ex) => (
              <div key={ex.name} className="p-5 rounded-xl border border-white/10 bg-kimi-bg hover:border-white/20 transition">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 rounded-lg bg-white/10">
                    <FileCode className="w-5 h-5 text-kimi-accent" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-kimi-text">{ex.name.replace(/-/g, ' ')}</h3>
                    <p className="text-xs text-kimi-muted line-clamp-2">{ex.prompt?.slice(0, 70)}…</p>
                  </div>
                </div>
                {ex.quality_metrics?.overall_score != null && (
                  <p className="text-xs text-kimi-muted mb-3">Quality score: {ex.quality_metrics.overall_score}/100</p>
                )}
                <button
                  onClick={() => user ? navigate(`/app/examples`) : navigate(`/auth?mode=register&redirect=${encodeURIComponent('/app/examples')}`)}
                  className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-white/10 text-kimi-text hover:bg-white/20 transition text-sm font-medium"
                >
                  <GitFork className="w-4 h-4" />
                  {user ? 'View all examples & fork' : 'Sign in to fork'}
                </button>
              </div>
            )) : (
              <>
                {['Todo app with auth & CRUD', 'Blog platform with comments', 'E-commerce store with cart'].map((label, i) => (
                  <div key={i} className="p-5 rounded-xl border border-white/10 bg-kimi-bg">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="p-2 rounded-lg bg-white/10"><FileCode className="w-5 h-5 text-kimi-accent" /></div>
                      <h3 className="font-semibold text-kimi-text">{label}</h3>
                    </div>
                    <button
                      onClick={() => navigate(user ? '/app' : '/auth?mode=register')}
                      className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-white/10 text-kimi-text hover:bg-white/20 transition text-sm"
                    >
                      <ArrowRight className="w-4 h-4" /> {user ? 'Open workspace' : 'Get started'}
                    </button>
                  </div>
                ))}
              </>
            )}
          </div>
          <div className="mt-6 text-center">
            <Link to="/app/examples" className="text-kimi-accent hover:text-kimi-text text-sm font-medium">
              View all examples →
            </Link>
          </div>
        </div>
      </section>

      {/* Where Can You Use CrucibAI — accordion */}
      <section className="py-20 px-6">
        <div className="max-w-3xl mx-auto">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Access</span>
          <h2 className="text-kimi-section font-bold text-kimi-text mt-2 mb-8">Where Can You Use CrucibAI?</h2>
          <p className="text-kimi-muted mb-8">Use CrucibAI in the browser, export your code, and deploy anywhere.</p>
          <div className="space-y-0 border border-white/10 rounded-xl overflow-hidden">
            {whereItems.map((item, i) => (
              <div key={i} className="border-b border-white/10 last:border-0">
                <button onClick={() => setOpenWhere(openWhere === i ? null : i)} className="w-full px-6 py-4 flex items-center justify-between text-left text-kimi-text font-medium">
                  {item.title}
                  <ChevronDown className={`w-4 h-4 text-kimi-muted transition-transform ${openWhere === i ? 'rotate-180' : ''}`} />
                </button>
                {openWhere === i && (
                  <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }} className="overflow-hidden">
                    <p className="px-6 pb-4 text-sm text-kimi-muted">{item.desc}</p>
                  </motion.div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How to Use — steps */}
      <section id="how" className="py-24 px-6 bg-kimi-bg-elevated/50">
        <div className="max-w-4xl mx-auto">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">How it works</span>
          <h2 className="text-kimi-section font-bold text-kimi-text mt-2 mb-4 text-center">How to Use CrucibAI</h2>
          <p className="text-kimi-muted text-center mb-16 max-w-xl mx-auto">Create at the speed of thought. Describe your idea and watch it become a working app.</p>
          <div className="grid md:grid-cols-4 gap-10">
            {[
              { step: '1', title: 'Describe', desc: 'On the landing page or in the workspace, tell us what you want in plain language. Attach a screenshot for design-to-code.' },
              { step: '2', title: 'Plan & build', desc: 'For bigger asks we create a plan first and suggest features. Then we generate production-ready code (React, Tailwind).' },
              { step: '3', title: 'Iterate', desc: 'Want changes? Just ask in the chat. We update the code instantly.' },
              { step: '4', title: 'Ship', desc: 'Export to ZIP or push to GitHub. Deploy to Vercel, Netlify, or any host. You own the code.' }
            ].map((item, i) => (
              <motion.div key={item.step} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.1 }}>
                <div className="text-xs text-kimi-muted font-mono mb-3">{item.step}</div>
                <h3 className="text-lg font-medium text-kimi-text mb-2">{item.title}</h3>
                <p className="text-sm text-kimi-muted leading-relaxed">{item.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CrucibAI vs Others — comparison table */}
      <section className="py-20 px-6 bg-kimi-bg-elevated/50">
        <div className="max-w-5xl mx-auto">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Compare</span>
          <h2 className="text-kimi-section font-bold text-kimi-text mt-2 mb-8">CrucibAI vs Other AI Tools</h2>
          <div className="overflow-x-auto rounded-xl border border-white/10">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="p-4 font-semibold text-kimi-text">Tool</th>
                  <th className="p-4 font-semibold text-kimi-text">Best for</th>
                  <th className="p-4 font-semibold text-kimi-text">Strongest at</th>
                  <th className="p-4 font-semibold text-kimi-text">Pick it if</th>
                </tr>
              </thead>
              <tbody>
                {comparisonRows.map((row, i) => (
                  <tr key={i} className="border-b border-white/10 last:border-0">
                    <td className="p-4 font-medium text-kimi-text">{row.tool}</td>
                    <td className="p-4 text-kimi-muted">{row.bestFor}</td>
                    <td className="p-4 text-kimi-muted">{row.strongest}</td>
                    <td className="p-4 text-kimi-muted">{row.pick}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Who builds better? Faster? More helpful? — value prop (where we win) */}
      <section id="who-builds-better" className="py-20 px-6">
        <div className="max-w-5xl mx-auto">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Why CrucibAI</span>
          <h2 className="text-kimi-section font-bold text-kimi-text mt-2 mb-2">Who Builds Better Products? Who Builds Faster? Which Is More Helpful?</h2>
          <p className="text-kimi-muted mb-10">That&apos;s where we win.</p>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="p-6 rounded-xl border border-white/10 bg-kimi-bg hover:border-kimi-accent/30 transition">
              <h3 className="text-lg font-semibold text-kimi-text mb-3">Better</h3>
              <p className="text-sm text-kimi-muted mb-3">Structured plans, 120 verifiable agents, quality score, and full audit trail. You see every step and every artifact.</p>
              <p className="text-xs text-kimi-accent font-medium">CrucibAI → structure, visibility, verifiable steps</p>
            </div>
            <div className="p-6 rounded-xl border border-white/10 bg-kimi-bg hover:border-kimi-accent/30 transition">
              <h3 className="text-lg font-semibold text-kimi-text mb-3">Faster</h3>
              <p className="text-sm text-kimi-muted mb-3">Parallel DAG: many agents run per phase. No artificial delay. Self-heal retries tests and security once if needed.</p>
              <p className="text-xs text-kimi-accent font-medium">CrucibAI → parallel, no fake latency, self-heal</p>
            </div>
            <div className="p-6 rounded-xl border border-white/10 bg-kimi-bg hover:border-kimi-accent/30 transition">
              <h3 className="text-lg font-semibold text-kimi-text mb-3">More helpful for everyone</h3>
              <p className="text-sm text-kimi-muted mb-3">Plan-first, one prompt to full app, visible progress. Works for non-devs and power users alike.</p>
              <p className="text-xs text-kimi-accent font-medium">CrucibAI → one prompt, full visibility, for all users</p>
            </div>
          </div>
        </div>
      </section>

      {/* Use cases */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Use cases</span>
          <h2 className="text-kimi-section font-bold text-kimi-text mt-2 mb-6">How is CrucibAI Used in Real-World Applications?</h2>
          <p className="text-kimi-muted mb-8">Startups, internal tools, agencies, and educators use CrucibAI to go from idea to shipped app faster.</p>
          <ul className="grid sm:grid-cols-2 gap-4 text-kimi-body text-kimi-muted">
            {['Startups: MVPs and landing pages in minutes', 'Internal tools: admin dashboards, reports, forms', 'Agencies: client demos and prototypes', 'Education: teaching app design and prototyping'].map((item, i) => (
              <li key={i} className="flex items-center gap-2"><span className="text-kimi-accent">•</span> {item}</li>
            ))}
          </ul>
        </div>
      </section>

      {/* Limitations */}
      <section className="py-16 px-6 bg-kimi-bg-elevated/50">
        <div className="max-w-3xl mx-auto">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Transparency</span>
          <h2 className="text-kimi-section font-bold text-kimi-text mt-2 mb-4">What Are the Limitations of CrucibAI?</h2>
          <p className="text-kimi-muted text-sm leading-relaxed">
            Complex multi-page apps may need several iterations. Very large codebases are subject to model context limits. Offline use is not supported. We recommend verifying critical logic and running your own tests before production.
          </p>
        </div>
      </section>

      {/* Roadmap / Future plans */}
      <section className="py-16 px-6">
        <div className="max-w-3xl mx-auto">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Roadmap</span>
          <h2 className="text-kimi-section font-bold text-kimi-text mt-2 mb-4">What Are the Future Plans for CrucibAI?</h2>
          <ul className="text-kimi-muted text-sm space-y-2">
            {['Expanding API access for developers', 'More structured outputs (README, API docs, FAQ schema)', 'Enhanced Swarm and Thinking modes', 'Personalization (preferences, stack, style)'].map((item, i) => (
              <li key={i} className="flex items-center gap-2"><span className="text-kimi-accent">•</span> {item}</li>
            ))}
          </ul>
        </div>
      </section>

      {/* FAQ — numbered accordion */}
      <section id="faq" className="py-24 px-6">
        <div className="max-w-2xl mx-auto">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">FAQ</span>
          <h2 className="text-kimi-section font-bold text-kimi-text mt-2 mb-4 text-center">Frequently Asked Questions</h2>
          <p className="text-kimi-muted text-center mb-12">Everything you need to know about building with CrucibAI.</p>
          <div className="space-y-0 border border-white/10 rounded-xl overflow-hidden">
            {allFaqs.map((faq, i) => (
              <div key={i} className="border-b border-white/10 last:border-0">
                <button onClick={() => setOpenFaq(openFaq === i ? null : i)} className="w-full py-5 px-6 flex items-center justify-between text-left">
                  <span className="flex items-center gap-3">
                    <span className="text-xs text-kimi-muted font-mono w-6">{i + 1}</span>
                    <span className="text-sm font-medium text-kimi-text">{faq.q}</span>
                  </span>
                  <ChevronDown className={`w-4 h-4 text-kimi-muted shrink-0 transition-transform ${openFaq === i ? 'rotate-180' : ''}`} />
                </button>
                <AnimatePresence>
                  {openFaq === i && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                      <p className="pb-5 px-6 text-sm text-kimi-muted">{faq.a}</p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer CTA — Kimi-style */}
      <section className="py-24 px-6 border-t border-white/10">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-bold text-kimi-text mb-4">Make your idea inevitable</h2>
          <p className="text-kimi-muted mb-8">Describe your vision. Watch it become inevitable. No code required.</p>
          <div className="flex flex-wrap justify-center gap-4">
            <button onClick={() => navigate(user ? '/app' : '/auth?mode=register')} className="px-6 py-3 bg-white text-black font-medium rounded-lg hover:bg-zinc-200 transition border border-black/10">
              Make It Inevitable
            </button>
            <Link to="/learn" className="px-6 py-3 bg-transparent text-kimi-text font-medium rounded-lg border border-white/30 hover:border-white/50 transition">
              View Documentation
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-6 border-t border-white/10 bg-kimi-bg">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-4 gap-12 mb-12">
            <div>
              <div className="text-lg font-semibold text-kimi-text mb-4">CrucibAI — Inevitable AI</div>
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
              </ul>
            </div>
            <div>
              <div className="text-xs text-kimi-muted uppercase tracking-wider mb-4">Resources</div>
              <ul className="space-y-3 text-sm">
                <li><Link to="/learn" className="text-kimi-muted hover:text-kimi-text transition">Learn</Link></li>
                <li><Link to="/benchmarks" className="text-kimi-muted hover:text-kimi-text transition">Benchmarks</Link></li>
                <li><Link to="/shortcuts" className="text-kimi-muted hover:text-kimi-text transition">Shortcuts</Link></li>
                <li><Link to="/prompts" className="text-kimi-muted hover:text-kimi-text transition">Prompt Library</Link></li>
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
          <div className="pt-8 border-t border-white/10 text-center">
            <p className="text-xs text-kimi-muted">© 2026 CrucibAI. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;

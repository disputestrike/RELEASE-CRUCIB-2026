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

  const comparisonData = {
    crucibai: { buildWeb: true, buildMobile: true, runAutomations: true, sameAI: true, importCode: true, ideExtensions: true, realtimeMonitor: true, planBeforeBuild: true, approvalWorkflows: true, qualityScore: true, appStorePack: true, pricePer100: '$12.99' },
    lovable: { buildWeb: true, buildMobile: false, runAutomations: false, sameAI: false, importCode: false, ideExtensions: false, realtimeMonitor: false, planBeforeBuild: true, approvalWorkflows: false, qualityScore: false, appStorePack: false, pricePer100: '$25' },
    bolt: { buildWeb: true, buildMobile: false, runAutomations: false, sameAI: false, importCode: false, ideExtensions: false, realtimeMonitor: false, planBeforeBuild: true, approvalWorkflows: false, qualityScore: false, appStorePack: false, pricePer100: '~$20' },
    n8n: { buildWeb: false, buildMobile: false, runAutomations: true, sameAI: false, importCode: false, ideExtensions: false, realtimeMonitor: false, planBeforeBuild: false, approvalWorkflows: true, qualityScore: false, appStorePack: false, pricePer100: 'N/A' },
    cursor: { buildWeb: false, buildMobile: false, runAutomations: false, sameAI: false, importCode: true, ideExtensions: true, realtimeMonitor: false, planBeforeBuild: false, approvalWorkflows: false, qualityScore: false, appStorePack: false, pricePer100: '$20' },
    flutterflow: { buildWeb: false, buildMobile: true, runAutomations: false, sameAI: false, importCode: false, ideExtensions: false, realtimeMonitor: false, planBeforeBuild: false, approvalWorkflows: false, qualityScore: false, appStorePack: true, pricePer100: '$25' }
  };
  const comparisonLabels = [
    { key: 'buildWeb', label: 'Build web apps' },
    { key: 'buildMobile', label: 'Build mobile apps' },
    { key: 'runAutomations', label: 'Run automations' },
    { key: 'sameAI', label: 'Same AI for apps + automations' },
    { key: 'importCode', label: 'Import existing code' },
    { key: 'ideExtensions', label: 'IDE extensions' },
    { key: 'realtimeMonitor', label: 'Real-time agent monitor' },
    { key: 'planBeforeBuild', label: 'Plan shown before build' },
    { key: 'approvalWorkflows', label: 'Approval workflows' },
    { key: 'qualityScore', label: 'Quality score per build' },
    { key: 'appStorePack', label: 'App Store submission pack' },
    { key: 'pricePer100', label: 'Price per 100 credits' }
  ];

  return (
    <div className="marketing-page min-h-screen bg-kimi-bg text-kimi-text grid-pattern-kimi">
      {/* Navigation — Kimi-style */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-kimi-bg border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3">
            <img src="/assets/logo.png" alt="CrucibAI" className="w-8 h-8" />
            <span className="text-xl font-semibold tracking-tight text-kimi-text">CrucibAI <span className="text-kimi-muted font-normal text-base">— Inevitable AI</span></span>
          </Link>
          <div className="hidden md:flex items-center gap-6">
            <Link to="/features" className="text-kimi-nav text-kimi-muted hover:text-kimi-text transition">Features</Link>
            <Link to="/pricing" className="text-kimi-nav text-kimi-muted hover:text-kimi-text transition">Pricing</Link>
            <Link to="/templates" className="text-kimi-nav text-kimi-muted hover:text-kimi-text transition">Templates</Link>
            <Link to="/prompts" className="text-kimi-nav text-kimi-muted hover:text-kimi-text transition">Prompts</Link>
            <Link to="/learn" className="text-kimi-nav text-kimi-muted hover:text-kimi-text transition">Documentation</Link>
            <Link to="/blog" className="text-kimi-nav text-kimi-muted hover:text-kimi-text transition">Blog</Link>
            {user ? (
              <button onClick={() => navigate('/app')} className="text-kimi-nav text-kimi-muted hover:text-kimi-text transition">Dashboard</button>
            ) : (
              <button onClick={() => navigate('/auth')} className="text-kimi-nav text-kimi-muted hover:text-kimi-text transition">Sign in</button>
            )}
            <button onClick={() => navigate(user ? '/app' : '/auth?mode=register')} className="px-4 py-2 bg-white text-gray-900 text-sm font-medium rounded-lg hover:bg-gray-100 transition">Get started free</button>
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
              <Link to="/prompts" className="text-lg" onClick={() => setMobileMenuOpen(false)}>Prompts</Link>
              <Link to="/learn" className="text-lg" onClick={() => setMobileMenuOpen(false)}>Documentation</Link>
              <Link to="/blog" className="text-lg" onClick={() => setMobileMenuOpen(false)}>Blog</Link>
              <button onClick={() => { navigate(user ? '/app' : '/auth?mode=register'); setMobileMenuOpen(false); }} className="w-full py-3 bg-white text-gray-900 rounded-lg font-medium mt-4">Get started</button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Hero */}
      <section className="pt-32 pb-20 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-sm text-kimi-muted mb-4">
            Agentic · 120-agent swarm · 99.2% success · Full transparency
          </motion.p>
          <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-kimi-hero font-bold tracking-tight text-kimi-text mb-6">
            Describe it Monday. Ship it Friday.
          </motion.h1>
          <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="text-lg text-kimi-muted mb-12 max-w-2xl mx-auto leading-relaxed">
            The only platform where the same AI that builds your app runs inside your automations. Web apps, mobile apps, and automations — one platform, one AI, no switching tools.
          </motion.p>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.15 }} className="flex flex-col sm:flex-row flex-wrap items-center justify-center gap-3">
            <button onClick={() => navigate(user ? '/app' : '/auth?mode=register')} className="glass-kimi-btn px-6 py-3 text-gray-900 font-medium rounded-xl transition">
              Make It Inevitable
            </button>
            <Link to="/app/workspace" className="px-6 py-3 bg-gray-50 text-kimi-text font-medium rounded-xl border border-gray-200 hover:bg-gray-100 transition">Open Workspace</Link>
          </motion.div>
          {!user && (
            <p className="mt-4 text-sm text-kimi-muted">Sign in to save projects and sync across devices.</p>
          )}
        </div>

        {/* Hero stats — 4 items, remove 72 hours */}
        <motion.section initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.15 }} className="max-w-4xl mx-auto mt-12 px-6">
          <div className="flex flex-wrap items-center justify-center gap-6 py-5 px-6 rounded-xl border border-gray-200 bg-kimi-bg-elevated/50">
            <span className="text-sm font-medium text-kimi-text">120 agents in parallel</span>
            <span className="text-sm font-medium text-kimi-text">99.2% deployment success</span>
            <span className="text-sm font-medium text-kimi-text">Half the price of Lovable</span>
            <span className="text-sm font-medium text-kimi-text">Web · Mobile · Automation</span>
          </div>
          <p className="text-center text-xs text-kimi-muted mt-2">Not promises. Every number is measured.</p>
        </motion.section>

        {/* Main Input — extra space + glass */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="max-w-2xl mx-auto mt-16">
          <p className="text-center text-sm font-medium text-kimi-accent mb-3">Agentic: describe it — we build it. Full automation, minimal supervision.</p>
          <div className="glass-kimi-panel rounded-2xl overflow-hidden">
            {/* Messages */}
            {messages.length > 0 && (
              <div className="max-h-80 overflow-y-auto p-5 space-y-4">
                {messages.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[80%] px-4 py-3 rounded-xl text-sm ${
                      msg.role === 'user' 
                        ? 'bg-white text-gray-900' 
                        : msg.error 
                          ? 'bg-gray-500/10 text-gray-400'
                          : 'bg-gray-100 text-gray-700'
                    }`}>
                      {msg.isBuilding ? (
                        <div className="flex items-center gap-2">
                          <div className="w-4 h-4 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin" />
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
                <div className="h-0.5 bg-gray-200 rounded-full overflow-hidden">
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
                  <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200">
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
                  <div key={i} className="flex items-center gap-2 px-3 py-2 bg-gray-100 rounded-lg text-sm">
                    {file.type?.startsWith('image/') ? (
                      <Image className="w-4 h-4 text-kimi-accent shrink-0" />
                    ) : (
                      <FileText className="w-4 h-4 text-gray-400 shrink-0" />
                    )}
                    <span className="text-gray-500 max-w-[180px] truncate">{file.name}</span>
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
                  <div className="flex gap-2 px-4 py-3 bg-gray-50 rounded-xl border border-gray-200 focus-within:ring-1 focus-within:ring-gray-300 transition min-h-[160px]">
                    <textarea
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      placeholder={messages.length > 0 ? "Ask for changes..." : "What do you want to build?"}
                      className="flex-1 bg-transparent text-gray-900 placeholder-gray-400 outline-none resize-none min-h-[120px] text-base leading-relaxed"
                      disabled={isBuilding}
                      rows={5}
                    />
                    <button
                      type="button"
                      onClick={isRecording ? stopVoiceRecording : startVoiceRecording}
                      disabled={isBuilding || isTranscribing}
                      className={`p-2.5 rounded-lg transition self-end shrink-0 ${isRecording ? 'bg-gray-500/30 text-gray-400 ring-2 ring-red-400/50' : 'text-kimi-muted hover:text-kimi-text hover:bg-gray-100'}`}
                      title={isRecording ? 'Click to stop and transcribe' : 'Voice input — click to speak'}
                    >
                      {isRecording ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
                    </button>
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="p-2.5 rounded-lg text-kimi-muted hover:text-kimi-text hover:bg-gray-100 transition self-end shrink-0"
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
                  className="px-6 py-4 bg-white text-gray-900 rounded-xl text-base font-medium disabled:opacity-30 disabled:cursor-not-allowed hover:bg-gray-100 transition shrink-0"
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
                      <span className="w-2 h-2 rounded-full bg-gray-500 animate-pulse" aria-hidden />
                      <span className="text-sm text-gray-400 font-medium">Listening… click the mic again to stop and see your text here.</span>
                    </>
                  )}
                  {isTranscribing && !isRecording && (
                    <>
                      <Loader2 className="w-4 h-4 text-kimi-accent animate-spin shrink-0" />
                      <span className="text-sm text-kimi-muted">Transcribing… your words will appear above when ready.</span>
                    </>
                  )}
                  {voiceError && !isRecording && !isTranscribing && (
                    <span className="text-sm text-gray-400">{voiceError}</span>
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
                        className="px-3 py-1.5 text-xs text-kimi-muted bg-gray-100 rounded-lg hover:bg-gray-200 hover:text-kimi-text transition border border-gray-200"
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

      {/* The Bridge — moat section */}
      <section id="why-crucibai" className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Why CrucibAI</span>
          <h2 className="text-kimi-section font-bold text-kimi-text mt-2 mb-12 text-center">One AI. Two superpowers. Nobody else has the bridge.</h2>
          <div className="grid md:grid-cols-2 gap-8 mb-8">
            <div className="p-6 rounded-2xl border border-gray-200 bg-kimi-bg-card">
              <h3 className="text-xl font-semibold text-kimi-accent mb-3">Build</h3>
              <p className="text-sm text-kimi-muted leading-relaxed">
                Describe your app in plain language. Our 120-agent swarm plans, builds, tests, and deploys it. Watch every agent work in real time. Web apps, mobile apps, landing pages — production-ready code you own.
              </p>
            </div>
            <div className="p-6 rounded-2xl border border-gray-200 bg-kimi-bg-card">
              <h3 className="text-xl font-semibold text-kimi-accent mb-3">Automate</h3>
              <p className="text-sm text-kimi-muted leading-relaxed">
                The same AI runs inside your automations. Daily digest. Lead follow-up. Content refresh. Describe what you want in one sentence — we create the agent. Schedule it, webhook it, chain the steps.
              </p>
            </div>
          </div>
          <p className="text-center text-sm font-medium text-kimi-text mb-2">run_agent — the bridge competitors can&apos;t copy</p>
          <p className="text-center text-sm text-kimi-muted">
            N8N and Zapier automate. They don&apos;t build apps. Lovable and Bolt build apps. They don&apos;t automate. CrucibAI does both — with the same AI, in the same platform.
          </p>
        </div>
      </section>

      {/* Watch It Work — AgentMonitor */}
      <section className="py-20 px-6 bg-kimi-bg-elevated/50">
        <div className="max-w-4xl mx-auto">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Full Transparency</span>
          <h2 className="text-kimi-section font-bold text-kimi-text mt-2 mb-6 text-center">No black boxes. Watch every agent work.</h2>
          <p className="text-kimi-muted text-center mb-10 max-w-2xl mx-auto">
            While competitors show you a spinner and hope for the best, CrucibAI shows you everything. Every agent, every phase, every decision — in real time. When the build is done, you have a quality score, a full audit trail, and code you own.
          </p>
          <div className="grid sm:grid-cols-3 gap-6 mb-10">
            <div className="p-4 rounded-xl border border-gray-200 bg-kimi-bg">
              <h4 className="font-semibold text-kimi-text mb-2">Per-agent visibility</h4>
              <p className="text-sm text-kimi-muted">See exactly which of the 120 agents is running, what it&apos;s doing, and how many tokens it used. Nothing hidden.</p>
            </div>
            <div className="p-4 rounded-xl border border-gray-200 bg-kimi-bg">
              <h4 className="font-semibold text-kimi-text mb-2">Quality score</h4>
              <p className="text-sm text-kimi-muted">Every build gets scored 0–100 across frontend, backend, tests, security, and deployment. You see the score before you ship.</p>
            </div>
            <div className="p-4 rounded-xl border border-gray-200 bg-kimi-bg">
              <h4 className="font-semibold text-kimi-text mb-2">Phase retry</h4>
              <p className="text-sm text-kimi-muted">If a phase falls below quality threshold, we flag it and retry automatically. Self-healing builds, visible to you the entire time.</p>
            </div>
          </div>
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-8 flex items-center justify-center min-h-[280px]">
            <p className="text-kimi-muted text-center text-sm">AgentMonitor — real-time agent status, phase progress, token usage, and quality score. <br /><span className="text-xs">Screenshot placeholder — add image when ready.</span></p>
          </div>
        </div>
      </section>

      {/* Monday to Friday */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">How it actually works</span>
          <h2 className="text-kimi-section font-bold text-kimi-text mt-2 mb-12 text-center">Monday to Friday. One platform, one AI.</h2>
          <div className="space-y-8">
            <div className="flex gap-4">
              <span className="text-kimi-accent font-mono shrink-0">Monday</span>
              <div>
                <h4 className="font-semibold text-kimi-text mb-1">Describe</h4>
                <p className="text-sm text-kimi-muted">Tell us what you want. Plain language. Attach a screenshot if you have one. We generate a plan — features, components, design — before writing a single line of code. You approve, we build.</p>
              </div>
            </div>
            <div className="flex gap-4">
              <span className="text-kimi-accent font-mono shrink-0">Tue–Wed</span>
              <div>
                <h4 className="font-semibold text-kimi-text mb-1">Build</h4>
                <p className="text-sm text-kimi-muted">Our 120-agent swarm runs in parallel. Frontend, backend, database, tests, security, deployment — each phase handled by dedicated agents. You watch the AgentMonitor. You see every step.</p>
              </div>
            </div>
            <div className="flex gap-4">
              <span className="text-kimi-accent font-mono shrink-0">Thursday</span>
              <div>
                <h4 className="font-semibold text-kimi-text mb-1">Automate</h4>
                <p className="text-sm text-kimi-muted">The same AI creates your automations. Daily lead digest to Slack. Email follow-up sequence. Content refresh agent. Describe each one in plain language. We create the agent, wire the steps, set the schedule.</p>
              </div>
            </div>
            <div className="flex gap-4">
              <span className="text-kimi-accent font-mono shrink-0">Friday</span>
              <div>
                <h4 className="font-semibold text-kimi-text mb-1">Ship</h4>
                <p className="text-sm text-kimi-muted">Export to ZIP. Push to GitHub. Deploy to Vercel or Netlify in one click. Your app is live. Your automations are running. You have the copy for your ads. You run them — we built the stack.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Built for — 4 personas (replaces For everyone) */}
      <section className="py-20 px-6 bg-kimi-bg-elevated/50">
        <div className="max-w-5xl mx-auto">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Built for</span>
          <h2 className="text-kimi-section font-bold text-kimi-text mt-2 mb-12 text-center">Whether you write code or not.</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="p-6 rounded-xl border border-gray-200 bg-kimi-bg hover:border-kimi-accent/30 transition">
              <h3 className="font-semibold text-kimi-text mb-2">Marketers &amp; Agencies</h3>
              <p className="text-sm text-kimi-muted mb-4">Build landing pages, funnels, and blogs in hours. Automate lead digests, follow-up sequences, and content pipelines with the same AI. Monday prompt, Friday launch. No dev dependency.</p>
              <button onClick={() => startBuild('Landing page')} className="text-sm font-medium text-kimi-accent hover:text-kimi-text transition">→ Start building marketing stacks</button>
            </div>
            <div className="p-6 rounded-xl border border-gray-200 bg-kimi-bg hover:border-kimi-accent/30 transition">
              <h3 className="font-semibold text-kimi-text mb-2">Founders &amp; Startups</h3>
              <p className="text-sm text-kimi-muted mb-4">Idea to deployed MVP without a dev team. Import existing code or start from scratch. Get web, mobile, and automation in one platform. Ship this week, iterate next week.</p>
              <button onClick={() => startBuild('MVP')} className="text-sm font-medium text-kimi-accent hover:text-kimi-text transition">→ Build your MVP</button>
            </div>
            <div className="p-6 rounded-xl border border-gray-200 bg-kimi-bg hover:border-kimi-accent/30 transition">
              <h3 className="font-semibold text-kimi-text mb-2">Developers</h3>
              <p className="text-sm text-kimi-muted mb-4">Your IDE, our AI. Extensions for VSCode, JetBrains, Sublime, and Vim. Inject Stripe checkout in one command. Auto-generate README, API docs, and FAQ schema. Import any codebase — paste, ZIP, or Git URL.</p>
              <Link to="/features" className="text-sm font-medium text-kimi-accent hover:text-kimi-text transition">→ Extend your workflow</Link>
            </div>
            <div className="p-6 rounded-xl border border-gray-200 bg-kimi-bg hover:border-kimi-accent/30 transition">
              <h3 className="font-semibold text-kimi-text mb-2">Product Teams</h3>
              <p className="text-sm text-kimi-muted mb-4">Prototype to production with approval workflows, step chaining, and webhook triggers. Every build has an audit trail and quality score. Enterprise-grade security without enterprise complexity.</p>
              <button onClick={() => startBuild('Internal tool')} className="text-sm font-medium text-kimi-accent hover:text-kimi-text transition">→ Build for your team</button>
            </div>
          </div>
        </div>
      </section>

      {/* Bring Your Code */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Already have code?</span>
          <h2 className="text-kimi-section font-bold text-kimi-text mt-2 mb-6 text-center">Bring it. We&apos;ll keep building.</h2>
          <p className="text-kimi-muted text-center mb-10 max-w-2xl mx-auto">
            Paste your code. Upload a ZIP. Drop a Git URL. We stand up your existing project in the workspace, run a security scan and accessibility check, and you keep building — with the full 120-agent swarm behind you.
          </p>
          <div className="grid sm:grid-cols-3 gap-6">
            <div className="p-4 rounded-xl border border-gray-200 bg-kimi-bg">
              <h4 className="font-semibold text-kimi-text mb-2">Paste, ZIP, or Git</h4>
              <p className="text-sm text-kimi-muted">Any existing project. Any state. We import it, organize it, and open it in the workspace ready to continue.</p>
            </div>
            <div className="p-4 rounded-xl border border-gray-200 bg-kimi-bg">
              <h4 className="font-semibold text-kimi-text mb-2">Security scan on import</h4>
              <p className="text-sm text-kimi-muted">We run a security check the moment your code arrives. Secrets in client code, auth on API, CORS configuration — you see the checklist before you build another line.</p>
            </div>
            <div className="p-4 rounded-xl border border-gray-200 bg-kimi-bg">
              <h4 className="font-semibold text-kimi-text mb-2">Keep building with AI</h4>
              <p className="text-sm text-kimi-muted">Your existing codebase, our 120 agents. Ask for features, fixes, or a full rebuild. You own the code throughout.</p>
            </div>
          </div>
          <div className="mt-10 text-center">
            <button onClick={() => navigate(user ? '/app' : '/auth?mode=register')} className="px-6 py-3 bg-white text-gray-900 font-medium rounded-lg hover:bg-gray-100 transition">
              {user ? 'Import in Dashboard' : 'Get started free'}
            </button>
          </div>
        </div>
      </section>

      {/* What You Can Build — 8 use cases */}
      <section id="use-cases" className="py-20 px-6 bg-kimi-bg-elevated/50">
        <div className="max-w-5xl mx-auto">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Use cases</span>
          <h2 className="text-kimi-section font-bold text-kimi-text mt-2 mb-8 text-center">Just about everything.</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { title: 'Dashboards', desc: 'Reporting, analytics, and data views with charts and filters. Real-time data, admin controls, export to PDF and Excel.', cta: 'Build a dashboard' },
              { title: 'Landing Pages', desc: 'Hero, features, waitlist, and pricing sections. Design-to-code from a screenshot. Live in 30 minutes.', cta: 'Start a landing page' },
              { title: 'Mobile Apps', desc: 'iOS and Android with Expo. Production-ready. App Store submission pack with step-by-step guides for App Store and Google Play.', cta: 'Build a mobile app' },
              { title: 'E‑Commerce & Checkout', desc: 'Product catalog, cart, checkout, payments. Inject Stripe in one command. Full automation from product list to order confirmation.', cta: 'Build a store' },
              { title: 'Automations & Agents', desc: 'Daily digest. Lead follow-up. Content pipeline. Webhook handlers. Describe it — we create it. Schedule or trigger by webhook.', cta: 'Create an agent' },
              { title: 'Internal Tools', desc: 'Admin tables, forms, approval workflows, CRUD. Step chaining between actions. Agentic: ship in hours, not months.', cta: 'Build an internal tool' },
              { title: 'SaaS Products', desc: 'Full-stack SaaS with auth, Stripe subscriptions, user dashboard, and admin panel. Import the Auth + SaaS pattern and build from there.', cta: 'Start a SaaS' },
              { title: 'Docs, Slides & Sheets', desc: 'Generate README, API docs, FAQ schema, presentations, and CSV data — directly from your project or from a prompt.', cta: 'Generate documents' }
            ].map((item, i) => (
              <div key={i} className="p-5 rounded-xl border border-gray-200 bg-kimi-bg hover:border-gray-200 transition">
                <h3 className="text-lg font-semibold text-kimi-text mb-2">{item.title}</h3>
                <p className="text-sm text-kimi-muted mb-4">{item.desc}</p>
                <button onClick={() => startBuild(item.cta)} className="text-sm font-medium text-kimi-accent hover:text-kimi-text transition">{item.cta} →</button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works — 4 steps */}
      <section id="how" className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Under the hood</span>
          <h2 className="text-kimi-section font-bold text-kimi-text mt-2 mb-6 text-center">Plan-first. Agent-powered. Fully transparent.</h2>
          <div className="grid md:grid-cols-2 gap-8">
            {[
              { step: '1', title: 'Describe', desc: 'Tell us what you want in plain language. Attach a screenshot for design-to-code. Or import existing code — paste, ZIP, or Git URL. Voice input supported.' },
              { step: '2', title: 'Plan & approve', desc: 'For every build, we generate a structured plan first — features, components, design decisions. You see the plan. You approve it. Then we build. No surprises.' },
              { step: '3', title: '120 agents build in parallel', desc: 'Planning, frontend, backend, database, styling, testing, security, deployment — each phase handled by dedicated agents running in parallel. Watch them work in AgentMonitor.' },
              { step: '4', title: 'Ship what you own', desc: 'Export to ZIP or push to GitHub. Deploy to Vercel or Netlify in one click. You own all the code. Your automations are running. You\'re live.' }
            ].map((item, i) => (
              <div key={i} className="p-6 rounded-xl border border-gray-200 bg-kimi-bg">
                <div className="text-xl font-mono text-kimi-accent mb-2">{item.step}</div>
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
              <div key={ex.name} className="p-5 rounded-xl border border-gray-200 bg-kimi-bg hover:border-gray-200 transition">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 rounded-lg bg-gray-50">
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
                  className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-gray-50 text-kimi-text hover:bg-gray-100 transition text-sm font-medium"
                >
                  <GitFork className="w-4 h-4" />
                  {user ? 'View all examples & fork' : 'Sign in to fork'}
                </button>
              </div>
            )) : (
              <>
                {['Todo app with auth & CRUD', 'Blog platform with comments', 'E-commerce store with cart'].map((label, i) => (
                  <div key={i} className="p-5 rounded-xl border border-gray-200 bg-kimi-bg">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="p-2 rounded-lg bg-gray-50"><FileCode className="w-5 h-5 text-kimi-accent" /></div>
                      <h3 className="font-semibold text-kimi-text">{label}</h3>
                    </div>
                    <button
                      onClick={() => navigate(user ? '/app' : '/auth?mode=register')}
                      className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-gray-50 text-kimi-text hover:bg-gray-100 transition text-sm"
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
          <div className="space-y-0 border border-gray-200 rounded-xl overflow-hidden">
            {whereItems.map((item, i) => (
              <div key={i} className="border-b border-gray-200 last:border-0">
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

      {/* How It Works — 4 steps */}
      <section id="how" className="py-24 px-6 bg-kimi-bg-elevated/50">
        <div className="max-w-4xl mx-auto">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Under the hood</span>
          <h2 className="text-kimi-section font-bold text-kimi-text mt-2 mb-6 text-center">Plan-first. Agent-powered. Fully transparent.</h2>
          <div className="grid md:grid-cols-2 gap-8">
            {[
              { step: '1', title: 'Describe', desc: 'Tell us what you want in plain language. Attach a screenshot for design-to-code. Or import existing code — paste, ZIP, or Git URL. Voice input supported.' },
              { step: '2', title: 'Plan & approve', desc: 'For every build, we generate a structured plan first — features, components, design decisions. You see the plan. You approve it. Then we build. No surprises.' },
              { step: '3', title: '120 agents build in parallel', desc: 'Planning, frontend, backend, database, styling, testing, security, deployment — each phase handled by dedicated agents running in parallel. Watch them work in AgentMonitor.' },
              { step: '4', title: 'Ship what you own', desc: 'Export to ZIP or push to GitHub. Deploy to Vercel or Netlify in one click. You own all the code. Your automations are running. You\'re live.' }
            ].map((item, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.1 }} className="p-6 rounded-xl border border-gray-200 bg-kimi-bg">
                <div className="text-xl font-mono text-kimi-accent mb-2">{item.step}</div>
                <h3 className="text-lg font-semibold text-kimi-text mb-2">{item.title}</h3>
                <p className="text-sm text-kimi-muted leading-relaxed">{item.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CrucibAI vs Others — checkmark comparison */}
      <section className="py-20 px-6 bg-kimi-bg-elevated/50">
        <div className="max-w-5xl mx-auto">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Compare</span>
          <h2 className="text-kimi-section font-bold text-kimi-text mt-2 mb-8">CrucibAI vs Lovable, Bolt, N8N, Cursor, FlutterFlow</h2>
          <div className="overflow-x-auto rounded-xl border border-gray-200">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="p-4 font-semibold text-kimi-text min-w-[120px]">Capability</th>
                  <th className="p-4 font-semibold text-kimi-text text-center min-w-[90px]">CrucibAI</th>
                  <th className="p-4 font-semibold text-kimi-muted text-center min-w-[90px]">Lovable</th>
                  <th className="p-4 font-semibold text-kimi-muted text-center min-w-[90px]">Bolt</th>
                  <th className="p-4 font-semibold text-kimi-muted text-center min-w-[90px]">N8N</th>
                  <th className="p-4 font-semibold text-kimi-muted text-center min-w-[90px]">Cursor</th>
                  <th className="p-4 font-semibold text-kimi-muted text-center min-w-[90px]">FlutterFlow</th>
                </tr>
              </thead>
              <tbody>
                {comparisonLabels.map(({ key, label }, i) => (
                  <tr key={i} className="border-b border-gray-200 last:border-0">
                    <td className="p-4 text-kimi-text">{label}</td>
                    <td className="p-4 text-center">{comparisonData.crucibai[key] === true ? <Check className="w-5 h-5 text-kimi-accent mx-auto" /> : typeof comparisonData.crucibai[key] === 'string' ? <span className="text-kimi-accent font-medium">{comparisonData.crucibai[key]}</span> : '—'}</td>
                    <td className="p-4 text-center">{comparisonData.lovable[key] === true ? <Check className="w-5 h-5 text-kimi-muted mx-auto" /> : comparisonData.lovable[key] === false ? '—' : <span className="text-kimi-muted">{comparisonData.lovable[key]}</span>}</td>
                    <td className="p-4 text-center">{comparisonData.bolt[key] === true ? <Check className="w-5 h-5 text-kimi-muted mx-auto" /> : comparisonData.bolt[key] === false ? '—' : <span className="text-kimi-muted">{comparisonData.bolt[key]}</span>}</td>
                    <td className="p-4 text-center">{comparisonData.n8n[key] === true ? <Check className="w-5 h-5 text-kimi-muted mx-auto" /> : comparisonData.n8n[key] === false ? '—' : <span className="text-kimi-muted">{comparisonData.n8n[key]}</span>}</td>
                    <td className="p-4 text-center">{comparisonData.cursor[key] === true ? <Check className="w-5 h-5 text-kimi-muted mx-auto" /> : comparisonData.cursor[key] === false ? '—' : <span className="text-kimi-muted">{comparisonData.cursor[key]}</span>}</td>
                    <td className="p-4 text-center">{comparisonData.flutterflow[key] === true ? <Check className="w-5 h-5 text-kimi-muted mx-auto" /> : comparisonData.flutterflow[key] === false ? '—' : <span className="text-kimi-muted">{comparisonData.flutterflow[key]}</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Trust — We build CrucibAI using CrucibAI */}
      <section id="trust" className="py-20 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Trust</span>
          <h2 className="text-kimi-section font-bold text-kimi-text mt-2 mb-6">We Build CrucibAI Using CrucibAI</h2>
          <p className="text-kimi-muted mb-8">We dogfood our own platform. Every feature we ship is built and tested with the same 120-agent swarm our customers use.</p>
          <div className="flex flex-wrap justify-center gap-8 text-sm">
            <div className="flex items-center gap-2">
              <Check className="w-5 h-5 text-kimi-accent shrink-0" />
              <span className="text-kimi-text">188 tests passing</span>
            </div>
            <div className="flex items-center gap-2">
              <Check className="w-5 h-5 text-kimi-accent shrink-0" />
              <span className="text-kimi-text">Security-first</span>
            </div>
            <div className="flex items-center gap-2">
              <Check className="w-5 h-5 text-kimi-accent shrink-0" />
              <span className="text-kimi-text">GDPR & CCPA compliant</span>
            </div>
          </div>
          <p className="mt-6 text-xs text-kimi-muted"><Link to="/security" className="hover:text-kimi-text transition">Security & Trust →</Link></p>
        </div>
      </section>

      {/* Who builds better? Faster? More helpful? — value prop (where we win) */}
      <section id="who-builds-better" className="py-20 px-6 bg-kimi-bg-elevated/50">
        <div className="max-w-5xl mx-auto">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Why CrucibAI</span>
          <h2 className="text-kimi-section font-bold text-kimi-text mt-2 mb-2">Who Builds Better Products? Who Builds Faster? Which Is More Helpful?</h2>
          <p className="text-kimi-muted mb-10">That&apos;s where we win.</p>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="p-6 rounded-xl border border-gray-200 bg-kimi-bg hover:border-kimi-accent/30 transition">
              <h3 className="text-lg font-semibold text-kimi-text mb-3">Better</h3>
              <p className="text-sm text-kimi-muted mb-3">Structured plans, 120 verifiable agents, quality score, and full audit trail. You see every step and every artifact.</p>
              <p className="text-xs text-kimi-accent font-medium">CrucibAI → structure, visibility, verifiable steps</p>
            </div>
            <div className="p-6 rounded-xl border border-gray-200 bg-kimi-bg hover:border-kimi-accent/30 transition">
              <h3 className="text-lg font-semibold text-kimi-text mb-3">Faster</h3>
              <p className="text-sm text-kimi-muted mb-3">Parallel DAG: many agents run per phase. No artificial delay. Self-heal retries tests and security once if needed.</p>
              <p className="text-xs text-kimi-accent font-medium">CrucibAI → parallel, no fake latency, self-heal</p>
            </div>
            <div className="p-6 rounded-xl border border-gray-200 bg-kimi-bg hover:border-kimi-accent/30 transition">
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

      {/* FAQ — top 12 on homepage, rest on Learn */}
      <section id="faq" className="py-24 px-6">
        <div className="max-w-2xl mx-auto">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">FAQ</span>
          <h2 className="text-kimi-section font-bold text-kimi-text mt-2 mb-4 text-center">Frequently Asked Questions</h2>
          <p className="text-kimi-muted text-center mb-12">Everything you need to know about building with CrucibAI.</p>
          <div className="space-y-0 border border-gray-200 rounded-xl overflow-hidden">
            {faqs.map((faq, i) => (
              <div key={i} className="border-b border-gray-200 last:border-0">
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
          <p className="mt-8 text-center text-sm text-kimi-muted">
            Have more questions? <Link to="/learn#faq-extra" className="text-kimi-accent hover:underline">See all FAQs on Learn →</Link>
          </p>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-24 px-6 border-t border-gray-200">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-bold text-kimi-text mb-4">Your idea is inevitable. Start Monday.</h2>
          <p className="text-kimi-muted mb-8">50 free credits. No credit card. Describe it today. Ship it Friday.</p>
          <div className="flex flex-wrap justify-center gap-4">
            <button onClick={() => navigate(user ? '/app' : '/auth?mode=register')} className="px-6 py-3 bg-white text-gray-900 font-medium rounded-lg hover:bg-gray-100 transition border border-black/10">
              Make It Inevitable
            </button>
            <Link to="/learn" className="px-6 py-3 bg-transparent text-kimi-text font-medium rounded-lg border border-white/30 hover:border-white/50 transition">
              Learn More
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-6 border-t border-gray-200 bg-kimi-bg">
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

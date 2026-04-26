import { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ArrowRight, Check, Menu, X, Play, ArrowUpRight, FileCode, GitFork } from 'lucide-react';
import { useAuth } from '../authContext';
import { API_BASE as API } from '../apiBase';
import axios from 'axios';
import { logApiError } from '../utils/apiError';
import Logo from '../components/Logo';
import SolutionsNavDropdown, { SOLUTION_LINKS, USE_CASE_LINKS } from '../components/SolutionsNavDropdown';

const OurProjectsPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [openFaq, setOpenFaq] = useState(null);
  const [openWhere, setOpenWhere] = useState(null);
  const [liveExamples, setLiveExamples] = useState([]);

  useEffect(() => {
    axios.get(`${API}/examples`).then((r) => setLiveExamples((r.data.examples || []).slice(0, 3))).catch((e) => { logApiError('LandingPage examples', e); setLiveExamples([]); });
  }, [API]);

  useEffect(() => {
    const id = (location.hash || '').replace(/^#/, '');
    if (!id || location.pathname !== '/our-projects') return undefined;
    const t = window.setTimeout(() => {
      document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 80);
    return () => clearTimeout(t);
  }, [location.hash, location.pathname]);

  const startBuild = (promptText, filesOverride = null) => {
    const prompt = (promptText || '').trim();
    if (!prompt) return;
    const q = `prompt=${encodeURIComponent(prompt)}`;
    const workspacePath = `/app/workspace?${q}`;
    const state = filesOverride?.length ? { initialAttachedFiles: filesOverride } : undefined;
    navigate(workspacePath, { state });
  };

  const faqs = [
    { q: 'What is CrucibAI?', a: 'CrucibAI is Inevitable AI — the platform where intelligence doesn\'t just act, it makes outcomes inevitable. Describe what you need in plain language; we generate production-ready code with plan-first flow and a swarm of agents and sub-agents. Full transparency: every phase, every agent, no black boxes.' },
    { q: 'Is CrucibAI free to use?', a: 'Yes. We offer a free tier with 200 credits. Paid plans are monthly (Builder, Pro, Scale, Teams) with more credits per month. Need more? Buy credits in bulk (100–10,000 at $0.03/credit, same rate as plans).' },
    { q: 'Do I need coding experience?', a: 'No. Our platform is designed for everyone. Just describe your idea and our AI handles the technical implementation.' },
    { q: 'What can I build?', a: 'Websites, dashboards, task managers, onboarding portals, pricing pages, e-commerce stores, internal tools, and more. If you can describe it, we can build it.' },
    { q: 'What is design-to-code?', a: 'Upload a UI screenshot or mockup and CrucibAI generates structured, responsive code (HTML/CSS, React, Tailwind). Attach it from the Workspace composer or Dashboard prompt.' },
    { q: 'What are Quick, Plan, Agent, and Thinking modes?', a: 'Quick: single-shot generation, no plan step. Plan: we create a structured plan first, then build. Agent: full orchestration with our agent swarm and sub-agents (planning, frontend, backend, design, SEO, tests, deploy). Thinking: step-by-step reasoning before code. Swarm runs selected agents in parallel for speed.' },
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
    { q: 'Does CrucibAI support voice input?', a: 'Yes. Use the microphone in the Workspace or Dashboard composer; we transcribe and insert your words into the prompt.' },
    { q: 'What file types can I attach?', a: 'Images, PDFs, text/code files, ZIP (loaded into workspace), and audio/voice notes (transcribed into your prompt). Use the attach control in the Workspace composer.' },
    { q: 'How do token bundles work?', a: 'You buy a bundle (e.g. Starter 100K tokens). Each AI request consumes tokens; when you run low you can buy more. Tokens do not expire.' },
    { q: 'Is there an API for developers?', a: 'We offer API access for prompt to plan and prompt to code. See our roadmap and documentation for availability.' },
    { q: 'How do I get help or report a bug?', a: 'Use the Documentation and Support links in the footer. For bugs, include steps to reproduce and your environment (browser, OS).' },
    { q: 'Can I build mobile apps?', a: 'Currently we focus on web apps (React). Mobile and PWA support are on the roadmap.' },
    { q: 'What browsers are supported?', a: 'We recommend Chrome, Firefox, or Edge. Safari is supported; voice input may have limitations on some browsers.' },
    { q: 'How does CrucibAI compare to Kimi?', a: 'Kimi excels at long-context chat and research. CrucibAI is Inevitable AI for app creation: plan-first builds, a swarm of agents and sub-agents, design-to-code, and one workspace from idea to export. Use CrucibAI when you want inevitable outcomes — ship software, not just promises.' }
  ];
  const allFaqs = [...faqs, ...faqsExtra];

  const whereItems = [
    { title: 'Web app', desc: 'Use CrucibAI in your browser. Open the workspace (or home dashboard) to describe your idea, build, iterate, and export. No setup required.' },
    { title: 'API', desc: 'Integrate via API for prompt → plan and prompt → code. Billing by token usage.' },
    { title: 'Export & deploy', desc: 'Download your project as a ZIP or push to GitHub. Deploy to Vercel, Netlify, or any host. You own the code and can customize anything.' }
  ];

  const comparisonData = {
    crucibai: { buildWeb: true, buildMobile: true, runAutomations: true, sameAI: true, importCode: true, ideExtensions: true, realtimeMonitor: true, planBeforeBuild: true, approvalWorkflows: true, qualityScore: true, appStorePack: true, pricePer100: '$15' },
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
        <div className="max-w-6xl mx-auto px-6 py-5 flex items-center gap-6">
          <Logo variant="full" height={32} href="/" className="shrink-0" />
          <div className="hidden sm:flex flex-1 items-center justify-center gap-6 md:gap-8 min-w-0">
            <SolutionsNavDropdown />
            <Link to="/pricing" className="text-kimi-nav text-kimi-muted hover:text-kimi-text transition">Pricing</Link>
            <Link to="/our-projects" className="text-kimi-nav text-kimi-muted hover:text-kimi-text transition">Our Project</Link>
          </div>
          <div className="hidden sm:flex items-center gap-3 md:gap-4 ml-auto shrink-0">
            <button type="button" onClick={() => navigate('/app')} className="text-sm text-kimi-nav text-kimi-muted hover:text-kimi-text transition">Dashboard</button>
            {!user && (
              <Link to="/auth" className="text-sm text-kimi-nav text-kimi-muted hover:text-kimi-text transition">Log in</Link>
            )}
            <button type="button" onClick={() => navigate('/app/workspace')} className="px-4 py-2 bg-white text-gray-900 text-sm font-medium rounded-lg hover:bg-gray-100 transition">Get started</button>
          </div>
          <button className="sm:hidden text-kimi-text" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </nav>

      {/* Mobile Menu */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-40 bg-kimi-bg pt-20 px-6 pb-8 overflow-y-auto sm:hidden">
            <div className="flex flex-col gap-6 text-kimi-text min-h-min">
              <p className="text-xs font-semibold uppercase tracking-wider text-kimi-muted">Our solution — who it&apos;s for</p>
              <div className="flex flex-col gap-2 pl-2 border-l border-gray-200">
                {SOLUTION_LINKS.map((item) => (
                  <Link key={item.to} to={item.to} className="text-base text-kimi-muted hover:text-kimi-text" onClick={() => setMobileMenuOpen(false)}>{item.label}</Link>
                ))}
              </div>
              <p className="text-xs font-semibold uppercase tracking-wider text-kimi-muted">Use cases</p>
              <div className="flex flex-col gap-2 pl-2 border-l border-gray-200">
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

      {/* Hero */}
      <section className="pt-32 pb-20 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-sm text-kimi-muted mb-4">
            Agentic · Swarm of agents &amp; sub-agents · High success rate · Full transparency
          </motion.p>
          <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-kimi-hero font-bold tracking-tight text-kimi-text mb-6">
            Describe it now. Ship it today.
          </motion.h1>
          <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="text-lg text-kimi-muted mb-12 max-w-2xl mx-auto leading-relaxed">
            The only platform where the same AI that builds your app runs inside your automations. Web apps, mobile apps, and automations — one platform, one AI, no switching tools.
          </motion.p>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.15 }} className="flex flex-col sm:flex-row flex-wrap items-center justify-center gap-3">
            <button onClick={() => navigate('/app/workspace')} className="glass-kimi-btn px-6 py-3 text-gray-900 font-medium rounded-xl transition">
              Make It Inevitable
            </button>
            <Link to="/app/workspace" className="px-6 py-3 bg-gray-50 text-kimi-text font-medium rounded-xl border border-gray-200 hover:bg-gray-100 transition">Open Workspace</Link>
          </motion.div>
          {!user && (
            <p className="mt-4 text-sm text-kimi-muted">Sign in to save projects and sync across devices.</p>
          )}
        </div>

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
                Describe your app in plain language. Our swarm of agents and sub-agents plans, builds, tests, and deploys it. Watch every agent work in real time. Web apps, mobile apps, landing pages — production-ready code you own.
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
              <p className="text-sm text-kimi-muted">See exactly which agent in the swarm is running, what it&apos;s doing, and how many tokens it used. Nothing hidden.</p>
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
                <p className="text-sm text-kimi-muted">Our agent swarm runs in parallel. Frontend, backend, database, tests, security, deployment — each phase handled by dedicated agents and sub-agents. You watch the AgentMonitor. You see every step.</p>
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

      {/* Who it's for — anchor targets for header "Our solution" menu */}
      <section id="solutions" className="py-20 px-6 bg-kimi-bg-elevated/50">
        <div className="max-w-6xl mx-auto">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Our solution</span>
          <h2 className="text-kimi-section font-bold text-kimi-text mt-2 mb-4 text-center">Who it&apos;s for</h2>
          <p className="text-center text-kimi-muted max-w-2xl mx-auto mb-12 text-sm leading-relaxed">
            One platform for web, mobile, and automation. Plan-first builds, full transparency, production-ready code you own — no matter your title.
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            <article id="solution-everyone" className="scroll-mt-28 p-6 rounded-xl border border-gray-200 bg-kimi-bg hover:border-kimi-accent/30 transition">
              <h3 className="font-semibold text-kimi-text mb-2">Everyone &amp; non-builders</h3>
              <p className="text-sm text-kimi-muted mb-4">You don&apos;t need to write code. Describe what you want — landing pages, internal tools, and automations ship with AgentMonitor so you always see what&apos;s happening.</p>
              <button type="button" onClick={() => startBuild('Landing page and a weekly summary automation')} className="text-sm font-medium text-kimi-accent hover:text-kimi-text transition">→ Start from plain language</button>
            </article>
            <article id="solution-founders" className="scroll-mt-28 p-6 rounded-xl border border-gray-200 bg-kimi-bg hover:border-kimi-accent/30 transition">
              <h3 className="font-semibold text-kimi-text mb-2">Founders</h3>
              <p className="text-sm text-kimi-muted mb-4">Idea to deployed MVP without hiring a bench. Web, mobile Expo projects, and the same AI for follow-up automations — ship this week, iterate next week.</p>
              <button type="button" onClick={() => startBuild('MVP')} className="text-sm font-medium text-kimi-accent hover:text-kimi-text transition">→ Build your MVP</button>
            </article>
            <article id="solution-enterprise" className="scroll-mt-28 p-6 rounded-xl border border-gray-200 bg-kimi-bg hover:border-kimi-accent/30 transition">
              <h3 className="font-semibold text-kimi-text mb-2">Enterprise</h3>
              <p className="text-sm text-kimi-muted mb-4">Quality scores, phase retry, audit trails, and security scans on import. Procurement-friendly transparency — every agent and phase is visible before you ship.</p>
              <Link to="/enterprise" className="text-sm font-medium text-kimi-accent hover:text-kimi-text transition">→ Enterprise programs</Link>
            </article>
            <article id="solution-pm" className="scroll-mt-28 p-6 rounded-xl border border-gray-200 bg-kimi-bg hover:border-kimi-accent/30 transition">
              <h3 className="font-semibold text-kimi-text mb-2">Project &amp; product managers</h3>
              <p className="text-sm text-kimi-muted mb-4">Plan-first flow: approve structure before code. Monday describe, Tue–Wed build with parallel phases, Thursday automate, Friday export or deploy — one timeline your stakeholders can follow.</p>
              <button type="button" onClick={() => startBuild('Internal approval tool with dashboard')} className="text-sm font-medium text-kimi-accent hover:text-kimi-text transition">→ Prototype with approvals</button>
            </article>
            <article id="solution-designers" className="scroll-mt-28 p-6 rounded-xl border border-gray-200 bg-kimi-bg hover:border-kimi-accent/30 transition">
              <h3 className="font-semibold text-kimi-text mb-2">Designers</h3>
              <p className="text-sm text-kimi-muted mb-4">Design-to-code from screenshots or references. Hero, features, pricing, and responsive layouts wired into real components — not static mocks.</p>
              <button type="button" onClick={() => startBuild('Design system landing page from my screenshot')} className="text-sm font-medium text-kimi-accent hover:text-kimi-text transition">→ Turn visuals into UI</button>
            </article>
            <article id="solution-sales" className="scroll-mt-28 p-6 rounded-xl border border-gray-200 bg-kimi-bg hover:border-kimi-accent/30 transition">
              <h3 className="font-semibold text-kimi-text mb-2">Sales teams</h3>
              <p className="text-sm text-kimi-muted mb-4">Microsites, leave-behinds, and pricing pages in hours. Chain the same AI into webhook or digest automations for lead follow-up and pipeline updates.</p>
              <button type="button" onClick={() => startBuild('Sales one-pager and ROI calculator')} className="text-sm font-medium text-kimi-accent hover:text-kimi-text transition">→ Ship sales collateral</button>
            </article>
            <article id="solution-marketers" className="scroll-mt-28 p-6 rounded-xl border border-gray-200 bg-kimi-bg hover:border-kimi-accent/30 transition">
              <h3 className="font-semibold text-kimi-text mb-2">Marketers &amp; growth</h3>
              <p className="text-sm text-kimi-muted mb-4">Landing pages, blogs, funnels, and SEO-ready sections. Automate lead digests, content refresh, and campaign hooks with the same platform — no hand-off to engineering for every launch.</p>
              <button type="button" onClick={() => startBuild('Landing page')} className="text-sm font-medium text-kimi-accent hover:text-kimi-text transition">→ Build marketing stacks</button>
            </article>
            <article id="solution-ops" className="scroll-mt-28 p-6 rounded-xl border border-gray-200 bg-kimi-bg hover:border-kimi-accent/30 transition">
              <h3 className="font-semibold text-kimi-text mb-2">Ops &amp; RevOps</h3>
              <p className="text-sm text-kimi-muted mb-4">Internal admin tables, CRUD, webhooks, and scheduled agents. Daily digests, SLA trackers, and handoffs your team can run without a separate automation-only product.</p>
              <button type="button" onClick={() => startBuild('Operations dashboard with alerts')} className="text-sm font-medium text-kimi-accent hover:text-kimi-text transition">→ Automate operations</button>
            </article>
            <article id="solution-developers" className="scroll-mt-28 p-6 rounded-xl border border-gray-200 bg-kimi-bg hover:border-kimi-accent/30 transition">
              <h3 className="font-semibold text-kimi-text mb-2">Developers</h3>
              <p className="text-sm text-kimi-muted mb-4">IDE extensions, import via paste / ZIP / Git, Braintree injection, README and API docs. The swarm handles the heavy lifting; you keep full code ownership.</p>
              <Link to="/learn" className="text-sm font-medium text-kimi-accent hover:text-kimi-text transition">→ Docs &amp; API</Link>
            </article>
          </div>
        </div>
      </section>

      {/* Bring Your Code */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Already have code?</span>
          <h2 className="text-kimi-section font-bold text-kimi-text mt-2 mb-6 text-center">Bring it. We&apos;ll keep building.</h2>
          <p className="text-kimi-muted text-center mb-10 max-w-2xl mx-auto">
            Paste your code. Upload a ZIP. Drop a Git URL. We stand up your existing project in the workspace, run a security scan and accessibility check, and you keep building — with the full agent swarm behind you.
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
              <p className="text-sm text-kimi-muted">Your existing codebase, our agent swarm. Ask for features, fixes, or a full rebuild. You own the code throughout.</p>
            </div>
          </div>
          <div className="mt-10 text-center">
            <button onClick={() => navigate('/app/workspace')} className="px-6 py-3 bg-white text-gray-900 font-medium rounded-lg hover:bg-gray-100 transition">
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
          <div className="grid md:grid-cols-3 gap-6 mb-14">
            <article id="use-case-poc" className="scroll-mt-28 p-6 rounded-xl border border-gray-200 bg-kimi-bg">
              <h3 className="text-lg font-semibold text-kimi-text mb-2">Proof of concept</h3>
              <p className="text-sm text-kimi-muted mb-4">Validate an idea in days: scoped UI, API sketch, and demo data. Approve the plan, watch the swarm build, export or deploy when stakeholders say go.</p>
              <button type="button" onClick={() => startBuild('Proof of concept demo app')} className="text-sm font-medium text-kimi-accent hover:text-kimi-text transition">→ Run a POC</button>
            </article>
            <article id="use-case-full-app" className="scroll-mt-28 p-6 rounded-xl border border-gray-200 bg-kimi-bg">
              <h3 className="text-lg font-semibold text-kimi-text mb-2">Full apps &amp; SaaS</h3>
              <p className="text-sm text-kimi-muted mb-4">Auth, database, Braintree, dashboards, and mobile-ready Expo paths. Same pipeline from landing to production — quality score and phase retry included.</p>
              <button type="button" onClick={() => startBuild('Full-stack SaaS with auth and Braintree')} className="text-sm font-medium text-kimi-accent hover:text-kimi-text transition">→ Build a full product</button>
            </article>
            <article id="use-case-automation" className="scroll-mt-28 p-6 rounded-xl border border-gray-200 bg-kimi-bg">
              <h3 className="text-lg font-semibold text-kimi-text mb-2">Automation &amp; agents</h3>
              <p className="text-sm text-kimi-muted mb-4">Schedules, webhooks, and run_agent steps that call the same AI that built your app. Daily digests, lead follow-up, and content pipelines without a second tool.</p>
              <button type="button" onClick={() => startBuild('Automation: daily digest to Slack')} className="text-sm font-medium text-kimi-accent hover:text-kimi-text transition">→ Create an agent</button>
            </article>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { title: 'Dashboards', desc: 'Reporting, analytics, and data views with charts and filters. Real-time data, admin controls, export to PDF and Excel.', cta: 'Build a dashboard' },
              { title: 'Landing Pages', desc: 'Hero, features, waitlist, and pricing sections. Design-to-code from a screenshot. Live in 30 minutes.', cta: 'Start a landing page' },
              { title: 'Mobile Apps', desc: 'iOS and Android with Expo. Production-ready. App Store submission pack with step-by-step guides for App Store and Google Play.', cta: 'Build a mobile app' },
              { title: 'E‑Commerce & Checkout', desc: 'Product catalog, cart, checkout, payments. Inject Braintree in one command. Full automation from product list to order confirmation.', cta: 'Build a store' },
              { title: 'Automations & Agents', desc: 'Daily digest. Lead follow-up. Content pipeline. Webhook handlers. Describe it — we create it. Schedule or trigger by webhook.', cta: 'Create an agent' },
              { title: 'Internal Tools', desc: 'Admin tables, forms, approval workflows, CRUD. Step chaining between actions. Agentic: ship in hours, not months.', cta: 'Build an internal tool' },
              { title: 'SaaS Products', desc: 'Full-stack SaaS with auth, Braintree subscriptions, user dashboard, and admin panel. Import the Auth + SaaS pattern and build from there.', cta: 'Start a SaaS' },
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
              { step: '3', title: 'Swarm builds in parallel', desc: 'Planning, frontend, backend, database, styling, testing, security, deployment — each phase handled by dedicated agents and sub-agents running in parallel. Watch them work in AgentMonitor.' },
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
          <p className="text-kimi-muted mb-8">Real apps from our agent swarm. Inevitable outcomes — fork any example to open it in your workspace.</p>
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
                  onClick={() => navigate('/app/examples')}
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
                      onClick={() => navigate('/app')}
                      className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-gray-50 text-kimi-text hover:bg-gray-100 transition text-sm"
                    >
                      <ArrowRight className="w-4 h-4" /> Open workspace
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
          <p className="text-kimi-muted mb-8">We dogfood our own platform. Every feature we ship is built and tested with the same agent swarm our customers use.</p>
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
              <p className="text-sm text-kimi-muted mb-3">Structured plans, verifiable swarm agents, quality score, and full audit trail. You see every step and every artifact.</p>
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
          <h2 className="text-3xl md:text-4xl font-bold text-kimi-text mb-4">Your idea is inevitable.</h2>
          <p className="text-kimi-muted mb-8">Describe what you want to build now. Ship it today.</p>
          <div className="flex flex-wrap justify-center gap-4">
            <button onClick={() => navigate('/app/workspace')} className="px-6 py-3 bg-white text-gray-900 font-medium rounded-lg hover:bg-gray-100 transition border border-black/10">
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

export default OurProjectsPage;

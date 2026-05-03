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
    const publicProjectPaths = ['/our-projects', '/projects', '/project'];
    if (!id || !publicProjectPaths.includes(location.pathname)) return undefined;
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
    { q: 'What is CrucibAI?', a: 'CrucibAI is Inevitable AI — a plan-first build workspace for proof-gated web apps, Expo mobile artifacts, backend/API projects, and automations. Public claims map to evidence: implemented, tested, partially implemented, or not claimable.' },
    { q: 'Is CrucibAI free to use?', a: 'Yes. We offer a free tier with 100 credits. Paid plans are monthly (Builder, Pro, Scale, Teams) with more credits per month. Need more? Buy credits in bulk (500–20,000 at $0.05/credit, same rate as plans).' },
    { q: 'Do I need coding experience?', a: 'No. Our platform is designed for everyone. Just describe your idea and our AI handles the technical implementation.' },
    { q: 'What can I build?', a: 'Websites, dashboards, task managers, onboarding portals, pricing pages, internal tools, backend/API projects, automation workflows, and Expo mobile starters. Completion depends on passing the validator for that build profile.' },
    { q: 'What is design-to-code?', a: 'Upload a UI screenshot or mockup and CrucibAI generates structured, responsive code (HTML/CSS, React, Tailwind). Attach it from the Workspace composer or Dashboard prompt.' },
    { q: 'What are Quick, Plan, Agent, and Thinking modes?', a: 'Quick: single-shot generation, no plan step. Plan: we create a structured plan first, then build. Agent: orchestration across planning, frontend, backend, design, tests, security, and deploy-readiness phases. Thinking: step-by-step reasoning before code. Agent counts and per-agent proof are shown from runtime data, not marketing numbers.' },
    { q: 'How do I make changes?', a: 'Just ask in the chat. Say "make it dark mode", "add a sidebar", or "change the colors" and we update the code instantly.' },
    { q: 'How are apps deployed?', a: 'You export your code as a ZIP or push to GitHub. Deployable web projects include build scripts and guidance. One-click deployment is only promised where the configured provider target is available and the validator passes.' },
    { q: 'Is my data secure?', a: 'Yes. We use industry-standard practices. Your API keys stay in your environment; we don’t store them. See our Privacy and Terms for details.' },
    { q: 'Do I own what I create?', a: 'Yes. All applications and code you generate belong to you. Use, modify, or sell them however you like.' },
    { q: 'What are the limitations?', a: 'Complex multi-page apps may need multiple iterations. Very large codebases are subject to model context limits. Offline use is not supported. We recommend verifying critical logic and running your own tests.' },
    { q: 'What’s next for CrucibAI?', a: 'We’re expanding API access for developers, adding more structured outputs (README, API docs, FAQ schema), and improving Swarm and Thinking modes. See our roadmap in the footer.' },
    { q: 'Enterprise & compliance?', a: "We're working toward SOC 2 and enterprise compliance controls. For Enterprise or custom plans, contact sales@crucibai.com for the current evidence and deployment options." }
  ];

  const faqsExtra = [
    { q: 'Can I use my own API keys?', a: 'Yes. In Settings you can add your preferred AI provider API key. CrucibAI will use your key for AI requests; token usage is billed by the provider according to their terms.' },
    { q: 'What stacks and frameworks are supported?', a: 'We focus on React and Tailwind for web apps. The workspace uses Sandpack for instant preview. You can export and adapt code for other frameworks.' },
    { q: 'How does plan-first work?', a: 'For larger prompts we first call a planning agent that returns a structured plan (features, components, design notes) and optional suggestions. You see the plan, then we generate code. This reduces backtracking and improves quality.' },
    { q: 'What is Swarm mode?', a: "Swarm (Beta) runs selected agents in parallel instead of sequentially, so multi-step builds can complete faster. It's available on paid plans." },
    { q: 'Can I collaborate with my team?', a: 'You can share exported code or push to a shared GitHub repo. Team and org features are on our roadmap.' },
    { q: 'Does CrucibAI support voice input?', a: 'Yes. Use the microphone in the Workspace or Dashboard composer; we transcribe and insert your words into the prompt.' },
    { q: 'What file types can I attach?', a: 'Images, PDFs, text/code files, ZIP (loaded into workspace), and audio/voice notes (transcribed into your prompt). Use the attach control in the Workspace composer.' },
    { q: 'How do credit bundles work?', a: 'You buy a monthly credit plan or top up in bulk. Each AI workflow consumes credits based on scope, validation depth, and repair loops. Use Credit Center to track usage.' },
    { q: 'Is there an API for developers?', a: 'We offer API access for prompt to plan and prompt to code. See our roadmap and documentation for availability.' },
    { q: 'How do I get help or report a bug?', a: 'Use the Documentation and Support links in the footer. For bugs, include steps to reproduce and your environment (browser, OS).' },
    { q: 'Can I build mobile apps?', a: 'Yes, through an Expo/React Native track that produces expo-mobile/ source, app.json, eas.json, screens, scripts, and mobile integrity proof. App Store and Google Play submission still require your developer credentials, signing, EAS build, and store metadata validation.' },
    { q: 'What browsers are supported?', a: 'We recommend Chrome, Firefox, or Edge. Safari is supported; voice input may have limitations on some browsers.' },
    { q: 'How does CrucibAI compare to Kimi?', a: 'Kimi excels at long-context chat and research. CrucibAI focuses on app creation: plan-first builds, design-to-code, validator-gated proof, and one workspace from idea to export.' }
  ];
  const allFaqs = [...faqs, ...faqsExtra];

  const whereItems = [
    { title: 'Web app', desc: 'Use CrucibAI in your browser. Open the workspace (or home dashboard) to describe your idea, build, iterate, and export. No setup required.' },
    { title: 'API', desc: 'Integrate via API for prompt → plan and prompt → code. Billing by token usage.' },
    { title: 'Export & deploy', desc: 'Download your project as a ZIP or push to GitHub. Deployable projects include build scripts and guidance; provider deploys are configuration-dependent. You own the code and can customize anything.' }
  ];

  const comparisonData = {
    crucibai: { buildWeb: true, buildMobile: 'Expo artifacts', runAutomations: 'Guarded bridge', sameAI: 'run_agent', importCode: 'ZIP + BIV', ideExtensions: false, realtimeMonitor: true, planBeforeBuild: true, approvalWorkflows: true, qualityScore: 'BIV score', appStorePack: false, pricePer100: '$5' },
    lovable: { buildWeb: true, buildMobile: false, runAutomations: false, sameAI: false, importCode: false, ideExtensions: false, realtimeMonitor: false, planBeforeBuild: true, approvalWorkflows: false, qualityScore: false, appStorePack: false, pricePer100: '$25' },
    bolt: { buildWeb: true, buildMobile: false, runAutomations: false, sameAI: false, importCode: false, ideExtensions: false, realtimeMonitor: false, planBeforeBuild: true, approvalWorkflows: false, qualityScore: false, appStorePack: false, pricePer100: '~$20' },
    n8n: { buildWeb: false, buildMobile: false, runAutomations: true, sameAI: false, importCode: false, ideExtensions: false, realtimeMonitor: false, planBeforeBuild: false, approvalWorkflows: true, qualityScore: false, appStorePack: false, pricePer100: 'N/A' },
    cursor: { buildWeb: false, buildMobile: false, runAutomations: false, sameAI: false, importCode: true, ideExtensions: true, realtimeMonitor: false, planBeforeBuild: false, approvalWorkflows: false, qualityScore: false, appStorePack: false, pricePer100: '$20' },
    flutterflow: { buildWeb: false, buildMobile: true, runAutomations: false, sameAI: false, importCode: false, ideExtensions: false, realtimeMonitor: false, planBeforeBuild: false, approvalWorkflows: false, qualityScore: false, appStorePack: true, pricePer100: '$25' }
  };
  const comparisonLabels = [
    { key: 'buildWeb', label: 'Build web apps' },
    { key: 'buildMobile', label: 'Expo mobile artifacts' },
    { key: 'runAutomations', label: 'Run automations' },
    { key: 'sameAI', label: 'Same AI for apps + automations' },
    { key: 'importCode', label: 'Import doctor / existing code' },
    { key: 'ideExtensions', label: 'IDE extensions' },
    { key: 'realtimeMonitor', label: 'Real-time agent monitor' },
    { key: 'planBeforeBuild', label: 'Plan shown before build' },
    { key: 'approvalWorkflows', label: 'Approval workflows' },
    { key: 'qualityScore', label: 'Build Integrity score' },
    { key: 'appStorePack', label: 'Store submission automation' },
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
            Plan-first · BIV-tested · Proof artifacts · Transparent logs
          </motion.p>
          <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-kimi-hero font-bold tracking-tight text-kimi-text mb-6">
            Describe it now. Build with proof.
          </motion.h1>
          <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="text-lg text-kimi-muted mb-12 max-w-2xl mx-auto leading-relaxed">
            The same AI path that builds your app can also run inside gated automations. Web apps, Expo mobile starters, and automations — one platform, one proof-gated handoff.
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
                Describe your app in plain language. Planning, generation, testing, security, and deploy-readiness phases produce artifacts that the validator checks. Web apps, dashboards, backend/API projects, landing pages, and Expo mobile starters — code you own, with proof attached.
              </p>
            </div>
            <div className="p-6 rounded-2xl border border-gray-200 bg-kimi-bg-card">
              <h3 className="text-xl font-semibold text-kimi-accent mb-3">Automate</h3>
              <p className="text-sm text-kimi-muted leading-relaxed">
                Automations can call the build system through the guarded run_agent bridge. Schedules, webhooks, and chained steps are configuration-dependent and must pass their own validator checks.
              </p>
            </div>
          </div>
          <p className="text-center text-sm font-medium text-kimi-text mb-2">run_agent — the guarded bridge between builds and automations</p>
          <p className="text-center text-sm text-kimi-muted">
            N8N and Zapier automate. Lovable and Bolt build apps. CrucibAI connects those motions through one proof-gated workspace.
          </p>
        </div>
      </section>

      {/* Watch It Work — AgentMonitor */}
      <section className="py-20 px-6 bg-kimi-bg-elevated/50">
        <div className="max-w-4xl mx-auto">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Evidence</span>
          <h2 className="text-kimi-section font-bold text-kimi-text mt-2 mb-6 text-center">Claims map to artifacts.</h2>
          <p className="text-kimi-muted text-center mb-10 max-w-2xl mx-auto">
            CrucibAI exposes job events, proof files, validator results, build output, and available agent telemetry. Complete per-agent cost accounting is still not claimable until the evidence matrix says it is.
          </p>
          <div className="grid sm:grid-cols-3 gap-6 mb-10">
            <div className="p-4 rounded-xl border border-gray-200 bg-kimi-bg">
              <h4 className="font-semibold text-kimi-text mb-2">Agent telemetry</h4>
              <p className="text-sm text-kimi-muted">See available phase and agent events, logs, and token fields. Exact public agent counts are only shown when runtime enumeration proves them.</p>
            </div>
            <div className="p-4 rounded-xl border border-gray-200 bg-kimi-bg">
              <h4 className="font-semibold text-kimi-text mb-2">Build Integrity score</h4>
              <p className="text-sm text-kimi-muted">The tested BIV score is 0-100 across architecture, design, completeness, runtime validity, integration, and deployability.</p>
            </div>
            <div className="p-4 rounded-xl border border-gray-200 bg-kimi-bg">
              <h4 className="font-semibold text-kimi-text mb-2">Bounded repair</h4>
              <p className="text-sm text-kimi-muted">Final BIV failure can trigger a bounded repair attempt and rerun. Full DAG node-level retry is still listed as partial.</p>
            </div>
          </div>
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-8 flex items-center justify-center min-h-[280px]">
            <p className="text-kimi-muted text-center text-sm">AgentMonitor — available job events, phase progress, token fields, and Build Integrity score. <br /><span className="text-xs">Screenshot placeholder — add image when ready.</span></p>
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
                <p className="text-sm text-kimi-muted">The build DAG runs by phase and records available job events, logs, proof artifacts, and Build Integrity score. AgentMonitor shows the telemetry the runtime actually produces.</p>
              </div>
            </div>
            <div className="flex gap-4">
              <span className="text-kimi-accent font-mono shrink-0">Thursday</span>
              <div>
                <h4 className="font-semibold text-kimi-text mb-1">Automate</h4>
                <p className="text-sm text-kimi-muted">Automations use the guarded run_agent bridge when configured. Schedules, webhooks, and chained steps are proof-gated by their workflow profile.</p>
              </div>
            </div>
            <div className="flex gap-4">
              <span className="text-kimi-accent font-mono shrink-0">Friday</span>
              <div>
                <h4 className="font-semibold text-kimi-text mb-1">Ship</h4>
                <p className="text-sm text-kimi-muted">Export to ZIP. Push to GitHub. Deploy through configured providers only after proof gates pass. You own the generated stack and proof bundle.</p>
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
            One platform for web, Expo mobile artifacts, and automation. Plan-first builds, validator-gated code, and evidence you own — no matter your title.
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            <article id="solution-everyone" className="scroll-mt-28 p-6 rounded-xl border border-gray-200 bg-kimi-bg hover:border-kimi-accent/30 transition">
              <h3 className="font-semibold text-kimi-text mb-2">Everyone &amp; non-builders</h3>
              <p className="text-sm text-kimi-muted mb-4">You don&apos;t need to write code. Describe what you want — landing pages, internal tools, and automations produce validator-gated artifacts with visible job events.</p>
              <button type="button" onClick={() => startBuild('Landing page and a weekly summary automation')} className="text-sm font-medium text-kimi-accent hover:text-kimi-text transition">→ Start from plain language</button>
            </article>
            <article id="solution-founders" className="scroll-mt-28 p-6 rounded-xl border border-gray-200 bg-kimi-bg hover:border-kimi-accent/30 transition">
              <h3 className="font-semibold text-kimi-text mb-2">Founders</h3>
              <p className="text-sm text-kimi-muted mb-4">Idea to exportable MVP artifacts without hiring a bench. Web, Expo mobile projects, and guarded follow-up automations can move through the same workspace.</p>
              <button type="button" onClick={() => startBuild('MVP')} className="text-sm font-medium text-kimi-accent hover:text-kimi-text transition">→ Build your MVP</button>
            </article>
            <article id="solution-enterprise" className="scroll-mt-28 p-6 rounded-xl border border-gray-200 bg-kimi-bg hover:border-kimi-accent/30 transition">
              <h3 className="font-semibold text-kimi-text mb-2">Enterprise</h3>
              <p className="text-sm text-kimi-muted mb-4">Build Integrity scores, bounded repair, proof artifacts, and baseline import/security checks. Procurement-friendly transparency is tied to evidence, not unsupported claims.</p>
              <Link to="/enterprise" className="text-sm font-medium text-kimi-accent hover:text-kimi-text transition">→ Enterprise programs</Link>
            </article>
            <article id="solution-pm" className="scroll-mt-28 p-6 rounded-xl border border-gray-200 bg-kimi-bg hover:border-kimi-accent/30 transition">
              <h3 className="font-semibold text-kimi-text mb-2">Project &amp; product managers</h3>
              <p className="text-sm text-kimi-muted mb-4">Plan-first flow: approve structure before code. Build phases, automation steps, export, and provider deployment are tracked against proof gates your stakeholders can review.</p>
              <button type="button" onClick={() => startBuild('Internal approval tool with dashboard')} className="text-sm font-medium text-kimi-accent hover:text-kimi-text transition">→ Prototype with approvals</button>
            </article>
            <article id="solution-designers" className="scroll-mt-28 p-6 rounded-xl border border-gray-200 bg-kimi-bg hover:border-kimi-accent/30 transition">
              <h3 className="font-semibold text-kimi-text mb-2">Designers</h3>
              <p className="text-sm text-kimi-muted mb-4">Design-to-code from screenshots or references. Hero, features, pricing, and responsive layouts are generated as validator-gated UI components.</p>
              <button type="button" onClick={() => startBuild('Design system landing page from my screenshot')} className="text-sm font-medium text-kimi-accent hover:text-kimi-text transition">→ Turn visuals into UI</button>
            </article>
            <article id="solution-sales" className="scroll-mt-28 p-6 rounded-xl border border-gray-200 bg-kimi-bg hover:border-kimi-accent/30 transition">
              <h3 className="font-semibold text-kimi-text mb-2">Sales teams</h3>
              <p className="text-sm text-kimi-muted mb-4">Microsites, leave-behinds, and pricing pages as proof-gated artifacts. Chain run_agent into configured webhook or digest automations for follow-up workflows.</p>
              <button type="button" onClick={() => startBuild('Sales one-pager and ROI calculator')} className="text-sm font-medium text-kimi-accent hover:text-kimi-text transition">→ Ship sales collateral</button>
            </article>
            <article id="solution-marketers" className="scroll-mt-28 p-6 rounded-xl border border-gray-200 bg-kimi-bg hover:border-kimi-accent/30 transition">
              <h3 className="font-semibold text-kimi-text mb-2">Marketers &amp; growth</h3>
              <p className="text-sm text-kimi-muted mb-4">Landing pages, blogs, funnels, and SEO-ready sections. Configure lead digests, content refresh, and campaign hooks through the same proof-gated workflow.</p>
              <button type="button" onClick={() => startBuild('Landing page')} className="text-sm font-medium text-kimi-accent hover:text-kimi-text transition">→ Build marketing stacks</button>
            </article>
            <article id="solution-ops" className="scroll-mt-28 p-6 rounded-xl border border-gray-200 bg-kimi-bg hover:border-kimi-accent/30 transition">
              <h3 className="font-semibold text-kimi-text mb-2">Ops &amp; RevOps</h3>
              <p className="text-sm text-kimi-muted mb-4">Internal admin tables, CRUD, webhooks, and scheduled agents. Daily digests, SLA trackers, and handoffs are generated when their workflow requirements are configured and validated.</p>
              <button type="button" onClick={() => startBuild('Operations dashboard with alerts')} className="text-sm font-medium text-kimi-accent hover:text-kimi-text transition">→ Automate operations</button>
            </article>
            <article id="solution-developers" className="scroll-mt-28 p-6 rounded-xl border border-gray-200 bg-kimi-bg hover:border-kimi-accent/30 transition">
              <h3 className="font-semibold text-kimi-text mb-2">Developers</h3>
              <p className="text-sm text-kimi-muted mb-4">ZIP/workspace imports are checked by Import Doctor and BIV. Git/paste continuation, dependency repair, preview-after-import repair, and IDE extensions remain conditional until end-to-end proof is added.</p>
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
            Upload a ZIP or validate a reconstructed workspace. Import Doctor checks package manager, framework, entrypoints, ZIP safety, and BIV result. Git/paste continuation, dependency repair, preview-after-import repair, and accessibility proof are still listed as partial or not claimable.
          </p>
          <div className="grid sm:grid-cols-3 gap-6">
            <div className="p-4 rounded-xl border border-gray-200 bg-kimi-bg">
              <h4 className="font-semibold text-kimi-text mb-2">ZIP and workspace import</h4>
              <p className="text-sm text-kimi-muted">ZIP safety and reconstructed workspace facts are validated before the code enters the normal build pipeline.</p>
            </div>
            <div className="p-4 rounded-xl border border-gray-200 bg-kimi-bg">
              <h4 className="font-semibold text-kimi-text mb-2">Baseline security checks</h4>
              <p className="text-sm text-kimi-muted">BIV blocks likely client-exposed secrets. Full CORS/auth/tenancy import security proof remains part of the security doctor roadmap.</p>
            </div>
            <div className="p-4 rounded-xl border border-gray-200 bg-kimi-bg">
              <h4 className="font-semibold text-kimi-text mb-2">Keep building with AI</h4>
              <p className="text-sm text-kimi-muted">Your existing codebase can continue through the same proof-gated build flow once the import doctor and BIV checks pass.</p>
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
              <p className="text-sm text-kimi-muted mb-4">Auth, database, PayPal, dashboards, and an Expo mobile track. Same pipeline from landing to production — quality score and phase retry included.</p>
              <button type="button" onClick={() => startBuild('Full-stack SaaS with auth and PayPal')} className="text-sm font-medium text-kimi-accent hover:text-kimi-text transition">→ Build a full product</button>
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
              { title: 'Mobile Apps (Expo)', desc: 'Generate an Expo/React Native starter with app metadata, EAS config, screens, and scripts. The Build Integrity Validator must prove mobile entry points and packaging artifacts before the build is complete.', cta: 'Plan a mobile build' },
              { title: 'E‑Commerce & Checkout', desc: 'Product catalog, cart, checkout, payments. Inject PayPal in one command. Full automation from product list to order confirmation.', cta: 'Build a store' },
              { title: 'Automations & Agents', desc: 'Daily digest. Lead follow-up. Content pipeline. Webhook handlers. Describe it — we create it. Schedule or trigger by webhook.', cta: 'Create an agent' },
              { title: 'Internal Tools', desc: 'Admin tables, forms, approval workflows, CRUD. Step chaining between actions. Agentic: ship in hours, not months.', cta: 'Build an internal tool' },
              { title: 'SaaS Products', desc: 'Full-stack SaaS with auth, PayPal subscriptions, user dashboard, and admin panel. Import the Auth + SaaS pattern and build from there.', cta: 'Start a SaaS' },
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
          <h2 className="text-kimi-section font-bold text-kimi-text mt-2 mb-6 text-center">Plan-first. Agent-powered. Evidence-backed.</h2>
          <div className="grid md:grid-cols-2 gap-8">
            {[
              { step: '1', title: 'Describe', desc: 'Tell us what you want in plain language. Attach a screenshot for design-to-code. ZIP and reconstructed workspaces are checked by Import Doctor; Git and paste continuation remain conditional until full proof is added.' },
              { step: '2', title: 'Plan & approve', desc: 'For every build, we generate a structured plan first — features, components, design decisions, known risks, and proof gates. You approve before code is produced.' },
              { step: '3', title: 'Swarm builds with evidence', desc: 'Planning, frontend, backend, styling, testing, security, and deployment phases run where the build profile requires them. AgentMonitor shows available runtime telemetry and proof artifacts.' },
              { step: '4', title: 'Ship what you own', desc: 'Export to ZIP or push to GitHub after proof gates pass. Provider deploys are configuration-dependent, and failed proof returns issues and retry targets instead of a false success.' }
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
            {liveExamples.length > 0 ? liveExamples.map((ex, index) => {
              const exampleName = typeof ex?.name === 'string' && ex.name.trim()
                ? ex.name.trim()
                : `Example ${index + 1}`;
              const examplePrompt = typeof ex?.prompt === 'string' && ex.prompt.trim()
                ? ex.prompt.trim()
                : 'Generated app example';
              return (
              <div key={ex?.id || ex?.slug || exampleName} className="p-5 rounded-xl border border-gray-200 bg-kimi-bg hover:border-gray-200 transition">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 rounded-lg bg-gray-50">
                    <FileCode className="w-5 h-5 text-kimi-accent" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-kimi-text">{exampleName.replace(/-/g, ' ')}</h3>
                    <p className="text-xs text-kimi-muted line-clamp-2">{examplePrompt.slice(0, 70)}…</p>
                  </div>
                </div>
                {ex?.quality_metrics?.overall_score != null && (
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
              );
            }) : (
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
          <p className="text-kimi-muted mb-8">Use CrucibAI in the browser, export your code, and deploy through configured provider targets or your own host.</p>
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
          <p className="text-kimi-muted mb-8">We dogfood our own platform and publish proof for the claims the current release can support.</p>
          <div className="flex flex-wrap justify-center gap-8 text-sm">
            <div className="flex items-center gap-2">
              <Check className="w-5 h-5 text-kimi-accent shrink-0" />
              <span className="text-kimi-text">Validator-tested builds</span>
            </div>
            <div className="flex items-center gap-2">
              <Check className="w-5 h-5 text-kimi-accent shrink-0" />
              <span className="text-kimi-text">Client-secret scan in BIV</span>
            </div>
            <div className="flex items-center gap-2">
              <Check className="w-5 h-5 text-kimi-accent shrink-0" />
              <span className="text-kimi-text">Privacy and compliance controls in progress</span>
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
              <p className="text-sm text-kimi-muted mb-3">Structured plans, validator results, Build Integrity score, and proof artifacts. You see what was produced and what passed.</p>
              <p className="text-xs text-kimi-accent font-medium">CrucibAI → structure, visibility, verifiable steps</p>
            </div>
            <div className="p-6 rounded-xl border border-gray-200 bg-kimi-bg hover:border-kimi-accent/30 transition">
              <h3 className="text-lg font-semibold text-kimi-text mb-3">Faster</h3>
              <p className="text-sm text-kimi-muted mb-3">Parallel DAG execution is supported where the runtime selects it. Final BIV failures can trigger bounded repair and rerun.</p>
              <p className="text-xs text-kimi-accent font-medium">CrucibAI → proof-gated phases, bounded repair</p>
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
          <p className="text-kimi-muted mb-8">Startups, internal tools, agencies, and educators use CrucibAI to go from idea to exportable, proof-gated artifacts faster.</p>
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
          <p className="text-kimi-muted mb-8">Describe what you want to build now. Export only after the proof gates pass.</p>
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

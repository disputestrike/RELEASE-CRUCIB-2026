import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '../App';
import PublicNav from '../components/PublicNav';
import PublicFooter from '../components/PublicFooter';
import { Code2, Zap, Bot, Shield, Download, Keyboard } from 'lucide-react';

const outcomeSections = [
  {
    icon: Code2,
    title: 'Build',
    desc: 'Describe what you want in plain language. Web apps, mobile apps, dashboards, SaaS — we build them all. Plan-first flow shows the structure before we code. Attach a screenshot for design-to-code. Import existing code via paste, ZIP, or Git URL. Voice input supported. Iterate in chat: "add dark mode", "make it responsive" — we update the code instantly.',
  },
  {
    icon: Bot,
    title: 'Agents & Automation',
    desc: 'The same AI that builds your app runs inside your automations. Describe an automation in plain language — we create the agent (schedule or webhook, with steps). Use run_agent to call our build swarm from your automation. Pre-built templates: daily digest, lead finder, inbox summarizer, status checker. Prompt-to-automation: describe it, we build it.',
  },
  {
    icon: Zap,
    title: '120-Agent Swarm',
    desc: 'Planning, frontend, backend, database, styling, testing, security, deployment — each phase handled by dedicated agents. They run in parallel for speed. AgentMonitor shows per-phase, per-agent status, token usage, and logs. Quality score per build. Phase retry when needed. Full transparency: every step, every artifact.',
  },
  {
    icon: Download,
    title: 'Deploy & Export',
    desc: 'Export to ZIP or push to GitHub. Deploy to Vercel or Netlify in one click. For mobile: Expo (React Native) projects plus App Store and Google Play submission pack. You own all the code. Your automations are running. You\'re live.',
  },
  {
    icon: Shield,
    title: 'Security & Quality',
    desc: 'Security scan and accessibility check on every project. Quality score (0–100) per build. 188 tests passing. Security-first. GDPR and CCPA compliant. We build CrucibAI using CrucibAI — we dogfood our own platform.',
  },
  {
    icon: Keyboard,
    title: 'Power Users',
    desc: 'IDE extensions for VS Code, JetBrains, Sublime, and Vim. Command palette (Ctrl+K), shortcuts, and quick actions. Templates, patterns, and prompt library for fast starts. API access for prompt-to-plan and prompt-to-code. Token usage tracking and add-ons when you need more.',
  },
];

export default function Features() {
  const navigate = useNavigate();
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-kimi-bg text-kimi-text grid-pattern-kimi">
      <PublicNav />
      <div className="max-w-5xl mx-auto px-6 py-16">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-12">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Benefits</span>
          <h1 className="text-kimi-section font-bold text-kimi-text mt-2 mb-4">Why your outcome is inevitable</h1>
          <p className="text-kimi-muted max-w-xl mx-auto">The same AI that builds your app runs inside your automations. Web, mobile, agents — one platform. 120-agent swarm, 99.2% success, full transparency. Not promises — measured.</p>
        </motion.div>
        {/* Proof strip */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }} className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 py-4 px-4 rounded-xl border border-white/10 bg-kimi-bg-card mb-16">
          <span className="flex items-center gap-2 text-sm text-kimi-muted">
            <span className="w-2 h-2 rounded-full bg-kimi-accent animate-pulse" /> 120-agent swarm
          </span>
          <span className="text-sm text-kimi-muted">99.2% success</span>
          <span className="text-sm text-kimi-muted">Full transparency</span>
          <span className="text-sm text-kimi-muted">Web + mobile + agents</span>
          <span className="text-sm font-medium text-kimi-text">Not promises. Measured.</span>
        </motion.div>
        <div className="space-y-8">
          {outcomeSections.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="p-8 rounded-2xl border border-white/10 bg-kimi-bg-card hover:border-white/20 transition"
            >
              <div className="flex items-start gap-6">
                <div className="p-3 rounded-xl bg-white/5 shrink-0">
                  <f.icon className="w-8 h-8 text-kimi-accent" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-kimi-text mb-3">{f.title}</h2>
                  <p className="text-sm text-kimi-muted leading-relaxed">{f.desc}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }} className="mt-20 text-center">
          <p className="text-kimi-muted mb-6">Make your outcome inevitable. No credit card required.</p>
          <button onClick={() => navigate(user ? '/app' : '/auth?mode=register')} className="px-6 py-3 bg-white text-gray-900 font-medium rounded-lg hover:bg-gray-200 transition">
            {user ? 'Go to workspace' : 'Get started free'}
          </button>
        </motion.div>
      </div>
      <PublicFooter />
    </div>
  );
}

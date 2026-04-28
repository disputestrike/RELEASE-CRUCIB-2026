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
    desc: 'Describe what you want in plain language. Web apps, dashboards, SaaS, landing pages, backend/API projects, and Expo mobile starters are built through a plan-first flow that shows the structure before code. Attach a screenshot for design-to-code. ZIP/workspace imports are checked by Import Doctor; Git/paste continuation still needs end-to-end proof before it is marketed as universal. Mobile outputs are validator-gated Expo/React Native artifacts; app store submission still requires your developer credentials and EAS/store proof.',
  },
  {
    icon: Bot,
    title: 'Agents & Automation',
    desc: 'Automations can call the build system through the guarded run_agent bridge. The bridge is tested for recursion depth, cycle detection, job budget, prompt size, and internal-token enforcement. Schedules, webhooks, and templates remain configuration-dependent.',
  },
  {
    icon: Zap,
    title: '120-Agent Swarm',
    desc: 'Planning, frontend, backend, database, styling, testing, security, deployment — each phase handled by dedicated agents. They run in parallel for speed. AgentMonitor shows per-phase, per-agent status, token usage, and logs. Quality score per build. Phase retry when needed. Full transparency: every step, every artifact.',
  },
  {
    icon: Download,
    title: 'Deploy & Export',
    desc: 'Export to ZIP or push to GitHub. Deployable web projects include build scripts and deployment guidance, and one-click deployment is only promised where the configured target is available and the validator passes. You own the code and the proof bundle travels with it.',
  },
  {
    icon: Shield,
    title: 'Security & Quality',
    desc: 'Security checks, preview gates, build integrity validation, and Build Integrity score (0-100) are enforced per build profile. Claims must map to artifacts: tests, proof files, screenshots, build output, and validator results. Accessibility is part of the validator roadmap and must be shown as proof before it is treated as complete.',
  },
  {
    icon: Keyboard,
    title: 'Power Users',
    desc: 'Command palette (Ctrl+K), shortcuts, quick actions, templates, patterns, and prompt library for fast starts. API access for prompt-to-plan and prompt-to-code where configured. Token usage tracking and add-ons when you need more. IDE extensions are not claimed unless a configured extension integration is present.',
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
          <span className="text-sm text-kimi-muted">Validator-gated delivery</span>
          <span className="text-sm text-kimi-muted">Full transparency</span>
          <span className="text-sm text-kimi-muted">Web + Expo mobile + agents</span>
          <span className="text-sm font-medium text-kimi-text">Artifacts first.</span>
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
          <p className="text-kimi-muted mb-6">Make your outcome inevitable. Start today.</p>
          <button onClick={() => navigate('/app/workspace')} className="px-6 py-3 bg-white text-gray-900 font-medium rounded-lg hover:bg-gray-200 transition">
            Go to workspace
          </button>
        </motion.div>
      </div>
      <PublicFooter />
    </div>
  );
}

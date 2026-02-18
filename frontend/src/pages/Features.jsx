import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '../App';
import PublicNav from '../components/PublicNav';
import PublicFooter from '../components/PublicFooter';
import {
  Code2, Zap, Bot, Layout, FileCode, BookOpen, Keyboard, Shield, Download,
  GitBranch, Palette, MessageSquare, BarChart3, ShoppingCart, Layers
} from 'lucide-react';

const features = [
  { icon: MessageSquare, title: 'Describe & build', desc: 'Tell us what you want in plain English. Our AI turns your idea into a working app in minutes.' },
  { icon: Code2, title: 'Production-ready code', desc: 'Get React, Tailwind, and modern stack. Clean, maintainable code you can own and deploy.' },
  { icon: Zap, title: '120-agent swarm', desc: 'Planning, frontend, backend, tests, security, deployment—each step powered by specialized agents.' },
  { icon: Bot, title: 'Create & run agents', desc: 'The same AI that builds your app runs inside your automations. Describe what you want in plain language — we create the agent (schedule, webhook, steps). Or build from templates.' },
  { icon: Layout, title: 'Templates', desc: 'Start from dashboards, blogs, SaaS shells, and more. One click to customize and ship.' },
  { icon: FileCode, title: 'Pattern library', desc: 'Reusable patterns: auth, payments, APIs. Save tokens and time on every project.' },
  { icon: BookOpen, title: 'Prompt library', desc: 'Proven prompts for e‑commerce, landing pages, task managers. Copy, tweak, and build.' },
  { icon: Keyboard, title: 'Shortcuts & commands', desc: 'Command palette (Ctrl+K), quick actions, and keyboard shortcuts for power users.' },
  { icon: BarChart3, title: 'Usage & tokens', desc: 'See usage by agent, track tokens, and buy packs when you need more. No surprises.' },
  { icon: Shield, title: 'Security & quality', desc: 'Security scan, accessibility check, and auto-fix. Ship with confidence.' },
  { icon: Download, title: 'Export & deploy', desc: 'Download ZIP or push to GitHub. Deploy to Vercel, Netlify, or any host. You own the code.' },
  { icon: Layers, title: 'Web + mobile', desc: 'Build web and mobile apps. Get Expo (React Native) projects and a store submission pack for App Store and Google Play.' },
  { icon: GitBranch, title: 'Iterate in chat', desc: 'Ask for changes in natural language. "Add dark mode", "make it responsive"—we update the code.' },
  { icon: Palette, title: 'Design control', desc: 'Describe colors, layout, and style. Or paste a screenshot; we turn it into code.' },
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
          <span className="text-sm text-kimi-muted">Typically under 72 hours</span>
          <span className="text-sm text-kimi-muted">Full transparency</span>
          <span className="text-sm text-kimi-muted">Minimal supervision</span>
          <span className="text-sm text-kimi-muted">Web + mobile + agents</span>
          <span className="text-sm font-medium text-kimi-text">Not promises. Measured.</span>
        </motion.div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.03 }}
              className="p-6 rounded-2xl border border-white/10 bg-kimi-bg-card hover:border-white/20 transition"
            >
              <div className="p-2.5 rounded-xl bg-white/5 w-fit mb-4">
                <f.icon className="w-6 h-6 text-kimi-accent" />
              </div>
              <h2 className="text-kimi-card font-semibold text-kimi-text mb-2">{f.title}</h2>
              <p className="text-sm text-kimi-muted leading-relaxed">{f.desc}</p>
            </motion.div>
          ))}
        </div>
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }} className="mt-20 text-center">
          <p className="text-kimi-muted mb-6">Make your outcome inevitable. No credit card required.</p>
          <button onClick={() => navigate(user ? '/app' : '/auth?mode=register')} className="px-6 py-3 bg-white text-black font-medium rounded-lg hover:bg-zinc-200 transition">
            {user ? 'Go to workspace' : 'Get started free'}
          </button>
        </motion.div>
      </div>
      <PublicFooter />
    </div>
  );
}

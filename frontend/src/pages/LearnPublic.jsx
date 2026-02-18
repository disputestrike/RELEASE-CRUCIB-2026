import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { BookOpen, Code, Zap, Shield, Palette, ArrowRight } from 'lucide-react';
import { useAuth } from '../App';
import PublicNav from '../components/PublicNav';
import PublicFooter from '../components/PublicFooter';

const sections = [
  { icon: Code, title: 'Describe what you want', body: 'In the Workspace chat, describe your app in plain English. Use "Build a todo app" or "Create a dashboard with charts".' },
  { icon: Zap, title: 'Use @ and / in chat', body: 'Type @ to add context (e.g. @App.js). Type / for commands like /fix or /explain. The command palette (Ctrl+K) lists all actions.' },
  { icon: Palette, title: 'Templates and prompts', body: 'Use the Prompt Library and Templates to start from proven patterns. Save your own prompts for reuse.' },
  { icon: Shield, title: 'Security and quality', body: 'Use Auto-fix when you see errors. Run Security scan and Accessibility check from the workspace or API.' },
];

export default function LearnPublic() {
  const navigate = useNavigate();
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-kimi-bg text-kimi-text grid-pattern-kimi">
      <PublicNav />
      <div className="max-w-2xl mx-auto px-6 py-16">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-4 mb-10">
          <div className="p-3 rounded-xl bg-blue-500/20">
            <BookOpen className="w-8 h-8 text-blue-400" />
          </div>
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Learn CrucibAI — Inevitable AI</h1>
            <p className="text-zinc-500">Quick tips to build apps with AI. No coding required.</p>
          </div>
        </motion.div>

        <div className="space-y-6">
          {sections.map(({ icon: Icon, title, body }, i) => (
            <motion.div
              key={title}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08 }}
              className="p-6 rounded-2xl border border-zinc-800 bg-zinc-900/30"
            >
              <div className="flex items-start gap-4">
                <div className="p-2 rounded-lg bg-zinc-800 shrink-0">
                  <Icon className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <h2 className="font-semibold mb-1">{title}</h2>
                  <p className="text-sm text-zinc-500 leading-relaxed">{body}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }} className="mt-12 text-center">
          <button
            onClick={() => navigate(user ? '/app' : '/auth?mode=register')}
            className="inline-flex items-center gap-2 px-6 py-3 bg-white text-black font-medium rounded-lg hover:bg-zinc-200 transition"
          >
            {user ? 'Go to workspace' : 'Get started free'}
            <ArrowRight className="w-4 h-4" />
          </button>
        </motion.div>
      </div>
      <PublicFooter />
    </div>
  );
}

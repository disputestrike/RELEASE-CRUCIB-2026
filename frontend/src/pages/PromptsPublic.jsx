import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { BookOpen, Copy, Check, ArrowRight } from 'lucide-react';
import { useAuth, API } from '../App';
import PublicNav from '../components/PublicNav';
import PublicFooter from '../components/PublicFooter';
import axios from 'axios';

const FALLBACK_PROMPTS = [
  { id: 'ecommerce', name: 'E-commerce with cart', prompt: 'Build a modern e-commerce product list with add-to-cart, cart sidebar, and checkout button. Use React and Tailwind.', category: 'app' },
  { id: 'auth-dashboard', name: 'Auth + Dashboard', prompt: 'Create a login page and a dashboard with sidebar navigation. Use React, Tailwind, and local state for auth.', category: 'app' },
  { id: 'landing-waitlist', name: 'Landing + waitlist', prompt: 'Build a landing page with hero, features section, and email waitlist signup. React and Tailwind.', category: 'marketing' },
  { id: 'stripe-saas', name: 'Stripe subscription SaaS', prompt: 'Build a SaaS landing page with pricing cards and Stripe Checkout integration for subscription. React and Tailwind.', category: 'app' },
  { id: 'todo', name: 'Task manager', prompt: 'Create a task manager with add, complete, delete, and filter by status. React and Tailwind.', category: 'app' },
];

export default function PromptsPublic() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [templates, setTemplates] = useState(FALLBACK_PROMPTS);
  const [copiedId, setCopiedId] = useState(null);

  useEffect(() => {
    axios.get(`${API}/prompts/templates`, { timeout: 5000 })
      .then((r) => { if (r.data?.templates?.length) setTemplates(r.data.templates); })
      .catch(() => {});
  }, []);

  const copyPrompt = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const tryPrompt = (prompt) => {
    if (user) {
      navigate('/app/workspace', { state: { initialPrompt: prompt } });
    } else {
      navigate(`/auth?mode=register&prompt=${encodeURIComponent(prompt)}`);
    }
  };

  return (
    <div className="min-h-screen bg-kimi-bg text-kimi-text grid-pattern-kimi">
      <PublicNav />
      <div className="max-w-3xl mx-auto px-6 py-16">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Proven copy</span>
          <h1 className="text-4xl font-semibold tracking-tight mt-2 mb-4">Prompt Library</h1>
          <p className="text-zinc-500">Proven prompts for every use case — e-commerce, landing pages, task managers, auth, SaaS, and more. Copy, tweak, and build. Sign up to try them one-click in the workspace.</p>
        </motion.div>

        <div className="space-y-6">
          {templates.map((t, i) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="p-6 rounded-2xl border border-zinc-800 bg-zinc-900/30"
            >
              <div className="flex items-start justify-between gap-4 mb-3">
                <h2 className="font-semibold">{t.name}</h2>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => copyPrompt(t.prompt, t.id)}
                    className="p-2 text-zinc-400 hover:text-[#1A1A1A] rounded-lg transition"
                    title="Copy prompt"
                  >
                    {copiedId === t.id ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  </button>
                  <button
                    onClick={() => tryPrompt(t.prompt)}
                    className="flex items-center gap-1 text-sm text-blue-400 hover:text-blue-300"
                  >
                    {user ? 'Use in workspace' : 'Get started to use'}
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <p className="text-sm text-zinc-500 font-mono bg-zinc-800/50 rounded-lg p-4 break-words">{t.prompt}</p>
            </motion.div>
          ))}
        </div>
      </div>
      <PublicFooter />
    </div>
  );
}

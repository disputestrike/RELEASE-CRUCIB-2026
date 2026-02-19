import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FileCode, ArrowRight } from 'lucide-react';
import { useAuth, API } from '../App';
import PublicNav from '../components/PublicNav';
import PublicFooter from '../components/PublicFooter';
import axios from 'axios';

const FALLBACK_TEMPLATES = [
  { id: 'dashboard', name: 'Dashboard', description: 'Sidebar + stats cards + chart placeholder', prompt: 'Create a dashboard with a sidebar, stat cards, and a chart area. React and Tailwind.' },
  { id: 'blog', name: 'Blog', description: 'Blog layout with posts list and post detail', prompt: 'Build a blog with a list of posts and a post detail view. React and Tailwind.' },
  { id: 'saas-shell', name: 'SaaS shell', description: 'Auth shell with nav and settings', prompt: 'Create a SaaS app shell with top nav, user menu, and settings page. React and Tailwind.' },
];

export default function TemplatesPublic() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [templates, setTemplates] = useState(FALLBACK_TEMPLATES);

  useEffect(() => {
    axios.get(`${API}/templates`, { timeout: 5000 })
      .then((r) => { if (r.data?.templates?.length) setTemplates(r.data.templates); })
      .catch(() => {});
  }, []);

  const handleUse = () => {
    navigate(user ? '/app/templates' : '/auth?mode=register');
  };

  return (
    <div className="min-h-screen bg-kimi-bg text-kimi-text grid-pattern-kimi">
      <PublicNav />
      <div className="max-w-4xl mx-auto px-6 py-16">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-12">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Quick start</span>
          <h1 className="text-4xl font-semibold tracking-tight mt-2 mb-4">Templates</h1>
          <p className="text-zinc-500">Start from proven app templates — dashboards, blogs, SaaS shells, e-commerce, and more. One click to customize and ship. Sign up free to use any template in the workspace.</p>
        </motion.div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {templates.map((t, i) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="p-6 rounded-2xl border border-zinc-800 bg-zinc-900/30 hover:border-zinc-700 transition"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 rounded-lg bg-zinc-800">
                  <FileCode className="w-5 h-5 text-blue-400" />
                </div>
                <h2 className="font-semibold">{t.name}</h2>
              </div>
              <p className="text-sm text-zinc-500 mb-6">{t.description}</p>
              <button
                onClick={handleUse}
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 transition"
              >
                {user ? 'Use in app' : 'Get started to use'}
                <ArrowRight className="w-4 h-4" />
              </button>
            </motion.div>
          ))}
        </div>
      </div>
      <PublicFooter />
    </div>
  );
}

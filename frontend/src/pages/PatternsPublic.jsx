import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Library, Lock, CreditCard, Code, Globe, Database, Zap, TrendingUp, ArrowRight } from 'lucide-react';
import { useAuth, API } from '../App';
import PublicNav from '../components/PublicNav';
import PublicFooter from '../components/PublicFooter';
import axios from 'axios';

const CATEGORIES = [
  { id: 'all', name: 'All', icon: Library },
  { id: 'auth', name: 'Auth', icon: Lock },
  { id: 'payments', name: 'Payments', icon: CreditCard },
  { id: 'backend', name: 'Backend', icon: Code },
  { id: 'frontend', name: 'Frontend', icon: Globe },
  { id: 'storage', name: 'Storage', icon: Database },
  { id: 'communications', name: 'Comms', icon: Zap },
  { id: 'realtime', name: 'Real-time', icon: TrendingUp },
];

const FALLBACK_PATTERNS = [
  { id: 'auth-jwt', name: 'JWT Authentication', desc: 'Login, signup, token refresh, protected routes.', category: 'auth', usage_count: 1250, tokens_saved: 45000 },
  { id: 'stripe-checkout', name: 'Stripe Checkout Flow', desc: 'Pricing cards, checkout session, webhook handling.', category: 'payments', usage_count: 890, tokens_saved: 60000 },
  { id: 'crud-api', name: 'RESTful CRUD API', desc: 'Create, read, update, delete with validation.', category: 'backend', usage_count: 2100, tokens_saved: 35000 },
  { id: 'responsive-dashboard', name: 'Responsive Dashboard', desc: 'Sidebar, stats, charts, mobile-first layout.', category: 'frontend', usage_count: 1560, tokens_saved: 80000 },
  { id: 'social-oauth', name: 'Social OAuth (Google/GitHub)', desc: 'OAuth flow, profile sync, session handling.', category: 'auth', usage_count: 780, tokens_saved: 55000 },
  { id: 'file-upload', name: 'File Upload with S3', desc: 'Presigned URLs, progress, image preview.', category: 'storage', usage_count: 650, tokens_saved: 40000 },
  { id: 'email-sendgrid', name: 'SendGrid Email', desc: 'Transactional emails, templates, delivery tracking.', category: 'communications', usage_count: 920, tokens_saved: 30000 },
  { id: 'realtime-ws', name: 'WebSocket Real-time', desc: 'Live updates, presence, reconnection.', category: 'realtime', usage_count: 430, tokens_saved: 65000 },
];

export default function PatternsPublic() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [patterns, setPatterns] = useState(FALLBACK_PATTERNS);
  const [category, setCategory] = useState('all');

  useEffect(() => {
    axios.get(`${API}/patterns`, { timeout: 5000 })
      .then((r) => { if (r.data?.patterns?.length) setPatterns(r.data.patterns); })
      .catch(() => {});
  }, []);

  const filtered = category === 'all' ? patterns : patterns.filter((p) => p.category === category);

  return (
    <div className="min-h-screen bg-kimi-bg text-kimi-text grid-pattern-kimi">
      <PublicNav />
      <div className="max-w-4xl mx-auto px-6 py-16">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Token savings</span>
          <h1 className="text-4xl font-semibold tracking-tight mt-2 mb-4">Pattern Library</h1>
          <p className="text-gray-500 mb-2">Reusable patterns for auth, payments, APIs, storage, comms, and real-time. Each pattern saves tokens and time — no re-explaining common flows.</p>
          <p className="text-sm text-gray-500 border-l-2 border-kimi-accent/50 pl-4 py-1">Token savings per pattern are based on typical builds vs. describing from scratch. Use patterns to reduce costs and speed up builds.</p>
        </motion.div>

        <div className="flex flex-wrap gap-2 mb-8">
          {CATEGORIES.map((c) => (
            <button
              key={c.id}
              onClick={() => setCategory(c.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition ${
                category === c.id ? 'bg-gray-200/20 text-gray-500 border border-gray-300/50' : 'border border-gray-800 text-gray-400 hover:text-[#1A1A1A]'
              }`}
            >
              <c.icon className="w-4 h-4" />
              {c.name}
            </button>
          ))}
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          {filtered.map((p, i) => (
            <motion.div
              key={p.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.03 }}
              className="p-5 rounded-xl border border-gray-800 bg-gray-900/30"
            >
              <h2 className="font-semibold mb-1">{p.name}</h2>
              <p className="text-sm text-gray-500 mb-1">{p.desc}</p>
              <p className="text-xs text-gray-600 capitalize">{p.category} · ~{(p.tokens_saved / 1000).toFixed(0)}K tokens saved</p>
            </motion.div>
          ))}
        </div>

        <div className="mt-12 text-center">
          <button
            onClick={() => navigate(user ? '/app/patterns' : '/auth?mode=register')}
            className="inline-flex items-center gap-2 px-6 py-3 bg-white text-gray-900 font-medium rounded-lg hover:bg-gray-200 transition"
          >
            {user ? 'Open in app' : 'Get started to use patterns'}
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
      <PublicFooter />
    </div>
  );
}

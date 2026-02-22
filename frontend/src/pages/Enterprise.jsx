import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Building2, Check, Send } from 'lucide-react';
import { useAuth, API } from '../App';
import PublicNav from '../components/PublicNav';
import PublicFooter from '../components/PublicFooter';
import axios from 'axios';

const USE_CASES = [
  { title: 'Digital Agencies', desc: 'Generate client projects 10x faster.' },
  { title: 'Enterprises', desc: 'Auto-generate internal tools, SDKs, microservices.' },
  { title: 'Startups', desc: 'Ship MVP in days, not weeks.' },
];

const PLAN_TABLE = [
  { plan: 'Free', credits: '50 credits', price: '$0', note: 'Landing pages, export & deploy' },
  { plan: 'Starter', credits: '100K credits', price: '$9.99/mo', note: 'Landing & simple apps' },
  { plan: 'Pro', credits: '500K credits', price: '$49.99/mo', note: 'Full apps & dashboards' },
  { plan: 'Business', credits: '2M credits', price: '$199.99/mo', note: 'Team, high volume' },
  { plan: 'Enterprise', credits: 'Unlimited', price: 'Custom', note: 'SLA, white-label, dedicated support' },
];

export default function Enterprise() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    company: '',
    email: '',
    team_size: '',
    use_case: '',
    budget: '',
    message: '',
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!form.company.trim()) {
      setError('Company is required.');
      return;
    }
    if (!form.email.trim()) {
      setError('Email is required.');
      return;
    }
    setLoading(true);
    try {
      await axios.post(`${API}/enterprise/contact`, {
        company: form.company.trim(),
        email: form.email.trim(),
        team_size: form.team_size.trim() || undefined,
        use_case: form.use_case.trim() || undefined,
        budget: form.budget.trim() || undefined,
        message: form.message.trim() || undefined,
      });
      setSubmitted(true);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-kimi-bg text-kimi-text grid-pattern-kimi">
      <PublicNav />
      <div className="max-w-5xl mx-auto px-6 py-16">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-16">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Enterprise</span>
          <h1 className="text-kimi-section font-bold text-kimi-text mt-2 mb-4">CrucibAI for Enterprise — Scale AI App Generation Across Your Team</h1>
          <p className="text-kimi-muted max-w-xl mx-auto">
            Inevitable outcomes at scale: custom plans, volume credits, SSO, and dedicated support. Tell us your needs and we&apos;ll get back within 24 hours.
          </p>
        </motion.div>

        {/* Plan comparison table */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-16 overflow-x-auto rounded-2xl border border-white/10 bg-kimi-bg-card"
        >
          <table className="w-full min-w-[500px] text-left">
            <thead>
              <tr className="border-b border-white/10">
                <th className="p-4 text-sm font-semibold text-kimi-text">Plan</th>
                <th className="p-4 text-sm font-semibold text-kimi-text">Credits</th>
                <th className="p-4 text-sm font-semibold text-kimi-text">Price</th>
                <th className="p-4 text-sm font-semibold text-kimi-text">Notes</th>
              </tr>
            </thead>
            <tbody>
              {PLAN_TABLE.map((row, i) => (
                <tr key={row.plan} className="border-b border-white/5 last:border-0">
                  <td className="p-4 font-medium text-kimi-text">{row.plan}</td>
                  <td className="p-4 text-kimi-muted">{row.credits}</td>
                  <td className="p-4 text-kimi-muted">{row.price}</td>
                  <td className="p-4 text-kimi-muted text-sm">{row.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </motion.div>

        {/* Use cases */}
        <div className="grid sm:grid-cols-3 gap-6 mb-16">
          {USE_CASES.map((u, i) => (
            <motion.div
              key={u.title}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 + i * 0.05 }}
              className="p-6 rounded-2xl border border-white/10 bg-kimi-bg-card hover:border-white/20 transition"
            >
              <Building2 className="w-8 h-8 text-kimi-accent mb-3" />
              <h3 className="font-semibold text-kimi-text mb-2">{u.title}</h3>
              <p className="text-sm text-kimi-muted">{u.desc}</p>
            </motion.div>
          ))}
        </div>

        {/* Contact form or thank-you */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="max-w-lg mx-auto"
        >
          {submitted ? (
            <div className="p-8 rounded-2xl border border-white/10 bg-kimi-bg-card text-center">
              <h2 className="text-xl font-semibold text-kimi-text mb-2">Thank you</h2>
              <p className="text-kimi-muted mb-6">We&apos;ll be in touch within 24 hours.</p>
              <button
                type="button"
                onClick={() => navigate(user ? '/app' : '/')}
                className="px-6 py-3 bg-white text-gray-900 font-medium rounded-lg hover:bg-gray-200 transition"
              >
                {user ? 'Back to workspace' : 'Back to home'}
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4 p-6 rounded-2xl border border-white/10 bg-kimi-bg-card">
              <h2 className="text-lg font-semibold text-kimi-text mb-4">Contact sales</h2>
              {error && <p className="text-sm text-gray-400">{error}</p>}
              <div>
                <label className="block text-sm text-kimi-muted mb-1">Company *</label>
                <input
                  type="text"
                  value={form.company}
                  onChange={(e) => setForm((f) => ({ ...f, company: e.target.value }))}
                  className="w-full px-4 py-2.5 rounded-lg bg-gray-800 border border-gray-700 text-[#1A1A1A] placeholder-zinc-500 focus:border-kimi-accent outline-none"
                  placeholder="Acme Inc."
                  required
                />
              </div>
              <div>
                <label className="block text-sm text-kimi-muted mb-1">Work email *</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                  className="w-full px-4 py-2.5 rounded-lg bg-gray-800 border border-gray-700 text-[#1A1A1A] placeholder-zinc-500 focus:border-kimi-accent outline-none"
                  placeholder="you@company.com"
                  required
                />
              </div>
              <div>
                <label className="block text-sm text-kimi-muted mb-1">Team size</label>
                <select
                  value={form.team_size}
                  onChange={(e) => setForm((f) => ({ ...f, team_size: e.target.value }))}
                  className="w-full px-4 py-2.5 rounded-lg bg-gray-800 border border-gray-700 text-[#1A1A1A] focus:border-kimi-accent outline-none"
                >
                  <option value="">Select</option>
                  <option value="1-10">1–10</option>
                  <option value="11-50">11–50</option>
                  <option value="51-200">51–200</option>
                  <option value="200+">200+</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-kimi-muted mb-1">Use case</label>
                <select
                  value={form.use_case}
                  onChange={(e) => setForm((f) => ({ ...f, use_case: e.target.value }))}
                  className="w-full px-4 py-2.5 rounded-lg bg-gray-800 border border-gray-700 text-[#1A1A1A] focus:border-kimi-accent outline-none"
                >
                  <option value="">Select</option>
                  <option value="agency">Agency</option>
                  <option value="enterprise">Enterprise</option>
                  <option value="startup">Startup</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-kimi-muted mb-1">Budget range</label>
                <select
                  value={form.budget}
                  onChange={(e) => setForm((f) => ({ ...f, budget: e.target.value }))}
                  className="w-full px-4 py-2.5 rounded-lg bg-gray-800 border border-gray-700 text-[#1A1A1A] focus:border-kimi-accent outline-none"
                >
                  <option value="">Select</option>
                  <option value="10K">$10K</option>
                  <option value="50K">$50K</option>
                  <option value="100K+">$100K+</option>
                  <option value="custom">Custom</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-kimi-muted mb-1">Message</label>
                <textarea
                  value={form.message}
                  onChange={(e) => setForm((f) => ({ ...f, message: e.target.value }))}
                  rows={3}
                  className="w-full px-4 py-2.5 rounded-lg bg-gray-800 border border-gray-700 text-[#1A1A1A] placeholder-zinc-500 focus:border-kimi-accent outline-none resize-none"
                  placeholder="Tell us about your goals and volume needs."
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-white text-gray-900 font-medium rounded-lg hover:bg-gray-200 transition disabled:opacity-60"
              >
                {loading ? 'Sending…' : 'Send request'}
                <Send className="w-4 h-4" />
              </button>
            </form>
          )}
        </motion.div>
      </div>
      <PublicFooter />
    </div>
  );
}

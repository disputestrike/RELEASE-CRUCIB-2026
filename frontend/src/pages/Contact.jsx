import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Send } from 'lucide-react';
import { API } from '../App';
import PublicNav from '../components/PublicNav';
import PublicFooter from '../components/PublicFooter';
import axios from 'axios';

const ISSUE_TYPES = [
  { value: '', label: 'Select topic' },
  { value: 'general', label: 'General inquiry' },
  { value: 'support', label: 'Technical support' },
  { value: 'billing', label: 'Billing & credits' },
  { value: 'enterprise', label: 'Enterprise / sales' },
  { value: 'feedback', label: 'Feedback' },
  { value: 'other', label: 'Other' },
];

export default function Contact() {
  const navigate = useNavigate();
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    name: '',
    email: '',
    issue_type: '',
    message: '',
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!form.email.trim()) {
      setError('Email is required.');
      return;
    }
    if (!form.message.trim()) {
      setError('Message is required.');
      return;
    }
    setLoading(true);
    try {
      await axios.post(`${API}/contact`, {
        email: form.email.trim(),
        message: form.message.trim(),
        issue_type: form.issue_type || undefined,
        name: form.name.trim() || undefined,
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
      <div className="max-w-xl mx-auto px-6 py-16">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-12">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Contact</span>
          <h1 className="text-kimi-section font-bold text-kimi-text mt-2 mb-4">Contact us</h1>
          <p className="text-kimi-muted">
            Have a question, feedback, or need help? Send us a message and we&apos;ll get back to you as soon as we can.
            For enterprise or custom plans, use the form on the <Link to="/enterprise" className="text-kimi-accent hover:underline">Enterprise page</Link>.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="max-w-lg mx-auto"
        >
          {submitted ? (
            <div className="p-8 rounded-2xl form-card-public text-center">
              <h2 className="text-xl font-semibold text-kimi-text mb-2">Message sent</h2>
              <p className="text-kimi-muted mb-6">Thanks for reaching out. We&apos;ll get back to you soon.</p>
              <button
                type="button"
                onClick={() => navigate('/')}
                className="px-6 py-3 bg-white text-gray-900 font-medium rounded-lg hover:bg-gray-200 transition"
              >
                Back to home
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4 p-6 rounded-2xl form-card-public">
              <h2 className="text-lg font-semibold text-kimi-text mb-4">Send a message</h2>
              {error && <p className="text-sm text-red-400">{error}</p>}
              <div>
                <label className="block text-sm text-kimi-muted mb-1">Topic</label>
                <select
                  value={form.issue_type}
                  onChange={(e) => setForm((f) => ({ ...f, issue_type: e.target.value }))}
                  className="w-full px-4 py-2.5 rounded-lg form-input-public"
                >
                  {ISSUE_TYPES.map((opt) => (
                    <option key={opt.value || 'empty'} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-kimi-muted mb-1">Name</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  className="w-full px-4 py-2.5 rounded-lg form-input-public"
                  placeholder="Your name"
                />
              </div>
              <div>
                <label className="block text-sm text-kimi-muted mb-1">Email *</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                  className="w-full px-4 py-2.5 rounded-lg form-input-public"
                  placeholder="you@example.com"
                  required
                />
              </div>
              <div>
                <label className="block text-sm text-kimi-muted mb-1">Message *</label>
                <textarea
                  value={form.message}
                  onChange={(e) => setForm((f) => ({ ...f, message: e.target.value }))}
                  rows={5}
                  maxLength={5000}
                  className="w-full px-4 py-2.5 rounded-lg form-input-public resize-none"
                  placeholder="How can we help?"
                  required
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-white text-gray-900 font-medium rounded-lg hover:bg-gray-200 transition disabled:opacity-60"
              >
                {loading ? 'Sending…' : 'Send message'}
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

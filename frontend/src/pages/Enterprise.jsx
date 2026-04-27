import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Building2, Check, Send, Shield, Lock, Server, Users, Activity,
  Key, FileText, Globe, Zap, AlertCircle, Clock, CheckCircle2,
} from 'lucide-react';
import { useAuth } from '../authContext';
import { API_BASE as API } from '../apiBase';
import PublicNav from '../components/PublicNav';
import PublicFooter from '../components/PublicFooter';
import axios from 'axios';

const USE_CASES = [
  { icon: Building2, title: 'Digital Agencies', desc: 'Generate client projects 10x faster with white-label builds and team workspaces.' },
  { icon: Server, title: 'Enterprises', desc: 'Generate internal tools, SDKs, and microservice artifacts with security and proof gates; formal compliance is handled by agreement.' },
  { icon: Zap, title: 'Startups', desc: 'Create proof-gated MVP artifacts quickly. Auth, payments, and database scaffolds are generated when requested and validator-supported.' },
];

const SOC2_CHECKLIST = [
  { category: 'Security', items: ['Authentication and session controls', 'Role-based access controls where configured', 'Client-secret scan in BIV', 'Provider-token handling by environment', 'Security headers in production routes', 'Responsible disclosure channel'] },
  { category: 'Availability', items: ['Provider-backed hosting options', 'Health check endpoints', 'Deploy readiness proof', 'Preview readiness proof', 'Incident response terms by agreement', 'Rollback plan by deployment target'] },
  { category: 'Confidentiality', items: ['Project-scoped workspaces', 'Secrets should remain in environment variables', 'No secret echo in validator issues', 'Privacy controls documented', 'Data deletion by account workflow', 'Audit trails where configured'] },
  { category: 'Processing Integrity', items: ['Build Integrity Validator before completion', 'Preview and runtime proof gates', 'Import Doctor baseline for ZIP/workspace imports', 'Bounded BIV repair attempt', 'DAG integrity checks', 'Evidence matrix for public claims'] },
];

const SLA_TIERS = [
  { plan: 'Free', uptime: '99%', support: 'Community', response: '—', deploy: 'Shared' },
  { plan: 'Pro', uptime: '99.5%', support: 'Email', response: '< 48h', deploy: 'Shared' },
  { plan: 'Teams', uptime: '99.9%', support: 'Priority Email', response: '< 8h', deploy: 'Isolated' },
  { plan: 'Enterprise', uptime: '99.9%', support: 'Dedicated Slack', response: '< 1h', deploy: 'Private' },
];

const SSO_FEATURES = [
  { icon: Key, title: 'SAML 2.0 SSO', desc: 'Available through enterprise setup when the identity provider integration is configured.' },
  { icon: Users, title: 'User Provisioning', desc: 'Provisioning requirements are scoped during enterprise onboarding.' },
  { icon: Lock, title: 'Org-level Controls', desc: 'Org policy controls are configured by plan and deployment target.' },
  { icon: Activity, title: 'Audit Logs', desc: 'Job events, proof artifacts, and relevant workspace actions are recorded where the runtime emits them.' },
];

const ENTERPRISE_FEATURES = [
  { icon: Shield, label: 'SOC 2 roadmap in progress' },
  { icon: Lock, label: 'SAML / WorkOS SSO' },
  { icon: Globe, label: 'SLA options by agreement' },
  { icon: Key, label: 'Custom API keys & volume' },
  { icon: FileText, label: 'Privacy controls documented' },
  { icon: Users, label: 'Dedicated success manager' },
  { icon: Server, label: 'Private deployment planning' },
  { icon: Clock, label: '< 1-hour incident response' },
];

export default function Enterprise() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('soc2');
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
    if (!form.company.trim()) { setError('Company is required.'); return; }
    if (!form.email.trim()) { setError('Work email is required.'); return; }
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
      <div className="max-w-6xl mx-auto px-6 py-16">

        {/* Hero */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-16">
          <span className="inline-flex items-center gap-2 text-xs uppercase tracking-wider text-kimi-muted mb-3">
            <Shield className="w-3.5 h-3.5" /> Enterprise
          </span>
          <h1 className="text-kimi-section font-bold text-kimi-text mt-2 mb-4">
            CrucibAI for Enterprise
          </h1>
          <p className="text-kimi-muted max-w-2xl mx-auto text-lg mb-8">
            Enterprise security roadmap, SAML SSO options, deployment planning, and dedicated support — scoped to the proof and provider integrations your team enables.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            {ENTERPRISE_FEATURES.map(f => (
              <span key={f.label} className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs border border-white/10 text-kimi-muted">
                <f.icon className="w-3 h-3" /> {f.label}
              </span>
            ))}
          </div>
        </motion.div>

        {/* Use cases */}
        <div className="grid sm:grid-cols-3 gap-6 mb-20">
          {USE_CASES.map((u, i) => (
            <motion.div
              key={u.title}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.05 }}
              className="p-6 rounded-2xl border border-white/10 bg-kimi-bg-card hover:border-white/20 transition"
            >
              <u.icon className="w-8 h-8 text-kimi-accent mb-3" />
              <h3 className="font-semibold text-kimi-text mb-2">{u.title}</h3>
              <p className="text-sm text-kimi-muted">{u.desc}</p>
            </motion.div>
          ))}
        </div>

        {/* SSO section */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }} className="mb-20">
          <h2 className="text-2xl font-bold text-kimi-text text-center mb-3">SAML / SSO</h2>
          <p className="text-kimi-muted text-center mb-10 max-w-xl mx-auto">
            Connect your identity provider in minutes. WorkOS-powered SAML 2.0 — works with Okta, Azure AD, Google Workspace, and more.
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {SSO_FEATURES.map(f => (
              <div key={f.title} className="p-5 rounded-2xl border border-white/10 bg-kimi-bg-card">
                <f.icon className="w-6 h-6 text-kimi-accent mb-3" />
                <h4 className="font-semibold text-kimi-text text-sm mb-1">{f.title}</h4>
                <p className="text-xs text-kimi-muted">{f.desc}</p>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Security / SLA tabs */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="mb-20">
          <div className="flex justify-center mb-8">
            <div className="flex gap-1 p-1 rounded-xl border border-white/10 bg-kimi-bg-card">
              {[{ id: 'soc2', label: 'Security Controls' }, { id: 'sla', label: 'SLA' }].map(t => (
                <button
                  key={t.id}
                  onClick={() => setActiveTab(t.id)}
                  className="px-5 py-2 rounded-lg text-sm font-medium transition"
                  style={{
                    background: activeTab === t.id ? 'rgba(255,255,255,0.1)' : 'transparent',
                    color: activeTab === t.id ? '#fff' : 'rgba(255,255,255,0.5)',
                  }}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {activeTab === 'soc2' && (
            <div>
              <h2 className="text-2xl font-bold text-kimi-text text-center mb-3">Security Controls</h2>
              <p className="text-kimi-muted text-center mb-10 max-w-xl mx-auto">
                CrucibAI documents the controls currently implemented and the controls that remain conditional. Formal SOC 2 evidence is still in progress.
              </p>
              <div className="grid sm:grid-cols-2 gap-6">
                {SOC2_CHECKLIST.map(sec => (
                  <div key={sec.category} className="p-6 rounded-2xl border border-white/10 bg-kimi-bg-card">
                    <div className="flex items-center gap-2 mb-4">
                      <Shield className="w-4 h-4 text-kimi-accent" />
                      <h3 className="font-semibold text-kimi-text">{sec.category}</h3>
                    </div>
                    <ul className="space-y-2">
                      {sec.items.map(item => (
                        <li key={item} className="flex items-start gap-2 text-sm text-kimi-muted">
                          <CheckCircle2 className="w-3.5 h-3.5 text-green-400 mt-0.5 shrink-0" />
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'sla' && (
            <div>
              <h2 className="text-2xl font-bold text-kimi-text text-center mb-3">Service Level Agreement</h2>
              <p className="text-kimi-muted text-center mb-10 max-w-xl mx-auto">
                Availability targets, response times, and support terms are defined by plan and by signed enterprise agreement.
              </p>
              <div className="overflow-x-auto rounded-2xl border border-white/10">
                <table className="w-full text-sm">
                  <thead>
                    <tr style={{ background: 'rgba(255,255,255,0.04)' }}>
                      {['Plan', 'Availability target', 'Support', 'Response Time', 'Compute'].map(h => (
                        <th key={h} className="text-left px-6 py-4 text-kimi-muted font-medium">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {SLA_TIERS.map((t, i) => (
                      <tr
                        key={t.plan}
                        className="border-t border-white/5 transition hover:bg-white/[0.02]"
                        style={t.plan === 'Enterprise' ? { background: 'rgba(124,58,237,0.06)' } : {}}
                      >
                        <td className="px-6 py-4 font-semibold text-kimi-text">
                          {t.plan}
                          {t.plan === 'Enterprise' && (
                            <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-kimi-accent/20 text-kimi-accent">Recommended</span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-green-400 font-medium">{t.uptime}</td>
                        <td className="px-6 py-4 text-kimi-muted">{t.support}</td>
                        <td className="px-6 py-4 text-kimi-muted">{t.response}</td>
                        <td className="px-6 py-4 text-kimi-muted">{t.deploy}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-kimi-muted text-center mt-4">
                SLA credits and uptime commitments apply only when included in a signed enterprise agreement.
              </p>
            </div>
          )}
        </motion.div>

        {/* Contact form */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="max-w-lg mx-auto"
        >
          {submitted ? (
            <div className="p-8 rounded-2xl form-card-public text-center">
              <CheckCircle2 className="w-10 h-10 text-green-400 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-kimi-text mb-2">Request received</h2>
              <p className="text-kimi-muted mb-6">Our enterprise team will be in touch within 24 hours. In the meantime, you can reach us at <a href="mailto:enterprise@crucibai.com" className="text-kimi-accent underline">enterprise@crucibai.com</a>.</p>
              <button
                type="button"
                onClick={() => navigate(user ? '/app' : '/')}
                className="px-6 py-3 bg-white text-gray-900 font-medium rounded-lg hover:bg-gray-200 transition"
              >
                {user ? 'Back to workspace' : 'Back to home'}
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4 p-6 rounded-2xl form-card-public">
              <h2 className="text-lg font-semibold text-kimi-text mb-1">Talk to enterprise sales</h2>
              <p className="text-sm text-kimi-muted mb-4">Custom pricing, SSO setup, and dedicated onboarding.</p>
              {error && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                  <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
                  <p className="text-sm text-red-400">{error}</p>
                </div>
              )}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-kimi-muted mb-1">Company *</label>
                  <input type="text" value={form.company} onChange={e => setForm(f => ({ ...f, company: e.target.value }))} className="w-full px-4 py-2.5 rounded-lg form-input-public" placeholder="Acme Inc." required />
                </div>
                <div>
                  <label className="block text-sm text-kimi-muted mb-1">Work email *</label>
                  <input type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} className="w-full px-4 py-2.5 rounded-lg form-input-public" placeholder="you@company.com" required />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-kimi-muted mb-1">Team size</label>
                  <select value={form.team_size} onChange={e => setForm(f => ({ ...f, team_size: e.target.value }))} className="w-full px-4 py-2.5 rounded-lg form-input-public">
                    <option value="">Select</option>
                    <option value="1-10">1–10</option>
                    <option value="11-50">11–50</option>
                    <option value="51-200">51–200</option>
                    <option value="200+">200+</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-kimi-muted mb-1">Budget</label>
                  <select value={form.budget} onChange={e => setForm(f => ({ ...f, budget: e.target.value }))} className="w-full px-4 py-2.5 rounded-lg form-input-public">
                    <option value="">Select</option>
                    <option value="under-10K">Under $10K/yr</option>
                    <option value="10K-50K">$10K–$50K/yr</option>
                    <option value="50K-100K">$50K–$100K/yr</option>
                    <option value="100K+">$100K+/yr</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm text-kimi-muted mb-1">Use case</label>
                <select value={form.use_case} onChange={e => setForm(f => ({ ...f, use_case: e.target.value }))} className="w-full px-4 py-2.5 rounded-lg form-input-public">
                  <option value="">Select</option>
                  <option value="internal-tools">Internal tools</option>
                  <option value="client-projects">Client projects (agency)</option>
                  <option value="product-mvp">Product / MVP</option>
                  <option value="enterprise-saas">Enterprise SaaS</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-kimi-muted mb-1">Anything else?</label>
                <textarea value={form.message} onChange={e => setForm(f => ({ ...f, message: e.target.value }))} rows={3} className="w-full px-4 py-2.5 rounded-lg form-input-public resize-none" placeholder="Tell us about your team's goals, integration needs, or compliance requirements." />
              </div>
              <button type="submit" disabled={loading} className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-white text-gray-900 font-medium rounded-lg hover:bg-gray-200 transition disabled:opacity-60">
                {loading ? 'Sending…' : 'Send enterprise request'}
                <Send className="w-4 h-4" />
              </button>
              <p className="text-xs text-kimi-muted text-center">Or email us directly at <a href="mailto:enterprise@crucibai.com" className="text-kimi-accent underline">enterprise@crucibai.com</a></p>
            </form>
          )}
        </motion.div>
      </div>
      <PublicFooter />
    </div>
  );
}

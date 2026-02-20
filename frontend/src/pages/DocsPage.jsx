import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import {
  BookOpen, Search, Code, Zap, Shield, Database, Users,
  FileText, Terminal, ChevronRight, Copy, Check, ExternalLink,
  MessageSquare, Layers, Rocket, Settings, Key, Globe
} from 'lucide-react';
import PublicNav from '../components/PublicNav';

const API_SECTIONS = [
  {
    id: 'auth',
    title: 'Authentication',
    icon: Key,
    description: 'Register, login, manage sessions and API keys.',
    endpoints: [
      { method: 'POST', path: '/api/auth/register', desc: 'Create a new account', body: '{ "email": "...", "password": "...", "name": "..." }', response: '{ "user_id": "...", "token": "..." }' },
      { method: 'POST', path: '/api/auth/login', desc: 'Login and receive JWT token', body: '{ "email": "...", "password": "..." }', response: '{ "token": "...", "user": {...} }' },
      { method: 'GET', path: '/api/auth/me', desc: 'Get current user profile', body: null, response: '{ "id": "...", "name": "...", "email": "...", "role": "..." }' },
      { method: 'POST', path: '/api/auth/refresh', desc: 'Refresh JWT token', body: '{ "refresh_token": "..." }', response: '{ "token": "..." }' },
      { method: 'POST', path: '/api/auth/2fa/setup', desc: 'Enable two-factor authentication', body: null, response: '{ "secret": "...", "qr_url": "..." }' },
    ]
  },
  {
    id: 'projects',
    title: 'Projects',
    icon: FileText,
    description: 'Create, list, update, and manage projects.',
    endpoints: [
      { method: 'GET', path: '/api/projects', desc: 'List all projects', body: null, response: '{ "projects": [...] }' },
      { method: 'POST', path: '/api/projects', desc: 'Create a new project', body: '{ "name": "...", "project_type": "fullstack", "description": "..." }', response: '{ "project_id": "...", "name": "..." }' },
      { method: 'GET', path: '/api/projects/:id', desc: 'Get project details', body: null, response: '{ "id": "...", "name": "...", "files": {...}, "status": "..." }' },
      { method: 'DELETE', path: '/api/projects/:id', desc: 'Delete a project', body: null, response: '{ "ok": true }' },
      { method: 'POST', path: '/api/projects/:id/duplicate', desc: 'Duplicate a project', body: null, response: '{ "project": {...} }' },
      { method: 'POST', path: '/api/projects/import', desc: 'Import from paste, ZIP, or Git', body: '{ "source": "git", "git_url": "..." }', response: '{ "project_id": "..." }' },
    ]
  },
  {
    id: 'ai',
    title: 'AI & Orchestration',
    icon: Layers,
    description: 'Chat, build, and orchestrate the 120-agent swarm.',
    endpoints: [
      { method: 'POST', path: '/api/ai/chat', desc: 'Send a chat message (streaming SSE)', body: '{ "message": "...", "session_id": "...", "mode": "build" }', response: 'SSE stream of agent responses' },
      { method: 'POST', path: '/api/ai/build', desc: 'Trigger full orchestration build', body: '{ "prompt": "Build a todo app", "project_type": "fullstack" }', response: '{ "build_id": "...", "status": "running" }' },
      { method: 'GET', path: '/api/ai/chat/history/:session_id', desc: 'Get chat history', body: null, response: '{ "messages": [...] }' },
      { method: 'POST', path: '/api/ai/explain-error', desc: 'Explain and auto-fix an error', body: '{ "error": "...", "code": "...", "file": "..." }', response: '{ "explanation": "...", "fixed_code": "..." }' },
      { method: 'POST', path: '/api/ai/quality-gate', desc: 'Run quality check on code', body: '{ "code": "...", "language": "javascript" }', response: '{ "score": 85, "issues": [...] }' },
      { method: 'POST', path: '/api/ai/plan', desc: 'Generate a build plan from prompt', body: '{ "prompt": "..." }', response: '{ "plan": {...}, "estimated_tokens": 50000 }' },
    ]
  },
  {
    id: 'agents',
    title: 'Agents',
    icon: Zap,
    description: 'Create, manage, and run custom AI agents.',
    endpoints: [
      { method: 'GET', path: '/api/agents', desc: 'List all agents', body: null, response: '{ "agents": [...] }' },
      { method: 'POST', path: '/api/agents', desc: 'Create a custom agent', body: '{ "name": "...", "prompt": "...", "schedule": "..." }', response: '{ "agent_id": "..." }' },
      { method: 'POST', path: '/api/agents/:id/run', desc: 'Execute an agent', body: '{ "input": "..." }', response: '{ "result": "...", "tokens_used": 500 }' },
      { method: 'GET', path: '/api/agents/dag', desc: 'Get the full agent DAG', body: null, response: '{ "agents": [...], "edges": [...] }' },
      { method: 'GET', path: '/api/agents/:id/logs', desc: 'Get agent execution logs', body: null, response: '{ "logs": [...] }' },
    ]
  },
  {
    id: 'deploy',
    title: 'Deploy',
    icon: Rocket,
    description: 'One-click deploy to Vercel, Netlify, or Railway.',
    endpoints: [
      { method: 'POST', path: '/api/deploy/one-click/vercel', desc: 'Deploy to Vercel', body: '{ "project_id": "..." }', response: '{ "url": "https://...", "status": "ready" }' },
      { method: 'POST', path: '/api/deploy/one-click/netlify', desc: 'Deploy to Netlify', body: '{ "project_id": "..." }', response: '{ "url": "https://...", "status": "ready" }' },
      { method: 'GET', path: '/api/projects/:id/export/zip', desc: 'Download deploy-ready ZIP', body: null, response: 'Binary ZIP file' },
      { method: 'GET', path: '/api/users/me/deploy-tokens', desc: 'Check deploy token status', body: null, response: '{ "has_vercel": true, "has_netlify": false }' },
      { method: 'PATCH', path: '/api/users/me/deploy-tokens', desc: 'Set deploy tokens', body: '{ "vercel_token": "...", "netlify_token": "..." }', response: '{ "ok": true }' },
    ]
  },
  {
    id: 'tokens',
    title: 'Tokens & Billing',
    icon: Database,
    description: 'Manage credits, view usage, and handle payments.',
    endpoints: [
      { method: 'GET', path: '/api/tokens/balance', desc: 'Get current token balance', body: null, response: '{ "balance": 50000, "tier": "pro" }' },
      { method: 'GET', path: '/api/tokens/usage', desc: 'Get usage history', body: null, response: '{ "usage": [...], "total": 125000 }' },
      { method: 'POST', path: '/api/stripe/create-checkout', desc: 'Create Stripe checkout session', body: '{ "tier": "pro" }', response: '{ "checkout_url": "https://..." }' },
      { method: 'GET', path: '/api/tokens/referral', desc: 'Get referral code and stats', body: null, response: '{ "code": "...", "referrals": 5, "earned": 5000 }' },
    ]
  },
  {
    id: 'search',
    title: 'Search',
    icon: Search,
    description: 'Global hybrid search across projects, files, and conversations.',
    endpoints: [
      { method: 'POST', path: '/api/search', desc: 'Hybrid search (semantic + keyword)', body: '{ "query": "...", "scope": "all" }', response: '{ "results": [...], "total": 42 }' },
    ]
  },
  {
    id: 'security',
    title: 'Security',
    icon: Shield,
    description: 'Audit logs, RBAC, and security scanning.',
    endpoints: [
      { method: 'GET', path: '/api/audit-log', desc: 'Get audit log entries', body: null, response: '{ "entries": [...] }' },
      { method: 'GET', path: '/api/audit-log/export', desc: 'Export audit log as CSV', body: null, response: 'CSV file' },
      { method: 'POST', path: '/api/ai/security-scan', desc: 'Run security scan on code', body: '{ "code": "...", "language": "python" }', response: '{ "vulnerabilities": [...], "score": 92 }' },
    ]
  },
  {
    id: 'automation',
    title: 'Automation',
    icon: Settings,
    description: 'Scheduled agents, webhooks, and action chains.',
    endpoints: [
      { method: 'POST', path: '/api/automation/schedule', desc: 'Schedule an agent to run on cron', body: '{ "agent_id": "...", "cron": "0 9 * * *" }', response: '{ "schedule_id": "..." }' },
      { method: 'POST', path: '/api/automation/webhook', desc: 'Create a webhook trigger', body: '{ "agent_id": "...", "event": "push" }', response: '{ "webhook_url": "https://..." }' },
      { method: 'POST', path: '/api/automation/chain', desc: 'Create an action chain', body: '{ "steps": [...] }', response: '{ "chain_id": "..." }' },
    ]
  },
];

const METHOD_COLORS = {
  GET: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  POST: 'bg-gray-200/20 text-gray-500 border-gray-300/30',
  PUT: 'bg-gray-700/20 text-gray-600 border-amber-500/30',
  PATCH: 'bg-gray-200/20 text-gray-500 border-gray-300/30',
  DELETE: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
};

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button onClick={handleCopy} className="p-1.5 rounded-md hover:bg-gray-700 transition" title="Copy">
      {copied ? <Check size={14} className="text-gray-400" /> : <Copy size={14} className="text-gray-500" />}
    </button>
  );
}

export default function DocsPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [activeSection, setActiveSection] = useState('auth');
  const [expandedEndpoint, setExpandedEndpoint] = useState(null);

  const filteredSections = useMemo(() => {
    if (!searchQuery.trim()) return API_SECTIONS;
    const q = searchQuery.toLowerCase();
    return API_SECTIONS.map(section => ({
      ...section,
      endpoints: section.endpoints.filter(ep =>
        ep.path.toLowerCase().includes(q) ||
        ep.desc.toLowerCase().includes(q) ||
        ep.method.toLowerCase().includes(q)
      )
    })).filter(s => s.endpoints.length > 0 || s.title.toLowerCase().includes(q));
  }, [searchQuery]);

  const currentSection = filteredSections.find(s => s.id === activeSection) || filteredSections[0];

  return (
    <div className="min-h-screen bg-black text-gray-200">
      <PublicNav />

      <div className="max-w-7xl mx-auto px-6 py-12">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-3 rounded-xl bg-gray-200/20">
              <BookOpen className="w-7 h-7 text-gray-500" />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">API Documentation</h1>
              <p className="text-gray-500">Complete reference for the CrucibAI API — 186 endpoints</p>
            </div>
          </div>

          {/* Base URL */}
          <div className="flex items-center gap-3 mt-4 p-3 rounded-lg bg-gray-900 border border-gray-800">
            <Globe size={16} className="text-gray-500" />
            <code className="text-sm text-gray-400 font-mono">Base URL: https://api.crucibai.com</code>
            <CopyButton text="https://api.crucibai.com" />
          </div>

          {/* Auth note */}
          <div className="mt-3 p-3 rounded-lg bg-gray-700/10 border border-amber-500/20 text-sm text-gray-600">
            <strong>Authentication:</strong> All endpoints (except /auth/register and /auth/login) require a Bearer token in the Authorization header: <code className="bg-gray-800 px-1.5 py-0.5 rounded text-xs">Authorization: Bearer YOUR_TOKEN</code>
          </div>
        </motion.div>

        {/* Search */}
        <div className="relative mb-8">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search endpoints... (e.g., /api/projects, deploy, chat)"
            className="w-full pl-10 pr-4 py-3 bg-gray-900 border border-gray-800 rounded-xl text-sm text-gray-200 placeholder-zinc-600 focus:outline-none focus:border-gray-300/50"
          />
        </div>

        <div className="flex gap-8">
          {/* Left nav */}
          <nav className="w-56 shrink-0 hidden lg:block">
            <div className="sticky top-24 space-y-1">
              {filteredSections.map(section => {
                const Icon = section.icon;
                return (
                  <button
                    key={section.id}
                    onClick={() => setActiveSection(section.id)}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition ${
                      activeSection === section.id
                        ? 'bg-gray-200/15 text-gray-500 font-medium'
                        : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800/50'
                    }`}
                  >
                    <Icon size={16} />
                    <span>{section.title}</span>
                    <span className="ml-auto text-xs text-gray-600">{section.endpoints.length}</span>
                  </button>
                );
              })}
            </div>
          </nav>

          {/* Main content */}
          <div className="flex-1 min-w-0">
            {currentSection && (
              <motion.div
                key={currentSection.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <div className="flex items-center gap-3 mb-2">
                  <currentSection.icon size={24} className="text-gray-500" />
                  <h2 className="text-2xl font-bold">{currentSection.title}</h2>
                </div>
                <p className="text-gray-500 mb-6">{currentSection.description}</p>

                <div className="space-y-3">
                  {currentSection.endpoints.map((ep, i) => {
                    const key = `${currentSection.id}-${i}`;
                    const isExpanded = expandedEndpoint === key;
                    return (
                      <div
                        key={key}
                        className={`rounded-xl border transition ${
                          isExpanded ? 'border-gray-300/30 bg-gray-900' : 'border-gray-800 bg-gray-900/50 hover:border-gray-700'
                        }`}
                      >
                        <button
                          onClick={() => setExpandedEndpoint(isExpanded ? null : key)}
                          className="w-full flex items-center gap-3 px-4 py-3 text-left"
                        >
                          <span className={`px-2 py-0.5 rounded text-xs font-mono font-bold border ${METHOD_COLORS[ep.method]}`}>
                            {ep.method}
                          </span>
                          <code className="text-sm font-mono text-gray-300 flex-1">{ep.path}</code>
                          <span className="text-xs text-gray-600 hidden sm:block">{ep.desc}</span>
                          <ChevronRight size={16} className={`text-gray-600 transition ${isExpanded ? 'rotate-90' : ''}`} />
                        </button>

                        {isExpanded && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            className="px-4 pb-4 border-t border-gray-800"
                          >
                            <p className="text-sm text-gray-400 mt-3 mb-3">{ep.desc}</p>

                            {ep.body && (
                              <div className="mb-3">
                                <div className="flex items-center justify-between mb-1">
                                  <span className="text-xs font-medium text-gray-500 uppercase">Request Body</span>
                                  <CopyButton text={ep.body} />
                                </div>
                                <pre className="p-3 rounded-lg bg-gray-700 border border-gray-800 text-xs font-mono text-gray-400 overflow-x-auto">
                                  {ep.body}
                                </pre>
                              </div>
                            )}

                            <div>
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-xs font-medium text-gray-500 uppercase">Response</span>
                                <CopyButton text={ep.response} />
                              </div>
                              <pre className="p-3 rounded-lg bg-gray-700 border border-gray-800 text-xs font-mono text-gray-500 overflow-x-auto">
                                {ep.response}
                              </pre>
                            </div>
                          </motion.div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </motion.div>
            )}
          </div>
        </div>

        {/* Footer CTA */}
        <div className="mt-16 text-center p-8 rounded-2xl border border-gray-800 bg-gray-900/50">
          <h3 className="text-xl font-bold mb-2">Ready to build?</h3>
          <p className="text-gray-500 mb-4">Start using the CrucibAI API to build apps with 120 agents.</p>
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={() => navigate(user ? '/app/workspace' : '/auth')}
              className="px-6 py-3 bg-gray-200 hover:bg-black rounded-lg font-medium transition"
            >
              {user ? 'Open Workspace' : 'Get Started Free'}
            </button>
            <a
              href="https://api.crucibai.com/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3 border border-gray-700 hover:border-gray-600 rounded-lg font-medium transition"
            >
              <ExternalLink size={16} /> OpenAPI Spec
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

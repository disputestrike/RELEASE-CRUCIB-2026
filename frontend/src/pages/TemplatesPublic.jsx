import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FileCode, ArrowRight } from 'lucide-react';
import { useAuth } from '../authContext';
import { API_BASE as API } from '../apiBase';
import PublicNav from '../components/PublicNav';
import PublicFooter from '../components/PublicFooter';
import axios from 'axios';
import { logApiError } from '../utils/apiError';

const FALLBACK_TEMPLATES = [
  { id: 'dashboard', name: 'Dashboard', description: 'Sidebar + stats cards + chart placeholder', prompt: 'Create a dashboard with a sidebar, stat cards, and a chart area. React and Tailwind.' },
  { id: 'blog', name: 'Blog', description: 'Blog layout with posts list and post detail', prompt: 'Build a blog with a list of posts and a post detail view. React and Tailwind.' },
  { id: 'saas-shell', name: 'SaaS shell', description: 'Auth shell with nav and settings', prompt: 'Create a SaaS app shell with top nav, user menu, and settings page. React and Tailwind.' },
  { id: 'ecommerce', name: 'E-Commerce Store', description: 'Product grid, cart, checkout flow with PayPal', prompt: 'Build an e-commerce store with product listing, cart, and checkout. React and Tailwind.' },
  { id: 'portfolio', name: 'Portfolio', description: 'Personal portfolio with projects, about, and contact', prompt: 'Create a personal portfolio site with hero, projects grid, about section, and contact form. React and Tailwind.' },
  { id: 'landing-page', name: 'Landing Page', description: 'Marketing landing page with hero, features, pricing, CTA', prompt: 'Build a marketing landing page with hero section, features grid, pricing table, and CTA. React and Tailwind.' },
  { id: 'crm', name: 'CRM Dashboard', description: 'Customer management with contacts, deals, pipeline', prompt: 'Create a CRM dashboard with contacts list, deals pipeline, and activity feed. React and Tailwind.' },
  { id: 'chat-app', name: 'Chat Application', description: 'Real-time messaging with channels and direct messages', prompt: 'Build a chat application with sidebar channels, message list, and input. React and Tailwind.' },
  { id: 'project-mgmt', name: 'Project Management', description: 'Kanban board with tasks, drag-and-drop, team view', prompt: 'Create a project management tool with kanban board, task cards, and team members. React and Tailwind.' },
  { id: 'social-media', name: 'Social Feed', description: 'Social media feed with posts, likes, comments', prompt: 'Build a social media feed with post cards, like/comment buttons, and user profiles. React and Tailwind.' },
  { id: 'admin-panel', name: 'Admin Panel', description: 'Full admin dashboard with users, roles, analytics', prompt: 'Create an admin panel with user management, role-based access, and analytics charts. React and Tailwind.' },
  { id: 'api-docs', name: 'API Documentation', description: 'Interactive API docs with endpoints, code samples', prompt: 'Build an API documentation page with endpoint list, request/response examples, and code snippets. React and Tailwind.' },
];

export default function TemplatesPublic() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [templates, setTemplates] = useState(FALLBACK_TEMPLATES);

  useEffect(() => {
    axios.get(`${API}/community/templates`, { timeout: 5000 })
      .then((r) => { if (r.data?.templates?.length) setTemplates(r.data.templates); })
      .catch((e) => {
        logApiError('TemplatesPublic community', e);
        axios.get(`${API}/templates`, { timeout: 5000 })
          .then((r) => { if (r.data?.templates?.length) setTemplates(r.data.templates); })
          .catch((err) => logApiError('TemplatesPublic fallback', err));
      });
  }, []);

  const handleUse = () => {
    navigate('/app/templates');
  };

  return (
    <div className="min-h-screen bg-kimi-bg text-kimi-text grid-pattern-kimi">
      <PublicNav />
      <div className="max-w-4xl mx-auto px-6 py-16">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-12">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Quick start</span>
          <h1 className="text-4xl font-semibold tracking-tight mt-2 mb-4">Templates</h1>
          <p className="text-gray-500">Start from app templates — dashboards, blogs, SaaS shells, e-commerce, and more. Customize in the workspace, then export or deploy only after the relevant proof gates pass.</p>
        </motion.div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {templates.map((t, i) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="p-6 rounded-2xl border border-stone-200 bg-white hover:border-stone-300 shadow-sm transition"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 rounded-lg bg-gray-100">
                  <FileCode className="w-5 h-5 text-[#1A1A1A]" />
                </div>
                <h2 className="font-semibold">{t.name}</h2>
              </div>
              <p className="text-sm text-stone-500 mb-4">{t.description}</p>
              <div className="flex flex-wrap gap-2 mb-6">
                {(t.tags || []).slice(0, 3).map((tag) => (
                  <span key={tag} className="text-xs px-2 py-1 rounded bg-stone-100 text-stone-600">{tag}</span>
                ))}
                {typeof t.proof_score === 'number' && (
                  <span className="text-xs px-2 py-1 rounded bg-green-50 text-green-700">{t.proof_score}/100 proof</span>
                )}
                {t.moderation_status && (
                  <span className="text-xs px-2 py-1 rounded bg-stone-100 text-stone-600">{t.moderation_status}</span>
                )}
              </div>
              <button
                onClick={handleUse}
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-gray-1000/20 text-[#1A1A1A] hover:bg-gray-1000/30 transition"
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

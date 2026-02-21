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
  { id: 'ai-chatbot', name: 'AI Chatbot UI', prompt: 'Build a ChatGPT-style chat interface with message bubbles, streaming text, code blocks, and a prompt input. React and Tailwind.', category: 'ai' },
  { id: 'kanban-board', name: 'Kanban Board', prompt: 'Create a Trello-style kanban board with columns (To Do, In Progress, Done), draggable cards, and add/edit tasks. React and Tailwind.', category: 'app' },
  { id: 'social-feed', name: 'Social Media Feed', prompt: 'Build a social media feed with post cards, like/comment buttons, image uploads, and infinite scroll. React and Tailwind.', category: 'app' },
  { id: 'analytics-dashboard', name: 'Analytics Dashboard', prompt: 'Create an analytics dashboard with line charts, bar charts, KPI cards, date range picker, and data tables. React, Tailwind, and Recharts.', category: 'data' },
  { id: 'booking-system', name: 'Booking System', prompt: 'Build a booking/appointment system with calendar view, time slot selection, and confirmation flow. React and Tailwind.', category: 'app' },
  { id: 'file-manager', name: 'File Manager', prompt: 'Create a file manager with folder tree, file grid/list view, upload, rename, and delete. React and Tailwind.', category: 'app' },
  { id: 'email-client', name: 'Email Client', prompt: 'Build an email client UI with inbox list, email detail view, compose modal, and folder navigation. React and Tailwind.', category: 'app' },
  { id: 'restaurant-menu', name: 'Restaurant Menu', prompt: 'Create a restaurant menu with categories, item cards with images, dietary tags, and order button. React and Tailwind.', category: 'marketing' },
  { id: 'real-estate', name: 'Real Estate Listings', prompt: 'Build a real estate listing page with property cards, filters (price, beds, location), map view, and detail modal. React and Tailwind.', category: 'app' },
  { id: 'fitness-tracker', name: 'Fitness Tracker', prompt: 'Create a fitness tracking dashboard with workout log, progress charts, goals, and daily stats. React, Tailwind, and Recharts.', category: 'app' },
  { id: 'invoice-generator', name: 'Invoice Generator', prompt: 'Build an invoice generator with line items, tax calculation, client info, and PDF export button. React and Tailwind.', category: 'business' },
  { id: 'music-player', name: 'Music Player', prompt: 'Create a music player UI with playlist, now playing bar, progress slider, and album art. React and Tailwind.', category: 'app' },
  { id: 'weather-app', name: 'Weather Dashboard', prompt: 'Build a weather dashboard with current conditions, 5-day forecast, location search, and weather icons. React and Tailwind.', category: 'app' },
  { id: 'quiz-app', name: 'Quiz Application', prompt: 'Create a quiz app with multiple choice questions, progress bar, score tracking, and results page. React and Tailwind.', category: 'education' },
  { id: 'portfolio-v2', name: 'Developer Portfolio', prompt: 'Build a developer portfolio with hero section, skills grid, project showcase with GitHub links, blog section, and contact form. React and Tailwind.', category: 'marketing' },
  { id: 'video-platform', name: 'Video Platform', prompt: 'Create a YouTube-style video platform with video grid, player page, comments, and channel sidebar. React and Tailwind.', category: 'app' },
  { id: 'crm-pipeline', name: 'CRM Pipeline', prompt: 'Build a CRM with contact list, deal pipeline (kanban), activity timeline, and email integration. React and Tailwind.', category: 'business' },
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
          <p className="text-gray-500">Proven prompts for every use case — e-commerce, landing pages, task managers, auth, SaaS, and more. Copy, tweak, and build. Sign up to try them one-click in the workspace.</p>
        </motion.div>

        <div className="space-y-6">
          {templates.map((t, i) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="p-6 rounded-2xl border border-stone-200 bg-white shadow-sm"
            >
              <div className="flex items-start justify-between gap-4 mb-3">
                <h2 className="font-semibold">{t.name}</h2>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => copyPrompt(t.prompt, t.id)}
                    className="p-2 text-gray-400 hover:text-[#1A1A1A] rounded-lg transition"
                    title="Copy prompt"
                  >
                    {copiedId === t.id ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  </button>
                  <button
                    onClick={() => tryPrompt(t.prompt)}
                    className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-500"
                  >
                    {user ? 'Use in workspace' : 'Get started to use'}
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <p className="text-sm text-gray-500 font-mono bg-stone-50 rounded-lg text-stone-700 p-4 break-words">{t.prompt}</p>
            </motion.div>
          ))}
        </div>
      </div>
      <PublicFooter />
    </div>
  );
}

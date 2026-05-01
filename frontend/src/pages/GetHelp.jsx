import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { HelpCircle, ChevronDown, MessageCircle, BookOpen } from 'lucide-react';
import PublicNav from '../components/PublicNav';
import PublicFooter from '../components/PublicFooter';

const HELP_FAQS = [
  {
    q: 'How do I get started?',
    a: 'Sign up at /auth, then go to the Workspace. Describe what you want to build in the chat (e.g. "Build a todo app" or "Create a landing page"). You can use voice input, attach images or files, and we\'ll generate a plan and then the code. Free tier includes 100 credits to get started.',
  },
  {
    q: 'How do credits work?',
    a: 'Each plan gives you a set number of credits per month. Usage varies by scope, stack, and repair depth. Use the Credit Center (/app/tokens) to see your balance and buy more. Plans are monthly; buy extra credits anytime at the same $0.05/credit rate.',
  },
  {
    q: 'The workspace says "Backend not available". What do I do?',
    a: 'That means the CrucibAI backend server isn\'t reachable. If you\'re on our hosted app, check status.crucibai.com or try again in a few minutes. If you\'re running locally, start the backend (see RUN_LOCAL.md). Ensure the frontend proxy points to the correct backend URL (e.g. http://localhost:8000).',
  },
  {
    q: 'Voice or file upload isn\'t working.',
    a: 'Voice transcription and some file processing require the backend. Make sure the backend is running and connected. For microphone access, your browser may block it until you allow it in site settings. Use Chrome, Firefox, or Edge for best support.',
  },
  {
    q: 'How do I report a bug or get technical support?',
    a: 'Use the Contact form (link in the footer or /contact). Choose "Technical support" and include: what you were doing, what you expected, what happened, and your browser/OS. We\'ll respond as soon as we can.',
  },
  {
    q: 'Billing or credit issues?',
    a: 'Check your Credit Center (/app/tokens) for balance and history. For refunds, failed payments, or plan changes, contact us via the Contact form and select "Billing & credits".',
  },
  {
    q: 'Where is the documentation?',
    a: 'Go to Learn (/learn) for quick tips and FAQs. Full docs are at /docs. Shortcuts and prompt library are at /shortcuts and /prompts.',
  },
  {
    q: 'Enterprise or custom plans?',
    a: 'Visit /enterprise for custom plans, volume credits, and dedicated support. Use the Enterprise contact form there or the general Contact form and select "Enterprise / sales".',
  },
];

export default function GetHelp() {
  const navigate = useNavigate();
  const [openIndex, setOpenIndex] = useState(null);

  return (
    <div className="min-h-screen bg-kimi-bg text-kimi-text grid-pattern-kimi">
      <PublicNav />
      <div className="max-w-2xl mx-auto px-6 py-16">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-12">
          <div className="inline-flex p-3 rounded-xl bg-white/5 mb-4">
            <HelpCircle className="w-10 h-10 text-kimi-accent" />
          </div>
          <h1 className="text-kimi-section font-bold text-kimi-text mt-2 mb-4">Get help</h1>
          <p className="text-kimi-muted">
            Answers to common questions. Can&apos;t find what you need? <Link to="/contact" className="text-kimi-accent hover:underline">Contact us</Link>.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="space-y-0 border border-white/10 rounded-2xl overflow-hidden bg-kimi-bg-card"
        >
          {HELP_FAQS.map((faq, i) => (
            <div key={i} className="border-b border-white/10 last:border-0">
              <button
                type="button"
                onClick={() => setOpenIndex(openIndex === i ? null : i)}
                className="w-full py-5 px-6 flex items-center justify-between text-left hover:bg-white/5 transition"
              >
                <span className="text-sm font-medium text-kimi-text pr-4">{faq.q}</span>
                <ChevronDown className={`w-4 h-4 text-kimi-muted shrink-0 transition-transform ${openIndex === i ? 'rotate-180' : ''}`} />
              </button>
              <AnimatePresence>
                {openIndex === i && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <p className="pb-5 px-6 text-sm text-kimi-muted leading-relaxed">{faq.a}</p>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ))}
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="mt-12 grid sm:grid-cols-2 gap-4"
        >
          <Link
            to="/contact"
            className="flex items-center gap-3 p-4 rounded-xl border border-white/10 bg-kimi-bg-card hover:border-kimi-accent/50 transition"
          >
            <MessageCircle className="w-6 h-6 text-kimi-accent shrink-0" />
            <div>
              <span className="font-medium text-kimi-text">Contact us</span>
              <p className="text-sm text-kimi-muted">Send a message and we&apos;ll get back to you.</p>
            </div>
          </Link>
          <Link
            to="/learn"
            className="flex items-center gap-3 p-4 rounded-xl border border-white/10 bg-kimi-bg-card hover:border-kimi-accent/50 transition"
          >
            <BookOpen className="w-6 h-6 text-kimi-accent shrink-0" />
            <div>
              <span className="font-medium text-kimi-text">Learn & docs</span>
              <p className="text-sm text-kimi-muted">Tips, FAQs, and documentation.</p>
            </div>
          </Link>
        </motion.div>
      </div>
      <PublicFooter />
    </div>
  );
}

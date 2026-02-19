import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { BookOpen, Code, Zap, Shield, Palette, ArrowRight, ChevronDown } from 'lucide-react';
import { useAuth } from '../App';
import PublicNav from '../components/PublicNav';
import PublicFooter from '../components/PublicFooter';

const faqsExtra = [
  { q: 'Can I use my own API keys?', a: 'Yes. In Settings you can add your preferred AI provider API key. CrucibAI will use your key for AI requests; token usage is billed by the provider according to their terms.' },
  { q: 'What stacks and frameworks are supported?', a: 'We focus on React and Tailwind for web apps. The workspace uses Sandpack for instant preview. You can export and adapt code for other frameworks.' },
  { q: 'How does plan-first work?', a: 'For larger prompts we first call a planning agent that returns a structured plan (features, components, design notes) and optional suggestions. You see the plan, then we generate code. This reduces backtracking and improves quality.' },
  { q: 'What is Swarm mode?', a: "Swarm (Beta) runs selected agents in parallel instead of sequentially, so multi-step builds can complete faster. It's available on paid plans." },
  { q: 'Can I collaborate with my team?', a: 'You can share exported code or push to a shared GitHub repo. Team and org features are on our roadmap.' },
  { q: 'Does CrucibAI support voice input?', a: 'Yes. Use the microphone button on the landing or in the workspace to record; we transcribe and insert your words into the prompt.' },
  { q: 'What file types can I attach?', a: 'Images (screenshots, mockups), PDFs, and text files. Images are used for design-to-code; PDFs and text add context for the AI.' },
  { q: 'How do token bundles work?', a: 'You buy a bundle (e.g. Starter 100K tokens). Each AI request consumes tokens; when you run low you can buy more. Tokens do not expire.' },
  { q: 'Is there an API for developers?', a: 'We offer API access for prompt to plan and prompt to code. See our roadmap and documentation for availability.' },
  { q: 'How do I get help or report a bug?', a: 'Use the Documentation and Support links in the footer. For bugs, include steps to reproduce and your environment (browser, OS).' },
  { q: 'Can I build mobile apps?', a: 'Yes. We support Expo + App Store submission pack. Describe your mobile app; we build it.' },
  { q: 'What browsers are supported?', a: 'We recommend Chrome, Firefox, or Edge. Safari is supported; voice input may have limitations on some browsers.' },
  { q: 'How does CrucibAI compare to Kimi?', a: 'Kimi excels at long-context chat and research. CrucibAI is Inevitable AI for app creation: plan-first builds, 120-agent swarm, design-to-code, and one workspace from idea to export. Use CrucibAI when you want inevitable outcomes — ship software, not just promises.' }
];

const sections = [
  { id: 'describe', icon: Code, title: 'Describe what you want', body: 'In the Workspace chat, describe your app in plain English. Use "Build a todo app" or "Create a dashboard with charts". Attach a screenshot for design-to-code. Or import existing code — paste, ZIP, or Git URL.' },
  { id: 'plan', icon: Palette, title: 'Plan & approve', body: 'For every build we generate a structured plan first — features, components, design decisions. You see the plan. You approve it. Then we build. No surprises.' },
  { id: 'at', icon: Zap, title: 'Use @ and / in chat', body: 'Type @ to add context (e.g. @App.js). Type / for commands like /fix or /explain. The command palette (Ctrl+K) lists all actions.' },
  { id: 'templates', icon: Palette, title: 'Templates and prompts', body: 'Use the Prompt Library and Templates to start from proven patterns. Save your own prompts for reuse. Patterns save tokens for auth, payments, APIs.' },
  { id: 'agents', icon: Zap, title: 'Create automations', body: 'The same AI that builds your app runs inside your automations. Describe what you want — daily digest, lead finder, inbox summarizer — we create the agent. Use run_agent to call our swarm from your automation.' },
  { id: 'swarm', icon: Zap, title: '120-agent swarm', body: 'Planning, frontend, backend, database, styling, testing, security, deployment — each phase handled by dedicated agents. AgentMonitor shows per-phase status, token usage, and logs.' },
  { id: 'export', icon: Code, title: 'Export and deploy', body: 'Export to ZIP or push to GitHub. Deploy to Vercel or Netlify in one click. For mobile: Expo plus App Store and Google Play submission pack. You own the code.' },
  { id: 'security', icon: Shield, title: 'Security and quality', body: 'Use Auto-fix when you see errors. Run Security scan and Accessibility check from the workspace or API. Quality score per build. 188 tests passing.' },
  { id: 'ide', icon: Code, title: 'IDE extensions', body: 'VS Code, JetBrains, Sublime, and Vim. Code from your editor with the same AI. Command palette and shortcuts for power users.' },
  { id: 'api', icon: Zap, title: 'API for developers', body: 'Prompt-to-plan and prompt-to-code via API. Token usage tracking. Add-ons when you need more. See documentation for availability.' },
];

export default function LearnPublic() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [openFaq, setOpenFaq] = useState(null);

  return (
    <div className="min-h-screen bg-kimi-bg text-kimi-text grid-pattern-kimi">
      <PublicNav />
      <div className="max-w-2xl mx-auto px-6 py-16">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-4 mb-10">
          <div className="p-3 rounded-xl bg-blue-500/20">
            <BookOpen className="w-8 h-8 text-blue-400" />
          </div>
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Learn CrucibAI — Inevitable AI</h1>
            <p className="text-zinc-500">Quick tips to build apps with AI. No coding required.</p>
          </div>
        </motion.div>

        <div className="space-y-6">
          {sections.map(({ id, icon: Icon, title, body }, i) => (
            <motion.div
              key={id || title}
              id={id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06 }}
              className="p-6 rounded-2xl border border-zinc-800 bg-zinc-900/30 scroll-mt-24"
            >
              <div className="flex items-start gap-4">
                <div className="p-2 rounded-lg bg-zinc-800 shrink-0">
                  <Icon className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <h2 className="font-semibold mb-1">{title}</h2>
                  <p className="text-sm text-zinc-500 leading-relaxed">{body}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        <section id="faq-extra" className="mt-16 pt-12 border-t border-zinc-800">
          <h2 className="text-xl font-semibold mb-6">All FAQs (14 more)</h2>
          <div className="space-y-0 border border-zinc-800 rounded-xl overflow-hidden">
            {faqsExtra.map((faq, i) => (
              <div key={i} className="border-b border-zinc-800 last:border-0">
                <button onClick={() => setOpenFaq(openFaq === i ? null : i)} className="w-full py-5 px-6 flex items-center justify-between text-left hover:bg-zinc-800/50 transition">
                  <span className="text-sm font-medium text-zinc-200">{faq.q}</span>
                  <ChevronDown className={`w-4 h-4 text-zinc-500 shrink-0 transition-transform ${openFaq === i ? 'rotate-180' : ''}`} />
                </button>
                <AnimatePresence>
                  {openFaq === i && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                      <p className="pb-5 px-6 text-sm text-zinc-500">{faq.a}</p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ))}
          </div>
        </section>

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }} className="mt-12 text-center">
          <button
            onClick={() => navigate(user ? '/app' : '/auth?mode=register')}
            className="inline-flex items-center gap-2 px-6 py-3 bg-white text-black font-medium rounded-lg hover:bg-zinc-200 transition"
          >
            {user ? 'Go to workspace' : 'Get started free'}
            <ArrowRight className="w-4 h-4" />
          </button>
        </motion.div>
      </div>
      <PublicFooter />
    </div>
  );
}

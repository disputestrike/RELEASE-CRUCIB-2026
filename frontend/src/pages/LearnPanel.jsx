import { Link } from 'react-router-dom';
import { BookOpen, Code, Zap, Shield, Palette } from 'lucide-react';

const sections = [
  {
    icon: Code,
    title: 'Describe what you want',
    body: 'In the Workspace chat, describe your app in plain English. Use "Build a todo app" or "Create a dashboard with charts".',
  },
  {
    icon: Zap,
    title: 'Use @ and / in chat',
    body: 'Type @ to add context (e.g. @App.js). Type / for commands like /fix or /explain. The command palette (Ctrl+K) lists all actions.',
  },
  {
    icon: Palette,
    title: 'Templates and prompts',
    body: 'Use the Prompt Library and Templates to start from proven patterns. Save your own prompts for reuse.',
  },
  {
    icon: Shield,
    title: 'Security and quality',
    body: 'Use Auto-fix when supported. Run baseline security checks and only treat accessibility as complete when a validator report proves it.',
  },
];

export default function LearnPanel() {
  return (
    <div className="min-h-screen bg-[#FAFAF8] text-[#1A1A1A] p-6">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-3 mb-8">
          <div className="p-3 rounded-xl bg-[#F3F1ED]">
            <BookOpen className="w-8 h-8 text-[#1A1A1A]" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Learn CrucibAI</h1>
            <p className="text-[#666666]">Quick tips to build apps with AI</p>
          </div>
        </div>
        <div className="space-y-6">
          {sections.map(({ icon: Icon, title, body }) => (
            <div key={title} className="p-5 rounded-xl border border-black/10 bg-[#F5F5F4]">
              <div className="flex items-start gap-4">
                <div className="p-2 rounded-lg bg-[#EBE8E2] shrink-0">
                  <Icon className="w-5 h-5 text-[#1A1A1A]" />
                </div>
                <div>
                  <h2 className="font-semibold mb-1">{title}</h2>
                  <p className="text-sm text-[#666666]">{body}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-8 p-5 rounded-xl border border-black/10 bg-[#F5F5F4]">
          <h2 className="font-semibold mb-2 flex items-center gap-2">
            <Shield className="w-5 h-5 text-[#1A1A1A]" /> Security &amp; accessibility
          </h2>
          <p className="text-sm text-[#666666] mb-3">
            When you build with us or bring existing code: run baseline <strong className="text-[#1A1A1A]">Security scan</strong> checks in the Workspace where configured. Accessibility is roadmap-only until a WCAG/axe/keyboard/contrast validator report proves it for the project.
          </p>
          <Link to="/security" className="text-sm text-[#1A1A1A] hover:text-[#333]">
            How we keep the platform and your code safe →
          </Link>
        </div>
      </div>
    </div>
  );
}

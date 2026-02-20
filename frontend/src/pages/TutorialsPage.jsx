import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import {
  BookOpen, Search, Code, Zap, Shield, Database, Users,
  FileText, Terminal, ChevronRight, ChevronDown, Copy, Check,
  ExternalLink, MessageSquare, Layers, Rocket, Settings, Key,
  Globe, Palette, Smartphone, Bot, Clock, ArrowRight, Play,
  Star, Filter
} from 'lucide-react';
import PublicNav from '../components/PublicNav';
import PublicFooter from '../components/PublicFooter';

const TUTORIALS = [
  {
    id: 'quickstart',
    title: 'Build Your First App in 5 Minutes',
    description: 'Go from zero to a working todo app with authentication — no code required.',
    difficulty: 'beginner',
    duration: '5 min',
    category: 'getting-started',
    icon: Rocket,
    steps: [
      { title: 'Sign up and open Workspace', content: 'Create a free account at crucibai.com. Click "Open Workspace" from the landing page or navigate to /app/workspace. You get 50 free credits to start.' },
      { title: 'Describe your app', content: 'In the chat input, type: "Build a todo app with user authentication, dark mode, and the ability to mark tasks as complete." Press Enter or click the send button.' },
      { title: 'Review the plan', content: 'CrucibAI generates a structured plan showing: features, components, database schema, and estimated token cost. Review it and click "Approve" to start the build.' },
      { title: 'Watch the agents work', content: 'Open the Agent Monitor (click the agents icon in the toolbar). You\'ll see 15-20 agents activate: Planner, Stack Selector, Frontend Generator, Backend Generator, Database Designer, Stylist, and more. Each shows real-time status.' },
      { title: 'Preview and export', content: 'Once the build completes, the Preview panel shows your running app. Click "Export" to download as ZIP, or use one-click deploy to push to Vercel or Netlify.' },
    ]
  },
  {
    id: 'fullstack-saas',
    title: 'Build a Full-Stack SaaS App',
    description: 'Create a complete SaaS with auth, payments, dashboard, and API — from a single prompt.',
    difficulty: 'intermediate',
    duration: '15 min',
    category: 'web-apps',
    icon: Layers,
    steps: [
      { title: 'Choose the SaaS template', content: 'Go to Templates and select "SaaS Starter". This pre-configures: React frontend, Node.js backend, PostgreSQL, Stripe payments, and user dashboard.' },
      { title: 'Customize with your prompt', content: 'In the Workspace, describe your SaaS: "Build a project management SaaS like Linear. Features: kanban boards, team collaboration, sprint planning, time tracking. Stripe billing with free/pro/enterprise tiers."' },
      { title: 'Use patterns for common features', content: 'Open the Pattern Library. Apply "Auth Pattern" (saves ~2,000 tokens), "Stripe Pattern" (saves ~3,000 tokens), and "RBAC Pattern" for team permissions. Patterns are pre-built, tested code blocks.' },
      { title: 'Iterate with @ mentions', content: 'After the first build, refine: "@Dashboard.jsx add a burndown chart using Chart.js" or "@server.py add a webhook endpoint for Stripe events". The @ symbol tells CrucibAI which file to modify.' },
      { title: 'Deploy to production', content: 'Click Export > One-Click Deploy > Vercel. Enter your Vercel token (Settings > Deploy Tokens). Your SaaS is live in under 60 seconds with a production URL.' },
    ]
  },
  {
    id: 'mobile-app',
    title: 'Build a Mobile App with Expo',
    description: 'Create a cross-platform mobile app for iOS and Android using React Native + Expo.',
    difficulty: 'intermediate',
    duration: '20 min',
    category: 'mobile',
    icon: Smartphone,
    steps: [
      { title: 'Select Mobile project type', content: 'In New Project, select "Mobile App (Expo)". This configures React Native with Expo, navigation, and platform-specific components.' },
      { title: 'Describe your mobile app', content: 'Example: "Build a fitness tracking app. Features: workout logging, progress charts, rest timer, exercise library with animations. Minimalist black and gray theme."' },
      { title: 'Preview on your device', content: 'After the build, scan the QR code with Expo Go on your phone. The app runs natively on your device for real-time testing.' },
      { title: 'Add push notifications', content: 'Type: "/add push notifications for workout reminders". CrucibAI adds Expo Notifications, a backend scheduler, and permission handling.' },
      { title: 'Submit to App Store', content: 'Click Export > App Store Pack. You get: signed IPA, App Store screenshots, metadata, and submission instructions. For Google Play: Export > Play Store Pack.' },
    ]
  },
  {
    id: 'ai-agent',
    title: 'Create a Custom AI Agent',
    description: 'Build an autonomous AI agent that runs on a schedule — lead finder, inbox summarizer, or data monitor.',
    difficulty: 'intermediate',
    duration: '10 min',
    category: 'automation',
    icon: Bot,
    steps: [
      { title: 'Go to Agents page', content: 'Navigate to /app/agents. Click "Create Agent". Give it a name like "Daily Lead Finder" and describe what it should do.' },
      { title: 'Define the agent behavior', content: 'Write the agent prompt: "Search LinkedIn for CTOs at Series A startups in fintech. Extract name, company, and recent posts. Score leads 1-10 based on fit. Output a daily digest."' },
      { title: 'Set a schedule', content: 'Choose "Daily at 9am" from the schedule dropdown. Or use cron syntax for custom schedules: "0 9 * * 1-5" for weekdays only.' },
      { title: 'Add a webhook trigger', content: 'Optionally, create a webhook URL so the agent also runs when triggered by external events — Slack message, GitHub push, or form submission.' },
      { title: 'Chain agents together', content: 'Create an action chain: Lead Finder → Email Drafter → CRM Updater. Each agent\'s output feeds into the next. Use the Automation page to manage chains.' },
    ]
  },
  {
    id: 'design-to-code',
    title: 'Convert a Design to Code',
    description: 'Upload a screenshot or Figma design and get pixel-perfect code in seconds.',
    difficulty: 'beginner',
    duration: '5 min',
    category: 'design',
    icon: Palette,
    steps: [
      { title: 'Open Workspace and attach an image', content: 'Click the attachment icon (paperclip) in the chat input. Upload a screenshot, Figma export, or hand-drawn wireframe.' },
      { title: 'Describe what you want', content: 'Type: "Convert this design to a React component with Tailwind CSS. Make it responsive and match the colors exactly." The image analysis agent extracts layout, colors, typography, and spacing.' },
      { title: 'Review the generated code', content: 'The Code panel shows the generated React component. The Preview panel shows it rendered. Compare side-by-side with your original design.' },
      { title: 'Refine with voice', content: 'Click the microphone icon and say: "Make the header sticky, add a subtle shadow, and increase the padding on mobile." Voice input supports 9 languages.' },
      { title: 'Export the component', content: 'Copy the code directly, or export the full project. The component is production-ready with proper imports, TypeScript types, and accessibility attributes.' },
    ]
  },
  {
    id: 'voice-coding',
    title: 'Code with Your Voice',
    description: 'Use voice input to describe features, fix bugs, and control the workspace hands-free.',
    difficulty: 'beginner',
    duration: '5 min',
    category: 'features',
    icon: MessageSquare,
    steps: [
      { title: 'Enable voice input', content: 'Click the microphone icon in the Workspace chat input. Grant browser microphone permission when prompted. Voice input works in Chrome, Firefox, and Edge.' },
      { title: 'Speak your prompt', content: 'Say: "Build a dashboard with three charts — revenue over time, user signups by country, and a pie chart for traffic sources." CrucibAI transcribes via Whisper and processes your request.' },
      { title: 'Use voice for fixes', content: 'Say: "Fix the login page — the form is not centered on mobile and the submit button needs a loading state." Voice is great for describing visual issues.' },
      { title: 'Switch languages', content: 'Voice input supports 9 languages: English, Spanish, French, German, Portuguese, Italian, Japanese, Korean, and Chinese. Switch in Settings > Voice.' },
      { title: 'Combine voice with @ mentions', content: 'Say: "At App dot jsx, add a dark mode toggle in the header." CrucibAI understands file references in speech.' },
    ]
  },
  {
    id: 'ide-extensions',
    title: 'Use CrucibAI from Your IDE',
    description: 'Install the VS Code, JetBrains, Sublime, or Vim extension to code with CrucibAI from your editor.',
    difficulty: 'beginner',
    duration: '5 min',
    category: 'ide',
    icon: Terminal,
    steps: [
      { title: 'Install the extension', content: 'VS Code: Search "CrucibAI" in Extensions marketplace. JetBrains: File > Settings > Plugins > Search "CrucibAI". Sublime: Package Control > Install > CrucibAI. Vim: Copy crucibai.vim to ~/.vim/plugin/.' },
      { title: 'Configure your API key', content: 'Open extension settings. Enter your CrucibAI API URL (default: https://api.crucibai.com) and API key (found in Settings > API Keys in the web app).' },
      { title: 'Generate code inline', content: 'VS Code: Ctrl+Shift+G to generate code at cursor. JetBrains: Alt+G. Vim: <leader>cg. Describe what you want and the code appears inline.' },
      { title: 'Quick fix errors', content: 'Select an error, press Ctrl+Shift+F (VS Code) or Alt+F (JetBrains). CrucibAI analyzes the error and suggests a fix. Accept with Enter.' },
      { title: 'Voice input from IDE', content: 'VS Code: Ctrl+Shift+V to start voice input. Speak your request. Works with all 9 supported languages.' },
    ]
  },
  {
    id: 'api-integration',
    title: 'Use the CrucibAI API',
    description: 'Integrate CrucibAI into your own tools, CI/CD pipeline, or custom workflow via the REST API.',
    difficulty: 'advanced',
    duration: '15 min',
    category: 'api',
    icon: Code,
    steps: [
      { title: 'Get your API key', content: 'Go to Settings > API Keys. Click "Generate New Key". Copy it — you won\'t see it again. Store it as an environment variable: CRUCIBAI_API_KEY.' },
      { title: 'Make your first API call', content: 'curl -X POST https://api.crucibai.com/api/ai/chat \\\n  -H "Authorization: Bearer YOUR_KEY" \\\n  -H "Content-Type: application/json" \\\n  -d \'{"message": "Build a REST API for a blog", "mode": "build"}\'' },
      { title: 'Stream responses', content: 'The /api/ai/chat endpoint returns Server-Sent Events (SSE). In JavaScript: const evtSource = new EventSource(url); evtSource.onmessage = (e) => console.log(JSON.parse(e.data));' },
      { title: 'Use in CI/CD', content: 'Add to your GitHub Actions workflow:\n- name: Generate tests\n  run: curl -X POST $CRUCIBAI_API/ai/chat -H "Authorization: Bearer $KEY" -d \'{"message": "Generate tests for src/", "mode": "test"}\'' },
      { title: 'Track usage', content: 'GET /api/tokens/usage returns your token consumption. Set up alerts when usage exceeds thresholds. The API respects your tier limits.' },
    ]
  },
  {
    id: 'security-audit',
    title: 'Run a Security Audit',
    description: 'Scan your generated code for vulnerabilities, fix them automatically, and get a security score.',
    difficulty: 'intermediate',
    duration: '10 min',
    category: 'security',
    icon: Shield,
    steps: [
      { title: 'Open the Workspace tools', content: 'In the Workspace, click the shield icon in the toolbar or type /security-scan in the chat.' },
      { title: 'Run the scan', content: 'CrucibAI runs: dependency audit (npm audit + pip-audit), secrets scan (gitleaks), OWASP Top 10 check, and custom security rules. Results appear in the Security panel.' },
      { title: 'Auto-fix vulnerabilities', content: 'Click "Auto-fix" next to any vulnerability. CrucibAI patches the code — updating dependencies, sanitizing inputs, adding CSRF tokens, or fixing SQL injection.' },
      { title: 'Check the security score', content: 'Your project gets a security score out of 100. Scores above 90 are production-ready. The score updates in real-time as you fix issues.' },
      { title: 'Export the report', content: 'Click Export > Security Report. Get a PDF with all findings, fixes applied, and remaining recommendations. Share with your team or compliance officer.' },
    ]
  },
  {
    id: 'team-collaboration',
    title: 'Collaborate with Your Team',
    description: 'Share projects, review builds together, and manage team permissions.',
    difficulty: 'intermediate',
    duration: '10 min',
    category: 'collaboration',
    icon: Users,
    steps: [
      { title: 'Share a project', content: 'In the Workspace, click Share. Choose "View only" or "Can edit". Copy the share link. Anyone with the link can see the project — no account required for view-only.' },
      { title: 'Set up team roles', content: 'Go to Settings > Team. Invite members by email. Assign roles: Admin (full access), Developer (build + edit), Viewer (read-only). RBAC is enforced across all endpoints.' },
      { title: 'Review builds together', content: 'Open a shared project. Both team members see the same Agent Monitor, code, and preview in real-time. Use the chat to discuss changes.' },
      { title: 'Version history', content: 'Every build creates a version. Click History in the right panel to see all versions. Compare diffs between versions. Restore any previous version with one click.' },
      { title: 'Export for the team', content: 'Export to GitHub (push to a shared repo), or download ZIP for local development. The exported code is clean, documented, and ready for git.' },
    ]
  },
];

const CATEGORIES = [
  { id: 'all', label: 'All Tutorials', icon: BookOpen },
  { id: 'getting-started', label: 'Getting Started', icon: Rocket },
  { id: 'web-apps', label: 'Web Apps', icon: Globe },
  { id: 'mobile', label: 'Mobile', icon: Smartphone },
  { id: 'automation', label: 'Automation', icon: Bot },
  { id: 'design', label: 'Design', icon: Palette },
  { id: 'features', label: 'Features', icon: Zap },
  { id: 'ide', label: 'IDE', icon: Terminal },
  { id: 'api', label: 'API', icon: Code },
  { id: 'security', label: 'Security', icon: Shield },
  { id: 'collaboration', label: 'Collaboration', icon: Users },
];

const DIFFICULTY_COLORS = {
  beginner: 'bg-gray-500/15 text-gray-400 border-gray-500/30',
  intermediate: 'bg-gray-200 text-[#1A1A1A] border-gray-300',
  advanced: 'bg-gray-200 text-[#1A1A1A] border-gray-300',
};

export default function TutorialsPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState('all');
  const [expandedTutorial, setExpandedTutorial] = useState(null);
  const [completedSteps, setCompletedSteps] = useState({});

  const filteredTutorials = useMemo(() => {
    let result = TUTORIALS;
    if (activeCategory !== 'all') {
      result = result.filter(t => t.category === activeCategory);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(t =>
        t.title.toLowerCase().includes(q) ||
        t.description.toLowerCase().includes(q) ||
        t.steps.some(s => s.title.toLowerCase().includes(q) || s.content.toLowerCase().includes(q))
      );
    }
    return result;
  }, [searchQuery, activeCategory]);

  const toggleStep = (tutorialId, stepIndex) => {
    const key = `${tutorialId}-${stepIndex}`;
    setCompletedSteps(prev => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-gray-200">
      <PublicNav />

      <div className="max-w-7xl mx-auto px-6 py-12">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-3 rounded-xl bg-gray-500/20">
              <BookOpen className="w-7 h-7 text-gray-400" />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Tutorials</h1>
              <p className="text-gray-500">{TUTORIALS.length} step-by-step guides to master CrucibAI</p>
            </div>
          </div>
        </motion.div>

        {/* Search */}
        <div className="relative mb-6">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search tutorials... (e.g., mobile, deploy, voice)"
            className="w-full pl-10 pr-4 py-3 bg-gray-900 border border-gray-800 rounded-xl text-sm text-gray-200 placeholder-zinc-600 focus:outline-none focus:border-gray-500/50"
          />
        </div>

        {/* Category filters */}
        <div className="flex flex-wrap gap-2 mb-8">
          {CATEGORIES.map(cat => {
            const Icon = cat.icon;
            return (
              <button
                key={cat.id}
                onClick={() => setActiveCategory(cat.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition ${
                  activeCategory === cat.id
                    ? 'bg-gray-500/15 text-gray-400 border border-gray-500/30'
                    : 'text-gray-500 hover:text-gray-300 border border-gray-800 hover:border-gray-700'
                }`}
              >
                <Icon size={14} />
                {cat.label}
              </button>
            );
          })}
        </div>

        {/* Tutorial cards */}
        <div className="space-y-4">
          {filteredTutorials.map((tutorial, idx) => {
            const Icon = tutorial.icon;
            const isExpanded = expandedTutorial === tutorial.id;
            const completedCount = tutorial.steps.filter((_, i) => completedSteps[`${tutorial.id}-${i}`]).length;

            return (
              <motion.div
                key={tutorial.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05 }}
                className={`rounded-xl border transition ${
                  isExpanded ? 'border-gray-500/30 bg-gray-900' : 'border-gray-800 bg-gray-900/50 hover:border-gray-700'
                }`}
              >
                {/* Tutorial header */}
                <button
                  onClick={() => setExpandedTutorial(isExpanded ? null : tutorial.id)}
                  className="w-full flex items-center gap-4 px-6 py-5 text-left"
                >
                  <div className={`p-2.5 rounded-xl shrink-0 ${
                    isExpanded ? 'bg-gray-500/20' : 'bg-gray-800'
                  }`}>
                    <Icon size={20} className={isExpanded ? 'text-gray-400' : 'text-gray-400'} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-lg">{tutorial.title}</h3>
                    <p className="text-sm text-gray-500 mt-0.5">{tutorial.description}</p>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className={`px-2 py-0.5 rounded text-xs border ${DIFFICULTY_COLORS[tutorial.difficulty]}`}>
                      {tutorial.difficulty}
                    </span>
                    <span className="flex items-center gap-1 text-xs text-gray-600">
                      <Clock size={12} /> {tutorial.duration}
                    </span>
                    {completedCount > 0 && (
                      <span className="text-xs text-gray-400">{completedCount}/{tutorial.steps.length}</span>
                    )}
                    <ChevronDown size={18} className={`text-gray-600 transition ${isExpanded ? 'rotate-180' : ''}`} />
                  </div>
                </button>

                {/* Expanded steps */}
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="px-6 pb-6 border-t border-gray-800">
                        <div className="mt-4 space-y-3">
                          {tutorial.steps.map((step, i) => {
                            const isCompleted = completedSteps[`${tutorial.id}-${i}`];
                            return (
                              <div
                                key={i}
                                className={`flex gap-4 p-4 rounded-lg transition cursor-pointer ${
                                  isCompleted ? 'bg-gray-500/5 border border-gray-500/20' : 'bg-gray-800/50 hover:bg-gray-800'
                                }`}
                                onClick={() => toggleStep(tutorial.id, i)}
                              >
                                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-sm font-bold ${
                                  isCompleted ? 'bg-gray-500 text-white' : 'bg-gray-700 text-gray-400'
                                }`}>
                                  {isCompleted ? <Check size={16} /> : i + 1}
                                </div>
                                <div className="flex-1 min-w-0">
                                  <h4 className={`font-medium text-sm ${isCompleted ? 'text-gray-400' : 'text-gray-200'}`}>
                                    {step.title}
                                  </h4>
                                  <p className="text-sm text-gray-500 mt-1 leading-relaxed whitespace-pre-line">
                                    {step.content}
                                  </p>
                                </div>
                              </div>
                            );
                          })}
                        </div>

                        {/* CTA */}
                        <div className="mt-4 flex items-center gap-3">
                          <button
                            onClick={() => navigate(user ? '/app/workspace' : '/auth')}
                            className="flex items-center gap-2 px-4 py-2 bg-gray-500 hover:bg-gray-600 rounded-lg text-sm font-medium transition"
                          >
                            <Play size={14} /> Try it now
                          </button>
                          <span className="text-xs text-gray-600">
                            {completedCount === tutorial.steps.length ? '✓ All steps completed!' : `${completedCount} of ${tutorial.steps.length} steps completed`}
                          </span>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </div>

        {filteredTutorials.length === 0 && (
          <div className="text-center py-16">
            <Search size={48} className="mx-auto text-gray-700 mb-4" />
            <p className="text-gray-500">No tutorials found. Try a different search or category.</p>
          </div>
        )}

        {/* Bottom CTA */}
        <div className="mt-16 text-center p-8 rounded-2xl border border-gray-800 bg-gray-900/50">
          <h3 className="text-xl font-bold mb-2">Need more help?</h3>
          <p className="text-gray-500 mb-4">Check the API docs, learn page, or open the Workspace and ask CrucibAI directly.</p>
          <div className="flex items-center justify-center gap-3 flex-wrap">
            <button onClick={() => navigate('/docs')} className="flex items-center gap-2 px-5 py-2.5 border border-gray-700 hover:border-gray-600 rounded-lg text-sm font-medium transition">
              <Code size={16} /> API Docs
            </button>
            <button onClick={() => navigate('/learn')} className="flex items-center gap-2 px-5 py-2.5 border border-gray-700 hover:border-gray-600 rounded-lg text-sm font-medium transition">
              <BookOpen size={16} /> Learn
            </button>
            <button onClick={() => navigate(user ? '/app/workspace' : '/auth')} className="flex items-center gap-2 px-5 py-2.5 bg-gray-500 hover:bg-gray-600 rounded-lg text-sm font-medium transition">
              <Zap size={16} /> Open Workspace
            </button>
          </div>
        </div>
      </div>

      <PublicFooter />
    </div>
  );
}

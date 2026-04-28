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
    title: 'Build Your First App',
    description: 'Go from prompt to a validator-checked web artifact with authentication scaffolding.',
    difficulty: 'beginner',
    duration: '5 min',
    category: 'getting-started',
    icon: Rocket,
    steps: [
      { title: 'Sign up and open Workspace', content: 'Create a free account and open the workspace. Credits fund build, validation, and repair attempts.' },
      { title: 'Describe your app', content: 'Describe the goal in plain language. The system extracts pages, components, data, and interactions into a plan before building.' },
      { title: 'Review the plan', content: 'Review the structured plan, risks, dependencies, and proof gates. Approve it before code is generated.' },
      { title: 'Watch evidence appear', content: 'AgentMonitor shows available job events, phase progress, logs, and Build Integrity score. It does not claim every hidden internal decision.' },
      { title: 'Preview and export', content: 'After proof gates pass, preview the app and export the ZIP. Provider deployments require configured tokens and targets.' },
    ]
  },
  {
    id: 'fullstack-saas',
    title: 'Build a SaaS App',
    description: 'Create a SaaS scaffold with auth, payment, dashboard, and API surfaces, then validate generated artifacts.',
    difficulty: 'intermediate',
    duration: '15 min',
    category: 'web-apps',
    icon: Layers,
    steps: [
      { title: 'Choose or describe the SaaS shape', content: 'Start from a template or describe the SaaS domain, pages, roles, billing model, and dashboard needs.' },
      { title: 'Customize the plan', content: 'The plan records frontend, backend, data, and security assumptions before generation.' },
      { title: 'Build with gates', content: 'Generated output must satisfy structure, preview, and Build Integrity checks before completion is claimed.' },
      { title: 'Iterate with evidence', content: 'Ask for changes against files or features, then rerun validation so the new output is checked.' },
      { title: 'Deploy through a configured provider', content: 'Use ZIP export by default. Vercel, Netlify, or Railway deploys are conditional on provider configuration and passing gates.' },
    ]
  },
  {
    id: 'mobile-app',
    title: 'Build a Mobile App with Expo',
    description: 'Generate Expo/React Native source artifacts for iOS and Android with mobile validator proof.',
    difficulty: 'intermediate',
    duration: '20 min',
    category: 'mobile',
    icon: Smartphone,
    steps: [
      { title: 'Select Mobile project type', content: 'Choose the Expo mobile target so the generator creates expo-mobile source, app.json, eas.json, screens, and scripts.' },
      { title: 'Describe your mobile app', content: 'Describe screens, navigation, data, device features, and visual direction.' },
      { title: 'Validate artifacts', content: 'The validator checks the Expo project files that are currently proven by the mobile build target.' },
      { title: 'Test with your mobile toolchain', content: 'Run Expo/EAS with your credentials and devices. Live store builds depend on your Apple/Google accounts.' },
      { title: 'Prepare store submission', content: 'Export source, metadata, and guidance. Automatic App Store or Google Play submission is not claimable without credentials, signing, EAS build, and store proof.' },
    ]
  },
  {
    id: 'ai-agent',
    title: 'Create a Custom AI Agent',
    description: 'Draft an automation agent and validate configured trigger and run_agent safety paths.',
    difficulty: 'intermediate',
    duration: '10 min',
    category: 'automation',
    icon: Bot,
    steps: [
      { title: 'Define the agent', content: 'Describe the task, inputs, outputs, and allowed tools.' },
      { title: 'Choose triggers', content: 'Schedules and webhooks are configuration-dependent; the workflow profile must validate them before they are treated as ready.' },
      { title: 'Use guarded run_agent', content: 'run_agent calls are protected by recursion, cycle, depth, budget, and internal-token guards.' },
      { title: 'Review the draft', content: 'Inspect the generated workflow and logs before running it against real data.' },
      { title: 'Run with limits', content: 'Automation execution must respect configured budgets and timeout limits.' },
    ]
  },
  {
    id: 'design-to-code',
    title: 'Convert a Design to Code',
    description: 'Upload a screenshot or design and get validator-checked code artifacts you can inspect and refine.',
    difficulty: 'beginner',
    duration: '5 min',
    category: 'design',
    icon: Palette,
    steps: [
      { title: 'Attach an image', content: 'Upload a screenshot, design export, or wireframe.' },
      { title: 'Describe the target', content: 'State the framework, styling system, responsiveness, and design constraints.' },
      { title: 'Review generated code', content: 'Inspect the code and preview. Visual quality is judged by the current validator and screenshots where available.' },
      { title: 'Refine the result', content: 'Request specific changes, then rerun validation.' },
      { title: 'Export after validation', content: 'Accessibility attributes are generated where supported, but full WCAG proof is only claimable when the accessibility gate reports concrete evidence.' },
    ]
  },
  {
    id: 'voice-coding',
    title: 'Code with Your Voice',
    description: 'Use browser voice input where supported to describe features and fixes.',
    difficulty: 'beginner',
    duration: '5 min',
    category: 'features',
    icon: MessageSquare,
    steps: [
      { title: 'Enable voice input', content: 'Grant microphone permission in a supported browser.' },
      { title: 'Speak your prompt', content: 'Describe the feature or fix clearly. The transcript becomes the build instruction.' },
      { title: 'Review before building', content: 'Confirm the interpreted plan before accepting generated changes.' },
      { title: 'Use file references', content: 'Mention specific files when you want targeted edits.' },
      { title: 'Fallback to typing', content: 'If microphone or speech recognition is unavailable, type the same instruction.' },
    ]
  },
  {
    id: 'api-integration',
    title: 'Use the CrucibAI API',
    description: 'Integrate configured CrucibAI endpoints into your own tools with normal API-key safety practices.',
    difficulty: 'advanced',
    duration: '15 min',
    category: 'api',
    icon: Code,
    steps: [
      { title: 'Get your API key', content: 'Store keys as environment variables and never commit them to client code.' },
      { title: 'Make your first API call', content: 'Call the documented endpoint for your configured environment.' },
      { title: 'Stream responses', content: 'Use SSE only where that endpoint is enabled.' },
      { title: 'Use in CI/CD', content: 'Add API calls with budgets, timeouts, and audit logging.' },
      { title: 'Track usage', content: 'Use token and cost reporting where configured; complete per-agent provider cost accounting remains a broader proof item.' },
    ]
  },
  {
    id: 'security-audit',
    title: 'Run a Security Audit',
    description: 'Run baseline security checks, review findings, and repair issues where supported.',
    difficulty: 'intermediate',
    duration: '10 min',
    category: 'security',
    icon: Shield,
    steps: [
      { title: 'Open security tools', content: 'Use the workspace security action or API where configured.' },
      { title: 'Run configured checks', content: 'The current claim is baseline security scanning and client-secret blocking in BIV, not a comprehensive CORS/auth/tenancy doctor.' },
      { title: 'Repair supported findings', content: 'Use repair where supported. Some findings require manual review or provider-specific configuration.' },
      { title: 'Check Build Integrity score', content: 'The score reflects validator checks that actually ran. It is not a universal production security certification.' },
      { title: 'Export evidence', content: 'Export the proof files that exist for the current build profile.' },
    ]
  },
  {
    id: 'team-collaboration',
    title: 'Collaborate with Your Team',
    description: 'Share project artifacts and review proof outputs with collaborators.',
    difficulty: 'intermediate',
    duration: '10 min',
    category: 'collaboration',
    icon: Users,
    steps: [
      { title: 'Share a project', content: 'Use configured sharing controls for the workspace or exported artifacts.' },
      { title: 'Set up team roles', content: 'Use the team settings available in your plan and environment.' },
      { title: 'Review builds together', content: 'Review the same files, preview, logs, and proof bundle.' },
      { title: 'Track versions', content: 'Use available history and export artifacts; restore actions must be backed by the configured project state.' },
      { title: 'Export for the team', content: 'Download ZIP or push to GitHub where configured.' },
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
  beginner: 'bg-[#F3F1ED] text-[#1A1A1A] border-black/10',
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
    <div className="min-h-screen bg-[#0a0a0a] text-zinc-200">
      <PublicNav />

      <div className="max-w-7xl mx-auto px-6 py-12">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-3 rounded-xl bg-[#1A1A1A]/20">
              <BookOpen className="w-7 h-7 text-[#1A1A1A]" />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Tutorials</h1>
              <p className="text-zinc-500">{TUTORIALS.length} step-by-step guides to master CrucibAI</p>
            </div>
          </div>
        </motion.div>

        {/* Search */}
        <div className="relative mb-6">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-zinc-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search tutorials... (e.g., mobile, deploy, voice)"
            className="w-full pl-10 pr-4 py-3 bg-zinc-900 border border-zinc-800 rounded-xl text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-[#666666]"
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
                    ? 'bg-[#1A1A1A]/15 text-[#1A1A1A] border border-black/15'
                    : 'text-zinc-500 hover:text-zinc-300 border border-zinc-800 hover:border-zinc-700'
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
                  isExpanded ? 'border-[#666666] bg-zinc-900' : 'border-zinc-800 bg-zinc-900/50 hover:border-zinc-700'
                }`}
              >
                {/* Tutorial header */}
                <button
                  onClick={() => setExpandedTutorial(isExpanded ? null : tutorial.id)}
                  className="w-full flex items-center gap-4 px-6 py-5 text-left"
                >
                  <div className={`p-2.5 rounded-xl shrink-0 ${
                    isExpanded ? 'bg-[#1A1A1A]/20' : 'bg-zinc-800'
                  }`}>
                    <Icon size={20} className={isExpanded ? 'text-[#1A1A1A]' : 'text-zinc-400'} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-lg">{tutorial.title}</h3>
                    <p className="text-sm text-zinc-500 mt-0.5">{tutorial.description}</p>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className={`px-2 py-0.5 rounded text-xs border ${DIFFICULTY_COLORS[tutorial.difficulty]}`}>
                      {tutorial.difficulty}
                    </span>
                    <span className="flex items-center gap-1 text-xs text-zinc-600">
                      <Clock size={12} /> {tutorial.duration}
                    </span>
                    {completedCount > 0 && (
                      <span className="text-xs text-[#1A1A1A]">{completedCount}/{tutorial.steps.length}</span>
                    )}
                    <ChevronDown size={18} className={`text-zinc-600 transition ${isExpanded ? 'rotate-180' : ''}`} />
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
                      <div className="px-6 pb-6 border-t border-zinc-800">
                        <div className="mt-4 space-y-3">
                          {tutorial.steps.map((step, i) => {
                            const isCompleted = completedSteps[`${tutorial.id}-${i}`];
                            return (
                              <div
                                key={i}
                                className={`flex gap-4 p-4 rounded-lg transition cursor-pointer ${
                                  isCompleted ? 'bg-[#F5F5F4] border border-black/10' : 'bg-zinc-800/50 hover:bg-zinc-800'
                                }`}
                                onClick={() => toggleStep(tutorial.id, i)}
                              >
                                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-sm font-bold ${
                                  isCompleted ? 'bg-[#1A1A1A] text-white' : 'bg-zinc-700 text-zinc-400'
                                }`}>
                                  {isCompleted ? <Check size={16} /> : i + 1}
                                </div>
                                <div className="flex-1 min-w-0">
                                  <h4 className={`font-medium text-sm ${isCompleted ? 'text-[#1A1A1A]' : 'text-zinc-200'}`}>
                                    {step.title}
                                  </h4>
                                  <p className="text-sm text-zinc-500 mt-1 leading-relaxed whitespace-pre-line">
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
                            onClick={() => navigate('/app/workspace')}
                            className="flex items-center gap-2 px-4 py-2 bg-[#1A1A1A] hover:bg-[#333] rounded-lg text-sm font-medium transition"
                          >
                            <Play size={14} /> Try it now
                          </button>
                          <span className="text-xs text-zinc-600">
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
            <Search size={48} className="mx-auto text-zinc-700 mb-4" />
            <p className="text-zinc-500">No tutorials found. Try a different search or category.</p>
          </div>
        )}

        {/* Bottom CTA */}
        <div className="mt-16 text-center p-8 rounded-2xl border border-zinc-800 bg-zinc-900/50">
          <h3 className="text-xl font-bold mb-2">Need more help?</h3>
          <p className="text-zinc-500 mb-4">Check the API docs, learn page, or open the Workspace and ask CrucibAI directly.</p>
          <div className="flex items-center justify-center gap-3 flex-wrap">
            <button onClick={() => navigate('/docs')} className="flex items-center gap-2 px-5 py-2.5 border border-zinc-700 hover:border-zinc-600 rounded-lg text-sm font-medium transition">
              <Code size={16} /> API Docs
            </button>
            <button onClick={() => navigate('/learn')} className="flex items-center gap-2 px-5 py-2.5 border border-zinc-700 hover:border-zinc-600 rounded-lg text-sm font-medium transition">
              <BookOpen size={16} /> Learn
            </button>
            <button onClick={() => navigate('/app/workspace')} className="flex items-center gap-2 px-5 py-2.5 bg-[#1A1A1A] hover:bg-[#333] rounded-lg text-sm font-medium transition">
              <Zap size={16} /> Open Workspace
            </button>
          </div>
        </div>
      </div>

      <PublicFooter />
    </div>
  );
}


import { Link } from 'react-router-dom';
import PublicNav from '../components/PublicNav';
import PublicFooter from '../components/PublicFooter';

const ENTRIES = [
  {
    version: '2.5',
    date: 'April 8, 2026',
    tag: 'Proof',
    tagColor: '#10b981',
    items: [
      'Live Railway golden path completed 18/18 steps with LLM, preview, proof, deploy build, deploy publish readiness, and no background crash',
      '50-prompt repeatability benchmark added to the backend release gate',
      'Generated apps can now publish to an in-platform public URL at /published/{job_id}/',
      'Benchmark, status, and security trust pages updated to reflect proof-backed release discipline',
    ],
  },
  {
    version: '2.4',
    date: 'March 17, 2026',
    tag: 'Major',
    tagColor: '#10b981',
    items: [
      'Live build progress on dashboard — see every running build, percent complete, current agent, and quality score in real time',
      'Pricing doubled across all tiers — same price, 2x credits. Free: 200, Builder: 500, Pro: 1000, Scale: 2000, Teams: 5000',
      'New user signup now includes 200 free credits — build 2 full apps before ever paying',
      'Share button in workspace — one click copies your project link',
      'Premium agent prompts — Frontend Generation now produces Tailwind + design-system-grade code, not generic divs',
      'Engine Room complete — Model Manager, Fine-Tuning, Safety Dashboard, VibeCode, IDE all in sidebar',
      'Sign up / Log in in all navigation bars (desktop + mobile)',
    ],
  },
  {
    version: '2.3',
    date: 'March 10, 2026',
    tag: 'Feature',
    tagColor: '#3b82f6',
    items: [
      'AI company layer — Model Manager (routing modes, model registry), Fine-Tuning (jobs, datasets), Safety Dashboard (red-team testing)',
      'System prompt guardrails — competitor mentions redirect to building, not code generation',
      'Build history panel in Workspace — see all prior builds with timestamps, quality scores, and token usage',
      'Quick build mode — runs only first 2 phases for a 2-minute preview',
      'ZIP upload (bring your code) — JSZip parser loads existing code directly into the workspace',
    ],
  },
  {
    version: '2.2',
    date: 'March 3, 2026',
    tag: 'Feature',
    tagColor: '#3b82f6',
    items: [
      'Voice input — 9 languages, audio transcription via Whisper',
      'Image-to-code — attach any screenshot or mockup and build from it',
      '12+ file types in the attach button — ZIP, audio, images, PDFs, code files',
      'Mobile app builds — Expo project generation with App Store and Play Store submission guide',
      'Export center — ZIP, GitHub push, Vercel deploy, Netlify deploy all in one place',
    ],
  },
  {
    version: '2.1',
    date: 'February 20, 2026',
    tag: 'Infrastructure',
    tagColor: '#737373',
    items: [
      'Deployed to Railway — live at crucibai-production.up.railway.app',
      'PostgreSQL via asyncpg — full relational database with pgvector memory',
      'Agent cache — 50% cache hit rate cuts AI costs in half on repeated build patterns',
      'Incremental execution — fingerprint-based agent skipping for faster iterations',
      'Parallel workers — multiple agents run simultaneously in the DAG',
    ],
  },
  {
    version: '2.0',
    date: 'February 1, 2026',
    tag: 'Launch',
    tagColor: '#8b5cf6',
    items: [
      'Agent swarm DAG — every agent has a defined role, dependencies, and system prompt',
      'LLM router — intelligently routes tasks across Cerebras (fast), Llama 70B (free), and Claude Haiku (quality)',
      'Braintree payments — 5 pricing tiers with annual discount and custom credit slider',
      'MFA, Google OAuth, JWT auth — production-grade security from day one',
      'AgentMonitor — real-time phase timeline, per-agent tokens, quality score, retry controls',
    ],
  },
];

export default function Changelog() {
  return (
    <div className="min-h-screen bg-[#FAFAF8]">
      <PublicNav />
      <div className="max-w-3xl mx-auto px-6 py-24">
        <div className="mb-16">
          <p className="text-xs uppercase tracking-widest text-gray-400 mb-3">What's new</p>
          <h1 className="text-4xl font-semibold text-gray-900 mb-4">Changelog</h1>
          <p className="text-gray-500">Every update to CrucibAI, in order. The product gets better every week.</p>
        </div>

        <div className="space-y-16">
          {ENTRIES.map((entry, i) => (
            <div key={i} className="flex gap-8">
              <div className="w-32 shrink-0 text-right">
                <p className="text-sm font-semibold text-gray-900">v{entry.version}</p>
                <p className="text-xs text-gray-400 mt-1">{entry.date}</p>
                <span className="inline-block mt-2 text-xs px-2 py-0.5 rounded-full font-medium text-white" style={{ background: entry.tagColor }}>
                  {entry.tag}
                </span>
              </div>
              <div className="flex-1 border-l border-gray-200 pl-8">
                <ul className="space-y-3">
                  {entry.items.map((item, j) => (
                    <li key={j} className="flex items-start gap-3 text-sm text-gray-700">
                      <span className="mt-2 w-1.5 h-1.5 rounded-full bg-gray-400 shrink-0" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-20 pt-10 border-t border-gray-200 text-center">
          <p className="text-sm text-gray-400 mb-4">Want to be notified of new releases?</p>
          <Link to="/auth?mode=register" className="inline-flex items-center gap-2 px-6 py-3 bg-black text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition">
            Sign up free →
          </Link>
        </div>
      </div>
      <PublicFooter />
    </div>
  );
}

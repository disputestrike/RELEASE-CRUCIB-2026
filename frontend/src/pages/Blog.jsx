import { Link } from 'react-router-dom';
import PublicNav from '../components/PublicNav';
import PublicFooter from '../components/PublicFooter';

const POSTS = [
  {
    slug: 'why-crucibai-inevitable-ai',
    title: 'Why CrucibAI? Inevitable AI for Builds and Automations',
    excerpt: 'The same AI that builds your app runs inside your automations. One platform for web, mobile, and workflows — no code required.',
    date: '2026-02',
  },
  {
    slug: 'bring-your-code-transfer-fix-continue',
    title: 'Bring Your Code: Transfer, Fix, Continue, or Rebuild',
    excerpt: 'Paste, ZIP, or Git URL — we stand up your project in the Workspace. Run security scan, accessibility check, and keep building.',
    date: '2026-02',
  },
  {
    slug: 'how-marketers-use-crucibai',
    title: 'How Marketers and Agencies Use CrucibAI',
    excerpt: 'Build landing pages, funnels, and blogs; automate digests and follow-ups with the same AI. A tool for customer acquisition.',
    date: '2026-02',
  },
  {
    slug: 'security-trust-platform-and-your-code',
    title: 'Security and Trust: Platform and Your Code',
    excerpt: 'How we keep the platform safe (auth, rate limits, CORS, HTTPS) and how you can run Security scan and Accessibility check on your code.',
    date: '2026-02',
  },
  {
    slug: 'prompt-to-automation-describe-and-go',
    title: 'Prompt-to-Automation: Describe Your Workflow in Plain Language',
    excerpt: 'Describe what you want in one sentence; we create the agent. Schedule, webhook, run_agent — no node-by-node setup required.',
    date: '2026-02',
  },
];

export default function Blog() {
  return (
    <div className="min-h-screen bg-[#050505] text-gray-200">
      <PublicNav />
      <main className="max-w-3xl mx-auto px-6 py-16">
        <h1 className="text-4xl font-bold text-white mb-2">Blog</h1>
        <p className="text-gray-400 mb-12">Product updates, use cases, and how to get the most from CrucibAI — Inevitable AI.</p>
        <ul className="space-y-8">
          {POSTS.map((post) => (
            <li key={post.slug} className="border-b border-white/10 pb-8">
              <Link to={`/blog#${post.slug}`} className="block group" aria-label={post.title}>
                <h2 className="text-xl font-semibold text-white group-hover:text-blue-400 transition mb-2">{post.title}</h2>
                <p className="text-gray-400 text-sm mb-2">{post.excerpt}</p>
                <span className="text-xs text-gray-500">{post.date}</span>
              </Link>
            </li>
          ))}
        </ul>
        <p className="mt-12 text-sm text-gray-500">
          More posts and SEO content coming. For docs and guides, see <Link to="/learn" className="text-blue-400 hover:text-blue-300">Learn</Link> and <Link to="/features" className="text-blue-400 hover:text-blue-300">Features</Link>.
        </p>
      </main>
      <PublicFooter />
    </div>
  );
}

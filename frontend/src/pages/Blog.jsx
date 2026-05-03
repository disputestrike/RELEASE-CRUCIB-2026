import { Link, useParams, useNavigate } from 'react-router-dom';
import PublicNav from '../components/PublicNav';
import PublicFooter from '../components/PublicFooter';

const POSTS = [
  {
    slug: 'why-crucibai-inevitable-ai',
    title: 'Why CrucibAI? Inevitable AI for Builds and Automations',
    excerpt: 'Proof-gated web, Expo mobile, and automation artifacts share one evidence model when configured gates pass.',
    date: '2026-02',
    body: [
      'Most tools do one thing well: build an app from a prompt, or run automations, or write code in your IDE. CrucibAI is built around a different idea: the same AI that builds your app should run inside your automations.',
      'When you describe an app, our swarm of agents and sub-agents — plan, frontend, backend, design, content, tests, deploy — builds it in a plan-first DAG. When you create your own agents (on a schedule or via webhook), you can add a step that runs one of those agents by name: Content Agent, Scraping Agent, and more. So the AI that built your landing page can also write your daily digest or your lead follow-up.',
      'That is not just automation or app-from-prompt. It is the bridge: one workspace where proof-gated builds and guarded automation calls share the same evidence model.',
      'We call it inevitable AI because once you see the plan, phases, and Build Integrity score, the outcome is tied to artifacts instead of vague promises. Describe your idea; the system builds, validates, and shows what passed or what still needs repair.',
    ],
  },
  {
    slug: 'bring-your-code-transfer-fix-continue',
    title: 'Bring Your Code: Transfer, Fix, Continue, or Rebuild',
    excerpt: 'ZIP and reconstructed workspaces are checked by Import Doctor. Git, paste, dependency repair, and accessibility proof stay conditional until fully verified.',
    date: '2026-02',
    body: [
      'You do not have to start from scratch. If you have a ZIP or reconstructed workspace, CrucibAI can run Import Doctor to inspect package manager, framework, entrypoints, ZIP safety, and Build Integrity evidence.',
      'Universal paste, Git clone, dependency repair, and preview-after-import repair are still conditional until end-to-end proof is added. The public claim is intentionally narrower: ZIP/workspace import validation exists today.',
      'After import validation, choose what to do next: inspect the report, repair issues, continue building, or export a proof-gated handoff when the gates pass.',
      'So: ZIP or reconstructed workspace -> Import Doctor -> Build Integrity result -> fix, improve, continue, or rebuild with evidence.',
    ],
  },
  {
    slug: 'how-marketers-use-crucibai',
    title: 'How Marketers and Agencies Use CrucibAI',
    excerpt: 'Build landing pages, funnels, and blogs; automate digests and follow-ups with the same AI. A tool for customer acquisition.',
    date: '2026-02',
    body: [
      'CrucibAI is built for anyone who needs to get in front of people: marketers, agencies, and teams that spend money to make money. One platform for the assets (sites, funnels, forms) and the workflows (emails, content, lead capture).',
      'Build marketing assets in plain language: Build a landing page with hero, features, pricing, and waitlist form. Build a blog with post list and detail view. Build a page with a form that saves leads and sends a thank-you email. You get exportable web artifacts after proof gates pass. Provider deploys require configured targets; ZIP export remains the default handoff.',
      'Then automate. Create an agent on a schedule or webhook: “Every morning at 9, summarize key updates and email them to me.” “When someone submits the contact form, run our Content Agent to draft a reply and post it to Slack.” The same agent swarm that builds your app runs inside these workflows. So the AI that built your site also powers your daily digest and follow-ups.',
      'We don’t replace your ad spend or channels. We help you own the destination — the sites and forms — and automate the follow-up. We generate ad copy and creatives; you (or your stack) push to Meta/Google. You run the ads; we built the stack.',
    ],
  },
  {
    slug: 'security-trust-platform-and-your-code',
    title: 'Security and Trust: Platform and Your Code',
    excerpt: 'How platform controls, baseline security checks, and Build Integrity gates work today, plus what remains roadmap-only.',
    date: '2026-02',
    body: [
      'We take security in two places: the platform we run, and the code you build or bring.',
      'On the platform we use rate limiting (per user and per IP), security headers (CSP, HSTS, X-Frame-Options, and more), request validation (max body size, blocking suspicious patterns), and CORS from configurable origins. Auth is JWT with bcrypt for passwords; we support MFA and API keys. We do not return secrets in API responses; PayPal payment events are handled server-side. We block disposable emails at signup and cap referral abuse. So the service itself is hardened for production use.',
      'For your code we give you evidence-backed checks. Build Integrity blocks likely client-exposed secrets and weak artifacts, and baseline security scans can produce reports. Comprehensive CORS/auth/tenancy security doctors and WCAG/axe/keyboard/contrast accessibility proof are still not claimable for every project.',
      'So: we protect the platform, and we give you visibility and checks for what you build and bring. No magic — just controls and feedback you can act on.',
    ],
  },
  {
    slug: 'prompt-to-automation-describe-and-go',
    title: 'Prompt-to-Automation: Describe Your Workflow in Plain Language',
    excerpt: 'Describe a workflow; configured schedules, webhooks, and run_agent actions are validated by the automation profile before they are treated as ready.',
    date: '2026-02',
    body: [
      'You don’t have to pick triggers and actions one by one. If you can say what you want in a sentence, we can create the agent for you.',
      'Examples: Every morning at 9, summarize the key updates and email them to me. When someone submits the contact form, run our Content Agent to draft a reply for approval. We turn the description into a structured spec when the configured trigger/action profile is available.',
      'Prompt-to-automation uses the same evidence rule as app builds: describe the outcome, generate the workflow, then validate the bridge, schedule, webhook, or run_agent call before claiming it is ready.',
      'Describe your automation in plain language. The system creates a draft, validates the configured path, and shows what passed or needs repair.',
    ],
  },
  {
    slug: 'monday-to-friday-ship-in-days',
    title: 'Monday to Friday: Ship in Days, Not Weeks',
    excerpt: 'Describe your idea on Monday. By Friday you can have proof-gated web artifacts, optional configured automations, and copy to test.',
    date: '2026-02',
    body: [
      'We do not say AI runs your company. We say: describe your idea once, get a plan, run proof-gated build phases, and export the artifacts that pass validation.',
      'Here is how it compresses. On Monday you describe what you want: a landing page, a waitlist, a simple dashboard, or a site plus a daily digest and follow-up when someone signs up. We turn that into a plan, then run the required phases. You see available phase telemetry, proof artifacts, and the Build Integrity score. By the end of the week you can have validated web output, forms, and optional automations when schedules or webhooks are configured.',
      'We also generate copy and creatives — headlines, body, CTA. You (or your stack) push those to Meta/Google. So: one operator plus CrucibAI instead of hiring a designer, copywriter, funnel builder, and dev. Execution compression, not magic.',
      'Same evidence model for app builds and guarded workflow calls. You run the ads; CrucibAI helps build the stack that passes proof gates.',
    ],
  },
];

export default function Blog() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const post = slug ? POSTS.find((p) => p.slug === slug) : null;

  if (post) {
    return (
      <div className="min-h-screen bg-[#FAFAF8] text-[#1A1A1A]">
        <PublicNav />
        <main className="max-w-3xl mx-auto px-6 py-16">
          <button
            type="button"
            onClick={() => navigate('/blog')}
            className="text-[#666666] hover:text-[#1A1A1A] text-sm mb-8 transition"
          >
            ← Back to Blog
          </button>
          <article>
            <h1 className="text-4xl font-bold text-[#1A1A1A] mb-2">{post.title}</h1>
            <p className="text-gray-500 text-sm mb-10">{post.date}</p>
            <div className="space-y-6 text-gray-300 leading-relaxed">
              {post.body.map((paragraph, i) => (
                <p key={i}>{paragraph}</p>
              ))}
            </div>
          </article>
          <p className="mt-12">
            <Link to="/blog" className="text-[#1A1A1A] hover:text-[#333]">
              ← All posts
            </Link>
          </p>
        </main>
        <PublicFooter />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FAFAF8] text-[#1A1A1A]">
      <PublicNav />
      <main className="max-w-3xl mx-auto px-6 py-16">
        <h1 className="text-4xl font-bold text-[#1A1A1A] mb-2">Blog</h1>
        <p className="text-[#666666] mb-12">Product updates, use cases, and how to get the most from CrucibAI — Inevitable AI.</p>
        <ul className="space-y-8">
          {POSTS.map((p) => (
            <li key={p.slug} className="border-b border-white/10 pb-8">
              <Link to={`/blog/${p.slug}`} className="block group" aria-label={p.title}>
                <h2 className="text-xl font-semibold text-[#1A1A1A] group-hover:text-[#333] transition mb-2">{p.title}</h2>
                <p className="text-[#666666] text-sm mb-2">{p.excerpt}</p>
                <span className="text-xs text-gray-500">{p.date}</span>
              </Link>
            </li>
          ))}
        </ul>
        <p className="mt-12 text-sm text-gray-500">
          More posts and SEO content coming. For docs and guides, see <Link to="/learn" className="text-[#1A1A1A] hover:text-[#333]">Learn</Link> and <Link to="/features" className="text-[#1A1A1A] hover:text-[#333]">Features</Link>.
        </p>
      </main>
      <PublicFooter />
    </div>
  );
}

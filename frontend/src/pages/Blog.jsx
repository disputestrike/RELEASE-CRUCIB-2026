import { Link, useParams, useNavigate } from 'react-router-dom';
import PublicNav from '../components/PublicNav';
import PublicFooter from '../components/PublicFooter';

const POSTS = [
  {
    slug: 'why-crucibai-inevitable-ai',
    title: 'Why CrucibAI? Inevitable AI for Builds and Automations',
    excerpt: 'The same AI that builds your app runs inside your automations. One platform for web, mobile, and workflows — no code required.',
    date: '2026-02',
    body: [
      'Most tools do one thing well: build an app from a prompt, or run automations, or write code in your IDE. CrucibAI is built around a different idea: the same AI that builds your app should run inside your automations.',
      'When you describe an app, our 120-agent swarm — plan, frontend, backend, design, content, tests, deploy — builds it in a plan-first DAG. When you create your own agents (on a schedule or via webhook), you can add a step that runs one of those agents by name: Content Agent, Scraping Agent, and more. So the AI that built your landing page can also write your daily digest or your lead follow-up.',
      'That’s not “we do automation” (N8N does) or “we do app from prompt” (Manus does). It’s the combo and the bridge: one platform where you build apps and run automations that call the same AI. No other product does that today.',
      'We call it inevitable AI because once you see the plan, the phases, and the quality score, the outcome isn’t a black box — it’s visible, retryable, and under your control. Describe your idea; we build the site and the automations. You get the stack in days, not weeks.',
    ],
  },
  {
    slug: 'bring-your-code-transfer-fix-continue',
    title: 'Bring Your Code: Transfer, Fix, Continue, or Rebuild',
    excerpt: 'Paste, ZIP, or Git URL — we stand up your project in the Workspace. Run security scan, accessibility check, and keep building.',
    date: '2026-02',
    body: [
      'You don’t have to start from scratch. If you have code from another builder, a local project, or a Git repo, you can bring it into CrucibAI and keep going.',
      'We support three ways to transfer: paste (single or multiple files), upload a ZIP (e.g. export from Replit, Bolt, or a folder), or paste a Git URL. We create an imported project, write the files into the workspace, and open it in the Workspace so you can edit, run Security scan, run Accessibility check, and use “Understand this project” to get a short summary of stack and structure.',
      'After we receive your code we stand it up, then you choose what to do next. Fix something with Validate-and-fix or chat (“fix the login bug”). Improve it (“add dark mode,” “make it responsive”). Or continue building in the same project and deploy when you’re ready. If you’d rather start over, you can explicitly choose “rebuild from start” — we never overwrite without your permission.',
      'So: paste, ZIP, or Git URL → we stand it up. You fix, improve, continue, or rebuild. Your code, your choice.',
    ],
  },
  {
    slug: 'how-marketers-use-crucibai',
    title: 'How Marketers and Agencies Use CrucibAI',
    excerpt: 'Build landing pages, funnels, and blogs; automate digests and follow-ups with the same AI. A tool for customer acquisition.',
    date: '2026-02',
    body: [
      'CrucibAI is built for anyone who needs to get in front of people: marketers, agencies, and teams that spend money to make money. One platform for the assets (sites, funnels, forms) and the workflows (emails, content, lead capture).',
      'Build marketing assets in plain language: “Build a landing page with hero, features, pricing, and waitlist form.” “Build a blog with post list and detail view.” “Build a page with a form that saves leads and sends a thank-you email.” You get real, deployable output — not mockups. Deploy to Vercel or Netlify, or download a ZIP.',
      'Then automate. Create an agent on a schedule or webhook: “Every morning at 9, summarize key updates and email them to me.” “When someone submits the contact form, run our Content Agent to draft a reply and post it to Slack.” The same 120-agent swarm that builds your app runs inside these workflows. So the AI that built your site also powers your daily digest and follow-ups.',
      'We don’t replace your ad spend or channels. We help you own the destination — the sites and forms — and automate the follow-up. We generate ad copy and creatives; you (or your stack) push to Meta/Google. You run the ads; we built the stack.',
    ],
  },
  {
    slug: 'security-trust-platform-and-your-code',
    title: 'Security and Trust: Platform and Your Code',
    excerpt: 'How we keep the platform safe (auth, rate limits, CORS, HTTPS) and how you can run Security scan and Accessibility check on your code.',
    date: '2026-02',
    body: [
      'We take security in two places: the platform we run, and the code you build or bring.',
      'On the platform we use rate limiting (per user and per IP), security headers (CSP, HSTS, X-Frame-Options, and more), request validation (max body size, blocking suspicious patterns), and CORS from configurable origins. Auth is JWT with bcrypt for passwords; we support MFA and API keys. We don’t return secrets in API responses; Stripe and webhook signatures are verified. We block disposable emails at signup and cap referral abuse. So the service itself is hardened for production use.',
      'For your code we give you tools. In the Workspace you can run a Security scan on your project — we analyze the code and return a report. You can run an Accessibility check for labels, contrast, keyboard, and ARIA. When you bring code (paste, ZIP, or Git), you can run those same checks on the imported files. We don’t run your app in production; we help you see risks and fix them before you deploy.',
      'So: we protect the platform, and we give you visibility and checks for what you build and bring. No magic — just controls and feedback you can act on.',
    ],
  },
  {
    slug: 'prompt-to-automation-describe-and-go',
    title: 'Prompt-to-Automation: Describe Your Workflow in Plain Language',
    excerpt: 'Describe what you want in one sentence; we create the agent. Schedule, webhook, run_agent — no node-by-node setup required.',
    date: '2026-02',
    body: [
      'You don’t have to pick triggers and actions one by one. If you can say what you want in a sentence, we can create the agent for you.',
      'Examples: “Every morning at 9, summarize the key updates and email them to me.” “When someone submits the contact form, run our Content Agent to draft a reply and post it to Slack for approval.” We take that description, turn it into a structured spec (trigger type, schedule or webhook, and actions like run_agent, email, HTTP, Slack), and create the agent. You can edit it afterward — add steps, change the schedule, or run it now to test.',
      'That’s prompt-to-automation. Same idea as app-from-prompt: describe the outcome, we build the thing. Zapier and N8N are node-based; you connect triggers and actions manually. We let you describe the outcome and we generate the workflow, using the same AI that powers app builds. So your daily digest, lead follow-up, or content pipeline can be “one sentence → agent created” and then you refine.',
      'Describe your automation in plain language. We create it. Then you run it, edit it, and own it.',
    ],
  },
  {
    slug: 'monday-to-friday-ship-in-days',
    title: 'Monday to Friday: Ship in Days, Not Weeks',
    excerpt: 'Describe your idea on Monday. By Friday you can have a live site, automations for leads and content, and the copy to run ads.',
    date: '2026-02',
    body: [
      'We don’t say AI runs your company. We say: describe your idea once — we build the site and the automations. You get a live funnel, lead capture, and ad-ready copy in days, not weeks.',
      'Here’s how it compresses. On Monday you describe what you want: a landing page, a waitlist, a simple dashboard, or “a site plus a daily digest and follow-up when someone signs up.” We turn that into a plan, then run the 120-agent swarm — frontend, backend, design, content, tests, deploy. You see the plan and the phases; you get a quality score and can retry a phase if something fails. By the end of the week you can have a live site, forms that capture leads, and optional automations (schedule or webhook) that use the same AI for digests and follow-ups.',
      'We also generate copy and creatives — headlines, body, CTA. You (or your stack) push those to Meta/Google. So: one operator plus CrucibAI instead of hiring a designer, copywriter, funnel builder, and dev. Execution compression, not magic.',
      'Same AI that builds your app runs your workflows. You run the ads; we built the stack. That’s the deal.',
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
            <Link to="/blog" className="text-#c0c0c0 hover:text-#d0d0d0">
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
                <h2 className="text-xl font-semibold text-[#1A1A1A] group-hover:text-#c0c0c0 transition mb-2">{p.title}</h2>
                <p className="text-[#666666] text-sm mb-2">{p.excerpt}</p>
                <span className="text-xs text-gray-500">{p.date}</span>
              </Link>
            </li>
          ))}
        </ul>
        <p className="mt-12 text-sm text-gray-500">
          More posts and SEO content coming. For docs and guides, see <Link to="/learn" className="text-#c0c0c0 hover:text-#d0d0d0">Learn</Link> and <Link to="/features" className="text-#c0c0c0 hover:text-#d0d0d0">Features</Link>.
        </p>
      </main>
      <PublicFooter />
    </div>
  );
}

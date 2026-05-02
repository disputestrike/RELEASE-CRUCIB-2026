/**
 * Home / Landing Page — Arctic Clarity Design System
 * Sections: Hero, Social Proof, Features, How It Works, Testimonials, CTA, Footer
 */

import { Link } from "wouter";
import {
  ArrowRight,
  BarChart3,
  Users,
  Zap,
  Shield,
  Globe,
  CheckCircle,
  Star,
  TrendingUp,
  Clock,
  Layers,
  ChevronRight,
} from "lucide-react";
import MarketingNav from "@/components/MarketingNav";
import { toast } from "sonner";

const HERO_BG = "https://d2xsxph8kpxj0f.cloudfront.net/310519663191500671/ZV5yZCPfMdcMC4W5dBWVqf/hero-bg-GdJ2JKEWntoCpsHhDqF2jE.webp";
const DASHBOARD_IMG = "https://d2xsxph8kpxj0f.cloudfront.net/310519663191500671/ZV5yZCPfMdcMC4W5dBWVqf/dashboard-preview-AFX93c4Eyyq3tPFytaH4qX.webp";
const ANALYTICS_IMG = "https://d2xsxph8kpxj0f.cloudfront.net/310519663191500671/ZV5yZCPfMdcMC4W5dBWVqf/feature-analytics-4SABvdkiYsFmDsHF864D5a.webp";
const COLLAB_IMG = "https://d2xsxph8kpxj0f.cloudfront.net/310519663191500671/ZV5yZCPfMdcMC4W5dBWVqf/feature-collab-mTeNfvZwo3F8D2BiEmcrTM.webp";

const features = [
  {
    icon: BarChart3,
    color: "bg-indigo-50 text-indigo-600",
    title: "Real-time Analytics",
    desc: "Track every metric that matters. From revenue to churn, get instant insights with interactive charts and customizable dashboards.",
  },
  {
    icon: Users,
    color: "bg-emerald-50 text-emerald-600",
    title: "Team Collaboration",
    desc: "Invite your whole team with role-based access control. Comment, share reports, and work together in real time.",
  },
  {
    icon: Zap,
    color: "bg-amber-50 text-amber-600",
    title: "Workflow Automation",
    desc: "Automate repetitive tasks with no-code triggers. Connect your tools and let FlowDesk handle the rest.",
  },
  {
    icon: Shield,
    color: "bg-rose-50 text-rose-600",
    title: "Enterprise Security",
    desc: "SOC 2 Type II certified. End-to-end encryption, SSO, and audit logs keep your data safe and compliant.",
  },
  {
    icon: Globe,
    color: "bg-sky-50 text-sky-600",
    title: "Global Infrastructure",
    desc: "Deployed across 12 regions worldwide. 99.99% uptime SLA with automatic failover and zero-downtime deploys.",
  },
  {
    icon: Layers,
    color: "bg-violet-50 text-violet-600",
    title: "150+ Integrations",
    desc: "Connect Slack, Salesforce, HubSpot, Stripe, and 150+ more tools in one click. Your data, unified.",
  },
];

const stats = [
  { value: "50K+", label: "Active teams" },
  { value: "$2.4B", label: "Revenue tracked" },
  { value: "99.99%", label: "Uptime SLA" },
  { value: "4.9/5", label: "Customer rating" },
];

const testimonials = [
  {
    name: "Sarah Chen",
    role: "Head of Growth, Vercel",
    avatar: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=48&h=48&fit=crop&crop=face",
    quote: "FlowDesk replaced four separate tools for us. Our team's productivity jumped 40% in the first month. The analytics alone are worth it.",
    rating: 5,
  },
  {
    name: "Marcus Williams",
    role: "CTO, Loom",
    avatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=48&h=48&fit=crop&crop=face",
    quote: "The automation features are incredible. We automated our entire onboarding flow and reduced manual work by 80%. Game changer.",
    rating: 5,
  },
  {
    name: "Priya Patel",
    role: "VP Engineering, Linear",
    avatar: "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=48&h=48&fit=crop&crop=face",
    quote: "Best-in-class security and the most intuitive UI I've seen in a SaaS product. Our entire org adopted it within a week.",
    rating: 5,
  },
];

const steps = [
  { num: "01", title: "Connect your tools", desc: "Link your existing stack in minutes with our one-click integrations." },
  { num: "02", title: "Define your metrics", desc: "Choose what matters to your business and build your custom dashboard." },
  { num: "03", title: "Automate & scale", desc: "Set up workflows, alerts, and reports that run on autopilot." },
];

export default function Home() {
  const handleComingSoon = () => toast.info("Feature coming soon!");

  return (
    <div className="min-h-screen bg-white">
      <MarketingNav />

      {/* ─── Hero ─── */}
      <section
        className="relative pt-24 pb-20 lg:pt-32 lg:pb-28 overflow-hidden"
        style={{
          backgroundImage: `url(${HERO_BG})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
        }}
      >
        {/* Subtle overlay for text contrast */}
        <div className="absolute inset-0 bg-white/60" />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
            {/* Left: Copy */}
            <div className="page-enter">
              {/* Badge */}
              <div className="inline-flex items-center gap-2 bg-indigo-50 border border-indigo-200 rounded-full px-3 py-1.5 mb-6">
                <span className="w-2 h-2 bg-indigo-500 rounded-full animate-pulse" />
                <span className="text-xs font-semibold text-indigo-700">Now with AI-powered insights</span>
              </div>

              <h1
                className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-slate-900 leading-[1.1] tracking-tight mb-6"
                style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
              >
                The SaaS platform
                <br />
                <span className="bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent">
                  built for growth
                </span>
              </h1>

              <p className="text-lg text-slate-600 leading-relaxed mb-8 max-w-lg">
                FlowDesk unifies your analytics, team workflows, and automation in one beautifully designed workspace. Stop context-switching. Start shipping.
              </p>

              <div className="flex flex-col sm:flex-row gap-3 mb-10">
                <Link href="/dashboard">
                  <a className="btn-gradient inline-flex items-center justify-center gap-2 text-base font-semibold px-6 py-3.5 rounded-xl">
                    Start for free
                    <ArrowRight className="w-4 h-4" />
                  </a>
                </Link>
                <button
                  className="inline-flex items-center justify-center gap-2 text-base font-semibold px-6 py-3.5 rounded-xl border border-slate-300 text-slate-700 hover:bg-slate-50 transition-colors"
                  onClick={handleComingSoon}
                >
                  Watch demo
                </button>
              </div>

              {/* Social proof mini */}
              <div className="flex items-center gap-3">
                <div className="flex -space-x-2">
                  {[
                    "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=32&h=32&fit=crop&crop=face",
                    "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=32&h=32&fit=crop&crop=face",
                    "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=32&h=32&fit=crop&crop=face",
                    "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=32&h=32&fit=crop&crop=face",
                  ].map((src, i) => (
                    <img
                      key={i}
                      src={src}
                      alt=""
                      className="w-8 h-8 rounded-full border-2 border-white object-cover"
                    />
                  ))}
                </div>
                <div>
                  <div className="flex gap-0.5">
                    {[...Array(5)].map((_, i) => (
                      <Star key={i} className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                    ))}
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">Loved by <strong className="text-slate-700">50,000+</strong> teams</p>
                </div>
              </div>
            </div>

            {/* Right: Dashboard preview */}
            <div className="relative stagger-2 page-enter">
              <div className="relative rounded-2xl overflow-hidden shadow-2xl border border-slate-200/80 ring-1 ring-slate-900/5">
                <img
                  src={DASHBOARD_IMG}
                  alt="FlowDesk Dashboard"
                  className="w-full h-auto"
                />
                {/* Floating stat card */}
                <div className="absolute bottom-4 left-4 bg-white rounded-xl shadow-lg border border-slate-200 px-4 py-3 flex items-center gap-3">
                  <div className="w-9 h-9 bg-emerald-100 rounded-lg flex items-center justify-center">
                    <TrendingUp className="w-4 h-4 text-emerald-600" />
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Monthly Revenue</p>
                    <p className="text-sm font-bold text-slate-900">+18.4% <span className="text-emerald-600">↑</span></p>
                  </div>
                </div>
              </div>
              {/* Decorative blur */}
              <div className="absolute -bottom-6 -right-6 w-48 h-48 bg-violet-200/40 rounded-full blur-3xl -z-10" />
            </div>
          </div>
        </div>
      </section>

      {/* ─── Stats ─── */}
      <section className="border-y border-slate-200 bg-slate-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
            {stats.map(({ value, label }) => (
              <div key={label} className="text-center">
                <p
                  className="text-3xl lg:text-4xl font-extrabold text-slate-900 mb-1"
                  style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
                >
                  {value}
                </p>
                <p className="text-sm text-slate-500">{label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Logos ─── */}
      <section className="py-14 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm font-medium text-slate-400 uppercase tracking-widest mb-8">
            Trusted by teams at
          </p>
          <div className="flex flex-wrap justify-center items-center gap-x-12 gap-y-6 opacity-40 grayscale">
            {["Vercel", "Linear", "Loom", "Notion", "Stripe", "Figma"].map((name) => (
              <span
                key={name}
                className="text-xl font-bold text-slate-700"
                style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
              >
                {name}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Features ─── */}
      <section id="features" className="py-20 lg:py-28 bg-slate-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <span className="inline-block text-xs font-semibold text-indigo-600 uppercase tracking-widest mb-3">
              Everything you need
            </span>
            <h2
              className="text-3xl lg:text-4xl font-extrabold text-slate-900 mb-4"
              style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
            >
              One platform, infinite possibilities
            </h2>
            <p className="text-lg text-slate-500">
              From startup to enterprise, FlowDesk scales with your team and adapts to your workflow.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map(({ icon: Icon, color, title, desc }) => (
              <div key={title} className="card-elevated rounded-2xl p-6">
                <div className={`w-11 h-11 rounded-xl ${color} flex items-center justify-center mb-4`}>
                  <Icon className="w-5 h-5" />
                </div>
                <h3
                  className="text-base font-bold text-slate-900 mb-2"
                  style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
                >
                  {title}
                </h3>
                <p className="text-sm text-slate-500 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Feature Spotlight 1 ─── */}
      <section className="py-20 lg:py-28 bg-white overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-20 items-center">
            <div>
              <span className="inline-block text-xs font-semibold text-indigo-600 uppercase tracking-widest mb-3">
                Analytics
              </span>
              <h2
                className="text-3xl lg:text-4xl font-extrabold text-slate-900 mb-5"
                style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
              >
                Insights that drive decisions
              </h2>
              <p className="text-lg text-slate-500 mb-8">
                Stop guessing. FlowDesk's real-time analytics surface the metrics that matter most — revenue, retention, and growth — in one unified view.
              </p>
              <ul className="space-y-3 mb-8">
                {[
                  "Custom dashboards with drag-and-drop widgets",
                  "Automated weekly reports delivered to your inbox",
                  "Cohort analysis and funnel visualization",
                  "AI-powered anomaly detection and alerts",
                ].map((item) => (
                  <li key={item} className="flex items-start gap-3 text-sm text-slate-600">
                    <CheckCircle className="w-5 h-5 text-emerald-500 flex-shrink-0 mt-0.5" />
                    {item}
                  </li>
                ))}
              </ul>
              <Link href="/dashboard">
                <a className="inline-flex items-center gap-2 text-sm font-semibold text-indigo-600 hover:text-indigo-700 transition-colors">
                  Explore analytics <ChevronRight className="w-4 h-4" />
                </a>
              </Link>
            </div>
            <div className="relative">
              <div className="rounded-2xl overflow-hidden shadow-xl border border-slate-200">
                <img src={ANALYTICS_IMG} alt="Analytics" className="w-full h-auto" />
              </div>
              <div className="absolute -top-4 -left-4 w-32 h-32 bg-indigo-100 rounded-full blur-3xl -z-10" />
            </div>
          </div>
        </div>
      </section>

      {/* ─── Feature Spotlight 2 ─── */}
      <section className="py-20 lg:py-28 bg-slate-50 overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-20 items-center">
            <div className="order-2 lg:order-1 relative">
              <div className="rounded-2xl overflow-hidden shadow-xl border border-slate-200">
                <img src={COLLAB_IMG} alt="Collaboration" className="w-full h-auto" />
              </div>
              <div className="absolute -bottom-4 -right-4 w-32 h-32 bg-emerald-100 rounded-full blur-3xl -z-10" />
            </div>
            <div className="order-1 lg:order-2">
              <span className="inline-block text-xs font-semibold text-emerald-600 uppercase tracking-widest mb-3">
                Collaboration
              </span>
              <h2
                className="text-3xl lg:text-4xl font-extrabold text-slate-900 mb-5"
                style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
              >
                Your team, in perfect sync
              </h2>
              <p className="text-lg text-slate-500 mb-8">
                Assign tasks, share context, and automate handoffs. FlowDesk keeps everyone aligned without the endless Slack threads.
              </p>
              <ul className="space-y-3 mb-8">
                {[
                  "Role-based permissions for every team member",
                  "Shared workspaces with real-time collaboration",
                  "Automated task routing and notifications",
                  "Audit logs for full accountability",
                ].map((item) => (
                  <li key={item} className="flex items-start gap-3 text-sm text-slate-600">
                    <CheckCircle className="w-5 h-5 text-emerald-500 flex-shrink-0 mt-0.5" />
                    {item}
                  </li>
                ))}
              </ul>
              <Link href="/team">
                <a className="inline-flex items-center gap-2 text-sm font-semibold text-emerald-600 hover:text-emerald-700 transition-colors">
                  Meet the team features <ChevronRight className="w-4 h-4" />
                </a>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ─── How It Works ─── */}
      <section className="py-20 lg:py-28 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-xl mx-auto mb-16">
            <span className="inline-block text-xs font-semibold text-indigo-600 uppercase tracking-widest mb-3">
              How it works
            </span>
            <h2
              className="text-3xl lg:text-4xl font-extrabold text-slate-900"
              style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
            >
              Up and running in minutes
            </h2>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {steps.map(({ num, title, desc }) => (
              <div key={num} className="relative text-center">
                <div className="w-14 h-14 rounded-2xl bg-indigo-600 text-white flex items-center justify-center mx-auto mb-5">
                  <span className="text-lg font-extrabold" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                    {num}
                  </span>
                </div>
                <h3
                  className="text-lg font-bold text-slate-900 mb-2"
                  style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
                >
                  {title}
                </h3>
                <p className="text-sm text-slate-500 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Testimonials ─── */}
      <section id="testimonials" className="py-20 lg:py-28 bg-slate-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-xl mx-auto mb-16">
            <span className="inline-block text-xs font-semibold text-indigo-600 uppercase tracking-widest mb-3">
              Testimonials
            </span>
            <h2
              className="text-3xl lg:text-4xl font-extrabold text-slate-900"
              style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
            >
              Loved by engineering leaders
            </h2>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {testimonials.map(({ name, role, avatar, quote, rating }) => (
              <div key={name} className="card-elevated rounded-2xl p-6 flex flex-col">
                <div className="flex gap-0.5 mb-4">
                  {[...Array(rating)].map((_, i) => (
                    <Star key={i} className="w-4 h-4 fill-amber-400 text-amber-400" />
                  ))}
                </div>
                <p className="text-sm text-slate-600 leading-relaxed flex-1 mb-6">"{quote}"</p>
                <div className="flex items-center gap-3">
                  <img src={avatar} alt={name} className="w-10 h-10 rounded-full object-cover" />
                  <div>
                    <p className="text-sm font-semibold text-slate-900">{name}</p>
                    <p className="text-xs text-slate-500">{role}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── CTA ─── */}
      <section className="py-20 lg:py-28 bg-gradient-to-br from-indigo-600 to-violet-700">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2
            className="text-3xl lg:text-5xl font-extrabold text-white mb-5"
            style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
          >
            Ready to ship faster?
          </h2>
          <p className="text-lg text-indigo-200 mb-10 max-w-xl mx-auto">
            Join 50,000+ teams already using FlowDesk to build, measure, and grow. No credit card required.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/dashboard">
              <a className="inline-flex items-center justify-center gap-2 bg-white text-indigo-700 font-bold px-8 py-4 rounded-xl hover:bg-indigo-50 transition-colors text-base">
                Start for free
                <ArrowRight className="w-4 h-4" />
              </a>
            </Link>
            <Link href="/pricing">
              <a className="inline-flex items-center justify-center gap-2 bg-white/10 text-white font-semibold px-8 py-4 rounded-xl hover:bg-white/20 transition-colors text-base border border-white/20">
                View pricing
              </a>
            </Link>
          </div>
          <p className="mt-6 text-xs text-indigo-300">Free plan forever · No credit card · Cancel anytime</p>
        </div>
      </section>

      {/* ─── Footer ─── */}
      <footer className="bg-slate-900 text-slate-400 py-14">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-8 mb-12">
            <div className="col-span-2">
              <div className="flex items-center gap-2.5 mb-4">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
                  <Zap className="w-4 h-4 text-white" />
                </div>
                <span className="font-bold text-lg text-white" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                  FlowDesk
                </span>
              </div>
              <p className="text-sm leading-relaxed mb-4 max-w-xs">
                The modern SaaS platform for teams that move fast and build things that last.
              </p>
              <div className="flex items-center gap-1 text-xs">
                <Clock className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-emerald-400 font-medium">All systems operational</span>
              </div>
            </div>
            {[
              { title: "Product", links: ["Features", "Pricing", "Changelog", "Roadmap"] },
              { title: "Company", links: ["About", "Blog", "Careers", "Press"] },
              { title: "Legal", links: ["Privacy", "Terms", "Security", "Cookies"] },
            ].map(({ title, links }) => (
              <div key={title}>
                <p className="text-xs font-semibold text-slate-300 uppercase tracking-widest mb-4">{title}</p>
                <ul className="space-y-2.5">
                  {links.map((link) => (
                    <li key={link}>
                      <a
                        href="#"
                        className="text-sm hover:text-white transition-colors"
                        onClick={(e) => { e.preventDefault(); toast.info("Feature coming soon!"); }}
                      >
                        {link}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <div className="border-t border-slate-800 pt-8 flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-xs">© 2026 FlowDesk, Inc. All rights reserved.</p>
            <p className="text-xs">Designed with care in San Francisco</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

import React, { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ChevronDown } from 'lucide-react';

/** Who it's for — deep links into /our-projects#solution-* */
const SOLUTION_LINKS = [
  { to: '/our-projects#solution-everyone', label: 'Everyone & non-builders', sub: 'Describe it in plain language — we build and automate.' },
  { to: '/our-projects#solution-founders', label: 'Founders', sub: 'Idea to MVP without a dev bench.' },
  { to: '/our-projects#solution-enterprise', label: 'Enterprise', sub: 'Security roadmap, audit artifacts, and scale.' },
  { to: '/our-projects#solution-pm', label: 'Project managers', sub: 'Plan-first builds your stakeholders can see.' },
  { to: '/our-projects#solution-designers', label: 'Designers', sub: 'Screenshots to validator-gated UI.' },
  { to: '/our-projects#solution-sales', label: 'Sales teams', sub: 'Decks, microsites, and follow-up flows.' },
  { to: '/our-projects#solution-marketers', label: 'Marketers', sub: 'Landing pages, funnels, and growth automations.' },
  { to: '/our-projects#solution-ops', label: 'Ops & RevOps', sub: 'Internal tools, digests, and webhooks.' },
  { to: '/our-projects#solution-developers', label: 'Developers', sub: 'ZIP import doctor, Git roadmap, full-stack targets.' },
];

const USE_CASE_LINKS = [
  { to: '/our-projects#use-case-poc', label: 'Proof of concept', sub: 'Spike ideas and demos in days.' },
  { to: '/our-projects#use-case-full-app', label: 'Full apps & SaaS', sub: 'Auth, DB, payments, Expo artifacts when requested.' },
  { to: '/our-projects#use-case-automation', label: 'Automation & agents', sub: 'Schedules, webhooks, run_agent.' },
  { to: '/our-projects#use-cases', label: 'All use cases', sub: 'Dashboards, stores, tools, and more.' },
];

/**
 * Header mega-menu: Our solution → audiences + use cases (links to story / our-projects anchors).
 */
export default function SolutionsNavDropdown({ triggerClassName = '' }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e) => {
      if (rootRef.current && !rootRef.current.contains(e.target)) setOpen(false);
    };
    const onKey = (e) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDoc);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <div className={`relative ${triggerClassName}`} ref={rootRef}>
      <button
        type="button"
        className="text-kimi-nav text-kimi-muted hover:text-kimi-text transition flex items-center gap-1 py-1"
        aria-expanded={open}
        aria-haspopup="true"
        onClick={() => setOpen((v) => !v)}
      >
        Our solution
        <ChevronDown className={`w-4 h-4 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} aria-hidden />
      </button>
      {open && (
        <div
          className="absolute left-0 top-full z-[100] mt-2 w-[min(720px,calc(100vw-2rem))] rounded-xl border border-white/10 bg-[var(--kimi-bg)] shadow-2xl p-5 md:p-6"
          role="menu"
        >
          <div className="grid gap-8 sm:grid-cols-2">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-kimi-muted mb-3">Who it&apos;s for</p>
              <ul className="space-y-0.5">
                {SOLUTION_LINKS.map((item) => (
                  <li key={item.to}>
                    <Link
                      to={item.to}
                      role="menuitem"
                      className="block rounded-lg px-2 py-2 hover:bg-white/5 transition"
                      onClick={() => setOpen(false)}
                    >
                      <span className="text-sm font-medium text-kimi-text">{item.label}</span>
                      <span className="block text-xs text-kimi-muted leading-snug">{item.sub}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-kimi-muted mb-3">Use cases</p>
              <ul className="space-y-0.5">
                {USE_CASE_LINKS.map((item) => (
                  <li key={item.to}>
                    <Link
                      to={item.to}
                      role="menuitem"
                      className="block rounded-lg px-2 py-2.5 hover:bg-white/5 transition"
                      onClick={() => setOpen(false)}
                    >
                      <span className="text-sm font-medium text-kimi-text">{item.label}</span>
                      <span className="block text-xs text-kimi-muted leading-snug">{item.sub}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export { SOLUTION_LINKS, USE_CASE_LINKS };

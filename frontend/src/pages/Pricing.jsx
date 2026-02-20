import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Zap, Check, ArrowRight, Plus } from 'lucide-react';
import { useAuth, API } from '../App';
import PublicNav from '../components/PublicNav';
import PublicFooter from '../components/PublicFooter';
import axios from 'axios';

// Final Model: Starter, Builder, Pro, Agency (+ add-ons). No LLM names on landing/pricing (Manus-style).
const DEFAULT_BUNDLES = {
  starter: { credits: 100, price: 12.99, name: 'Starter', speed: 'Fast builds' },
  builder: { credits: 500, price: 29.99, name: 'Builder', speed: 'Fast builds' },
  pro: { credits: 2000, price: 79.99, name: 'Pro', speed: 'Priority speed' },
  agency: { credits: 10000, price: 199.99, name: 'Agency', speed: 'Priority speed' },
};
const BUNDLE_ORDER = ['starter', 'builder', 'pro', 'agency'];

const DEFAULT_ADDONS = {
  light: { credits: 50, price: 7, name: 'Light' },
  dev: { credits: 250, price: 30, name: 'Dev' },
};
const ADDON_ORDER = ['light', 'dev'];

// CrucibAI-specific features per plan (Manus-style: list what they get, not model names)
const PLAN_FEATURES = {
  starter: ['Landing pages & simple apps', 'Plan-first build & preview', 'Export to ZIP & GitHub', 'All features'],
  builder: ['Landing pages & full web apps', 'Plan-first build & live preview', 'Export to ZIP & GitHub', '120-agent swarm & templates'],
  pro: ['Everything in Builder', 'Dashboards & data-heavy apps', 'Priority build speed', 'Higher credit volume'],
  agency: ['Everything in Pro', 'High-volume builds', 'Priority speed & support', 'Team-ready credits'],
};

const CREDITS_PER_LANDING = 50;
const CREDITS_PER_APP = 100;
const RECOMMEND_ORDER = ['starter', 'builder', 'pro', 'agency'];

function OutcomeCalculator({ bundles, onSelectPlan }) {
  const [landings, setLandings] = useState(0);
  const [apps, setApps] = useState(0);
  const needed = landings * CREDITS_PER_LANDING + apps * CREDITS_PER_APP;
  let recommended = null;
  let recommendedCredits = 0;
  for (const key of RECOMMEND_ORDER) {
    const b = bundles[key];
    if (b && b.credits >= needed) {
      recommended = key;
      recommendedCredits = b.credits;
      break;
    }
  }
  if (!recommended && bundles.agency) {
    recommended = 'agency';
    recommendedCredits = bundles.agency.credits;
  }
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-6">
        <label className="flex items-center gap-2">
          <span className="text-[#1A1A1A] text-sm">Landing pages:</span>
          <input
            type="number"
            min={0}
            value={landings}
            onChange={(e) => setLandings(parseInt(e.target.value, 10) || 0)}
            className="w-20 px-2 py-1.5 rounded-lg bg-white border border-stone-200 text-[#1A1A1A]"
          />
        </label>
        <label className="flex items-center gap-2">
          <span className="text-[#1A1A1A] text-sm">Full apps:</span>
          <input
            type="number"
            min={0}
            value={apps}
            onChange={(e) => setApps(parseInt(e.target.value, 10) || 0)}
            className="w-20 px-2 py-1.5 rounded-lg bg-white border border-stone-200 text-[#1A1A1A]"
          />
        </label>
      </div>
      <p className="text-sm text-[#1A1A1A]">
        Estimated credits needed: <strong className="text-[#1A1A1A]">{needed}</strong>
        {recommended && (
          <> — We recommend <strong className="text-[#1A1A1A]">{bundles[recommended]?.name || recommended}</strong> ({recommendedCredits} credits/mo).</>
        )}
      </p>
      {recommended && (
        <button
          type="button"
          onClick={() => onSelectPlan(recommended)}
          className="px-4 py-2 rounded-lg bg-[#1A1A1A] hover:opacity-90 text-white text-sm font-medium"
        >
          Get {bundles[recommended]?.name || recommended}
        </button>
      )}
    </div>
  );
}

export default function Pricing() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [bundles, setBundles] = useState(DEFAULT_BUNDLES);
  const [addons, setAddons] = useState(DEFAULT_ADDONS);
  const [annualPrices, setAnnualPrices] = useState({ starter: 129, builder: 299, pro: 799, agency: 1999 });
  const [billingPeriod, setBillingPeriod] = useState('monthly'); // 'monthly' | 'annual'

  useEffect(() => {
    axios.get(`${API}/tokens/bundles`, { timeout: 5000 })
      .then((r) => {
        if (r.data?.bundles && typeof r.data.bundles === 'object') {
          const b = {};
          const a = {};
          for (const [key, val] of Object.entries(r.data.bundles)) {
            const credits = val.credits ?? (val.tokens / 1000);
            const item = { credits, price: val.price, name: val.name || key, speed: val.speed || '' };
            if (ADDON_ORDER.includes(key)) a[key] = item;
            else if (BUNDLE_ORDER.includes(key)) b[key] = item;
          }
          if (Object.keys(b).length > 0) setBundles((prev) => ({ ...prev, ...b }));
          if (Object.keys(a).length > 0) setAddons((prev) => ({ ...prev, ...a }));
        }
        if (r.data?.annual_prices && typeof r.data.annual_prices === 'object') setAnnualPrices((prev) => ({ ...prev, ...r.data.annual_prices }));
      })
      .catch(() => {});
  }, []);

  return (
    <div className="min-h-screen bg-kimi-bg text-kimi-text grid-pattern-kimi">
      <PublicNav />
      <div className="max-w-6xl mx-auto px-6 py-16">
        <div className="text-center mb-16">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Plans</span>
          <h1 className="text-kimi-section font-bold text-kimi-text mt-2 mb-4">Pricing</h1>
          <p className="text-kimi-muted max-w-xl mx-auto">Inevitable outcomes: plan-first, 120-agent swarm, full transparency. Free tier includes 50 credits. No surprises, no hidden limitations.</p>
          <div className="mt-8 max-w-2xl mx-auto p-4 rounded-xl border border-stone-200 bg-white text-left">
            <p className="text-sm font-medium text-[#1A1A1A] mb-2">Why CrucibAI — Inevitable AI</p>
            <ul className="text-sm text-[#1A1A1A] space-y-1">
              <li>• 120-agent swarm, 99.2% success — measured, not promised.</li>
              <li>• Plan-first, full transparency — know exactly what you&apos;re building.</li>
              <li>• No surprises — credits, caps, and rollover are transparent.</li>
            </ul>
          </div>
          <div className="mt-6 max-w-2xl mx-auto p-4 rounded-xl border border-stone-200 bg-white text-left">
            <p className="text-sm font-medium text-[#1A1A1A] mb-2">vs Lovable</p>
            <p className="text-sm text-[#1A1A1A] mb-2">Lovable charges $25/month for 100 credits — plus a separate bill for Lovable Cloud for deployment. CrucibAI: $12.99 for 100 credits. Add-ons (Light $7, Dev $30) when you need more — Lovable has no top-up.</p>
            <p className="text-sm text-[#1A1A1A]">Half the price. Web, mobile, and automations in one platform.</p>
          </div>
        </div>

        {/* Free tier */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-12 p-8 rounded-2xl border border-stone-200 bg-white max-w-2xl mx-auto shadow-sm"
        >
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
            <div>
              <h2 className="text-2xl font-semibold mb-2">Start for free</h2>
              <p className="text-stone-500 mb-4">50 credits. Build landing pages, export, and deploy. No credit card.</p>
              <ul className="space-y-2 text-sm text-[#1A1A1A]">
                <li className="flex items-center gap-2"><Check className="w-4 h-4 text-green-500 shrink-0" /> 50 credits for landing pages</li>
                <li className="flex items-center gap-2"><Check className="w-4 h-4 text-green-500 shrink-0" /> Plan-first build & live preview</li>
                <li className="flex items-center gap-2"><Check className="w-4 h-4 text-green-500 shrink-0" /> Export to ZIP & push to GitHub</li>
                <li className="flex items-center gap-2"><Check className="w-4 h-4 text-green-500 shrink-0" /> 120-agent swarm, templates & prompt library</li>
              </ul>
            </div>
            <div className="shrink-0">
              <p className="text-3xl font-bold mb-2">$0</p>
              <p className="text-stone-500 text-sm mb-4">No credit card required</p>
              <button
                onClick={() => navigate(user ? '/app' : '/auth?mode=register')}
                className="w-full md:w-auto px-6 py-3 bg-[#1A1A1A] text-white font-medium rounded-lg hover:opacity-90 transition"
              >
                {user ? 'Go to Workspace' : 'Get started free'}
              </button>
            </div>
          </div>
        </motion.div>

        {/* Credit plans */}
        <h2 className="text-xl font-semibold text-center mb-2">Credit plans</h2>
        <p className="text-stone-500 text-center mb-4">More credits, faster builds. Unused credits roll over.</p>
        <div className="flex justify-center gap-2 mb-10">
          <button
            type="button"
            onClick={() => setBillingPeriod('monthly')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${billingPeriod === 'monthly' ? 'bg-[#1A1A1A] text-white' : 'bg-gray-200 text-[#1A1A1A] hover:bg-gray-300'}`}
          >
            Monthly
          </button>
          <button
            type="button"
            onClick={() => setBillingPeriod('annual')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${billingPeriod === 'annual' ? 'bg-[#1A1A1A] text-white' : 'bg-gray-200 text-[#1A1A1A] hover:bg-gray-300'}`}
          >
            Annual <span className="text-stone-500 text-xs">Save 17%</span>
          </button>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {BUNDLE_ORDER.filter((k) => bundles[k]).map((key, i) => {
            const b = bundles[key];
            const isBuilder = key === 'builder';
            const features = PLAN_FEATURES[key] || ['All features'];
            const showSpeed = b.speed && !String(b.speed).toLowerCase().includes('haiku') && !String(b.speed).toLowerCase().includes('cerebras');
            const annualPrice = annualPrices[key];
            const displayPrice = billingPeriod === 'annual' && annualPrice ? annualPrice : b.price;
            const monthlyEquivalent = billingPeriod === 'annual' && annualPrice ? (annualPrice / 12).toFixed(2) : null;
            const savePct = billingPeriod === 'annual' && annualPrice && b.price ? Math.round((1 - annualPrice / (b.price * 12)) * 100) : 0;
            return (
              <motion.div
                key={key}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className={`relative p-6 rounded-2xl border border-stone-200 bg-white shadow-sm hover:border-stone-300 transition ${
                  isBuilder ? 'ring-2 ring-[#1A1A1A]/10' : ''
                }`}
              >
                {isBuilder && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full bg-[#1A1A1A] text-[#FAFAF8] text-xs font-medium">
                    Popular
                  </span>
                )}
                <div className="flex items-center gap-2 mb-4">
                  <h3 className="text-lg font-semibold">{b.name}</h3>
                </div>
                <div className="mb-2">
                  <span className="text-3xl font-bold">${Number(displayPrice).toFixed(2)}</span>
                  <span className="text-stone-500 font-normal text-base ml-1">{billingPeriod === 'annual' ? '/year' : '/month'}</span>
                  {monthlyEquivalent && <span className="text-stone-500 text-sm block mt-0.5">${monthlyEquivalent}/mo</span>}
                  {savePct > 0 && <span className="text-stone-500 text-xs font-medium">Save {savePct}%</span>}
                </div>
                <p className="text-stone-500 text-sm mb-1">{b.credits} credits per month</p>
                {showSpeed && <p className="text-stone-500 text-xs mb-4">{b.speed}</p>}
                <ul className="space-y-2 text-xs text-[#1A1A1A] mb-6">
                  {features.map((f, j) => (
                    <li key={j} className="flex items-center gap-2"><Check className="w-3.5 h-3.5 text-green-500 shrink-0" /> {f}</li>
                  ))}
                  <li className="flex items-center gap-2"><Check className="w-3.5 h-3.5 text-green-500 shrink-0" /> Unused credits roll over</li>
                </ul>
                <button
                  onClick={() => navigate(user ? '/app/tokens' : '/auth?mode=register')}
                  className={`w-full py-2.5 rounded-lg font-medium transition flex items-center justify-center gap-2 text-white ${
                    isBuilder ? 'bg-[#1A1A1A] hover:opacity-90' : 'bg-[#1A1A1A] hover:opacity-90'
                  }`}
                >
                  {user ? 'Buy credits' : 'Get started'}
                  <ArrowRight className="w-4 h-4" />
                </button>
              </motion.div>
            );
          })}
        </div>

        {/* Agent templates note */}
        <p className="text-center text-[#1A1A1A] text-sm mt-8 max-w-2xl mx-auto">
          Every paid plan includes 5 pre-built automation agent templates (daily digest, lead finder, inbox summarizer, status checker, YouTube poster). Describe your automation in plain language — we create it.
        </p>

        {/* Add-ons */}
        <h2 className="text-lg font-semibold text-center mt-14 mb-2">Add-ons</h2>
        <p className="text-zinc-500 text-center mb-6">One-time top-ups. Buy as many as you need, anytime—no limit. Credits roll over. Light (50 credits, $7) or Dev (250 credits, $30).</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 max-w-2xl mx-auto">
          {ADDON_ORDER.filter((k) => addons[k]).map((key) => {
            const a = addons[key];
            return (
              <motion.div
                key={key}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-4 p-6 rounded-2xl border border-stone-200 bg-white shadow-sm"
              >
                <Plus className="w-5 h-5 text-stone-500 shrink-0" />
                <div className="min-w-0 flex-1">
                  <span className="font-medium text-[#1A1A1A]">{a.name}</span>
                  <span className="text-stone-500 text-sm ml-2">— {a.credits} credits</span>
                </div>
                <span className="text-lg font-bold text-[#1A1A1A]">${Number(a.price).toFixed(2)}</span>
                <button
                  type="button"
                  onClick={() => {
                    if (user) {
                      navigate('/app/tokens', { state: { addon: key } });
                    } else {
                      const redirect = `/app/tokens?addon=${encodeURIComponent(key)}`;
                      navigate(`/auth?mode=register&redirect=${encodeURIComponent(redirect)}`);
                    }
                  }}
                  className="py-2 px-4 rounded-lg bg-[#1A1A1A] hover:opacity-90 text-white text-sm font-medium shrink-0"
                >
                  {user ? 'Buy' : 'Get started'}
                </button>
              </motion.div>
            );
          })}
        </div>

        <p className="text-center text-stone-500 text-sm mt-10">
          Need a custom plan? <Link to="/enterprise" className="text-[#1A1A1A] hover:underline">Enterprise / Contact sales</Link>.
        </p>

        {/* Outcome calculator */}
        <div className="mt-16 max-w-2xl mx-auto p-6 rounded-2xl border border-stone-200 bg-white shadow-sm">
          <h3 className="text-lg font-semibold mb-2">How many credits do I need?</h3>
          <p className="text-stone-500 text-sm mb-4">Rough guide: ~50 credits ≈ 1 landing page, ~100 credits ≈ 1 full app. Enter your goals for a recommendation.</p>
          <OutcomeCalculator bundles={bundles} onSelectPlan={(key) => {
            if (user) navigate('/app/tokens', { state: { addon: key } });
            else navigate(`/auth?mode=register&redirect=${encodeURIComponent('/app/tokens?addon=' + encodeURIComponent(key))}`);
          }} />
        </div>

        <div className="mt-20 max-w-2xl mx-auto border-t border-stone-200 pt-16">
          <h3 className="text-lg font-semibold mb-4">Clarity & how credits work</h3>
          <p className="text-stone-500 text-sm leading-relaxed">
            Know exactly what you're building. No surprises, no hidden limitations. Plans are monthly (or annual for 17% off). Each build uses credits (1 credit ≈ 1,000 tokens). Unused credits roll over. Add-ons anytime—no limit. Sustainable unit economics (e.g. 92% margin on paid) means we survive and keep improving—unlike VC-funded competitors.
          </p>
        </div>
      </div>
      <PublicFooter />
    </div>
  );
}

import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Zap, Check, ArrowRight } from 'lucide-react';
import { useAuth } from '../authContext';
import { API_BASE as API } from '../apiBase';
import PublicNav from '../components/PublicNav';
import PublicFooter from '../components/PublicFooter';
import axios from 'axios';
import { logApiError } from '../utils/apiError';

// Credit pricing model (capacity-based, no fixed app-count guarantees).
const DEFAULT_BUNDLES = {
  free:    { credits: 100,  price: 0,   name: 'Free' },
  builder: { credits: 500,  price: 20,  name: 'Builder' },
  pro:     { credits: 1500, price: 50,  name: 'Pro' },
  scale:   { credits: 3000, price: 100, name: 'Scale' },
  teams:   { credits: 6000, price: 200, name: 'Teams' },
};
const BUNDLE_ORDER = ['builder', 'pro', 'scale', 'teams'];

const PLAN_FEATURES = {
  free: [
    'Flexible credit capacity for proof-gated build workflows',
    'Live preview · export ZIP · push to GitHub',
    'Agent swarm & sub-agents · voice input · templates',
    'No credit card required',
  ],
  builder: [
    'Flexible monthly build capacity',
    'Supported targets: frontend, backend/API, DB/auth/payment scaffolds when requested',
    'Mobile: Expo project + store submission guide; submission not included',
    'Voice input · image-to-code · agent swarm',
  ],
  pro: [
    'Higher monthly build capacity',
    'Everything in Builder',
    'Max speed (priority queue) · priority support',
  ],
  scale: [
    'Large-scale monthly build capacity',
    'Everything in Pro',
    'High-volume builds for agencies & studios',
  ],
  teams: [
    'Team-wide monthly build capacity',
    'Everything in Scale',
    'Teams, agencies, white-label studios',
    'Priority support · team billing',
  ],
};

const CREDITS_PER_LANDING = 50;
const CREDITS_PER_APP = 100;
const RECOMMEND_ORDER = ['free', 'builder', 'pro', 'scale', 'teams'];
const CUSTOM_CREDITS_MIN = 500;
const CUSTOM_CREDITS_MAX = 20000;
const CUSTOM_CREDITS_STEP = 500;
const PRICE_PER_CREDIT = 0.05;

function CustomCreditsSlider({ min, max, step, pricePerCredit, user, token, api, navigate, axios, logApiError }) {
  const [credits, setCredits] = useState(min);
  const [loading, setLoading] = useState(false);
  const total = Math.round(credits * pricePerCredit * 100) / 100;

  const handleBuy = async () => {
    if (!user) {
      navigate('/app/tokens');
      return;
    }
    setLoading(true);
    try {
      navigate('/app/tokens', { state: { customCredits: credits } });
    } catch (e) {
      logApiError('Open Braintree credit checkout', e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6 rounded-2xl border border-stone-200 bg-white shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center gap-4">
        <div className="flex-1">
          <label className="block text-sm font-medium text-[#1A1A1A] mb-2">Credits: {credits}</label>
          <input
            type="range"
            min={min}
            max={max}
            step={step}
            value={credits}
            onChange={(e) => setCredits(Number(e.target.value))}
            className="w-full h-2 rounded-lg appearance-none bg-stone-200 accent-[#1A1A1A]"
          />
        </div>
        <div className="flex items-center gap-4 shrink-0">
          <span className="text-lg font-bold text-[#1A1A1A]">Total: ${total.toFixed(2)}</span>
          <button
            type="button"
            onClick={handleBuy}
            disabled={loading}
            className="py-2 px-4 rounded-lg bg-[#1A1A1A] hover:opacity-90 text-white text-sm font-medium disabled:opacity-60"
          >
            {loading ? 'Processing…' : `Buy ${credits} credits`}
          </button>
        </div>
      </div>
    </div>
  );
}

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
  if (!recommended && bundles.teams) {
    recommended = 'teams';
    recommendedCredits = bundles.teams.credits;
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
  const { user, token } = useAuth();
  const [bundles, setBundles] = useState(DEFAULT_BUNDLES);
  const [annualPrices, setAnnualPrices] = useState({ free: 0, builder: 199.99, pro: 499.99, scale: 999.99, teams: 1999.99 });
  const [billingPeriod, setBillingPeriod] = useState('monthly'); // 'monthly' | 'annual'
  const [customAddon, setCustomAddon] = useState({ min_credits: CUSTOM_CREDITS_MIN, max_credits: CUSTOM_CREDITS_MAX, price_per_credit: PRICE_PER_CREDIT });

  useEffect(() => {
    axios.get(`${API}/tokens/bundles`, { timeout: 5000 })
      .then((r) => {
        if (r.data?.bundles && typeof r.data.bundles === 'object') {
          const b = {};
          for (const [key, val] of Object.entries(r.data.bundles)) {
            if (!BUNDLE_ORDER.includes(key)) continue;
            const credits = val.credits ?? (val.tokens / 1000);
            b[key] = { credits, price: val.price, name: val.name || key };
          }
          if (Object.keys(b).length > 0) setBundles((prev) => ({ ...prev, ...b }));
        }
        if (r.data?.annual_prices && typeof r.data.annual_prices === 'object') setAnnualPrices((prev) => ({ ...prev, ...r.data.annual_prices }));
        if (r.data?.custom_addon && typeof r.data.custom_addon === 'object') {
          setCustomAddon((prev) => ({
            min_credits: r.data.custom_addon.min_credits ?? prev.min_credits,
            max_credits: r.data.custom_addon.max_credits ?? prev.max_credits,
            price_per_credit: r.data.custom_addon.price_per_credit ?? prev.price_per_credit,
          }));
        }
      })
      .catch((e) => logApiError('Pricing', e));
  }, []);

  return (
    <div className="min-h-screen bg-kimi-bg text-kimi-text grid-pattern-kimi">
      <PublicNav />
      <div className="max-w-6xl mx-auto px-6 py-16">
        <div className="text-center mb-16">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Plans</span>
          <h1 className="text-kimi-section font-bold text-kimi-text mt-2 mb-4">Pricing</h1>
          <p className="text-kimi-muted max-w-xl mx-auto">Credits fund proof-gated build workflows for web apps, backend/API projects, automations, and Expo mobile artifacts. Backend, database, auth, and payment scaffolds are generated when requested and validator-supported. Free tier: 100 credits.</p>
          <div className="mt-8 max-w-2xl mx-auto p-4 rounded-xl border border-stone-200 bg-white text-left">
            <p className="text-sm font-medium text-[#1A1A1A] mb-2">What each credit funds</p>
            <ul className="text-sm text-[#1A1A1A] space-y-1">
              <li>• Build profiles are checked by the Build Integrity Validator before completion.</li>
              <li>• Expo mobile outputs include source, app metadata, EAS config, and store submission guidance; store submission is not automatic.</li>
              <li>• Credit usage varies by build scope and validation depth.</li>
              <li>• Linear pricing — same $0.05/credit whether you buy 500 or 20,000.</li>
            </ul>
          </div>
          <p className="text-sm text-kimi-muted mt-4">Credits represent flexible build capacity, not fixed app-count guarantees.</p>
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
              <p className="text-stone-500 mb-4">100 credits. Flexible starter capacity. No credit card.</p>
              <ul className="space-y-2 text-sm text-[#1A1A1A]">
                <li className="flex items-center gap-2"><Check className="w-4 h-4 text-[#1A1A1A] shrink-0" /> Flexible starter build capacity</li>
                <li className="flex items-center gap-2"><Check className="w-4 h-4 text-[#1A1A1A] shrink-0" /> Live preview · export to ZIP · push to GitHub</li>
                <li className="flex items-center gap-2"><Check className="w-4 h-4 text-[#1A1A1A] shrink-0" /> Plan-first flow · voice input · templates &amp; prompts</li>
              </ul>
            </div>
            <div className="shrink-0">
              <p className="text-3xl font-bold mb-2">$0</p>
              <p className="text-stone-500 text-sm mb-4">Start today with the free tier.</p>
              <button
                onClick={() => navigate('/app')}
                className="w-full md:w-auto px-6 py-3 bg-[#1A1A1A] text-white font-medium rounded-lg hover:opacity-90 transition"
              >
                {user ? 'Go to Workspace' : 'Get started free'}
              </button>
            </div>
          </div>
        </motion.div>

        {/* Credit plans */}
        <h2 className="text-xl font-semibold text-center mb-2">Credit plans</h2>
        <p className="text-stone-500 text-center mb-4">More credits, faster builds. Plans are monthly; buy credits as you need them.</p>
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

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 items-stretch">
          {BUNDLE_ORDER.filter((k) => bundles[k]).map((key, i) => {
            const b = bundles[key];
            const isBuilder = key === 'builder';
            const features = PLAN_FEATURES[key] || ['All features'];
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
                className={`relative p-6 rounded-2xl border border-stone-200 bg-white shadow-sm hover:border-stone-300 transition flex flex-col min-h-[320px] ${
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
                <p className="text-stone-500 text-sm mb-4">{b.credits} credits per month</p>
                <ul className="space-y-2 text-xs text-[#1A1A1A] mb-6 flex-1">
                  {features.map((f, j) => (
                    <li key={j} className="flex items-center gap-2"><Check className="w-3.5 h-3.5 text-[#1A1A1A] shrink-0" /> {f}</li>
                  ))}
                </ul>
                <div className="mt-auto pt-2">
                  <button
                    onClick={() => navigate('/app/tokens')}
                    className="w-full py-2.5 rounded-lg font-medium transition flex items-center justify-center gap-2 text-white bg-[#1A1A1A] hover:opacity-90"
                  >
                    {user ? 'Buy credits' : 'Get started'}
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </motion.div>
            );
          })}
        </div>

        {/* Agent templates note */}
        <p className="text-center text-[#1A1A1A] text-sm mt-8 max-w-2xl mx-auto">
          Every paid plan includes 5 pre-built automation agent templates (daily digest, lead finder, inbox summarizer, status checker, YouTube poster). Describe your automation in plain language — we create it.
        </p>

        {/* Custom credits (slider) */}
        <h2 className="text-lg font-semibold text-center mt-14 mb-2">Need more credits?</h2>
        <p className="text-zinc-500 text-center mb-6">Buy in bulk at the same rate — ${(customAddon.price_per_credit || PRICE_PER_CREDIT).toFixed(2)}/credit · 500–{(customAddon.max_credits || CUSTOM_CREDITS_MAX).toLocaleString()} credits.</p>
        <CustomCreditsSlider
          min={customAddon.min_credits ?? CUSTOM_CREDITS_MIN}
          max={customAddon.max_credits ?? CUSTOM_CREDITS_MAX}
          step={CUSTOM_CREDITS_STEP}
          pricePerCredit={customAddon.price_per_credit ?? PRICE_PER_CREDIT}
          user={user}
          token={token}
          api={API}
          navigate={navigate}
          axios={axios}
          logApiError={logApiError}
        />

        <p className="text-center text-stone-500 text-sm mt-10">
          Need a custom plan? <Link to="/enterprise" className="text-[#1A1A1A] hover:underline">Enterprise</Link>
          {' · '}
          <Link to="/contact" className="text-[#1A1A1A] hover:underline">Contact us</Link>.
        </p>

        {/* Outcome calculator */}
        <div className="mt-16 max-w-2xl mx-auto p-6 rounded-2xl border border-stone-200 bg-white shadow-sm">
          <h3 className="text-lg font-semibold mb-2">How many credits do I need?</h3>
          <p className="text-stone-500 text-sm mb-4">Use this estimator for rough planning only; real credit usage depends on scope, stack, and repair depth.</p>
          <OutcomeCalculator bundles={bundles} onSelectPlan={(key) => {
            if (user) navigate('/app/tokens', { state: { addon: key } });
            else navigate('/app/tokens?addon=' + encodeURIComponent(key));
          }} />
        </div>

        <div className="mt-20 max-w-2xl mx-auto border-t border-stone-200 pt-16">
          <h3 className="text-lg font-semibold mb-4">Clarity & how credits work</h3>
          <p className="text-stone-500 text-sm leading-relaxed">
            Know what evidence supports each build. Plans are monthly (or annual for 17% off). Buy more credits anytime—no limit.
          </p>
        </div>
      </div>
      <PublicFooter />
    </div>
  );
}

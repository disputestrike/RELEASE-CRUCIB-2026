import { useState, useEffect, useRef } from 'react';
import { useLocation, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Zap, TrendingUp, ArrowUpRight, Clock, Check, 
  CreditCard, History, PieChart, Link2, Copy
} from 'lucide-react';
import { useAuth, API } from '../App';
import axios from 'axios';
import { logApiError } from '../utils/apiError';
import { PieChart as RePieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis } from 'recharts';

const BRAINTREE_DROPIN_SCRIPT = 'https://js.braintreegateway.com/web/dropin/1.44.1/js/dropin.min.js';

const loadBraintreeDropin = () => new Promise((resolve, reject) => {
  if (window.braintree?.dropin) {
    resolve(window.braintree.dropin);
    return;
  }
  const existing = document.querySelector(`script[src="${BRAINTREE_DROPIN_SCRIPT}"]`);
  if (existing) {
    existing.addEventListener('load', () => resolve(window.braintree.dropin), { once: true });
    existing.addEventListener('error', reject, { once: true });
    return;
  }
  const script = document.createElement('script');
  script.src = BRAINTREE_DROPIN_SCRIPT;
  script.async = true;
  script.onload = () => resolve(window.braintree.dropin);
  script.onerror = reject;
  document.body.appendChild(script);
});

const formatBraintreeError = (detail) => {
  if (!detail) return 'Braintree checkout could not complete. Please try again.';
  if (typeof detail === 'string') return detail;
  if (detail.error === 'braintree_requires_config') {
    const required = Array.isArray(detail.required_config) ? detail.required_config.join(', ') : 'Braintree credentials';
    return `Braintree is not configured yet. Add ${required} in Railway variables, then redeploy.`;
  }
  if (detail.error === 'braintree_sdk_missing') {
    return 'Braintree SDK is not installed in this deployment yet. Redeploy after the latest backend dependency update.';
  }
  if (detail.error === 'braintree_transaction_failed') {
    return 'Braintree rejected the transaction. Please check the card details or try another payment method.';
  }
  if (detail.message) return String(detail.message);
  return 'Braintree checkout could not complete. Please try again.';
};

const TokenCenter = () => {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const { user, token, refreshUser } = useAuth();
  const [bundles, setBundles] = useState({});
  const [history, setHistory] = useState([]);
  const [usage, setUsage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState(null);
  const addonFromPricing = location.state?.addon || searchParams.get('addon');
  const [activeTab, setActiveTab] = useState('purchase');
  const [referralCode, setReferralCode] = useState(null);
  const [referralStats, setReferralStats] = useState(null);
  const [referralCopied, setReferralCopied] = useState(false);
  const [braintreeTarget, setBraintreeTarget] = useState(null);
  const [braintreeReady, setBraintreeReady] = useState(false);
  const [braintreeError, setBraintreeError] = useState('');
  const [braintreeStatus, setBraintreeStatus] = useState(null);
  const braintreeInstanceRef = useRef(null);
  const bundleRefs = useRef({});
  const creditsFromPricing = Number(location.state?.customCredits || searchParams.get('credits') || 0);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const headers = token ? { Authorization: `Bearer ${token}` } : {};
        const [bundlesRes, historyRes, usageRes, codeRes, statsRes, paymentStatusRes] = await Promise.all([
          axios.get(`${API}/tokens/bundles`),
          axios.get(`${API}/tokens/history`, { headers }),
          axios.get(`${API}/tokens/usage`, { headers }),
          token ? axios.get(`${API}/referrals/code`, { headers }).catch((e) => { logApiError('TokenCenter referrals/code', e); return { data: {} }; }) : Promise.resolve({ data: {} }),
          token ? axios.get(`${API}/referrals/stats`, { headers }).catch((e) => { logApiError('TokenCenter referrals/stats', e); return { data: {} }; }) : Promise.resolve({ data: {} }),
          axios.get(`${API}/payments/braintree/status`).catch((e) => { logApiError('TokenCenter braintree/status', e); return { data: { provider: 'braintree', configured: false } }; })
        ]);
        setBundles(bundlesRes.data.bundles);
        setHistory(historyRes.data.history);
        setUsage(usageRes.data);
        setBraintreeStatus(paymentStatusRes.data);
        setReferralCode(codeRes.data?.code ?? null);
        setReferralStats(statsRes.data ? { this_month: statsRes.data.this_month, total: statsRes.data.total, cap: statsRes.data.cap } : null);
      } catch (e) {
        logApiError('TokenCenter fetchData', e);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [token]);

  // When coming from Pricing add-on link: show purchase tab and scroll to that bundle
  useEffect(() => {
    if (!addonFromPricing || loading || !bundles[addonFromPricing]) return;
    setActiveTab('purchase');
    const ref = bundleRefs.current[addonFromPricing];
    if (ref) {
      const t = setTimeout(() => ref.scrollIntoView({ behavior: 'smooth', block: 'center' }), 300);
      return () => clearTimeout(t);
    }
  }, [addonFromPricing, loading, bundles]);

  const openBraintreeCheckout = (target) => {
    if (!token) {
      window.location.href = '/login';
      return;
    }
    setBraintreeError('');
    setBraintreeReady(false);
    setBraintreeTarget(target);
    if (braintreeStatus?.configured === false) {
      setBraintreeError(formatBraintreeError({
        error: 'braintree_requires_config',
        required_config: braintreeStatus.required_config,
      }));
    }
  };

  const bundleOrder = ['builder', 'pro', 'scale', 'teams'];
  const sortedBundles = bundleOrder.filter(k => bundles[k]).map(k => ({ key: k, ...bundles[k] }));

  // Custom credits slider (100–5000 at $0.06/credit)
  const [customCredits, setCustomCredits] = useState(500);
  const customMin = 100;
  const customMax = 10000;
  const customStep = 100;
  const pricePerCredit = 0.06;
  const customTotal = Math.round(customCredits * pricePerCredit * 100) / 100;

  useEffect(() => {
    if (!creditsFromPricing) return;
    const boundedCredits = Math.max(customMin, Math.min(customMax, Math.round(creditsFromPricing / customStep) * customStep));
    setActiveTab('purchase');
    setCustomCredits(boundedCredits);
    openBraintreeCheckout({ credits: boundedCredits, label: `${boundedCredits} credits`, amount: Math.round(boundedCredits * pricePerCredit * 100) / 100 });
  }, [creditsFromPricing]);

  const completeBraintreeCheckout = async () => {
    if (!braintreeTarget || !braintreeInstanceRef.current) return;
    setPurchasing('braintree');
    try {
      const payload = await braintreeInstanceRef.current.requestPaymentMethod();
      await axios.post(
        `${API}/payments/braintree/checkout`,
        {
          bundle: braintreeTarget.bundle || null,
          credits: braintreeTarget.credits || null,
          payment_method_nonce: payload.nonce,
          device_data: payload.deviceData || null,
          idempotency_key: `web-${Date.now()}-${Math.random().toString(16).slice(2)}`,
        },
        { headers: { Authorization: `Bearer ${token}` } },
      );
      await refreshUser();
      const historyRes = await axios.get(`${API}/tokens/history`, { headers: { Authorization: `Bearer ${token}` } });
      setHistory(historyRes.data.history);
      setBraintreeTarget(null);
    } catch (e) {
      setBraintreeError(formatBraintreeError(e.response?.data?.detail));
      logApiError('TokenCenter Braintree checkout', e);
    } finally {
      setPurchasing(null);
    }
  };

  useEffect(() => {
    if (!braintreeTarget) return undefined;
    let cancelled = false;
    const setup = async () => {
      if (braintreeStatus?.configured === false) {
        setBraintreeError(formatBraintreeError({
          error: 'braintree_requires_config',
          required_config: braintreeStatus.required_config,
        }));
        return;
      }
      try {
        const [{ data }, dropin] = await Promise.all([
          axios.get(`${API}/payments/braintree/client-token`, { headers: { Authorization: `Bearer ${token}` } }),
          loadBraintreeDropin(),
        ]);
        if (cancelled) return;
        if (!data?.client_token) {
          throw new Error('Missing Braintree client token');
        }
        const instance = await dropin.create({
          authorization: data.client_token,
          container: '#braintree-dropin-container',
          card: { cardholderName: { required: false } },
        });
        if (cancelled) {
          instance.teardown?.();
          return;
        }
        braintreeInstanceRef.current = instance;
        setBraintreeReady(true);
      } catch (e) {
        setBraintreeError(formatBraintreeError(e.response?.data?.detail || e.message));
        logApiError('TokenCenter Braintree setup', e);
      }
    };
    setup();
    return () => {
      cancelled = true;
      setBraintreeReady(false);
      const instance = braintreeInstanceRef.current;
      braintreeInstanceRef.current = null;
      instance?.teardown?.().catch(() => {});
    };
  }, [braintreeTarget, braintreeStatus, token]);

  const usageChartData = usage?.by_agent ? Object.entries(usage.by_agent).map(([name, value]) => ({
    name,
    value
  })) : [];

  const COLORS = ['#1A1A1A', '#3D3D3D', '#525252', '#666666', '#737373', '#888888', '#9CA3AF', '#A3A3A3'];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-12 h-12 border-2 border-gray-400 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  const credits = user?.credit_balance ?? (user?.token_balance != null ? Math.floor(user.token_balance / 1000) : 0);

  return (
    <div className="space-y-8" data-testid="credit-center">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold mb-2">Credit Center</h1>
        <p className="text-[#666666]">Buy credits and track your usage. 50 credits ≈ 1 landing page · 100 credits ≈ 1 full app · 150 credits ≈ 1 mobile app. Credits roll over.</p>
      </div>

      {/* Balance Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="p-8 bg-gradient-to-br from-gray-200 to-gray-200 rounded-2xl border border-gray-400/30"
      >
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          <div>
            <p className="text-[#666666] mb-2 flex items-center gap-2">
              <Zap className="w-5 h-5 text-[#666666]" />
              Current Balance
            </p>
            <p className="text-5xl font-bold" data-testid="credit-balance">
              {credits.toLocaleString()}
            </p>
            <p className="text-gray-500 mt-2">credits available</p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-zinc-900/30 rounded-lg">
              <p className="text-sm text-gray-500">Total Used</p>
              <p className="text-2xl font-bold">{usage?.total_used?.toLocaleString() || 0}</p>
            </div>
            <div className="p-4 bg-zinc-900/30 rounded-lg">
              <p className="text-sm text-gray-500">Plan</p>
              <p className="text-2xl font-bold capitalize">{user?.plan || 'Free'}</p>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Referral: share link (free tier only for referrer reward) */}
      {referralCode && (
        <div className="p-6 bg-[#F5F5F4] rounded-xl border border-black/10">
          <h2 className="text-lg font-semibold text-[#1A1A1A] flex items-center gap-2 mb-2">
            <Link2 className="w-5 h-5 text-[#1A1A1A]" /> Invite friends — 100 credits each
          </h2>
          <p className="text-sm text-gray-500 mb-3">Share your link. When they sign up, they get 100 credits. You get 100 credits too if you're on the free plan (max 10 referrals/month).</p>
          <div className="flex flex-wrap items-center gap-2">
            <code className="px-3 py-2 bg-zinc-900/30 rounded-lg text-sm text-gray-300 break-all">
              {typeof window !== 'undefined' ? `${window.location.origin}/auth?ref=${referralCode}` : `/auth?ref=${referralCode}`}
            </code>
            <button
              type="button"
              onClick={() => {
                const url = typeof window !== 'undefined' ? `${window.location.origin}/auth?ref=${referralCode}` : '';
                if (url && navigator.clipboard) {
                  navigator.clipboard.writeText(url);
                  setReferralCopied(true);
                  setTimeout(() => setReferralCopied(false), 2000);
                }
              }}
              className="flex items-center gap-1 px-3 py-2 rounded-lg bg-[#1A1A1A] hover:bg-[#333] text-white text-sm font-medium"
            >
              <Copy className="w-4 h-4" /> {referralCopied ? 'Copied!' : 'Copy link'}
            </button>
          </div>
          {referralStats != null && (
            <p className="text-xs text-gray-500 mt-2">
              You've referred <strong>{referralStats.this_month ?? 0}</strong> this month (cap {referralStats.cap ?? 10}), <strong>{referralStats.total ?? 0}</strong> total.
            </p>
          )}
        </div>
      )}

      {/* Pricing section heading */}
      <div className="mb-4">
        <h2 className="text-xl font-semibold text-[#1A1A1A]">Pricing & usage</h2>
        <p className="text-sm text-gray-500">Credits for builds. Usage this period: {usage?.total_used?.toLocaleString() ?? 0} tokens</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-4 border-b border-black/10">
        {[
          { id: 'purchase', label: 'Buy Credits', icon: CreditCard },
          { id: 'history', label: 'History', icon: History },
          { id: 'usage', label: 'Usage Analytics', icon: PieChart }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-3 border-b-2 transition ${
              activeTab === tab.id
                ? 'border-gray-400 text-[#1A1A1A]'
                : 'border-transparent text-[#666666] hover:text-[#1A1A1A]'
            }`}
            data-testid={`tab-${tab.id}`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Purchase Tab */}
      {activeTab === 'purchase' && (
        <>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
          {sortedBundles.map((bundle, i) => (
            <motion.div
              key={bundle.key}
              ref={el => { if (el) bundleRefs.current[bundle.key] = el; }}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className={`p-6 rounded-xl border transition-all ${
                bundle.key === 'builder'
                  ? 'bg-[#F3F1ED] border-[#1A1A1A]/20 scale-105'
                  : 'bg-[#F5F5F4] border-black/10 hover:border-black/15'
              } ${addonFromPricing === bundle.key ? 'ring-2 ring-[#1A1A1A]/20' : ''}`}
            >
              {bundle.key === 'builder' && (
                <div className="text-xs font-medium text-[#1A1A1A] mb-4">MOST POPULAR</div>
              )}
              <h3 className="text-xl font-semibold mb-2">{bundle.name || bundle.key}</h3>
              <div className="mb-4">
                <span className="text-3xl font-bold">${Number(bundle.price).toFixed(2)}</span>
                <span className="text-gray-500 text-sm ml-1">/month</span>
              </div>
              <p className="text-[#666666] mb-6">
                <Zap className="w-4 h-4 inline mr-1 text-[#666666]" />
                {(bundle.credits ?? (bundle.tokens / 1000)).toLocaleString()} credits per month
              </p>
              <button
                onClick={() => handlePurchase(bundle.key)}
                disabled={purchasing === bundle.key}
                className={`w-full py-2.5 rounded-lg font-medium transition ${
                  bundle.key === 'builder'
                    ? 'bg-[#1A1A1A] hover:bg-[#333] text-white'
                    : 'bg-[#EBE8E2] hover:bg-[#E0DCD5] text-[#1A1A1A]'
                } disabled:opacity-50`}
                data-testid={`buy-${bundle.key}-btn`}
              >
                {purchasing === 'braintree' ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mx-auto"></div>
                ) : (
                  'Buy credits'
                )}
              </button>
            </motion.div>
          ))}
        </div>
        {/* Need more? Buy credits (slider) */}
        <div className="mt-8 p-6 rounded-xl border border-black/10 bg-[#F5F5F4]">
          <h3 className="text-lg font-semibold text-[#1A1A1A] mb-2">Need more? Buy credits</h3>
          <p className="text-sm text-gray-500 mb-4">100–5,000 credits at $0.06/credit. Credits roll over.</p>
          <div className="flex flex-col sm:flex-row sm:items-center gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-[#1A1A1A] mb-2">Credits: {customCredits}</label>
              <input
                type="range"
                min={customMin}
                max={customMax}
                step={customStep}
                value={customCredits}
                onChange={(e) => setCustomCredits(Number(e.target.value))}
                className="w-full h-2 rounded-lg appearance-none bg-stone-200 accent-[#1A1A1A]"
              />
            </div>
            <div className="flex items-center gap-4 shrink-0">
              <span className="text-lg font-bold text-[#1A1A1A]">Total: ${customTotal.toFixed(2)}</span>
              <button
                type="button"
                onClick={() => openBraintreeCheckout({ credits: customCredits, label: `${customCredits} credits`, amount: customTotal })}
                disabled={purchasing === 'custom' || purchasing === 'braintree'}
                className="py-2 px-4 rounded-lg bg-[#1A1A1A] hover:bg-[#333] text-white text-sm font-medium disabled:opacity-50"
              >
                {purchasing === 'custom' ? 'Processing…' : `Buy ${customCredits} credits`}
              </button>
              <button
                type="button"
                onClick={() => openBraintreeCheckout({ credits: customCredits, label: `${customCredits} credits`, amount: customTotal })}
                disabled={purchasing === 'custom' || purchasing === 'braintree'}
                className="py-2 px-4 rounded-lg border border-[#1A1A1A] text-[#1A1A1A] hover:bg-[#1A1A1A] hover:text-white text-sm font-medium disabled:opacity-50"
              >
                {purchasing === 'braintree' ? 'Processing...' : 'Pay with Braintree'}
              </button>
            </div>
          </div>
        </div>
        </>
      )}

      {/* History Tab */}
      {activeTab === 'history' && (
        <div className="p-6 bg-[#F5F5F4] rounded-xl border border-black/10">
          {history.length === 0 ? (
            <div className="text-center py-12">
              <History className="w-12 h-12 text-gray-600 mx-auto mb-4" />
              <p className="text-[#666666]">No transactions yet</p>
            </div>
          ) : (
            <div className="space-y-4">
              {history.map(item => (
                <div
                  key={item.id}
                  className="flex items-center justify-between p-4 bg-white/5 rounded-lg"
                >
                  <div className="flex items-center gap-4">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      item.type === 'purchase' ? 'bg-[#F3F1ED]' :
                      item.type === 'bonus' ? 'bg-[#F3F1ED]' :
                      item.type === 'refund' ? 'bg-[#F3F1ED]' :
                      'bg-[#F5F5F4]'
                    }`}>
                      {item.type === 'purchase' ? <CreditCard className="w-5 h-5 text-[#1A1A1A]" /> :
                       item.type === 'bonus' ? <Zap className="w-5 h-5 text-[#1A1A1A]" /> :
                       <ArrowUpRight className="w-5 h-5 text-[#1A1A1A]" />}
                    </div>
                    <div>
                      <p className="font-medium capitalize">{item.type}</p>
                      <p className="text-sm text-gray-500">
                        {item.description || (item.bundle ? `${item.bundle} bundle` : 'Credit transaction')}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={`font-bold ${
                      (item.credits ?? item.tokens) > 0 ? 'text-[#1A1A1A]' : 'text-[#666666]'
                    }`}>
                      {((item.credits ?? (item.tokens > 0 ? item.tokens / 1000 : 0)) > 0 ? '+' : '')}
                      {(item.credits ?? (item.tokens ? Math.floor(item.tokens / 1000) : 0))?.toLocaleString()} credits
                    </p>
                    <p className="text-sm text-gray-500">
                      {new Date(item.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Usage Tab */}
      {activeTab === 'usage' && (
        <div className="space-y-6">
          {/* Usage trends (last 14 days) */}
          {(usage?.daily_trend?.length > 0) && (
            <div className="p-6 bg-[#F5F5F4] rounded-xl border border-black/10">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-[#1A1A1A]" /> Usage trends
              </h3>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={[...(usage.daily_trend || [])].reverse()} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                    <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 11 }} tickFormatter={(v) => v.slice(5)} />
                    <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} tickFormatter={(v) => (v >= 1000 ? `${(v/1000).toFixed(1)}k` : v)} />
                    <Tooltip contentStyle={{ backgroundColor: '#111', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }} formatter={(v) => [v?.toLocaleString(), 'Tokens']} labelFormatter={(l) => l} />
                    <Bar dataKey="tokens" fill="#1A1A1A" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
          <div className="grid lg:grid-cols-2 gap-6">
          <div className="p-6 bg-[#F5F5F4] rounded-xl border border-black/10">
            <h3 className="text-lg font-semibold mb-6">Usage by Agent</h3>
            {usageChartData.length > 0 ? (
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <RePieChart>
                    <Pie
                      data={usageChartData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {usageChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ backgroundColor: '#111', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                      formatter={(value) => [value.toLocaleString(), 'Tokens']}
                    />
                  </RePieChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="h-64 flex items-center justify-center text-gray-500">
                No usage data yet
              </div>
            )}
          </div>
          
          <div className="p-6 bg-[#F5F5F4] rounded-xl border border-black/10">
            <h3 className="text-lg font-semibold mb-6">Top Consumers</h3>
            <div className="space-y-4">
              {usageChartData.slice(0, 5).map((item, i) => (
                <div key={item.name} className="flex items-center gap-4">
                  <div className="w-8 text-gray-500 font-mono">#{i + 1}</div>
                  <div className="flex-1">
                    <p className="font-medium">{item.name}</p>
                    <div className="relative h-2 bg-[#EBE8E2] rounded-full mt-1 overflow-hidden">
                      <div
                        className="absolute inset-y-0 left-0 rounded-full"
                        style={{
                          width: `${((usage?.total_used && item.value) ? (item.value / usage.total_used) * 100 : 0)}%`,
                          backgroundColor: COLORS[i % COLORS.length]
                        }}
                      />
                    </div>
                  </div>
                  <div className="text-right text-[#666666]">
                    {item.value.toLocaleString()}
                  </div>
                </div>
              ))}
              {usageChartData.length === 0 && (
                <p className="text-gray-500 text-center py-8">No usage data yet</p>
              )}
            </div>
          </div>
          </div>
        </div>
      )}
      {braintreeTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl">
            <div className="flex items-start justify-between gap-4 mb-4">
              <div>
                <h3 className="text-xl font-semibold text-[#1A1A1A]">Braintree checkout</h3>
                <p className="text-sm text-gray-600">
                  {braintreeTarget.label} - ${Number(braintreeTarget.amount || 0).toFixed(2)}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setBraintreeTarget(null)}
                className="text-sm text-gray-500 hover:text-gray-900"
              >
                Close
              </button>
            </div>
            <div id="braintree-dropin-container" className="min-h-[120px]" />
            {braintreeError && (
              <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {braintreeError}
              </div>
            )}
            <div className="mt-5 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setBraintreeTarget(null)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={completeBraintreeCheckout}
                disabled={!braintreeReady || purchasing === 'braintree'}
                className="rounded-lg bg-[#1A1A1A] px-4 py-2 text-sm font-medium text-white hover:bg-[#333] disabled:opacity-50"
              >
                {purchasing === 'braintree' ? 'Processing...' : 'Complete payment'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TokenCenter;

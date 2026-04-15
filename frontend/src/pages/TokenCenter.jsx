import { useState, useEffect, useRef } from 'react';
import { useLocation, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Zap, TrendingUp, ArrowUpRight, Clock, Check, 
  CreditCard, History, PieChart, Link2, Copy
} from 'lucide-react';
import { useAuth } from '../authContext';
import { API_BASE as API } from '../apiBase';
import axios from 'axios';
import { logApiError } from '../utils/apiError';
import { PieChart as RePieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis } from 'recharts';
import './TokenCenter.css';

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
  const bundleRefs = useRef({});

  useEffect(() => {
    const fetchData = async () => {
      try {
        const headers = token ? { Authorization: `Bearer ${token}` } : {};
        const [bundlesRes, historyRes, usageRes, codeRes, statsRes] = await Promise.all([
          axios.get(`${API}/tokens/bundles`),
          axios.get(`${API}/tokens/history`, { headers }),
          axios.get(`${API}/tokens/usage`, { headers }),
          token ? axios.get(`${API}/referrals/code`, { headers }).catch((e) => { logApiError('TokenCenter referrals/code', e); return { data: {} }; }) : Promise.resolve({ data: {} }),
          token ? axios.get(`${API}/referrals/stats`, { headers }).catch((e) => { logApiError('TokenCenter referrals/stats', e); return { data: {} }; }) : Promise.resolve({ data: {} })
        ]);
        setBundles(bundlesRes.data.bundles);
        setHistory(historyRes.data.history);
        setUsage(usageRes.data);
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

  const handlePurchase = async (bundleKey) => {
    setPurchasing(bundleKey);
    try {
      await axios.post(`${API}/tokens/purchase`, { bundle: bundleKey }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      await refreshUser();
      const historyRes = await axios.get(`${API}/tokens/history`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setHistory(historyRes.data.history);
    } catch (e) {
      console.error(e);
    } finally {
      setPurchasing(null);
    }
  };

  const handleStripeCheckout = async (bundleKey) => {
    setPurchasing(`stripe-${bundleKey}`);
    try {
      const { data } = await axios.post(
        `${API}/stripe/create-checkout-session`,
        { bundle: bundleKey },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (data?.url) window.location.href = data.url;
    } catch (e) {
      console.error(e);
    } finally {
      setPurchasing(null);
    }
  };

  const bundleOrder = ['builder', 'pro', 'scale', 'teams'];
  const sortedBundles = bundleOrder.filter(k => bundles[k]).map(k => ({ key: k, ...bundles[k] }));

  // Custom credits slider (100–10000 at $0.03/credit, same as plans)
  const [customCredits, setCustomCredits] = useState(500);
  const customMin = 100;
  const customMax = 10000;
  const customStep = 100;
  const pricePerCredit = 0.03;
  const customTotal = Math.round(customCredits * pricePerCredit * 100) / 100;

  const handlePurchaseCustom = async () => {
    setPurchasing('custom');
    try {
      await axios.post(`${API}/tokens/purchase-custom`, { credits: customCredits }, {
        headers: { Authorization: `Bearer ${token}` },
      });
      await refreshUser();
      const historyRes = await axios.get(`${API}/tokens/history`, { headers: { Authorization: `Bearer ${token}` } });
      setHistory(historyRes.data.history);
    } catch (e) {
      const detail = e.response?.data?.detail ?? '';
      if (typeof detail === 'string' && detail.includes('Stripe')) {
        try {
          const { data } = await axios.post(
            `${API}/stripe/create-checkout-session-custom`,
            { credits: customCredits },
            { headers: { Authorization: `Bearer ${token}` } },
          );
          if (data?.url) window.location.href = data.url;
        } catch (e2) {
          logApiError('TokenCenter Stripe custom', e2);
        }
      } else {
        logApiError('TokenCenter purchase-custom', e);
      }
    } finally {
      setPurchasing(null);
    }
  };

  const handleStripeCheckoutCustom = async () => {
    setPurchasing('stripe-custom');
    try {
      const { data } = await axios.post(
        `${API}/stripe/create-checkout-session-custom`,
        { credits: customCredits },
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (data?.url) window.location.href = data.url;
    } catch (e) {
      logApiError('TokenCenter Stripe custom', e);
    } finally {
      setPurchasing(null);
    }
  };

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
    <div className="credit-center space-y-8" data-testid="credit-center">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold mb-2" style={{ color: 'var(--theme-text)' }}>Credit Center</h1>
        <p className="credit-center-muted" style={{ color: 'var(--theme-muted)' }}>Buy credits and track your usage. 50 credits ≈ 1 landing page · 100 credits ≈ 1 full app · 150 credits ≈ 1 mobile app.</p>
      </div>

      {/* Balance Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="credit-center-card p-8 rounded-2xl border"
        style={{ background: 'var(--theme-surface)', borderColor: 'var(--theme-border)', color: 'var(--theme-text)' }}
      >
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          <div>
            <p className="credit-center-muted mb-2 flex items-center gap-2" style={{ color: 'var(--theme-muted)' }}>
              <Zap className="w-5 h-5" style={{ color: 'var(--theme-muted)' }} />
              Current Balance
            </p>
            <p className="text-5xl font-bold" data-testid="credit-balance" style={{ color: 'var(--theme-text)' }}>
              {credits.toLocaleString()}
            </p>
            <p className="credit-center-muted mt-2" style={{ color: 'var(--theme-muted)' }}>credits available</p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 rounded-lg" style={{ background: 'var(--theme-input)' }}>
              <p className="text-sm credit-center-muted" style={{ color: 'var(--theme-muted)' }}>Total Used</p>
              <p className="text-2xl font-bold" style={{ color: 'var(--theme-text)' }}>{usage?.total_used?.toLocaleString() || 0}</p>
            </div>
            <div className="p-4 rounded-lg" style={{ background: 'var(--theme-input)' }}>
              <p className="text-sm credit-center-muted" style={{ color: 'var(--theme-muted)' }}>Plan</p>
              <p className="text-2xl font-bold capitalize" style={{ color: 'var(--theme-text)' }}>{user?.plan || 'Free'}</p>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Referral: share link (free tier only for referrer reward) */}
      {referralCode && (
        <div className="credit-center-section p-6 rounded-xl border" style={{ background: 'var(--theme-surface)', borderColor: 'var(--theme-border)' }}>
          <h2 className="credit-center-heading text-lg font-semibold flex items-center gap-2 mb-2" style={{ color: 'var(--theme-text)' }}>
            <Link2 className="w-5 h-5" style={{ color: 'var(--theme-text)' }} /> Invite friends — 100 credits each
          </h2>
          <p className="text-sm credit-center-muted mb-3" style={{ color: 'var(--theme-muted)' }}>Share your link. When they sign up, they get 100 credits. You get 100 credits too if you're on the free plan (max 10 referrals/month).</p>
          <div className="flex flex-wrap items-center gap-2">
            <code className="px-3 py-2 rounded-lg text-sm break-all" style={{ background: 'var(--theme-input)', color: 'var(--theme-muted)' }}>
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
        <h2 className="credit-center-heading text-xl font-semibold" style={{ color: 'var(--theme-text)' }}>Pricing & usage</h2>
        <p className="text-sm credit-center-muted" style={{ color: 'var(--theme-muted)' }}>Credits for builds. Usage this period: {usage?.total_used?.toLocaleString() ?? 0} tokens</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-4 border-b" style={{ borderColor: 'var(--theme-border)' }}>
        {[
          { id: 'purchase', label: 'Buy Credits', icon: CreditCard },
          { id: 'history', label: 'History', icon: History },
          { id: 'usage', label: 'Usage Analytics', icon: PieChart }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 border-b-2 transition ${
              activeTab === tab.id ? 'border-[var(--theme-accent)]' : 'border-transparent'
            }`}
              style={{ color: activeTab === tab.id ? 'var(--theme-text)' : 'var(--theme-muted)' }}
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
              className={`credit-center-card p-6 rounded-xl border transition-all ${bundle.key === 'builder' ? 'scale-105' : ''} ${addonFromPricing === bundle.key ? 'ring-2 ring-[var(--theme-accent)]' : ''}`}
              style={{ background: 'var(--theme-surface)', borderColor: 'var(--theme-border)' }}
            >
              {bundle.key === 'builder' && (
                <div className="text-xs font-medium mb-4" style={{ color: 'var(--theme-text)' }}>MOST POPULAR</div>
              )}
              <h3 className="credit-center-heading text-xl font-semibold mb-2" style={{ color: 'var(--theme-text)' }}>{bundle.name || bundle.key}</h3>
              <div className="mb-4">
                <span className="text-3xl font-bold" style={{ color: 'var(--theme-text)' }}>${Number(bundle.price).toFixed(2)}</span>
                <span className="text-sm ml-1 credit-center-muted" style={{ color: 'var(--theme-muted)' }}>/month</span>
              </div>
              <p className="credit-center-muted mb-6" style={{ color: 'var(--theme-muted)' }}>
                <Zap className="w-4 h-4 inline mr-1" style={{ color: 'var(--theme-muted)' }} />
                {(bundle.credits ?? (bundle.tokens / 1000)).toLocaleString()} credits per month
              </p>
              <button
                onClick={() => handlePurchase(bundle.key)}
                disabled={purchasing === bundle.key}
                className="w-full py-2.5 rounded-lg font-medium transition bg-[#1A1A1A] hover:bg-[#333] text-white disabled:opacity-50"
                data-testid={`buy-${bundle.key}-btn`}
              >
                {purchasing === bundle.key && !purchasing.startsWith('stripe') ? (
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mx-auto"></div>
                ) : (
                  'Add credits'
                )}
              </button>
              <button
                onClick={() => handleStripeCheckout(bundle.key)}
                disabled={purchasing === `stripe-${bundle.key}`}
                className="w-full mt-2 py-2 rounded-lg font-medium bg-[#1A1A1A] hover:bg-[#333] text-white transition disabled:opacity-50"
                data-testid={`stripe-${bundle.key}-btn`}
              >
                {purchasing === `stripe-${bundle.key}` ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mx-auto"></div>
                ) : (
                  'Pay with Stripe'
                )}
              </button>
            </motion.div>
          ))}
        </div>
        {/* Need more? Buy credits (slider) */}
        <div className="credit-center-card mt-8 p-6 rounded-xl border" style={{ background: 'var(--theme-surface)', borderColor: 'var(--theme-border)' }}>
          <h3 className="credit-center-heading text-lg font-semibold mb-2" style={{ color: 'var(--theme-text)' }}>Need more? Buy credits</h3>
          <p className="text-sm credit-center-muted mb-4" style={{ color: 'var(--theme-muted)' }}>100–10,000 credits at $0.03/credit (same rate as plans).</p>
          <div className="flex flex-col sm:flex-row sm:items-center gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium mb-2" style={{ color: 'var(--theme-text)' }}>Credits: {customCredits}</label>
              <input
                type="range"
                min={customMin}
                max={customMax}
                step={customStep}
                value={customCredits}
                onChange={(e) => setCustomCredits(Number(e.target.value))}
                className="w-full h-2 rounded-lg appearance-none"
                style={{ background: 'var(--theme-border)', accentColor: 'var(--theme-accent)' }}
              />
            </div>
            <div className="flex items-center gap-4 shrink-0">
              <span className="text-lg font-bold" style={{ color: 'var(--theme-text)' }}>Total: ${customTotal.toFixed(2)}</span>
              <button
                type="button"
                onClick={handlePurchaseCustom}
                disabled={purchasing === 'custom' || purchasing === 'stripe-custom'}
                className="py-2 px-4 rounded-lg bg-[#1A1A1A] hover:bg-[#333] text-white text-sm font-medium disabled:opacity-50"
              >
                {purchasing === 'custom' ? 'Processing…' : `Buy ${customCredits} credits`}
              </button>
              <button
                type="button"
                onClick={handleStripeCheckoutCustom}
                disabled={purchasing === 'custom' || purchasing === 'stripe-custom'}
                className="py-2 px-4 rounded-lg border border-[#1A1A1A] text-[#1A1A1A] hover:bg-[#1A1A1A] hover:text-white text-sm font-medium disabled:opacity-50"
              >
                {purchasing === 'stripe-custom' ? 'Redirecting…' : 'Pay with Stripe'}
              </button>
            </div>
          </div>
        </div>
        </>
      )}

      {/* History Tab */}
      {activeTab === 'history' && (
        <div className="credit-center-section p-6 rounded-xl border" style={{ background: 'var(--theme-surface)', borderColor: 'var(--theme-border)' }}>
          {history.length === 0 ? (
            <div className="text-center py-12">
              <History className="w-12 h-12 mx-auto mb-4" style={{ color: 'var(--theme-muted)' }} />
              <p className="credit-center-muted" style={{ color: 'var(--theme-muted)' }}>No transactions yet</p>
            </div>
          ) : (
            <div className="space-y-4">
              {history.map(item => (
                <div
                  key={item.id}
                  className="flex items-center justify-between p-4 rounded-lg"
                  style={{ background: 'var(--theme-input)' }}
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: 'var(--theme-border)' }}>
                      {item.type === 'purchase' ? <CreditCard className="w-5 h-5" style={{ color: 'var(--theme-text)' }} /> :
                       item.type === 'bonus' ? <Zap className="w-5 h-5" style={{ color: 'var(--theme-text)' }} /> :
                       <ArrowUpRight className="w-5 h-5" style={{ color: 'var(--theme-text)' }} />}
                    </div>
                    <div>
                      <p className="font-medium capitalize" style={{ color: 'var(--theme-text)' }}>{item.type}</p>
                      <p className="text-sm credit-center-muted" style={{ color: 'var(--theme-muted)' }}>
                        {item.description || (item.bundle ? `${item.bundle} bundle` : 'Credit transaction')}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-bold" style={{ color: (item.credits ?? item.tokens) > 0 ? 'var(--theme-text)' : 'var(--theme-muted)' }}>
                      {((item.credits ?? (item.tokens > 0 ? item.tokens / 1000 : 0)) > 0 ? '+' : '')}
                      {(item.credits ?? (item.tokens ? Math.floor(item.tokens / 1000) : 0))?.toLocaleString()} credits
                    </p>
                    <p className="text-sm credit-center-muted" style={{ color: 'var(--theme-muted)' }}>
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
            <div className="credit-center-section p-6 rounded-xl border" style={{ background: 'var(--theme-surface)', borderColor: 'var(--theme-border)' }}>
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
          <div className="credit-center-section p-6 rounded-xl border" style={{ background: 'var(--theme-surface)', borderColor: 'var(--theme-border)' }}>
            <h3 className="credit-center-heading text-lg font-semibold mb-6" style={{ color: 'var(--theme-text)' }}>Usage by Agent</h3>
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
          
          <div className="credit-center-section p-6 rounded-xl border" style={{ background: 'var(--theme-surface)', borderColor: 'var(--theme-border)' }}>
            <h3 className="credit-center-heading text-lg font-semibold mb-6" style={{ color: 'var(--theme-text)' }}>Top Consumers</h3>
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
    </div>
  );
};

export default TokenCenter;
import { useState, useEffect, useRef } from 'react';
import { useLocation, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Zap, TrendingUp, ArrowUpRight, Clock, Check, 
  CreditCard, History, PieChart, Link2, Copy
} from 'lucide-react';
import { useAuth, API } from '../App';
import axios from 'axios';
import { PieChart as RePieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis } from 'recharts';

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
          token ? axios.get(`${API}/referrals/code`, { headers }).catch(() => ({ data: {} })) : Promise.resolve({ data: {} }),
          token ? axios.get(`${API}/referrals/stats`, { headers }).catch(() => ({ data: {} })) : Promise.resolve({ data: {} })
        ]);
        setBundles(bundlesRes.data.bundles);
        setHistory(historyRes.data.history);
        setUsage(usageRes.data);
        setReferralCode(codeRes.data?.code ?? null);
        setReferralStats(statsRes.data ? { this_month: statsRes.data.this_month, total: statsRes.data.total, cap: statsRes.data.cap } : null);
      } catch (e) {
        console.error(e);
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

  const bundleOrder = ['starter', 'builder', 'pro', 'agency', 'light', 'dev'];
  const sortedBundles = bundleOrder.filter(k => bundles[k]).map(k => ({ key: k, ...bundles[k] }));

  const usageChartData = usage?.by_agent ? Object.entries(usage.by_agent).map(([name, value]) => ({
    name,
    value
  })) : [];

  const COLORS = ['#1A1A1A', '#808080', '#FF8F5E', '#F59E0B', '#EF4444', '#06B6D4', '#EC4899', '#84CC16'];

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
        <p className="text-[#666666]">Buy credits and track your usage. 50 credits ≈ 1 landing page.</p>
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
              <Zap className="w-5 h-5 text-yellow-500" />
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
        <div className="p-6 bg-white/5 rounded-xl border border-white/10">
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
              className="flex items-center gap-1 px-3 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-[#1A1A1A] text-sm font-medium"
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
      <div className="flex gap-4 border-b border-white/10">
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
                  ? 'bg-gray-700/10 border-gray-400/50 scale-105'
                  : 'bg-[#0a0a0a] border-white/10 hover:border-white/20'
              } ${addonFromPricing === bundle.key ? 'ring-2 ring-white/30' : ''}`}
            >
              {bundle.key === 'builder' && (
                <div className="text-xs font-medium text-[#1A1A1A] mb-4">MOST POPULAR</div>
              )}
              <h3 className="text-xl font-semibold mb-2">{bundle.name || bundle.key}</h3>
              <div className="mb-4">
                <span className="text-3xl font-bold">${bundle.price}</span>
                <span className="text-gray-500 text-sm ml-1">
                  {['light', 'dev'].includes(bundle.key) ? ' one-time' : '/month'}
                </span>
              </div>
              <p className="text-[#666666] mb-6">
                <Zap className="w-4 h-4 inline mr-1 text-yellow-500" />
                {(bundle.credits ?? (bundle.tokens / 1000)).toLocaleString()} credits
                {!['light', 'dev'].includes(bundle.key) && ' per month'}
              </p>
              <button
                onClick={() => handlePurchase(bundle.key)}
                disabled={purchasing === bundle.key}
                className={`w-full py-2.5 rounded-lg font-medium transition ${
                  bundle.key === 'builder'
                    ? 'bg-gray-700 hover:bg-gray-800'
                    : 'bg-white/10 hover:bg-white/20'
                } disabled:opacity-50`}
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
                className="w-full mt-2 py-2 rounded-lg font-medium bg-emerald-600 hover:bg-emerald-500 text-[#1A1A1A] transition disabled:opacity-50"
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
      )}

      {/* History Tab */}
      {activeTab === 'history' && (
        <div className="p-6 bg-[#0a0a0a] rounded-xl border border-white/10">
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
                      item.type === 'purchase' ? 'bg-green-500/20' :
                      item.type === 'bonus' ? 'bg-gray-700/20' :
                      item.type === 'refund' ? 'bg-gray-700/20' :
                      'bg-gray-500/20'
                    }`}>
                      {item.type === 'purchase' ? <CreditCard className="w-5 h-5 text-green-400" /> :
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
                      (item.credits ?? item.tokens) > 0 ? 'text-green-400' : 'text-red-400'
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
            <div className="p-6 bg-[#0a0a0a] rounded-xl border border-white/10">
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
          <div className="p-6 bg-[#0a0a0a] rounded-xl border border-white/10">
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
          
          <div className="p-6 bg-[#0a0a0a] rounded-xl border border-white/10">
            <h3 className="text-lg font-semibold mb-6">Top Consumers</h3>
            <div className="space-y-4">
              {usageChartData.slice(0, 5).map((item, i) => (
                <div key={item.name} className="flex items-center gap-4">
                  <div className="w-8 text-gray-500 font-mono">#{i + 1}</div>
                  <div className="flex-1">
                    <p className="font-medium">{item.name}</p>
                    <div className="relative h-2 bg-white/10 rounded-full mt-1 overflow-hidden">
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
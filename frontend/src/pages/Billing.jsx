import { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import {
  AlertCircle,
  CheckCircle2,
  CreditCard,
  History,
  Loader2,
  RefreshCcw,
  ShieldCheck,
  XCircle,
  Zap,
} from 'lucide-react';
import { API_BASE as API } from '../apiBase';
import { useAuth } from '../authContext';
import { logApiError } from '../utils/apiError';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function money(value, currency = 'USD') {
  const amount = Number(value || 0);
  return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(amount);
}

function dateText(value) {
  if (!value) return 'Not scheduled';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

function statusTone(status) {
  const s = String(status || '').toLowerCase();
  if (['active', 'success', 'completed', 'approved'].includes(s))
    return 'text-emerald-700 bg-emerald-50 border-emerald-200';
  if (['past_due', 'failed', 'declined', 'approval_pending'].includes(s))
    return 'text-amber-700 bg-amber-50 border-amber-200';
  if (['canceled', 'expired', 'suspended'].includes(s))
    return 'text-red-700 bg-red-50 border-red-200';
  return 'text-stone-700 bg-stone-50 border-stone-200';
}

function ErrorBox({ children }) {
  if (!children) return null;
  return (
    <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
      <span>{children}</span>
    </div>
  );
}

function NoticeBox({ children }) {
  if (!children) return null;
  return (
    <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
      <CheckCircle2 className="h-4 w-4 shrink-0" />
      {children}
    </div>
  );
}

// ---------------------------------------------------------------------------
// PayPal JS SDK loader
// ---------------------------------------------------------------------------

function buildPayPalScriptUrl(clientId, intent = 'capture') {
  const vault = intent === 'subscription' ? '&vault=true' : '';
  return `https://www.paypal.com/sdk/js?client-id=${clientId}&currency=USD&intent=${intent}${vault}&components=buttons`;
}

let _sdkLoadPromise = null;

function loadPayPalSdk(clientId, intent = 'capture') {
  const src = buildPayPalScriptUrl(clientId, intent);
  // If already on page for same intent, resolve immediately
  const existing = document.querySelector(`script[data-pp-intent="${intent}"]`);
  if (existing && window.paypal) return Promise.resolve(window.paypal);

  // Re-use in-flight load
  if (_sdkLoadPromise) return _sdkLoadPromise;

  _sdkLoadPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = src;
    script.setAttribute('data-pp-intent', intent);
    script.async = true;
    script.onload = () => {
      _sdkLoadPromise = null;
      resolve(window.paypal);
    };
    script.onerror = (e) => {
      _sdkLoadPromise = null;
      reject(new Error('Failed to load PayPal SDK'));
    };
    document.body.appendChild(script);
  });
  return _sdkLoadPromise;
}

// ---------------------------------------------------------------------------
// PayPal Buttons component
// ---------------------------------------------------------------------------

function PayPalButtons({ clientId, planName, priceId, billingType, amount, onSuccess, onError }) {
  const containerRef = useRef(null);
  const renderedRef = useRef(false);
  const [sdkReady, setSdkReady] = useState(false);
  const [sdkError, setSdkError] = useState('');
  const { token } = useAuth();

  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const isSubscription = billingType === 'recurring';

  useEffect(() => {
    if (!clientId) return;
    setSdkError('');
    const intent = isSubscription ? 'subscription' : 'capture';
    loadPayPalSdk(clientId, intent)
      .then(() => setSdkReady(true))
      .catch((e) => setSdkError(e.message || 'PayPal SDK failed to load'));
  }, [clientId, isSubscription]);

  useEffect(() => {
    if (!sdkReady || !containerRef.current || renderedRef.current) return;
    if (!window.paypal?.Buttons) return;
    renderedRef.current = true;

    const buttonConfig = isSubscription
      ? {
          style: { layout: 'vertical', color: 'gold', shape: 'rect', label: 'subscribe' },
          createSubscription: async (_data, actions) => {
            try {
              const resp = await axios.post(
                `${API}/billing/create-subscription`,
                { price_id: priceId },
                { headers }
              );
              return resp.data.paypal_subscription_id;
            } catch (e) {
              onError?.(e.response?.data?.detail?.message || e.message || 'Could not create subscription');
              throw e;
            }
          },
          onApprove: async (data) => {
            try {
              const resp = await axios.post(
                `${API}/billing/activate-subscription`,
                { paypal_subscription_id: data.subscriptionID },
                { headers }
              );
              onSuccess?.({ type: 'subscription', data: resp.data });
            } catch (e) {
              onError?.(e.response?.data?.detail?.message || e.message || 'Could not activate subscription');
            }
          },
          onError: (err) => {
            onError?.(String(err) || 'PayPal subscription error');
          },
          onCancel: () => {
            onError?.('Payment canceled.');
          },
        }
      : {
          style: { layout: 'vertical', color: 'gold', shape: 'rect', label: 'pay' },
          createOrder: async () => {
            try {
              const resp = await axios.post(
                `${API}/billing/create-order`,
                { price_id: priceId },
                { headers }
              );
              return resp.data.paypal_order_id;
            } catch (e) {
              onError?.(e.response?.data?.detail?.message || e.message || 'Could not create order');
              throw e;
            }
          },
          onApprove: async (data) => {
            try {
              const resp = await axios.post(
                `${API}/billing/capture-order`,
                { paypal_order_id: data.orderID },
                { headers }
              );
              onSuccess?.({ type: 'one_time', data: resp.data });
            } catch (e) {
              onError?.(e.response?.data?.detail?.message || e.message || 'Payment capture failed');
            }
          },
          onError: (err) => {
            onError?.(String(err) || 'PayPal payment error');
          },
          onCancel: () => {
            onError?.('Payment canceled.');
          },
        };

    window.paypal.Buttons(buttonConfig).render(containerRef.current).catch(() => {
      renderedRef.current = false;
    });
  }, [sdkReady]);

  if (sdkError) return <ErrorBox>{sdkError}</ErrorBox>;
  if (!sdkReady) {
    return (
      <div className="flex items-center justify-center gap-2 py-3 text-sm text-stone-500">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading PayPal…
      </div>
    );
  }
  return <div ref={containerRef} className="min-h-[50px]" />;
}

// ---------------------------------------------------------------------------
// Plan card
// ---------------------------------------------------------------------------

const PLAN_COLORS = {
  builder: 'border-blue-200 bg-blue-50',
  pro: 'border-purple-200 bg-purple-50',
  scale: 'border-indigo-200 bg-indigo-50',
  teams: 'border-emerald-200 bg-emerald-50',
};

function PlanCard({ plan, clientId, billingInterval, onSuccess, onError }) {
  const slug = plan.metadata?.plan_slug || plan.slug?.split('-')[0] || 'plan';
  const colorClass = PLAN_COLORS[slug] || 'border-stone-200 bg-stone-50';
  return (
    <div className={`rounded-xl border p-5 ${colorClass}`}>
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <p className="text-lg font-bold text-stone-950">{plan.name}</p>
          <p className="text-2xl font-bold text-stone-950">
            {money(plan.amount)}
            <span className="text-sm font-normal text-stone-500">
              /{billingInterval === 'yearly' ? 'yr' : 'mo'}
            </span>
          </p>
        </div>
        <div className="flex items-center gap-1 rounded-full bg-white px-2 py-1 text-xs font-semibold text-stone-700 shadow-sm">
          <Zap className="h-3 w-3 text-amber-500" />
          {plan.credits?.toLocaleString()} credits
        </div>
      </div>
      <PayPalButtons
        clientId={clientId}
        planName={plan.name}
        priceId={plan.id}
        billingType={plan.billing_type}
        amount={plan.amount}
        onSuccess={onSuccess}
        onError={onError}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Billing page
// ---------------------------------------------------------------------------

export default function Billing() {
  const { token } = useAuth();
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [action, setAction] = useState('');
  const [billingInterval, setBillingInterval] = useState('monthly');
  const [clientId, setClientId] = useState('');

  const headers = token ? { Authorization: `Bearer ${token}` } : {};

  const loadOverview = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError('');
    try {
      const { data } = await axios.get(`${API}/billing/overview`, { headers });
      setOverview(data);
      if (data.paypal_client_id) setClientId(data.paypal_client_id);
    } catch (e) {
      const detail = e.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : detail?.message || 'Could not load billing overview.');
      logApiError('Billing overview', e);
    } finally {
      setLoading(false);
    }
  }, [token]);

  // Also load config for client ID if overview doesn't have it
  useEffect(() => {
    axios.get(`${API}/billing/config`).then(({ data }) => {
      if (data.paypal_client_id) setClientId(data.paypal_client_id);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    loadOverview();
  }, [loadOverview]);

  const activeSubscription = overview?.active_subscriptions?.[0] || null;
  const currentPlan = overview?.plans?.find((p) => p.id === activeSubscription?.price_id) || null;
  const history = overview?.billing_history || [];

  const allPlans = (overview?.plans || []).filter((p) => p.active);
  const visiblePlans = allPlans.filter((p) =>
    billingInterval === 'yearly'
      ? p.billing_type === 'recurring' && p.interval === 'yearly'
      : p.billing_type === 'recurring' && p.interval === 'monthly'
  );
  const oneTimePlans = allPlans.filter((p) => p.billing_type === 'one_time');

  const handleSuccess = async ({ type, data: result }) => {
    setNotice(
      type === 'subscription'
        ? `Subscription activated! Your plan is now active.`
        : `Payment successful! Your credits have been added.`
    );
    await loadOverview();
  };

  const handlePaymentError = (msg) => {
    setError(msg || 'Payment failed.');
  };

  const handleCancel = async (cancelAtPeriodEnd) => {
    if (!activeSubscription) return;
    setAction(cancelAtPeriodEnd ? 'cancel-later' : 'cancel-now');
    setError('');
    setNotice('');
    try {
      await axios.post(
        `${API}/billing/cancel-subscription`,
        { subscriptionId: activeSubscription.id, cancel_at_period_end: cancelAtPeriodEnd },
        { headers }
      );
      setNotice(
        cancelAtPeriodEnd
          ? 'Subscription canceled. Access remains through the current period.'
          : 'Subscription canceled immediately.'
      );
      await loadOverview();
    } catch (e) {
      const detail = e.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : detail?.message || 'Could not cancel subscription.');
      logApiError('Cancel subscription', e);
    } finally {
      setAction('');
    }
  };

  if (!token) {
    return (
      <div className="mx-auto max-w-3xl p-8">
        <h1 className="text-3xl font-semibold text-stone-950">Billing</h1>
        <p className="mt-2 text-stone-600">Sign in to manage billing.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      {/* Header */}
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <p className="text-sm font-medium uppercase tracking-wide text-stone-500">Starlight Global LLC</p>
          <h1 className="text-3xl font-semibold text-stone-950">Billing &amp; Plans</h1>
          <p className="mt-1 max-w-2xl text-sm text-stone-600">
            Payments powered by PayPal. Secure checkout, no card stored on our servers.
          </p>
        </div>
        <button
          type="button"
          onClick={loadOverview}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-lg border border-stone-300 px-3 py-2 text-sm font-medium text-stone-800 hover:bg-stone-50 disabled:opacity-60"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCcw className="h-4 w-4" />}
          Refresh
        </button>
      </div>

      <NoticeBox>{notice}</NoticeBox>
      <ErrorBox>{error}</ErrorBox>

      {loading ? (
        <div className="flex min-h-[320px] items-center justify-center rounded-xl border border-stone-200 bg-white">
          <Loader2 className="h-6 w-6 animate-spin text-stone-500" />
        </div>
      ) : (
        <>
          {/* Current subscription status */}
          {activeSubscription && (
            <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
              <div className="mb-4 flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-stone-950">Current subscription</h2>
                  <p className="text-sm text-stone-500">Plan, status, and renewal timing.</p>
                </div>
                <span className={`rounded-full border px-3 py-1 text-xs font-medium ${statusTone(activeSubscription.status)}`}>
                  {activeSubscription.status}
                </span>
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-lg bg-stone-50 p-4">
                  <p className="text-xs uppercase text-stone-500">Plan</p>
                  <p className="mt-1 text-lg font-semibold text-stone-950">
                    {currentPlan?.name || activeSubscription.price_id}
                  </p>
                  <p className="text-sm text-stone-500">
                    {currentPlan ? `${money(currentPlan.amount)} / ${currentPlan.interval || 'period'}` : 'Active plan'}
                  </p>
                </div>
                <div className="rounded-lg bg-stone-50 p-4">
                  <p className="text-xs uppercase text-stone-500">Next billing date</p>
                  <p className="mt-1 text-lg font-semibold text-stone-950">
                    {dateText(activeSubscription.current_period_end)}
                  </p>
                  <p className="text-sm text-stone-500">
                    {activeSubscription.cancel_at_period_end
                      ? 'Access remains through this date.'
                      : 'Auto-renews unless canceled.'}
                  </p>
                </div>
                <div className="rounded-lg bg-stone-50 p-4">
                  <p className="text-xs uppercase text-stone-500">Product</p>
                  <p className="mt-1 text-lg font-semibold text-stone-950">Crucible AI</p>
                  <p className="text-sm text-stone-500">By Starlight Global LLC.</p>
                </div>
              </div>
              {/* Cancel controls */}
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => handleCancel(true)}
                  disabled={action === 'cancel-later'}
                  className="inline-flex items-center gap-2 rounded-lg border border-amber-300 px-4 py-2 text-sm font-medium text-amber-800 hover:bg-amber-50 disabled:opacity-50"
                >
                  <ShieldCheck className="h-4 w-4" />
                  {action === 'cancel-later' ? 'Canceling…' : 'Cancel at period end'}
                </button>
                <button
                  type="button"
                  onClick={() => handleCancel(false)}
                  disabled={action === 'cancel-now'}
                  className="inline-flex items-center gap-2 rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
                >
                  <XCircle className="h-4 w-4" />
                  {action === 'cancel-now' ? 'Canceling…' : 'Cancel now'}
                </button>
              </div>
            </section>
          )}

          {/* Subscription Plans */}
          <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
            <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-lg font-semibold text-stone-950">Subscription plans</h2>
                <p className="text-sm text-stone-500">Recurring access with monthly credits. Cancel anytime.</p>
              </div>
              {/* Monthly / Yearly toggle */}
              <div className="flex rounded-lg border border-stone-200 bg-stone-50 p-1">
                <button
                  type="button"
                  onClick={() => setBillingInterval('monthly')}
                  className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                    billingInterval === 'monthly'
                      ? 'bg-white text-stone-950 shadow-sm'
                      : 'text-stone-500 hover:text-stone-700'
                  }`}
                >
                  Monthly
                </button>
                <button
                  type="button"
                  onClick={() => setBillingInterval('yearly')}
                  className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                    billingInterval === 'yearly'
                      ? 'bg-white text-stone-950 shadow-sm'
                      : 'text-stone-500 hover:text-stone-700'
                  }`}
                >
                  Yearly
                  <span className="ml-1 rounded-full bg-emerald-100 px-1.5 py-0.5 text-xs font-semibold text-emerald-700">
                    Save ~17%
                  </span>
                </button>
              </div>
            </div>
            {visiblePlans.length === 0 ? (
              <p className="rounded-lg border border-dashed border-stone-300 p-6 text-sm text-stone-500">
                No {billingInterval} plans available.
              </p>
            ) : (
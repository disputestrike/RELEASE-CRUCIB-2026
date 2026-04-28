import { useEffect, useMemo, useRef, useState } from 'react';
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
} from 'lucide-react';
import { API_BASE as API } from '../apiBase';
import { useAuth } from '../authContext';
import { logApiError } from '../utils/apiError';

const BRAINTREE_DROPIN_SCRIPT = 'https://js.braintreegateway.com/web/dropin/1.46.1/js/dropin.min.js';

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
  if (['active', 'success', 'settled', 'submitted_for_settlement'].includes(s)) return 'text-emerald-700 bg-emerald-50 border-emerald-200';
  if (['past_due', 'failed', 'declined'].includes(s)) return 'text-amber-700 bg-amber-50 border-amber-200';
  if (['canceled', 'expired'].includes(s)) return 'text-red-700 bg-red-50 border-red-200';
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

export default function Billing() {
  const { token } = useAuth();
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [action, setAction] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [dropinReady, setDropinReady] = useState(false);
  const [dropinError, setDropinError] = useState('');
  const [selectedPlan, setSelectedPlan] = useState('');
  const dropinRef = useRef(null);

  const headers = useMemo(() => (
    token ? { Authorization: `Bearer ${token}` } : {}
  ), [token]);

  const loadOverview = async () => {
    if (!token) return;
    setLoading(true);
    setError('');
    try {
      const { data } = await axios.get(`${API}/billing/overview`, { headers });
      setOverview(data);
    } catch (e) {
      const detail = e.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : detail?.message || 'Could not load billing overview.');
      logApiError('Billing overview', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOverview();
  }, [token]);

  useEffect(() => {
    if (!token) return undefined;
    let cancelled = false;
    const setup = async () => {
      setDropinError('');
      setDropinReady(false);
      try {
        const [{ data }, dropin] = await Promise.all([
          axios.get(`${API}/billing/client-token`, { headers }),
          loadBraintreeDropin(),
        ]);
        if (cancelled) return;
        if (!data?.client_token) throw new Error('Missing Braintree client token');
        const instance = await dropin.create({
          authorization: data.client_token,
          container: '#billing-braintree-dropin',
          card: { cardholderName: { required: false } },
        });
        if (cancelled) {
          instance?.teardown?.();
          return;
        }
        dropinRef.current = instance;
        setDropinReady(true);
      } catch (e) {
        const detail = e.response?.data?.detail;
        setDropinError(typeof detail === 'string' ? detail : detail?.message || e.message || 'Braintree card form is not available.');
        logApiError('Billing Braintree setup', e);
      }
    };
    setup();
    return () => {
      cancelled = true;
      setDropinReady(false);
      const instance = dropinRef.current;
      dropinRef.current = null;
      instance?.teardown?.().catch(() => {});
    };
  }, [token, headers]);

  const activeSubscription = overview?.active_subscriptions?.[0] || null;
  const currentPlan = overview?.plans?.find((plan) => plan.id === activeSubscription?.price_id) || null;
  const paymentMethod = overview?.default_payment_method || null;
  const recurringPlans = (overview?.plans || []).filter((plan) => plan.billing_type === 'recurring' && plan.active);
  const history = overview?.billing_history || [];

  useEffect(() => {
    if (!selectedPlan && recurringPlans.length > 0) {
      setSelectedPlan(recurringPlans[0].id);
    }
  }, [selectedPlan, recurringPlans]);

  const requestNonce = async () => {
    if (!dropinRef.current) throw new Error('Card form is not ready.');
    const payload = await dropinRef.current.requestPaymentMethod();
    return payload.nonce;
  };

  const updatePaymentMethod = async () => {
    setAction('payment-method');
    setError('');
    setNotice('');
    try {
      const nonce = await requestNonce();
      await axios.post(`${API}/billing/payment-method`, { paymentMethodNonce: nonce }, { headers });
      setNotice('Payment method updated and active subscriptions were refreshed.');
      await loadOverview();
    } catch (e) {
      const detail = e.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : detail?.message || e.message || 'Could not update payment method.');
      logApiError('Billing payment method', e);
    } finally {
      setAction('');
    }
  };

  const changePlan = async () => {
    if (!activeSubscription || !selectedPlan) return;
    setAction('change-plan');
    setError('');
    setNotice('');
    try {
      await axios.post(
        `${API}/billing/change-plan`,
        { subscriptionId: activeSubscription.id, newPriceId: selectedPlan },
        { headers },
      );
      setNotice('Plan changed.');
      await loadOverview();
    } catch (e) {
      const detail = e.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : detail?.message || 'Could not change plan.');
      logApiError('Billing change plan', e);
    } finally {
      setAction('');
    }
  };

  const cancelSubscription = async (cancelAtPeriodEnd) => {
    if (!activeSubscription) return;
    setAction(cancelAtPeriodEnd ? 'cancel-later' : 'cancel-now');
    setError('');
    setNotice('');
    try {
      await axios.post(
        `${API}/billing/cancel-subscription`,
        { subscriptionId: activeSubscription.id, cancelAtPeriodEnd },
        { headers },
      );
      setNotice(cancelAtPeriodEnd ? 'Subscription canceled in Braintree. Access remains through the current period.' : 'Subscription canceled immediately.');
      await loadOverview();
    } catch (e) {
      const detail = e.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : detail?.message || 'Could not cancel subscription.');
      logApiError('Billing cancel subscription', e);
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
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <p className="text-sm font-medium uppercase tracking-wide text-stone-500">Starlight LLC</p>
          <h1 className="text-3xl font-semibold text-stone-950">Manage Billing</h1>
          <p className="mt-1 max-w-2xl text-sm text-stone-600">
            Braintree powers card vaulting, one-time purchases, subscriptions, and billing history for Starlight products.
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

      {notice && (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
          <CheckCircle2 className="h-4 w-4" />
          {notice}
        </div>
      )}
      <ErrorBox>{error}</ErrorBox>

      {loading ? (
        <div className="flex min-h-[320px] items-center justify-center rounded-xl border border-stone-200 bg-white">
          <Loader2 className="h-6 w-6 animate-spin text-stone-500" />
        </div>
      ) : (
        <>
          <div className="grid gap-4 lg:grid-cols-3">
            <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm lg:col-span-2">
              <div className="mb-4 flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-stone-950">Current subscription</h2>
                  <p className="text-sm text-stone-500">Plan, status, and renewal timing.</p>
                </div>
                {activeSubscription && (
                  <span className={`rounded-full border px-3 py-1 text-xs font-medium ${statusTone(activeSubscription.status)}`}>
                    {activeSubscription.status}
                  </span>
                )}
              </div>
              {activeSubscription ? (
                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="rounded-lg bg-stone-50 p-4">
                    <p className="text-xs uppercase text-stone-500">Plan</p>
                    <p className="mt-1 text-lg font-semibold text-stone-950">{currentPlan?.name || activeSubscription.price_id}</p>
                    <p className="text-sm text-stone-500">
                      {currentPlan ? `${money(currentPlan.amount, currentPlan.currency)} / ${currentPlan.interval || 'period'}` : 'Pricing record'}
                    </p>
                  </div>
                  <div className="rounded-lg bg-stone-50 p-4">
                    <p className="text-xs uppercase text-stone-500">Next billing date</p>
                    <p className="mt-1 text-lg font-semibold text-stone-950">{dateText(activeSubscription.current_period_end)}</p>
                    <p className="text-sm text-stone-500">{activeSubscription.cancel_at_period_end ? 'Access remains through this date.' : 'Auto-renews unless canceled.'}</p>
                  </div>
                  <div className="rounded-lg bg-stone-50 p-4">
                    <p className="text-xs uppercase text-stone-500">Product</p>
                    <p className="mt-1 text-lg font-semibold text-stone-950">Crucible AI</p>
                    <p className="text-sm text-stone-500">Product under Starlight LLC.</p>
                  </div>
                </div>
              ) : (
                <div className="rounded-lg border border-dashed border-stone-300 p-6 text-sm text-stone-600">
                  No active subscription. One-time purchases and prior billing records are listed below.
                </div>
              )}
            </section>

            <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
              <div className="mb-4 flex items-center gap-2">
                <CreditCard className="h-5 w-5 text-stone-700" />
                <h2 className="text-lg font-semibold text-stone-950">Payment method</h2>
              </div>
              {paymentMethod ? (
                <div className="rounded-lg bg-stone-50 p-4">
                  <p className="text-sm font-medium text-stone-950">{paymentMethod.card_type || 'Card'} ending {paymentMethod.last4 || '----'}</p>
                  <p className="text-sm text-stone-500">
                    Expires {paymentMethod.expiration_month || '--'}/{paymentMethod.expiration_year || '--'}
                  </p>
                </div>
              ) : (
                <p className="text-sm text-stone-600">No default payment method stored yet.</p>
              )}
              <div className="mt-4 rounded-lg border border-stone-200 p-3">
                <div id="billing-braintree-dropin" className="min-h-[120px]" />
                <ErrorBox>{dropinError}</ErrorBox>
                <button
                  type="button"
                  onClick={updatePaymentMethod}
                  disabled={!dropinReady || action === 'payment-method'}
                  className="mt-3 w-full rounded-lg bg-stone-950 px-4 py-2 text-sm font-medium text-white hover:bg-stone-800 disabled:opacity-50"
                >
                  {action === 'payment-method' ? 'Saving...' : 'Update payment method'}
                </button>
              </div>
            </section>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
              <h2 className="text-lg font-semibold text-stone-950">Change plan</h2>
              <p className="mt-1 text-sm text-stone-500">Braintree plans must already exist in the Braintree dashboard and be mapped by braintree_plan_id.</p>
              <div className="mt-4 flex flex-col gap-3 sm:flex-row">
                <select
                  value={selectedPlan}
                  onChange={(e) => setSelectedPlan(e.target.value)}
                  disabled={!activeSubscription}
                  className="min-h-[42px] flex-1 rounded-lg border border-stone-300 px-3 text-sm"
                >
                  {recurringPlans.map((plan) => (
                    <option key={plan.id} value={plan.id}>
                      {plan.name} - {money(plan.amount, plan.currency)} / {plan.interval}
                      {!plan.braintree_plan_id ? ' (needs Braintree plan ID)' : ''}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={changePlan}
                  disabled={!activeSubscription || !selectedPlan || action === 'change-plan'}
                  className="rounded-lg border border-stone-950 px-4 py-2 text-sm font-medium text-stone-950 hover:bg-stone-950 hover:text-white disabled:opacity-50"
                >
                  {action === 'change-plan' ? 'Changing...' : 'Change plan'}
                </button>
              </div>
            </section>

            <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
              <h2 className="text-lg font-semibold text-stone-950">Cancel subscription</h2>
              <p className="mt-1 text-sm text-stone-500">Canceling at period end stops the Braintree subscription now and preserves local access through the paid-through date.</p>
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => cancelSubscription(true)}
                  disabled={!activeSubscription || action === 'cancel-later'}
                  className="inline-flex items-center gap-2 rounded-lg border border-amber-300 px-4 py-2 text-sm font-medium text-amber-800 hover:bg-amber-50 disabled:opacity-50"
                >
                  <ShieldCheck className="h-4 w-4" />
                  {action === 'cancel-later' ? 'Canceling...' : 'Cancel at period end'}
                </button>
                <button
                  type="button"
                  onClick={() => cancelSubscription(false)}
                  disabled={!activeSubscription || action === 'cancel-now'}
                  className="inline-flex items-center gap-2 rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
                >
                  <XCircle className="h-4 w-4" />
                  {action === 'cancel-now' ? 'Canceling...' : 'Cancel now'}
                </button>
              </div>
            </section>
          </div>

          <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
            <div className="mb-4 flex items-center gap-2">
              <History className="h-5 w-5 text-stone-700" />
              <h2 className="text-lg font-semibold text-stone-950">Billing history</h2>
            </div>
            {history.length === 0 ? (
              <p className="rounded-lg border border-dashed border-stone-300 p-6 text-sm text-stone-600">No billing history yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[720px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-stone-200 text-xs uppercase text-stone-500">
                      <th className="py-3 pr-4 font-medium">Date</th>
                      <th className="py-3 pr-4 font-medium">Type</th>
                      <th className="py-3 pr-4 font-medium">Status</th>
                      <th className="py-3 pr-4 font-medium">Amount</th>
                      <th className="py-3 pr-4 font-medium">Braintree reference</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((item) => (
                      <tr key={item.id} className="border-b border-stone-100">
                        <td className="py-3 pr-4 text-stone-700">{dateText(item.created_at)}</td>
                        <td className="py-3 pr-4 text-stone-700">{item.payment_type || 'payment'}</td>
                        <td className="py-3 pr-4">
                          <span className={`rounded-full border px-2 py-1 text-xs ${statusTone(item.status)}`}>{item.status}</span>
                        </td>
                        <td className="py-3 pr-4 font-medium text-stone-950">{money(item.amount, item.currency)}</td>
                        <td className="py-3 pr-4 font-mono text-xs text-stone-500">{item.braintree_transaction_id || item.braintree_subscription_id || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}


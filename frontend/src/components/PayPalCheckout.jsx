/**
 * PayPalCheckout.jsx
 *
 * Drop-in PayPal JS SDK checkout button for CrucibAI.
 *
 * Usage:
 *   <PayPalCheckout
 *     plan="pro"                        // plan key from /api/billing/plans
 *     onSuccess={(result) => ...}       // called with capture result
 *     onError={(err) => ...}            // optional
 *   />
 *
 * Requires: REACT_APP_PAYPAL_CLIENT_ID in your .env
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { Loader2, CheckCircle2, XCircle } from 'lucide-react';
import { API_BASE as API } from '../apiBase';
import { useAuth } from '../authContext';

const PAYPAL_SDK_URL = (clientId) =>
  `https://www.paypal.com/sdk/js?client-id=${clientId}&currency=USD&intent=capture`;

const loadPayPalSdk = (clientId) =>
  new Promise((resolve, reject) => {
    if (window.paypal) {
      resolve(window.paypal);
      return;
    }
    const existing = document.querySelector(`script[data-paypal-sdk]`);
    if (existing) {
      existing.addEventListener('load', () => resolve(window.paypal), { once: true });
      existing.addEventListener('error', reject, { once: true });
      return;
    }
    const script = document.createElement('script');
    script.src = PAYPAL_SDK_URL(clientId);
    script.setAttribute('data-paypal-sdk', 'true');
    script.async = true;
    script.onload = () => resolve(window.paypal);
    script.onerror = () => reject(new Error('Failed to load PayPal SDK'));
    document.body.appendChild(script);
  });

export default function PayPalCheckout({ plan = 'pro', onSuccess, onError, className = '' }) {
  const { token } = useAuth();
  const containerRef = useRef(null);
  const [status, setStatus] = useState('idle'); // idle | loading | ready | processing | done | error
  const [errorMsg, setErrorMsg] = useState('');
  const [captureResult, setCaptureResult] = useState(null);
  const rendered = useRef(false);

  const clientId = process.env.REACT_APP_PAYPAL_CLIENT_ID || '';

  const handleError = useCallback((msg) => {
    setStatus('error');
    setErrorMsg(msg);
    if (onError) onError(new Error(msg));
  }, [onError]);

  useEffect(() => {
    if (!clientId) {
      handleError('PayPal client ID not configured (set REACT_APP_PAYPAL_CLIENT_ID).');
      return;
    }
    if (rendered.current) return;
    rendered.current = true;
    setStatus('loading');

    loadPayPalSdk(clientId)
      .then((paypal) => {
        if (!containerRef.current) return;
        setStatus('ready');

        paypal.Buttons({
          style: {
            layout: 'vertical',
            color: 'gold',
            shape: 'rect',
            label: 'pay',
            height: 44,
          },

          // Step 1: create order on our backend
          createOrder: async () => {
            setStatus('processing');
            try {
              const res = await axios.post(
                `${API}/billing/create-order`,
                {
                  price_id: plan?.startsWith?.('price_') ? plan : `price_${plan}_one_time`,
                  idempotency_key: `paypal-${Date.now()}-${Math.random().toString(16).slice(2)}`,
                },
                token ? { headers: { Authorization: `Bearer ${token}` } } : {}
              );
              return res.data.paypal_order_id;
            } catch (err) {
              handleError(err?.response?.data?.detail || err.message || 'Failed to create order');
              throw err;
            }
          },

          // Step 2: capture on approval
          onApprove: async (data) => {
            try {
              const res = await axios.post(
                `${API}/billing/capture-order`,
                { paypal_order_id: data.orderID },
                token ? { headers: { Authorization: `Bearer ${token}` } } : {}
              );
              setCaptureResult(res.data);
              setStatus('done');
              if (onSuccess) onSuccess(res.data);
            } catch (err) {
              handleError(err?.response?.data?.detail || err.message || 'Capture failed');
            }
          },

          onError: (err) => {
            handleError(err?.message || 'PayPal error');
          },

          onCancel: () => {
            setStatus('ready');
          },
        }).render(containerRef.current);
      })
      .catch((err) => handleError(err.message));

    // Cleanup
    return () => {
      rendered.current = false;
    };
  }, [clientId, plan, token, handleError, onSuccess]);

  if (status === 'done' && captureResult) {
    return (
      <div className={`paypal-checkout paypal-checkout--done ${className}`}>
        <CheckCircle2 size={28} className="paypal-checkout__icon paypal-checkout__icon--success" />
        <div className="paypal-checkout__message">
          <strong>Payment successful!</strong>
          <span>{captureResult.order?.credits || captureResult.credits || 0} credits added to your account.</span>
          <span className="paypal-checkout__sub">
            {captureResult.order?.price_id || captureResult.plan || plan} plan - ${captureResult.order?.amount || captureResult.amount || ''} {captureResult.order?.currency || captureResult.currency || 'USD'}
          </span>
        </div>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className={`paypal-checkout paypal-checkout--error ${className}`}>
        <XCircle size={20} className="paypal-checkout__icon paypal-checkout__icon--error" />
        <span className="paypal-checkout__error-msg">{errorMsg}</span>
        <button
          className="paypal-checkout__retry"
          onClick={() => { rendered.current = false; setStatus('idle'); setErrorMsg(''); }}
        >
          Try again
        </button>
      </div>
    );
  }

  return (
    <div className={`paypal-checkout ${className}`}>
      {(status === 'loading' || status === 'processing') && (
        <div className="paypal-checkout__spinner">
          <Loader2 size={16} className="paypal-checkout__spin" />
          <span>{status === 'processing' ? 'Processing…' : 'Loading PayPal…'}</span>
        </div>
      )}
      <div
        ref={containerRef}
        className="paypal-checkout__buttons"
        style={{ minHeight: status === 'ready' || status === 'processing' ? 44 : 0 }}
      />
    </div>
  );
}

/* ── Minimal scoped styles (no external CSS file needed) ── */
const styleTag = document.createElement('style');
styleTag.textContent = `
  .paypal-checkout { display: flex; flex-direction: column; gap: 8px; }
  .paypal-checkout__spinner { display: flex; align-items: center; gap: 6px; font-size: 13px; color: #888; padding: 8px 0; }
  .paypal-checkout__spin { animation: paypal-spin 0.9s linear infinite; }
  @keyframes paypal-spin { to { transform: rotate(360deg); } }
  .paypal-checkout--done { flex-direction: row; align-items: flex-start; gap: 12px; padding: 14px; border-radius: 10px; background: #f0fdf4; border: 1px solid #bbf7d0; }
  .paypal-checkout__icon--success { color: #16a34a; flex-shrink: 0; }
  .paypal-checkout__message { display: flex; flex-direction: column; gap: 2px; font-size: 14px; }
  .paypal-checkout__message strong { font-weight: 600; color: #15803d; }
  .paypal-checkout__sub { font-size: 12px; color: #888; }
  .paypal-checkout--error { flex-direction: row; align-items: center; gap: 8px; padding: 10px; border-radius: 8px; background: #fef2f2; border: 1px solid #fecaca; font-size: 13px; color: #dc2626; }
  .paypal-checkout__icon--error { flex-shrink: 0; }
  .paypal-checkout__retry { margin-left: auto; font-size: 12px; text-decoration: underline; cursor: pointer; background: none; border: none; color: #dc2626; }
`;
if (!document.querySelector('[data-paypal-checkout-styles]')) {
  styleTag.setAttribute('data-paypal-checkout-styles', 'true');
  document.head.appendChild(styleTag);
}

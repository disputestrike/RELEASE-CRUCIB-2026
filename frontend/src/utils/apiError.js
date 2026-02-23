/**
 * Centralized API error logging (audit fix Phase D).
 * Use in .catch((e) => logApiError('context', e)) so failures are visible in console.
 */
export function logApiError(context, err) {
  const msg = err?.response?.data?.detail ?? err?.message ?? String(err);
  const status = err?.response?.status;
  if (process.env.NODE_ENV !== 'production') {
    console.error(`[API ${context}]`, status ?? 'network', msg, err);
  } else {
    console.error(`[API ${context}]`, status ?? 'network', typeof msg === 'string' ? msg : JSON.stringify(msg));
  }
}

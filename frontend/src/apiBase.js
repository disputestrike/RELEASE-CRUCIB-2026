/**
 * Prefer an explicit backend URL when configured. Otherwise, in local development,
 * hit the backend directly on :8000 so workspace actions do not depend on a dev proxy.
 */
const _raw = process.env.REACT_APP_BACKEND_URL;

function inferDevBackendUrl() {
  if (typeof window === 'undefined' || process.env.NODE_ENV !== 'development') return '';
  const { protocol, hostname } = window.location || {};
  if (!protocol || !hostname) return '';
  return `${protocol}//${hostname}:8000`;
}

const BACKEND_URL =
  (_raw != null && String(_raw).trim()) ||
  (process.env.REACT_APP_API_URL != null && String(process.env.REACT_APP_API_URL).trim()) ||
  inferDevBackendUrl();

export const API_BASE = BACKEND_URL ? `${String(BACKEND_URL).replace(/\/$/, '')}/api` : '/api';

/**
 * Job SSE URL. In local development, CRA's webpack proxy often breaks EventSource/SSE, so we
 * call the API directly on port 8000. In production, same-origin /api is used unless
 * REACT_APP_BACKEND_URL is set.
 */
export function getJobStreamUrl(jobId) {
  if (!jobId) return '';
  const enc = encodeURIComponent(jobId);
  if (BACKEND_URL) {
    return `${String(BACKEND_URL).replace(/\/$/, '')}/api/jobs/${enc}/stream`;
  }
  if (typeof window !== 'undefined' && window.location?.hostname) {
    if (process.env.NODE_ENV === 'development') {
      const { protocol, hostname } = window.location;
      return `${protocol}//${hostname}:8000/api/jobs/${enc}/stream`;
    }
    return `${window.location.origin}/api/jobs/${enc}/stream`;
  }
  return `${API_BASE}/jobs/${enc}/stream`;
}

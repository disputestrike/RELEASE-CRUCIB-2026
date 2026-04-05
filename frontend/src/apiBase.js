/**
 * Same-origin /api when REACT_APP_BACKEND_URL is unset (CRA dev proxy).
 * Matches App.js API resolution — use here to avoid import cycles with App.jsx.
 */
const _raw = process.env.REACT_APP_BACKEND_URL;
const BACKEND_URL =
  _raw === '' || _raw === undefined ? '' : _raw || process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const API_BASE = BACKEND_URL ? `${String(BACKEND_URL).replace(/\/$/, '')}/api` : '/api';

/**
 * Job SSE URL. In local development, CRA's webpack proxy often breaks EventSource/SSE, so we
 * call the API directly on port 8000. In production, same-origin /api is used unless
 * REACT_APP_BACKEND_URL is set.
 */
export function getJobStreamUrl(jobId) {
  if (!jobId) return '';
  const enc = encodeURIComponent(jobId);
  if (_raw !== '' && _raw !== undefined && String(_raw).trim()) {
    return `${String(_raw).replace(/\/$/, '')}/api/jobs/${enc}/stream`;
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

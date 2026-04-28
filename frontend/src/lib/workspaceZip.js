/**
 * Workspace ZIP export uses delivery gates on the backend for “completed” jobs.
 * Failed / running / partial jobs must request ?draft=true to download interim bundles.
 */

/** @returns {string} '' or '?draft=true' */
export function workspaceZipQuery(jobStatus) {
  const s = String(jobStatus ?? '').trim().toLowerCase();
  if (!s) return '?draft=true';
  if (['completed', 'success', 'done'].includes(s)) return '';
  return '?draft=true';
}

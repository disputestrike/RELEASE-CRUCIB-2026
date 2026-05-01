import { stableTaskIdForJob } from './workspaceTaskBinding';

export function normalizeIdentityToken(value) {
  const raw = String(value || '').trim();
  if (!raw) return '';
  if (raw.startsWith('task_job_') && raw.length > 'task_job_'.length) {
    return raw.slice('task_job_'.length);
  }
  return raw;
}

export function resolveCanonicalTaskIdentity({
  jobId,
  taskId,
  sessionTaskId,
  activeTaskId,
  serverJob,
  existingTask,
  existingByJob,
  fallbackTaskId,
  currentUrlTaskId,
  lastRewriteKey,
}) {
  const preferredJobId = normalizeIdentityToken(jobId || serverJob?.id || existingByJob?.jobId || existingTask?.jobId);
  const fallback = String(fallbackTaskId || '').trim();
  const aliases = [
    taskId,
    sessionTaskId,
    activeTaskId,
    existingTask?.id,
    existingByJob?.id,
    preferredJobId ? stableTaskIdForJob(preferredJobId) : '',
    fallback,
  ]
    .map((id) => String(id || '').trim())
    .filter(Boolean);
  const canonicalId = String(
    (preferredJobId && stableTaskIdForJob(preferredJobId)) || existingByJob?.id || existingTask?.id || fallback || '',
  ).trim();
  const aliasSet = new Set(aliases);
  const urlTask = String(currentUrlTaskId || '').trim();
  const rewriteKey = preferredJobId ? `${preferredJobId}|${canonicalId}` : canonicalId;
  const shouldRewriteUrl = Boolean(
    canonicalId &&
      (urlTask === '' || urlTask !== canonicalId) &&
      (!urlTask || aliasSet.has(urlTask) || normalizeIdentityToken(urlTask) !== normalizeIdentityToken(canonicalId)) &&
      rewriteKey !== String(lastRewriteKey || ''),
  );
  return {
    canonicalId,
    canonicalJobId: preferredJobId || '',
    aliases: Array.from(aliasSet),
    shouldRewriteUrl,
    rewriteKey,
    shouldUpsert: Boolean(canonicalId),
  };
}

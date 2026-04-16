export function normalizeListJobStatus(status) {
  const value = String(status || '').toLowerCase();
  if (value === 'complete') return 'completed';
  return value || 'pending';
}

export function listJobToTaskEntry(job) {
  const jobId = job?.id || job?.job_id;
  if (!jobId) return null;

  const goalText = String(job?.goal || job?.payload?.goal || job?.name || 'Build').trim();
  const createdRaw = job?.created_at || job?.createdAt;
  let createdAt = Date.now();
  if (createdRaw) {
    const parsed = Date.parse(String(createdRaw));
    if (Number.isFinite(parsed)) createdAt = parsed;
  }

  return {
    id: `task_job_${jobId}`,
    jobId,
    name: goalText.slice(0, 120),
    prompt: goalText,
    status: normalizeListJobStatus(job?.status),
    type: 'build',
    createdAt,
    linkedProjectId: job?.project_id ?? job?.payload?.project_id ?? null,
  };
}

export function buildStreamEventId(event) {
  if (event?.id) return event.id;
  return `${event?.type || 'event'}-${event?.step_id ?? ''}-${event?.ts ?? ''}-${JSON.stringify(event?.payload || {}).slice(0, 80)}`;
}

export function normalizeJobEvents(events, maxEvents = 500) {
  const rows = Array.isArray(events) ? events : [];
  const deduped = [];
  const seen = new Set();

  for (let i = 0; i < rows.length; i += 1) {
    const event = rows[i];
    const id = buildStreamEventId(event);
    if (seen.has(id)) continue;
    seen.add(id);
    deduped.push({ ...event, id });
  }

  const limit = Number.isFinite(maxEvents) ? Math.max(1, Math.floor(maxEvents)) : 500;
  if (deduped.length <= limit) return deduped;
  return deduped.slice(-limit);
}

export function taskStatusFromJobStatus(jobStatus) {
  const status = String(jobStatus || '').toLowerCase();
  if (status === 'completed') return 'completed';
  if (status === 'failed' || status === 'cancelled') return 'failed';
  if (status === 'planned' || status === 'approved' || status === 'queued' || status === 'running' || status === 'blocked') {
    return 'running';
  }
  return 'running';
}

export function jobTimestampToMillis(value, fallback = Date.now()) {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value < 1e12 ? value * 1000 : value;
  }
  if (typeof value === 'string' && value.trim()) {
    const parsed = new Date(value).getTime();
    if (Number.isFinite(parsed)) return parsed;
  }
  return fallback;
}

export function stableTaskIdForJob(jobId) {
  const clean = String(jobId || '').trim();
  return clean ? `task_job_${clean}` : '';
}

export function taskEntryFromJob({ job, jobId, taskId, existingTask, fallbackPrompt = '' }) {
  const durableJobId = String(jobId || job?.id || job?.job_id || '').trim();
  if (!durableJobId) return null;
  const prompt = String(job?.goal || existingTask?.prompt || fallbackPrompt || '').trim();
  const name = String(existingTask?.name || prompt || 'Build').split('\n')[0].slice(0, 120);
  const id = String(taskId || existingTask?.id || stableTaskIdForJob(durableJobId)).trim();
  if (!id) return null;
  return {
    id,
    name,
    prompt,
    status: taskStatusFromJobStatus(job?.status || existingTask?.status),
    type: 'build',
    jobId: durableJobId,
    createdAt: existingTask?.createdAt ?? jobTimestampToMillis(job?.created_at || job?.createdAt),
    ...(job?.project_id ? { linkedProjectId: job.project_id } : {}),
  };
}

export function bindWorkspaceSearchParams(prevParams, { jobId, taskId, projectId } = {}) {
  const next = new URLSearchParams(prevParams || '');
  if (jobId) next.set('jobId', String(jobId));
  if (taskId) next.set('taskId', String(taskId));
  if (projectId) next.set('projectId', String(projectId));
  return next;
}

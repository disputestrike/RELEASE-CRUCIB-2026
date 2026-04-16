/**
 * Map backend SSE / job_events shapes → PDF-style { type, jobId, timestamp, payload }.
 */
export function normalizeSseToWorkspaceEvent(jobId, data) {
  if (!data || !data.type) return null;
  const ts = typeof data.ts === 'number' ? data.ts : Date.now();
  const payload = data.payload && typeof data.payload === 'object' ? data.payload : {};

  const t = data.type;
  if (t === 'step_started') {
    return {
      type: 'phase.started',
      jobId,
      timestamp: ts,
      payload: { phaseName: payload.phase || payload.step_key || 'Build', ...payload },
    };
  }
  if (t === 'step_completed') {
    return {
      type: 'phase.complete',
      jobId,
      timestamp: ts,
      payload: { phaseName: payload.phase || payload.step_key || 'Build', ...payload },
    };
  }
  if (t === 'step_failed' || t === 'job_failed') {
    return {
      type: 'issue.detected',
      jobId,
      timestamp: ts,
      payload: { title: payload.error_message || payload.message || t, severity: 'high', ...payload },
    };
  }
  if (t === 'job_completed') {
    return {
      type: 'job.complete',
      jobId,
      timestamp: ts,
      payload: {
        qualityScore: payload.quality_score ?? payload.qualityScore ?? 0,
        url: payload.url,
        ...payload,
      },
    };
  }
  if (t === 'brain_guidance') {
    const inner = payload.payload || payload;
    return {
      type: 'agent.thinking',
      jobId,
      timestamp: ts,
      payload: inner,
    };
  }
  if (t.includes('file') || t.includes('workspace_write') || payload.path) {
    return {
      type: 'artifact.created',
      jobId,
      timestamp: ts,
      payload: {
        type: 'file',
        path: payload.path || payload.file_path || '',
        ...payload,
      },
    };
  }
  return {
    type: t.replace(/\./g, '_'),
    jobId,
    timestamp: ts,
    payload,
  };
}

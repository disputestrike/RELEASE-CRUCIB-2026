/**
 * Derive Manus-class live UI strings from job stream + steps (no fake data).
 */
import { formatWorkspaceActivityEvent } from './workspaceActivityEvents';

function humanizeAgentLabel(raw) {
  const t = (raw || '').trim();
  if (!t) return '';
  const noAgents = t.replace(/^agents\./i, '');
  const spaced = noAgents.replace(/[._]+/g, ' ').replace(/\s+/g, ' ').trim();
  if (!spaced) return '';
  return spaced.replace(/\b\w/g, (c) => c.toUpperCase());
}

function chipKindForEvent(type, label = '') {
  const t = String(type || '');
  if (['step_completed', 'dag_node_completed', 'file_written', 'job_completed'].includes(t)) {
    return 'ok';
  }
  if (
    ['step_failed', 'job_failed', 'step_infrastructure_failure', 'step_retry_exhausted'].includes(t) ||
    /failed|blocked|issue|needs work/i.test(label)
  ) {
    return 'warn';
  }
  if (
    [
      'step_started',
      'step_retrying',
      'step_verifying',
      'job_started',
      'job_status_changed',
      'verification_attempt_failed',
    ].includes(t) ||
    /working|retrying|verifying|preflight|pre-build/i.test(label)
  ) {
    return 'run';
  }
  return 'info';
}

export function extractActivityChips(events, limit = 10) {
  if (!Array.isArray(events) || !events.length) return [];
  const chips = [];
  const seen = new Set();
  for (let i = events.length - 1; i >= 0 && chips.length < limit; i -= 1) {
    const ev = events[i];
    const t = ev?.type || ev?.event_type;
    const id = ev?.id || `${t}-${i}`;
    if (seen.has(id)) continue;
    const label = formatWorkspaceActivityEvent(ev);
    if (!label) continue;
    seen.add(id);
    chips.push({ id, label, kind: chipKindForEvent(t, label) });
  }
  return chips.reverse();
}

function extractActivityChipsLegacy(events, limit = 10) {
  if (!Array.isArray(events) || !events.length) return [];
  const chips = [];
  const seen = new Set();
  for (let i = events.length - 1; i >= 0 && chips.length < limit; i -= 1) {
    const ev = events[i];
    const t = ev?.type || ev?.event_type;
    const p = ev?.payload || {};
    const id = ev?.id || `${t}-${i}`;
    if (seen.has(id)) continue;
    let label = '';
    let kind = 'info';
    const name = humanizeAgentLabel(p.agent_name || p.step_key || p.step || '');
    switch (t) {
      case 'step_completed':
        label = name ? `Done · ${name}` : 'Step completed';
        kind = 'ok';
        break;
      case 'step_started':
        label = name ? `Working · ${name}` : 'Started step';
        kind = 'run';
        break;
      case 'step_failed':
        label = name ? `Issue · ${name}` : 'Step issue';
        kind = 'warn';
        break;
      case 'step_retrying':
        label = name ? `Retry · ${name}` : 'Retrying';
        kind = 'run';
        break;
      case 'dag_node_completed': {
        const files = p.output_files;
        const f = Array.isArray(files) && files.length ? String(files[0]).split('/').pop() : '';
        label = f ? `Wrote · ${f}` : 'Workspace updated';
        kind = 'ok';
        break;
      }
      case 'job_started':
        label = 'Run started';
        kind = 'run';
        break;
      case 'job_completed':
        label = 'Run finished';
        kind = 'ok';
        break;
      case 'job_failed':
        label = 'Run needs repair';
        kind = 'warn';
        break;
      default:
        label = '';
    }
    if (!label) continue;
    seen.add(id);
    chips.push({ id, label, kind });
  }
  return chips.reverse();
}

export function deriveRightRailSubtitle(events, steps) {
  if (Array.isArray(events) && events.length) {
    for (let i = events.length - 1; i >= 0; i -= 1) {
      const ev = events[i];
      const t = ev?.type || ev?.event_type;
      const formatted = formatWorkspaceActivityEvent(ev);
      if (formatted && t !== 'brain_guidance' && t !== 'workspace_transcript') {
        return formatted;
      }
    }
  }
  const sorted = [...(steps || [])].sort((a, b) => (a.order_index ?? 0) - (b.order_index ?? 0));
  const run = sorted.find((s) => s.status === 'running' || s.status === 'verifying');
  if (run) {
    const n = humanizeAgentLabel(run.agent_name || run.step_key || '');
    if (n) return `Working on - ${n}`;
  }
  return '';
}

function deriveRightRailSubtitleLegacy(events, steps) {
  if (Array.isArray(events) && events.length) {
    for (let i = events.length - 1; i >= 0; i -= 1) {
      const ev = events[i];
      const t = ev?.type || ev?.event_type;
      const p = ev?.payload || {};
      if (t === 'step_started' || t === 'step_retrying') {
        const n = humanizeAgentLabel(p.agent_name || p.step_key || p.step);
        if (n) return `Working on · ${n}`;
      }
      if (t === 'dag_node_completed') {
        const files = p.output_files;
        if (Array.isArray(files) && files.length) {
          const path = String(files[0]);
          const short = path.length > 42 ? `…${path.slice(-40)}` : path;
          return `Updated · ${short}`;
        }
      }
    }
  }
  const sorted = [...(steps || [])].sort((a, b) => (a.order_index ?? 0) - (b.order_index ?? 0));
  const run = sorted.find((s) => s.status === 'running' || s.status === 'verifying');
  if (run) {
    const n = humanizeAgentLabel(run.agent_name || run.step_key || '');
    if (n) return `Working on · ${n}`;
  }
  return '';
}

function parseTs(v) {
  if (v == null) return null;
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function computeDockMeta({ job, steps, stage, events }) {
  const sorted = [...(steps || [])].sort((a, b) => (a.order_index ?? 0) - (b.order_index ?? 0));
  const total = sorted.length;
  const completed = sorted.filter((s) => s.status === 'completed').length;
  const running = sorted.find((s) => s.status === 'running' || s.status === 'verifying');
  const failed = sorted.find((s) => s.status === 'failed' || s.status === 'blocked');

  let title = '';
  if (running) {
    title = humanizeAgentLabel(running.agent_name || running.step_key || '') || 'In progress';
  } else if (failed && (job?.status === 'failed' || job?.status === 'blocked')) {
    title = humanizeAgentLabel(failed.agent_name || failed.step_key || '') || 'Ready to continue';
  } else if (job?.status === 'approved' && !running) {
    if (!sorted.length) {
      title = 'Starting your run';
    } else if (total > 0 && completed === total) {
      title = 'All steps complete';
    } else {
      const next = sorted.find((s) => s.status !== 'completed' && s.status !== 'failed' && s.status !== 'blocked');
      title = next ? humanizeAgentLabel(next.agent_name || next.step_key || '') || 'Starting' : 'Starting your run';
    }
  } else if (total > 0 && completed === total) {
    title = 'All steps complete';
  } else if (sorted.length) {
    const next = sorted.find((s) => s.status !== 'completed' && s.status !== 'failed' && s.status !== 'blocked');
    title = next ? humanizeAgentLabel(next.agent_name || next.step_key || '') || 'Queued' : 'Queued';
  } else {
    title = job?.status === 'queued' ? 'In queue' : 'Setting up';
  }

  let stateKey = 'idle';
  let stateLabel = 'Ready';
  if (stage === 'plan') {
    stateKey = 'waiting';
    stateLabel = 'Waiting for you';
  } else if (job?.status === 'failed' || job?.status === 'blocked') {
    stateKey = 'working';
    stateLabel = 'Ready to continue';
  } else if (job?.status === 'cancelled') {
    stateKey = 'needs_input';
    stateLabel = 'Paused';
  } else if (job?.status === 'approved') {
    stateKey = 'working';
    stateLabel = 'Starting';
  } else if (job?.status === 'queued') {
    stateKey = 'queued';
    stateLabel = 'In queue';
  } else if (job?.status === 'running' || stage === 'running') {
    stateKey = running ? 'working' : 'working';
    stateLabel = running ? 'Working' : 'Working';
  } else if (job?.status === 'completed') {
    stateKey = 'done';
    stateLabel = 'Done';
  }

  let elapsedSec = null;
  const startTs =
    parseTs(running?.started_at) ||
    parseTs(running?.updated_at) ||
    (Array.isArray(events) && events.length
      ? parseTs(events[events.length - 1]?.ts || events[events.length - 1]?.timestamp)
      : null);
  if (
    startTs &&
    (job?.status === 'running' || job?.status === 'queued' || job?.status === 'approved')
  ) {
    elapsedSec = Math.max(0, Math.floor((Date.now() - startTs.getTime()) / 1000));
  }

  return {
    title: title.slice(0, 120),
    progress: total > 0 ? { done: completed, total } : null,
    stateKey,
    stateLabel,
    elapsedSec,
  };
}

/**
 * Run is actively moving (or about to): same signal for Preview "building" and composer steer routing.
 */
export function isWorkspaceLiveBuildPhase({ jobStatus, stage }) {
  return (
    stage === 'running' ||
    jobStatus === 'running' ||
    jobStatus === 'queued' ||
    jobStatus === 'approved' ||
    jobStatus === 'failed' ||
    jobStatus === 'blocked'
  );
}

/**
 * PreviewPanel status: keep in sync with workspace run lifecycle (Sandpack / remote URL).
 */
export function selectWorkspacePreviewStatus({ jobStatus, stage, isCompleted }) {
  if (jobStatus === 'cancelled') return 'blocked';
  if (isCompleted) return 'ready';
  if (isWorkspaceLiveBuildPhase({ jobStatus, stage })) {
    return 'building';
  }
  return 'idle';
}

export function derivePreviewReadiness({
  previewStatus,
  previewUrl,
  hasSandpack,
  devPreviewStatus,
  devPreviewError,
  isBootingDevPreview,
}) {
  if (previewStatus === 'blocked') {
    return {
      state: 'blocked',
      label: 'Paused',
      detail: devPreviewError || 'Run paused before preview could be refreshed.',
      severity: 'error',
    };
  }
  if (previewUrl) {
    return {
      state: 'remote_live',
      label: 'Live URL',
      detail: 'Rendering from a real preview or deployment URL.',
      severity: 'ok',
    };
  }
  const serverState = devPreviewStatus?.preview_state || devPreviewStatus?.readiness?.state || devPreviewStatus?.status;
  if (serverState === 'ready' && devPreviewStatus?.dev_server_url) {
    return {
      state: 'dev_server_ready',
      label: 'Dev preview ready',
      detail: 'Backend preview server returned a loadable app URL.',
      severity: 'ok',
    };
  }
  if (hasSandpack) {
    return {
      state: 'sandpack_fallback',
      label: 'File preview',
      detail: 'Rendering directly from generated workspace files while the live server catches up.',
      severity: 'ok',
    };
  }
  if (isBootingDevPreview) {
    return {
      state: 'booting',
      label: 'Starting server',
      detail: 'Checking the job workspace for a build, dist, out, public, or index.html preview root.',
      severity: 'working',
    };
  }
  if (serverState === 'waiting_for_index' || devPreviewStatus?.status === 'building') {
    const fileCount = devPreviewStatus?.readiness?.file_count;
    return {
      state: 'waiting_for_index',
      label: 'Waiting for app entry',
      detail:
        typeof fileCount === 'number'
          ? `${fileCount} files found, but no index.html is ready yet.`
          : 'Workspace exists, but no index.html is ready yet.',
      severity: 'working',
    };
  }
  if (serverState === 'waiting_for_workspace' || devPreviewStatus?.status === 'pending') {
    return {
      state: 'waiting_for_workspace',
      label: 'Waiting for files',
      detail: 'No preview workspace is ready yet. The build may still be planning or writing files.',
      severity: 'working',
    };
  }
  if (devPreviewError) {
    return {
      state: 'error',
      label: 'Preview issue',
      detail: devPreviewError,
      severity: 'error',
    };
  }
  if (previewStatus === 'ready') {
    return {
      state: 'ready_without_target',
      label: 'Ready, no target',
      detail: 'Build is complete, but no live URL or packable preview files were found.',
      severity: 'warn',
    };
  }
  return {
    state: 'idle',
    label: 'Next up',
    detail: 'Preview will appear after files land or a live preview URL is assigned.',
    severity: 'idle',
  };
}

/** Status strip when there is no job id yet (input / plan / loading). */
export function computeDockMetaPreJob({ stage, loading }) {
  if (loading) {
    return {
      title: 'Working on it',
      progress: null,
      stateKey: 'working',
      stateLabel: 'Please wait',
      elapsedSec: null,
    };
  }
  if (stage === 'plan') {
    return {
      title: 'Review the plan',
      progress: null,
      stateKey: 'waiting',
      stateLabel: 'Waiting for you',
      elapsedSec: null,
    };
  }
  return {
    title: 'Describe what to build',
    progress: null,
    stateKey: 'idle',
    stateLabel: 'Ready',
    elapsedSec: null,
  };
}

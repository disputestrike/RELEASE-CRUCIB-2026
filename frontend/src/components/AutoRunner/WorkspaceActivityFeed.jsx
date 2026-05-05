/**
 * WorkspaceActivityFeed — Manus-style briefing above the composer: soft surfaces,
 * checklist steps, and short live lines (no heavy timeline chrome).
 */
import React, { useEffect, useMemo, useRef } from 'react';
import { Check, Loader2, Circle } from 'lucide-react';
import { formatWorkspaceActivityEvent } from '../../workspace/workspaceActivityEvents';
import './WorkspaceActivityFeed.css';

function humanizeAgentLabel(raw) {
  const t = (raw || '').trim();
  if (!t) return 'Step';
  const noAgents = t.replace(/^agents\./i, '');
  const spaced = noAgents.replace(/[._]+/g, ' ').replace(/\s+/g, ' ').trim();
  if (!spaced) return 'Step';
  return spaced.replace(/\b\w/g, (c) => c.toUpperCase());
}

function stepLabel(s) {
  const raw = (s.agent_name || s.step_key || 'Step').trim();
  const deinternal = raw
    .replace(/^agents\./i, '')
    .replace(/\.agent$/i, '')
    .replace(/_/g, ' ');
  return humanizeAgentLabel(deinternal || 'Step');
}

function humanizeJobStatus(status) {
  const s = String(status || '').toLowerCase();
  const map = {
    running: 'Writing files',
    queued: 'In queue',
    approved: 'Starting',
    failed: 'Fixing',
    completed: 'Done',
    cancelled: 'Stopped',
    blocked: 'Fixing',
    pending: 'Starting',
  };
  return map[s] || (status ? String(status).replace(/_/g, ' ') : '');
}

function formatEvent(ev) {
  const t = ev.type || ev.event_type;
  const p = ev.payload && typeof ev.payload === 'object' ? ev.payload : {};
  const fromJson = () => {
    try {
      return JSON.parse(ev?.payload_json || '{}');
    } catch {
      return {};
    }
  };
  const payload = Object.keys(p).length ? p : fromJson();
  const name = humanizeAgentLabel(payload.agent_name || payload.step_key || payload.step || ev.step || payload.node_key || '');
  switch (t) {
    case 'step_started':
      return name && name !== 'Step' ? `Working on: ${name}` : 'Working on the next step';
    case 'step_completed':
      return name && name !== 'Step' ? `Done: ${name}` : 'Step completed';
    case 'step_failed':
      return name && name !== 'Step' ? `Fixing: ${name}` : 'Fixing the next item';
    case 'step_retrying':
      return name && name !== 'Step' ? `Retrying: ${name}` : 'Retrying step';
    case 'job_started':
      return 'Build started';
    case 'job_completed':
      return 'Workspace ready';
    case 'job_failed': {
      return 'Fix loop continuing';
    }
    case 'dag_node_started':
      return name && name !== 'Step' ? `Starting ${name}` : 'Starting next task';
    case 'dag_node_completed': {
      const files = payload.output_files;
      if (Array.isArray(files) && files.length) {
        const short = files.slice(0, 4).map((x) => String(x).split('/').pop() || x);
        return `Wrote ${files.length} file(s): ${short.join(', ')}${files.length > 4 ? '…' : ''}`;
      }
      return name && name !== 'Step' ? `Done: ${name}` : 'Task completed';
    }
    case 'user_steering':
      return 'Steering applied';
    case 'job_reactivated':
      return 'Run reactivated';
    case 'brain_guidance':
      // Center chat also maps brain_guidance; keep a one-line echo here for the live strip only.
      if (payload.headline) return String(payload.headline).trim().slice(0, 160);
      if (payload.summary) return String(payload.summary).trim().slice(0, 160);
      return 'Brain update';
    case 'workspace_transcript': {
      const isAsst = payload.role === 'assistant';
      const line = (payload.text || payload.body || '').trim().slice(0, 120);
      if (!line) return null;
      return isAsst ? `Reply: ${line}` : `You: ${line}`;
    }
    case 'preflight_report': {
      const pf = payload.preflight || payload;
      const n = Array.isArray(pf?.issues) ? pf.issues.length : 0;
      if (pf?.passed === true && n === 0) return 'Preflight: environment OK';
      if (pf?.passed === true) return `Preflight: OK (${n} note(s))`;
      if (pf?.passed === false) return `Preflight: ${n || 'some'} issue(s) (run may still proceed)`;
      return n ? `Preflight: ${n} note(s)` : 'Preflight: completed';
    }
    case 'spec_guardian': {
      const sg = payload.spec_guard || payload;
      if (sg?.blocks_run) return 'Spec check: blocked run (goal out of template scope)';
      return 'Spec check: OK';
    }
    case 'file_written': {
      const path = (payload.path || '').trim();
      const base = path ? path.split('/').pop() || path : '';
      return base ? `Saved file: ${base}` : 'File written';
    }
    case 'brain_prebuild_briefing': {
      const sim = payload.similar_builds_found;
      const pred = Array.isArray(payload.predicted_failures) ? payload.predicted_failures.length : 0;
      if (typeof sim === 'number' && sim > 0) return `Pre-build: ${sim} similar past build(s); ${pred} risk flag(s)`;
      if (pred > 0) return `Pre-build: ${pred} predicted risk(s)`;
      return payload.intelligence_available ? 'Pre-build intelligence loaded' : null;
    }
    case 'verification_result': {
      const ok = payload.passed === true || payload.passed === 'true';
      const sc = payload.score;
      if (ok) return typeof sc === 'number' ? `Proof: passed (${sc})` : 'Proof: passed';
      return typeof sc === 'number' ? `Proof: needs work (${sc})` : 'Proof: needs work';
    }
    case 'verification_attempt_failed':
      return 'Checking again after an update';
    case 'step_retry_exhausted':
      return 'Continuing with a smaller fix pass';
    case 'step_verifying':
      return name && name !== 'Step' ? `Checking proof: ${name}` : 'Checking proof';
    case 'scheduler_deadlock_detected':
      return 'Scheduler: deadlock resolved';
    case 'execution_authority':
    case 'step_created':
    case 'job_status_changed':
    case 'step_status_changed':
      return null;
    default:
      return null;
  }
}

export default function WorkspaceActivityFeed({
  stage,
  plan,
  job,
  steps = [],
  events = [],
  effectiveJobId,
  loading = false,
  connectionMode = 'offline',
  /** When the job row has not hydrated yet, show the in-composer goal text. */
  fallbackGoal = '',
  /** When true, do not repeat the goal as body text (shown in chat bubbles above). */
  hideGoalEcho = false,
  openWorkspacePath,
}) {
  const sortedSteps = useMemo(
    () => [...steps].sort((a, b) => (a.order_index ?? 0) - (b.order_index ?? 0)),
    [steps],
  );
  /** Do not imply active work when the job row is already terminal (stale step rows can lag). */
  const suppressRunningFocus = ['failed', 'cancelled', 'blocked', 'completed'].includes(job?.status);
  const runningStep = useMemo(() => {
    if (suppressRunningFocus) return undefined;
    return sortedSteps.find((s) => s.status === 'running' || s.status === 'verifying');
  }, [sortedSteps, suppressRunningFocus]);
  const completedCount = useMemo(() => sortedSteps.filter((s) => s.status === 'completed').length, [sortedSteps]);
  const totalSteps = sortedSteps.length;

  const feedEvents = useMemo(() => {
    const lines = [];
    for (const ev of events) {
      const text = formatWorkspaceActivityEvent(ev);
      if (text) lines.push({ id: ev.id ?? `${text}-${lines.length}`, text });
    }
    return lines.slice(-40);
  }, [events]);

  // Auto-scroll the live stream to the bottom as new events arrive so users see
  // latest activity without manual scrolling. Respects reduced-motion preferences.
  const streamRef = useRef(null);
  useEffect(() => {
    const el = streamRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [feedEvents.length]);

  const latestWritePaths = useMemo(() => {
    for (let i = events.length - 1; i >= 0; i -= 1) {
      const ev = events[i];
      const t = ev.type || ev.event_type;
      if (t !== 'dag_node_completed') continue;
      const p = ev.payload || {};
      const files = p.output_files;
      if (!Array.isArray(files) || files.length === 0) continue;
      return files.slice(0, 6).map((x) => String(x));
    }
    return [];
  }, [events]);

  if (!effectiveJobId) {
    return null;
  }

  const goalRaw = (job?.goal || fallbackGoal || '').trim();
  const goalLine = goalRaw.slice(0, 240);
  const goalTruncated = goalRaw.length > 240;

  const hasOptionalLog = sortedSteps.length > 0 || feedEvents.length > 0 || totalSteps > 0;
  /** Always-visible lines (not tucked inside the disclosure) until the run is terminal. */
  const showLiveStrip =
    feedEvents.length > 0 &&
    job?.status &&
    !['completed', 'failed', 'cancelled'].includes(String(job.status).toLowerCase());

  return (
    <section className="uw-activity-feed" aria-label="Behind the scenes">
      <div className="uw-af-surface uw-af-surface--secondary">
        <div className="uw-af-top">
          <p className="uw-af-heading uw-af-heading--secondary">Behind the scenes</p>
          <div className="uw-af-meta">
            {job?.status ? (
              <span className="uw-af-pill">{humanizeJobStatus(job.status)}</span>
            ) : loading ? (
              <span className="uw-af-pill">…</span>
            ) : null}
            <span className={`uw-af-live uw-af-live--${connectionMode}`} title="Connection to your run">
              <span className="uw-af-live-dot" aria-hidden />
              {connectionMode === 'stream' ? 'Live' : connectionMode === 'polling' ? 'Syncing' : 'Offline'}
            </span>
          </div>
        </div>

        {stage === 'plan' && plan && (
          <p className="uw-af-plan-hint">Plan is ready — review the proposal below, then continue.</p>
        )}

        {!job && effectiveJobId && (
          <p className="uw-af-body uw-af-body--tight">{loading ? 'Loading job…' : 'Connecting…'}</p>
        )}

        {goalLine && !hideGoalEcho && (
          <p className="uw-af-goal">
            {goalLine}
            {goalTruncated ? '…' : ''}
          </p>
        )}

        {showLiveStrip && (
          <ul className="uw-af-live-strip" aria-live="polite" aria-label="Live activity from your run">
            {feedEvents.slice(-10).map((row) => (
              <li key={row.id}>{row.text}</li>
            ))}
          </ul>
        )}

        {runningStep && (
          <div className="uw-af-focus-wrap">
            <div className="uw-af-focus" role="status">
              <span className="uw-af-focus-icon" aria-hidden>
                <Loader2 className="uw-af-spin" size={16} />
              </span>
                <span className="uw-af-focus-text">
                <span className="uw-af-focus-title">{stepLabel(runningStep)}</span>
                {runningStep.narrative ? (
                  <span className="uw-af-focus-sub">{runningStep.narrative}</span>
                ) : null}
              </span>
            </div>
          </div>
        )}

        {openWorkspacePath && latestWritePaths.length > 0 && (
          <div className="uw-af-writes" aria-label="Latest workspace writes">
            <p className="uw-af-writes-label">Open in Code</p>
            <ul className="uw-af-writes-list">
              {latestWritePaths.map((p) => (
                <li key={p}>
                  <button type="button" className="uw-af-write-link" onClick={() => openWorkspacePath(p)}>
                    {p}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {hasOptionalLog ? (
          <details className="uw-af-optional-log">
            <summary className="uw-af-optional-summary">
              Timeline &amp; steps
              {sortedSteps.length > 0 ? ` (${sortedSteps.length})` : ''}
            </summary>
            {sortedSteps.length > 0 ? (
              <ul className="uw-af-checklist">
                {sortedSteps.map((s) => (
                  <li key={s.id} className={`uw-af-check st-${s.status}`}>
                    <span className="uw-af-check-ic" aria-hidden>
                      {s.status === 'completed' ? (
                        <Check size={14} strokeWidth={2.5} />
                      ) : s.status === 'running' || s.status === 'verifying' ? (
                        <Loader2 className="uw-af-spin" size={14} />
                      ) : s.status === 'failed' || s.status === 'blocked' ? (
                        <span className="uw-af-dot uw-af-dot--err" />
                      ) : (
                        <Circle size={11} strokeWidth={1.5} className="uw-af-pending-ring" />
                      )}
                    </span>
                    <span className="uw-af-check-label">{stepLabel(s)}</span>
                  </li>
                ))}
              </ul>
            ) : null}

            {feedEvents.length > 0 ? (
              <ul className="uw-af-stream" ref={streamRef}>
                {feedEvents.map((row) => (
                  <li key={row.id}>{row.text}</li>
                ))}
              </ul>
            ) : null}

            {totalSteps > 0 ? (
              <div className="uw-af-foot">
                <span>
                  {completedCount} / {totalSteps} steps
                </span>
              </div>
            ) : null}
          </details>
        ) : null}
      </div>
    </section>
  );
}

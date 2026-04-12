/**
 * WorkspaceActivityFeed — Manus-style briefing above the composer: soft surfaces,
 * checklist steps, and short live lines (no heavy timeline chrome).
 */
import React, { useMemo } from 'react';
import { Check, Loader2, Circle } from 'lucide-react';
import './WorkspaceActivityFeed.css';

function stepLabel(s) {
  return (s.agent_name || s.step_key || 'Step').trim();
}

function formatEvent(ev) {
  const t = ev.type || ev.event_type;
  const p = ev.payload || {};
  const name = (p.agent_name || p.step_key || p.step || ev.step || '').trim();
  switch (t) {
    case 'step_started':
      return name ? `Working on: ${name}` : 'Started a new step';
    case 'step_completed':
      return name ? `Finished: ${name}` : 'Step completed';
    case 'step_failed':
      return name ? `Issue: ${name}` : 'Step failed';
    case 'step_retrying':
      return name ? `Retrying: ${name}` : 'Retrying step';
    case 'job_started':
      return 'Build started';
    case 'job_completed':
      return 'Build completed';
    case 'job_failed':
      return 'Build failed';
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
  const runningStep = useMemo(
    () => sortedSteps.find((s) => s.status === 'running' || s.status === 'verifying'),
    [sortedSteps],
  );
  const completedCount = useMemo(() => sortedSteps.filter((s) => s.status === 'completed').length, [sortedSteps]);
  const totalSteps = sortedSteps.length;

  const feedEvents = useMemo(() => {
    const lines = [];
    for (const ev of events) {
      const text = formatEvent(ev);
      if (text) lines.push({ id: ev.id ?? `${text}-${lines.length}`, text });
    }
    return lines.slice(-14);
  }, [events]);

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

  return (
    <section className="uw-activity-feed" aria-label="Live activity">
      <div className="uw-af-surface">
        <div className="uw-af-top">
          <p className="uw-af-heading">Live activity</p>
          <div className="uw-af-meta">
            {job?.status ? <span className="uw-af-pill">{job.status}</span> : loading ? <span className="uw-af-pill">…</span> : null}
            <span className={`uw-af-live uw-af-live--${connectionMode}`} title="Stream status">
              <span className="uw-af-live-dot" aria-hidden />
              {connectionMode === 'stream' ? 'Live' : connectionMode === 'polling' ? 'Polling' : 'Offline'}
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

        {runningStep && (
          <div className="uw-af-focus-wrap">
            <div className="uw-af-focus" role="status">
              <span className="uw-af-focus-icon" aria-hidden>
                <Loader2 className="uw-af-spin" size={16} />
              </span>
              <span className="uw-af-focus-text">
                <span className="uw-af-focus-title">{stepLabel(runningStep)}</span>
                {(runningStep.narrative || runningStep.step_key) && (
                  <span className="uw-af-focus-sub">{runningStep.narrative || runningStep.step_key}</span>
                )}
              </span>
            </div>
          </div>
        )}

        {sortedSteps.length > 0 && (
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

        {feedEvents.length > 0 && (
          <ul className="uw-af-stream">
            {feedEvents.map((row) => (
              <li key={row.id}>{row.text}</li>
            ))}
          </ul>
        )}

        {totalSteps > 0 && (
          <div className="uw-af-foot">
            <span>
              {completedCount} / {totalSteps} steps
            </span>
          </div>
        )}
      </div>
    </section>
  );
}

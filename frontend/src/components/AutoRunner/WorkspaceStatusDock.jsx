/**
 * Persistent status strip above the composer (Manus-style dock): current beat, progress, state, optional elapsed.
 */
import React, { useMemo } from 'react';
import { computeDockMeta, computeDockMetaPreJob } from '../../workspace/workspaceLiveUi';
import './WorkspaceStatusDock.css';

function formatElapsed(sec) {
  if (sec == null || sec < 0) return null;
  if (sec < 60) return `${sec}s`;
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

export default function WorkspaceStatusDock({ 
  jobId, 
  job, 
  steps, 
  stage, 
  events, 
  connectionMode, 
  loading = false,
  taskProgress = null,
  actionChips = [],
  controller = null,
}) {
  const meta = useMemo(
    () => (jobId ? computeDockMeta({ job, steps, stage, events }) : computeDockMetaPreJob({ stage, loading })),
    [jobId, job, steps, stage, events, loading],
  );

  const displayTitle = taskProgress?.summary || meta.title;
  const displayPercentage = taskProgress?.percentage;

  return (
    <div className="wsd-root" role="status" aria-live="polite">
      <div className="wsd-main">
        <span className="wsd-title">{displayTitle}</span>
        {displayPercentage != null ? (
          <span className="wsd-progress">
            {Math.round(displayPercentage)}%
          </span>
        ) : meta.progress ? (
          <span className="wsd-progress">
            {meta.progress.done}/{meta.progress.total}
          </span>
        ) : null}
      </div>
      <div className="wsd-meta">
        <span className={`wsd-state wsd-state--${meta.stateKey}`}>{meta.stateLabel}</span>
        {formatElapsed(meta.elapsedSec) ? <span className="wsd-elapsed">{formatElapsed(meta.elapsedSec)}</span> : null}
        <span className={`wsd-sync wsd-sync--${connectionMode || 'offline'}`} title="Connection">
          {connectionMode === 'stream' ? 'Live' : connectionMode === 'polling' ? 'Syncing' : 'Offline'}
        </span>
      </div>
    </div>
  );
}

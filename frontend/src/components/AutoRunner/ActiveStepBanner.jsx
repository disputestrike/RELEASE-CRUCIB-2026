/**
 * ActiveStepBanner — pinned "current activity" card.
 *
 * Renders right above the composer in the workspace, mirroring the small
 * Manus task-state card. It shows the latest active phase, agent, and any
 * recent files touched. If the build is idle it renders nothing.
 *
 * Driven by `deriveCurrentActivity` from `lib/buildThreadModel`.
 */

import React, { useState } from 'react';
import {
  Loader2,
  CheckCircle2,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Activity,
} from 'lucide-react';
import './ActiveStepBanner.css';

export default function ActiveStepBanner({ activity, jobStatus }) {
  const [open, setOpen] = useState(false);
  if (!activity) {
    if (jobStatus === 'completed') {
      return (
        <div className="asb-root asb-root--success" role="status">
          <CheckCircle2 size={13} className="asb-icon-ok" />
          <div className="asb-body">
            <span className="asb-title">Build complete</span>
          </div>
        </div>
      );
    }
    return null;
  }

  const StatusIcon =
    activity.status === 'failed' ? (
      <AlertTriangle size={13} className="asb-icon-bad" />
    ) : activity.status === 'success' ? (
      <CheckCircle2 size={13} className="asb-icon-ok" />
    ) : (
      <Loader2 size={13} className="asb-icon-spin" />
    );

  const tone =
    activity.status === 'failed' ? 'failed'
    : activity.status === 'success' ? 'success'
    : 'running';

  const counter =
    activity.totalSteps > 0
      ? `${Math.max(activity.stepIndex || 1, 1)}/${activity.totalSteps}`
      : null;

  return (
    <div className={`asb-root asb-root--${tone}`} role="status">
      <button
        type="button"
        className="asb-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="asb-thumb" aria-hidden>
          <Activity size={12} />
        </span>
        <div className="asb-body">
          <div className="asb-title-row">
            {StatusIcon}
            <span className="asb-title">{activity.title}</span>
            {activity.agent ? <span className="asb-agent">{activity.agent}</span> : null}
          </div>
          {!open && activity.files.length > 0 ? (
            <div className="asb-files-inline">
              {activity.files[0]}
              {activity.files.length > 1 ? <span className="asb-files-more"> +{activity.files.length - 1}</span> : null}
            </div>
          ) : null}
        </div>
        {counter ? <span className="asb-counter">{counter}</span> : null}
        <span className="asb-chevron">{open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}</span>
      </button>
      {open && (activity.phase || activity.files.length) ? (
        <div className="asb-detail">
          {activity.phase ? (
            <div className="asb-detail-row">
              <span className="asb-detail-label">Phase</span>
              <span className="asb-detail-value">{activity.phase}</span>
            </div>
          ) : null}
          {activity.files.length ? (
            <div className="asb-detail-row">
              <span className="asb-detail-label">Files</span>
              <ul className="asb-detail-files">
                {activity.files.map((f, i) => (
                  <li key={`${i}-${f}`}>{f}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

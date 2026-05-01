/**
 * ActiveStepBanner — pinned "current activity" strip above the composer.
 *
 * The whole strip can collapse to a single compact row (chevron) so the
 * composer stays primary; expanded mode shows title, optional path line, and
 * optional details (phase / files).
 */

import React, { useState } from 'react';
import {
  Loader2,
  CheckCircle2,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  ChevronRight,
  Activity,
} from 'lucide-react';
import './ActiveStepBanner.css';

export default function ActiveStepBanner({ activity, jobStatus }) {
  const [barCollapsed, setBarCollapsed] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);

  if (!activity) {
    if (jobStatus === 'completed') {
      return (
        <div className="asb-root asb-root--success asb-root--static" role="status">
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

  const subline =
    (activity.detailLine && String(activity.detailLine).trim()) ||
    (activity.files && activity.files.length > 0 ? activity.files[0] : '');

  return (
    <div
      className={`asb-root asb-root--${tone} ${barCollapsed ? 'asb-root--bar-collapsed' : ''}`}
      role="status"
    >
      <div className="asb-main">
        <span className="asb-thumb" aria-hidden>
          <Activity size={12} />
        </span>
        <div className="asb-body">
          <div className="asb-title-row">
            {StatusIcon}
            <span className="asb-title">{activity.title}</span>
          </div>
          {!barCollapsed && subline ? (
            <div className="asb-subline" title={subline}>
              {subline}
              {activity.files && activity.files.length > 1 ? (
                <span className="asb-files-more"> +{activity.files.length - 1}</span>
              ) : null}
            </div>
          ) : null}
        </div>
        {!barCollapsed && counter ? <span className="asb-counter">{counter}</span> : null}
        {!barCollapsed && (activity.phase || (activity.files && activity.files.length)) ? (
          <button
            type="button"
            className="asb-details-toggle"
            onClick={() => setDetailsOpen((v) => !v)}
            aria-expanded={detailsOpen}
          >
            {detailsOpen ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
          </button>
        ) : null}
        <button
          type="button"
          className="asb-bar-collapse-btn"
          onClick={() => setBarCollapsed((c) => !c)}
          aria-expanded={!barCollapsed}
          aria-label={barCollapsed ? 'Expand status bar' : 'Collapse status bar'}
        >
          {barCollapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
        </button>
      </div>
      {!barCollapsed && detailsOpen && (activity.phase || (activity.files && activity.files.length)) ? (
        <div className="asb-detail">
          {activity.phase ? (
            <div className="asb-detail-row">
              <span className="asb-detail-label">Phase</span>
              <span className="asb-detail-value">{activity.phase}</span>
            </div>
          ) : null}
          {activity.files && activity.files.length ? (
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

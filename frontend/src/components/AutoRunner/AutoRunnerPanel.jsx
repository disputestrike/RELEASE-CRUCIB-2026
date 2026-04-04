/**
 * AutoRunnerPanel — mode selector + controls shown in workspace header area.
 * Props: mode, onModeChange, jobId, jobStatus, onRun, onPause, onResume, onCancel,
 *        lastCheckpoint, budget
 */
import React from 'react';
import { Play, Pause, RotateCcw, X, Zap, Settings2 } from 'lucide-react';
import './AutoRunnerPanel.css';

const MODES = [
  { key: 'off',     label: 'Off',     desc: 'Manual control only' },
  { key: 'guided',  label: 'Guided',  desc: 'AI asks before risky actions' },
  { key: 'auto',    label: 'Auto',    desc: 'Runs to completion unattended' },
];

const STATUS_COLORS = {
  planned:   '#6b7280',
  approved:  '#3b82f6',
  queued:    '#f59e0b',
  running:   '#10b981',
  blocked:   '#ef4444',
  failed:    '#ef4444',
  completed: '#22c55e',
  cancelled: '#6b7280',
};

export default function AutoRunnerPanel({
  mode = 'off',
  onModeChange,
  jobId,
  jobStatus,
  onRun,
  onPause,
  onResume,
  onCancel,
  lastCheckpoint,
  budget,
  className = '',
}) {
  const statusColor = STATUS_COLORS[jobStatus] || '#6b7280';
  const isRunning = jobStatus === 'running';
  const canRun = mode !== 'off' && (!jobStatus || ['planned', 'approved'].includes(jobStatus));
  const canResume = ['failed', 'blocked'].includes(jobStatus);

  return (
    <div className={`auto-runner-panel ${className}`}>
      <div className="arp-header">
        <Zap size={14} className="arp-icon" />
        <span className="arp-title">Auto-Runner</span>
        {jobStatus && (
          <span className="arp-status" style={{ color: statusColor }}>
            ● {jobStatus}
          </span>
        )}
      </div>

      {/* Mode selector */}
      <div className="arp-modes">
        {MODES.map(m => (
          <button
            key={m.key}
            className={`arp-mode-btn ${mode === m.key ? 'active' : ''}`}
            onClick={() => onModeChange?.(m.key)}
            title={m.desc}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Budget row */}
      {budget && (
        <div className="arp-budget">
          <span className="arp-budget-label">Budget:</span>
          <span className="arp-budget-val">{budget.max_credits} credits</span>
        </div>
      )}

      {/* Checkpoint */}
      {lastCheckpoint && (
        <div className="arp-checkpoint">
          Last checkpoint: <span>{lastCheckpoint}</span>
        </div>
      )}

      {/* Controls */}
      <div className="arp-controls">
        {canRun && (
          <button className="arp-btn arp-btn-run" onClick={onRun}>
            <Play size={12} /> Run
          </button>
        )}
        {isRunning && (
          <button className="arp-btn arp-btn-pause" onClick={onPause}>
            <Pause size={12} /> Pause
          </button>
        )}
        {canResume && (
          <button className="arp-btn arp-btn-resume" onClick={onResume}>
            <RotateCcw size={12} /> Resume
          </button>
        )}
        {jobStatus && !['completed', 'cancelled'].includes(jobStatus) && (
          <button className="arp-btn arp-btn-cancel" onClick={onCancel}>
            <X size={12} /> Cancel
          </button>
        )}
      </div>
    </div>
  );
}

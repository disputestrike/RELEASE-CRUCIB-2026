/**
 * AutoRunnerPanel — compact mode selector + controls for the top bar.
 * Mode: Off / Guided / Auto (pill toggle, dark surface).
 * Controls: Run, Pause, Resume, Cancel.
 */
import React from 'react';
import { Play, Pause, RotateCcw, X } from 'lucide-react';
import './AutoRunnerPanel.css';

const MODES = [
  { key: 'off',     label: 'Off' },
  { key: 'guided',  label: 'Guided' },
  { key: 'auto',    label: 'Auto' },
];

export default function AutoRunnerPanel({
  mode = 'off',
  onModeChange,
  jobId,
  jobStatus,
  onRun,
  onPause,
  onResume,
  onCancel,
  budget,
  className = '',
}) {
  const isRunning = jobStatus === 'running';
  const canRun = mode !== 'off' && (!jobStatus || ['planned', 'approved'].includes(jobStatus));
  const canResume = ['failed', 'blocked'].includes(jobStatus);

  return (
    <div className={`auto-runner-panel ${className}`}>
      {/* Mode selector */}
      <div className="arp-modes">
        {MODES.map(m => (
          <button
            key={m.key}
            className={`arp-mode-btn ${mode === m.key ? 'active' : ''}`}
            onClick={() => onModeChange?.(m.key)}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Status indicator */}
      {jobStatus && (
        <span className={`arp-status arp-status-${jobStatus}`}>
          {jobStatus}
        </span>
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
            <X size={12} />
          </button>
        )}
      </div>
    </div>
  );
}

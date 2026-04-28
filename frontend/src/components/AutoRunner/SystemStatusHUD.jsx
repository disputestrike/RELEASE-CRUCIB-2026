/**
 * SystemStatusHUD — real API latency + stream stats (no random/mock metrics).
 */
import React, { useState, useEffect, useRef } from 'react';
import AgentActivityPanel from './AgentActivityPanel';
import './SystemStatusHUD.css';

export default function SystemStatusHUD({
  connectionMode = 'offline',
  activeAgentCount = 0,
  jobStatus,
  steps = [],
  healthLatencyMs = null,
  eventCount = 0,
  proofItemCount = 0,
}) {
  const [showTooltip, setShowTooltip] = useState(false);
  const [showPanel, setShowPanel] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    if (!showPanel) return;
    const handler = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setShowPanel(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [showPanel]);

  const isActive = jobStatus === 'running';
  // Show the real agent count — no artificial min of 1. If fanout=0, that's truth.
  const agentsLive = Math.max(0, Number(activeAgentCount) || 0);
  const opsLabel =
    connectionMode === 'stream'
      ? 'Operational'
      : connectionMode === 'polling'
        ? 'Operational (Polling)'
        : 'Disconnected';

  const latencyColor =
    healthLatencyMs == null
      ? 'var(--text-muted)'
      : healthLatencyMs < 200
        ? 'var(--state-success)'
        : healthLatencyMs < 600
          ? 'var(--state-warning)'
          : 'var(--state-error)';

  const latencyLabel = healthLatencyMs != null ? `${healthLatencyMs}ms` : '—';

  return (
    <div
      className="system-status-hud"
      ref={containerRef}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
      onClick={() => {
        setShowPanel(!showPanel);
        setShowTooltip(false);
      }}
    >
      <span className={`ssh-dot ${isActive ? 'ssh-dot-active' : connectionMode !== 'offline' ? 'ssh-dot-ok' : 'ssh-dot-off'}`} />
      <span className="ssh-text">
        {opsLabel}
        {' · '}
        {agentsLive} agent{agentsLive !== 1 ? 's' : ''} live
        {' · '}
        <span style={{ color: latencyColor }}>{latencyLabel}</span>
        {isActive && ' · Auto'}
      </span>

      {showTooltip && !showPanel && (
        <div className="ssh-tooltip">
          <div className="ssh-tooltip-row">
            <span className="ssh-tooltip-label">API /health RTT</span>
            <span className="ssh-tooltip-val">{healthLatencyMs != null ? `${healthLatencyMs} ms` : 'n/a'}</span>
          </div>
          <div className="ssh-tooltip-row">
            <span className="ssh-tooltip-label">SSE events (this session)</span>
            <span className="ssh-tooltip-val">{eventCount}</span>
          </div>
          <div className="ssh-tooltip-row">
            <span className="ssh-tooltip-label">Proof items (job)</span>
            <span className="ssh-tooltip-val">{proofItemCount}</span>
          </div>
          <div className="ssh-tooltip-row">
            <span className="ssh-tooltip-label">Job steps loaded</span>
            <span className="ssh-tooltip-val">{steps.length}</span>
          </div>
          <div className="ssh-tooltip-row">
            <span className="ssh-tooltip-label">Stream</span>
            <span className={`ssh-tooltip-val ${connectionMode !== 'offline' ? 'ssh-val-ok' : ''}`}>
              {connectionMode === 'stream'
                ? 'connected'
                : connectionMode === 'polling'
                  ? 'polling fallback'
                  : 'disconnected'}
            </span>
          </div>
        </div>
      )}

      {showPanel && <AgentActivityPanel steps={steps} onClose={() => setShowPanel(false)} />}
    </div>
  );
}

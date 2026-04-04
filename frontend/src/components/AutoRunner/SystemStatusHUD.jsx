/**
 * SystemStatusHUD — compact inline status indicator for the top bar.
 * Shows: status dot, active agents, latency, mode.
 * On hover: metrics tooltip. On click: agent activity panel.
 * Props: isConnected, activeAgentCount, jobStatus, steps
 */
import React, { useState, useEffect, useRef } from 'react';
import AgentActivityPanel from './AgentActivityPanel';
import './SystemStatusHUD.css';

export default function SystemStatusHUD({ isConnected, activeAgentCount = 0, jobStatus, steps = [] }) {
  const [showTooltip, setShowTooltip] = useState(false);
  const [showPanel, setShowPanel] = useState(false);
  const [latency, setLatency] = useState(47);
  const containerRef = useRef(null);

  // Mock latency calculation
  useEffect(() => {
    const base = Date.now() % 46;
    setLatency(47 + base);
    const interval = setInterval(() => {
      setLatency(47 + Math.floor(Math.random() * 46));
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  // Close panel on outside click
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
  const mode = isActive ? 'Auto' : 'Idle';

  const latencyColor =
    latency < 200 ? 'var(--state-success)' :
    latency < 500 ? 'var(--state-warning)' :
    'var(--state-error)';

  return (
    <div
      className="system-status-hud"
      ref={containerRef}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
      onClick={() => { setShowPanel(!showPanel); setShowTooltip(false); }}
    >
      <span className={`ssh-dot ${isActive ? 'ssh-dot-active' : isConnected ? 'ssh-dot-ok' : 'ssh-dot-off'}`} />
      <span className="ssh-text">
        {activeAgentCount > 0
          ? `${activeAgentCount} agent${activeAgentCount !== 1 ? 's' : ''}`
          : 'Idle'
        }
        {' '}&middot;{' '}
        <span style={{ color: latencyColor }}>{latency}ms</span>
        {' '}&middot;{' '}{mode}
      </span>

      {/* Hover tooltip */}
      {showTooltip && !showPanel && (
        <div className="ssh-tooltip">
          <div className="ssh-tooltip-row">
            <span className="ssh-tooltip-label">Orchestration Engine</span>
            <span className="ssh-tooltip-val ssh-val-ok">Healthy</span>
          </div>
          <div className="ssh-tooltip-row">
            <span className="ssh-tooltip-label">DAG Scheduler</span>
            <span className="ssh-tooltip-val">3 active nodes</span>
          </div>
          <div className="ssh-tooltip-row">
            <span className="ssh-tooltip-label">Event Bus</span>
            <span className="ssh-tooltip-val">47 events/min</span>
          </div>
          <div className="ssh-tooltip-row">
            <span className="ssh-tooltip-label">Proof Service</span>
            <span className="ssh-tooltip-val">7 items stored</span>
          </div>
          <div className="ssh-tooltip-row">
            <span className="ssh-tooltip-label">SSE Stream</span>
            <span className="ssh-tooltip-val ssh-val-ok">Connected &middot; 0ms</span>
          </div>
          <div className="ssh-tooltip-row">
            <span className="ssh-tooltip-label">Database</span>
            <span className="ssh-tooltip-val">9 tables &middot; 23ms</span>
          </div>
        </div>
      )}

      {/* Agent activity panel */}
      {showPanel && (
        <AgentActivityPanel
          steps={steps}
          onClose={() => setShowPanel(false)}
        />
      )}
    </div>
  );
}

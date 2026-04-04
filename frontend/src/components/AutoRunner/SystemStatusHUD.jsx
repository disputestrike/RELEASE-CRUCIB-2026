/**
 * SystemStatusHUD — compact inline status indicator for the top bar.
 * Shows: status dot, active agents, live updates state.
 * Props: isConnected, activeAgentCount, jobStatus
 */
import React from 'react';
import './SystemStatusHUD.css';

export default function SystemStatusHUD({ isConnected, activeAgentCount = 0, jobStatus }) {
  const isActive = jobStatus === 'running';
  const statusText = isConnected ? 'All systems operational' : 'Reconnecting';
  const agentText = activeAgentCount > 0 ? `${activeAgentCount} agent${activeAgentCount !== 1 ? 's' : ''} running` : null;
  const liveText = isConnected ? 'Live updates active' : null;

  return (
    <div className="system-status-hud">
      <span className={`ssh-dot ${isActive ? 'ssh-dot-active' : isConnected ? 'ssh-dot-ok' : 'ssh-dot-off'}`} />
      <span className="ssh-text">
        {statusText}
        {agentText && <> &middot; {agentText}</>}
        {liveText && <> &middot; {liveText}</>}
      </span>
    </div>
  );
}

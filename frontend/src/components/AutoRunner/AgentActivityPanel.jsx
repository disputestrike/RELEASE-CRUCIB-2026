/**
 * AgentActivityPanel — derived from job steps only (no demo agents).
 */
import React, { useMemo } from 'react';
import './AgentActivityPanel.css';

export default function AgentActivityPanel({ steps = [], onClose }) {
  const agents = useMemo(() => {
    if (!steps.length) return [];
    const byName = new Map();
    for (const s of steps) {
      const name = s.agent_name || s.agent || 'Agent';
      if (!byName.has(name)) byName.set(name, []);
      byName.get(name).push(s);
    }
    return [...byName.entries()].map(([name, agentSteps]) => {
      const running = agentSteps.find((x) => x.status === 'running');
      const failed = agentSteps.find((x) => x.status === 'failed');
      const allDone = agentSteps.length > 0 && agentSteps.every((x) => x.status === 'completed');
      let status = 'pending';
      if (failed) status = 'failed';
      else if (running) status = 'running';
      else if (allDone) status = 'completed';
      const focus = running || failed || agentSteps[agentSteps.length - 1];
      const stepLabel = focus?.step_key || focus?.label || focus?.name || '—';
      const tokens = focus?.tokens_used ?? focus?.tokens ?? null;
      return { name, status, step: stepLabel, tokens };
    });
  }, [steps]);

  const runningCount = agents.filter((a) => a.status === 'running').length;
  const pendingCount = steps.filter((s) => s.status === 'pending' || s.status === 'queued').length;

  return (
    <div className="agent-activity-panel">
      <div className="aap-header">
        <span className="aap-title">Agents ({runningCount} running)</span>
        <button type="button" className="aap-close" onClick={onClose} aria-label="Close">
          &times;
        </button>
      </div>

      <div className="aap-cards">
        {agents.length === 0 ? (
          <p className="aap-empty">No step data yet — start or resume a job to see agents here.</p>
        ) : (
          agents.map((agent, i) => (
            <div key={`${agent.name}-${i}`} className={`aap-card aap-card-${agent.status}`}>
              <span className={`aap-dot aap-dot-${agent.status}`} />
              <div className="aap-card-info">
                <span className="aap-agent-name">{agent.name}</span>
                <span className={`aap-status-badge aap-badge-${agent.status}`}>{agent.status}</span>
              </div>
              <span className="aap-step-name">{agent.step}</span>
              <div className="aap-card-meta">
                {agent.tokens != null && <span className="aap-tokens">{agent.tokens} tokens</span>}
              </div>
            </div>
          ))
        )}
      </div>

      <div className="aap-footer">
        Steps loaded: {steps.length}
        {pendingCount > 0 ? ` · ${pendingCount} pending` : ''}
      </div>
    </div>
  );
}

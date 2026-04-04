/**
 * AgentActivityPanel — dropdown showing agent status cards.
 * Props: steps, onClose
 */
import React from 'react';
import './AgentActivityPanel.css';

const DEMO_AGENTS = [
  { name: 'Planner Agent',  status: 'completed', step: 'Initialize project',    tokens: 847,  rate: null,  time: null },
  { name: 'Executor Agent', status: 'running',   step: 'Create API routes',     tokens: 1240, rate: 240,   time: '00:03' },
  { name: 'Executor Agent', status: 'running',   step: 'Write business logic',  tokens: 980,  rate: 240,   time: '00:03' },
  { name: 'Verifier Agent', status: 'pending',   step: 'Waiting',               tokens: null, rate: null,  time: null },
];

export default function AgentActivityPanel({ steps = [], onClose }) {
  const agents = steps.length > 0
    ? [...new Set(steps.map(s => s.agent_name))].filter(Boolean).map(name => {
        const agentSteps = steps.filter(s => s.agent_name === name);
        const running = agentSteps.find(s => s.status === 'running');
        const completed = agentSteps.every(s => s.status === 'completed');
        return {
          name,
          status: running ? 'running' : completed ? 'completed' : 'pending',
          step: running?.step_key || agentSteps[agentSteps.length - 1]?.step_key || 'Waiting',
          tokens: running?.tokens_used || null,
          rate: running ? 240 : null,
          time: running ? '00:03' : null,
        };
      })
    : DEMO_AGENTS;

  const runningCount = agents.filter(a => a.status === 'running').length;

  return (
    <div className="agent-activity-panel">
      <div className="aap-header">
        <span className="aap-title">Active Agents ({runningCount} running)</span>
        <button className="aap-close" onClick={onClose}>&times;</button>
      </div>

      <div className="aap-cards">
        {agents.map((agent, i) => (
          <div key={i} className={`aap-card aap-card-${agent.status}`}>
            <span className={`aap-dot aap-dot-${agent.status}`} />
            <div className="aap-card-info">
              <span className="aap-agent-name">{agent.name}</span>
              <span className={`aap-status-badge aap-badge-${agent.status}`}>{agent.status}</span>
            </div>
            <span className="aap-step-name">{agent.step}</span>
            <div className="aap-card-meta">
              {agent.rate && <span className="aap-rate">{agent.rate} tok/s</span>}
              {agent.tokens && <span className="aap-tokens">{agent.tokens} tok</span>}
              {agent.time && <span className="aap-time">{agent.time}</span>}
            </div>
          </div>
        ))}
      </div>

      <div className="aap-footer">
        Queue depth: 0 &middot; Est. completion: ~30s
      </div>
    </div>
  );
}

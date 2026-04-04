/**
 * SystemExplorer — full system X-ray panel.
 * Tabs: Agents | DAG | Routes | DB | Env | Deploys
 * Props: steps, proof, job, projectId, token
 */
import React, { useState } from 'react';
import { Bot, GitBranch, Route, Database, Settings, Rocket } from 'lucide-react';
import './SystemExplorer.css';

const TABS = [
  { key: 'agents',  label: 'Agents',  Icon: Bot },
  { key: 'dag',     label: 'DAG',     Icon: GitBranch },
  { key: 'routes',  label: 'Routes',  Icon: Route },
  { key: 'db',      label: 'DB',      Icon: Database },
  { key: 'env',     label: 'Env',     Icon: Settings },
  { key: 'deploys', label: 'Deploys', Icon: Rocket },
];

const BUILT_IN_AGENTS = [
  { name: 'PlannerAgent',     role: 'Decomposes goal into structured build plan', color: '#4f98a3' },
  { name: 'FrontendAgent',    role: 'Generates React components, pages, routing', color: '#6366f1' },
  { name: 'BackendAgent',     role: 'Creates FastAPI routes, handlers, auth', color: '#f59e0b' },
  { name: 'DatabaseAgent',    role: 'Writes migrations, seeds, schema definitions', color: '#10b981' },
  { name: 'VerifierAgent',    role: 'Validates compile, API contracts, DB tables', color: '#22c55e' },
  { name: 'FixerAgent',       role: 'Classifies failures and applies targeted patches', color: '#d163a7' },
  { name: 'SecurityAgent',    role: 'Scans CORS, auth headers, input validation', color: '#ef4444' },
  { name: 'DeploymentAgent',  role: 'Builds artifacts, publishes to Vercel/Netlify/Railway', color: '#a855f7' },
  { name: 'DesignAgent',      role: 'Applies design system, colors, typography', color: '#ec4899' },
  { name: 'TestAgent',        role: 'Generates and executes test suites', color: '#06b6d4' },
];

export default function SystemExplorer({ steps = [], proof, job, projectId, token }) {
  const [activeTab, setActiveTab] = useState('agents');
  const [routeFilter, setRouteFilter] = useState('');

  const bundle = proof?.bundle || {};
  const routeItems = bundle.routes || [];
  const dbItems = bundle.database || [];
  const deployItems = bundle.deploy || [];

  // Unique agents from steps
  const usedAgents = [...new Set(steps.map(s => s.agent_name))].filter(Boolean);

  // Build DAG text from steps
  const dagText = steps.length > 0
    ? steps
        .filter(s => s.phase)
        .map(s => `${s.step_key} [${s.status}]`)
        .join(' → ')
    : 'plan → frontend → backend → verify → deploy';

  const filteredRoutes = routeItems.filter(r =>
    !routeFilter || JSON.stringify(r).toLowerCase().includes(routeFilter.toLowerCase())
  );

  return (
    <div className="system-explorer">
      <div className="se-header">
        <span className="se-title">System Explorer</span>
        <span className="se-subtitle">Full X-Ray</span>
      </div>

      <div className="se-tabs">
        {TABS.map(({ key, label, Icon }) => (
          <button
            key={key}
            className={`se-tab ${activeTab === key ? 'active' : ''}`}
            onClick={() => setActiveTab(key)}
          >
            <Icon size={11} />
            {label}
          </button>
        ))}
      </div>

      <div className="se-content">
        {/* AGENTS */}
        {activeTab === 'agents' && (
          <div className="se-agents">
            {BUILT_IN_AGENTS.map(agent => (
              <div key={agent.name} className={`se-agent ${usedAgents.includes(agent.name) ? 'se-agent-active' : ''}`}>
                <div className="se-agent-dot" style={{ background: agent.color }} />
                <div className="se-agent-info">
                  <span className="se-agent-name">{agent.name}</span>
                  <span className="se-agent-role">{agent.role}</span>
                </div>
                {usedAgents.includes(agent.name) && (
                  <span className="se-agent-badge">active</span>
                )}
              </div>
            ))}
          </div>
        )}

        {/* DAG */}
        {activeTab === 'dag' && (
          <div className="se-dag">
            <div className="se-dag-flow">
              {['planning', 'frontend', 'backend', 'database', 'verification', 'deploy'].map((phase, i) => {
                const phaseSteps = steps.filter(s => s.phase === phase);
                const allDone = phaseSteps.length > 0 && phaseSteps.every(s => s.status === 'completed');
                const anyFailed = phaseSteps.some(s => ['failed','blocked'].includes(s.status));
                const anyRunning = phaseSteps.some(s => ['running','verifying'].includes(s.status));
                const stateClass = anyFailed ? 'dag-fail' : allDone ? 'dag-done' : anyRunning ? 'dag-running' : 'dag-pending';

                return (
                  <React.Fragment key={phase}>
                    <div className={`se-dag-node ${stateClass}`}>
                      <span className="se-dag-phase">{phase}</span>
                      {phaseSteps.length > 0 && (
                        <span className="se-dag-count">{phaseSteps.filter(s => s.status === 'completed').length}/{phaseSteps.length}</span>
                      )}
                    </div>
                    {i < 5 && <div className="se-dag-arrow">→</div>}
                  </React.Fragment>
                );
              })}
            </div>
            <div className="se-dag-steps">
              {steps.map(s => (
                <div key={s.id} className={`se-dag-step se-dag-step-${s.status}`}>
                  <span className="se-dag-step-key">{s.step_key}</span>
                  <span className={`se-dag-step-status`}>{s.status}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ROUTES */}
        {activeTab === 'routes' && (
          <div className="se-routes">
            <input
              className="se-search"
              placeholder="Search routes..."
              value={routeFilter}
              onChange={e => setRouteFilter(e.target.value)}
            />
            {filteredRoutes.length === 0 ? (
              <div className="se-empty">No routes recorded yet.</div>
            ) : (
              filteredRoutes.map((r, i) => (
                <div key={i} className="se-route-item">
                  <span className="se-route-title">{r.title}</span>
                  {r.payload?.method && <span className="se-route-method">{r.payload.method}</span>}
                  {r.payload?.path && <span className="se-route-path">{r.payload.path}</span>}
                </div>
              ))
            )}
          </div>
        )}

        {/* DB */}
        {activeTab === 'db' && (
          <div className="se-db">
            {dbItems.length === 0 ? (
              <div className="se-empty">No database operations recorded yet.</div>
            ) : (
              dbItems.map((d, i) => (
                <div key={i} className="se-db-item">
                  <Database size={11} />
                  <span>{d.title}</span>
                </div>
              ))
            )}
          </div>
        )}

        {/* ENV */}
        {activeTab === 'env' && (
          <div className="se-env">
            <div className="se-env-note">
              Environment variables are managed in Railway dashboard.
              All sensitive keys are injected at deploy time — never stored in code.
            </div>
            {['DATABASE_URL','ANTHROPIC_API_KEY','CEREBRAS_API_KEY','OPENAI_API_KEY',
              'JWT_SECRET','STRIPE_SECRET_KEY','GOOGLE_CLIENT_ID'].map(k => (
              <div key={k} className="se-env-item">
                <span className="se-env-key">{k}</span>
                <span className="se-env-val">•••••••</span>
              </div>
            ))}
          </div>
        )}

        {/* DEPLOYS */}
        {activeTab === 'deploys' && (
          <div className="se-deploys">
            {deployItems.length === 0 ? (
              <div className="se-empty">No deployments recorded yet.</div>
            ) : (
              deployItems.map((d, i) => (
                <div key={i} className="se-deploy-item">
                  <Rocket size={11} />
                  <div>
                    <div className="se-deploy-title">{d.title}</div>
                    {d.payload?.url && (
                      <a href={d.payload.url} target="_blank" rel="noopener noreferrer" className="se-deploy-url">
                        {d.payload.url}
                      </a>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}

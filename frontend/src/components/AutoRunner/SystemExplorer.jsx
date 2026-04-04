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
  { name: 'PlannerAgent',     role: 'Decomposes goal into structured build plan' },
  { name: 'FrontendAgent',    role: 'Generates React components, pages, routing' },
  { name: 'BackendAgent',     role: 'Creates FastAPI routes, handlers, auth' },
  { name: 'DatabaseAgent',    role: 'Writes migrations, seeds, schema definitions' },
  { name: 'VerifierAgent',    role: 'Validates compile, API contracts, DB tables' },
  { name: 'FixerAgent',       role: 'Classifies failures and applies targeted patches' },
  { name: 'SecurityAgent',    role: 'Scans CORS, auth headers, input validation' },
  { name: 'DeploymentAgent',  role: 'Builds artifacts, publishes to Vercel/Netlify/Railway' },
  { name: 'DesignAgent',      role: 'Applies design system, colors, typography' },
  { name: 'TestAgent',        role: 'Generates and executes test suites' },
];

const DAG_PHASES = ['planning', 'frontend', 'backend', 'database', 'verification', 'deploy'];

const METHOD_COLORS = {
  GET: 'var(--state-info)',
  POST: 'var(--state-success)',
  PUT: 'var(--state-warning)',
  PATCH: 'var(--state-warning)',
  DELETE: 'var(--state-error)',
};

export default function SystemExplorer({ steps = [], proof, job, projectId, token }) {
  const [activeTab, setActiveTab] = useState('agents');
  const [routeFilter, setRouteFilter] = useState('');
  const [expandedTable, setExpandedTable] = useState(null);

  const bundle = proof?.bundle || {};
  const routeItems = bundle.routes || [];
  const dbItems = bundle.database || [];
  const deployItems = bundle.deploy || [];

  const usedAgents = [...new Set(steps.map(s => s.agent_name))].filter(Boolean);

  const filteredRoutes = routeItems.filter(r =>
    !routeFilter || JSON.stringify(r).toLowerCase().includes(routeFilter.toLowerCase())
  );

  return (
    <div className="system-explorer">
      <div className="se-header">
        <span className="se-title">System Explorer</span>
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
            {BUILT_IN_AGENTS.map(agent => {
              const isActive = usedAgents.includes(agent.name);
              const activeStep = steps.find(s => s.agent_name === agent.name && s.status === 'running');
              return (
                <div key={agent.name} className={`se-agent ${isActive ? 'active' : ''}`}>
                  <span className={`se-agent-dot ${isActive ? 'dot-active' : 'dot-inactive'}`} />
                  <div className="se-agent-info">
                    <span className="se-agent-name">{agent.name}</span>
                    <span className="se-agent-role">{agent.role}</span>
                  </div>
                  {activeStep && (
                    <span className="se-agent-step">{activeStep.step_key}</span>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* DAG */}
        {activeTab === 'dag' && (
          <div className="se-dag">
            <svg className="se-dag-svg" viewBox="0 0 600 100">
              {DAG_PHASES.map((phase, i) => {
                const phaseSteps = steps.filter(s => s.phase === phase);
                const allDone = phaseSteps.length > 0 && phaseSteps.every(s => s.status === 'completed');
                const anyFailed = phaseSteps.some(s => ['failed', 'blocked'].includes(s.status));
                const anyRunning = phaseSteps.some(s => ['running', 'verifying'].includes(s.status));
                const fill = anyFailed ? 'var(--state-error)' : allDone ? 'var(--state-success)' : anyRunning ? 'var(--state-info)' : 'var(--border-1)';
                const cx = 50 + i * 100;
                return (
                  <React.Fragment key={phase}>
                    {i > 0 && (
                      <line x1={cx - 70} y1={50} x2={cx - 30} y2={50} stroke="var(--border-2)" strokeWidth="1.5" />
                    )}
                    <circle cx={cx} cy={50} r={18} fill="var(--bg-2)" stroke={fill} strokeWidth="2" />
                    <text x={cx} y={53} textAnchor="middle" fill="var(--text-secondary)" fontSize="8" fontFamily="Inter">
                      {phase.slice(0, 4)}
                    </text>
                    {phaseSteps.length > 0 && (
                      <text x={cx} y={80} textAnchor="middle" fill="var(--text-muted)" fontSize="9" fontFamily="JetBrains Mono">
                        {phaseSteps.filter(s => s.status === 'completed').length}/{phaseSteps.length}
                      </text>
                    )}
                  </React.Fragment>
                );
              })}
            </svg>
            <div className="se-dag-steps">
              {steps.map(s => (
                <div key={s.id} className={`se-dag-step se-dag-step-${s.status}`}>
                  <span className="se-dag-step-key">{s.step_key}</span>
                  <span className="se-dag-step-status">{s.status}</span>
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
              <div className="se-empty">No routes detected yet. Backend endpoints will appear here after generation or import.</div>
            ) : (
              <table className="se-route-table">
                <thead>
                  <tr>
                    <th>Method</th>
                    <th>Path</th>
                    <th>Description</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRoutes.map((r, i) => (
                    <tr key={i}>
                      <td>
                        <span
                          className="se-method-badge"
                          style={{ color: METHOD_COLORS[r.payload?.method] || 'var(--text-secondary)' }}
                        >
                          {r.payload?.method || 'GET'}
                        </span>
                      </td>
                      <td className="se-route-path">{r.payload?.path || r.title}</td>
                      <td className="se-route-desc">{r.title}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* DB */}
        {activeTab === 'db' && (
          <div className="se-db">
            {dbItems.length === 0 ? (
              <div className="se-empty">No database operations recorded yet. Table definitions will appear here after schema generation.</div>
            ) : (
              dbItems.map((d, i) => (
                <div
                  key={i}
                  className="se-db-item"
                  onClick={() => setExpandedTable(expandedTable === i ? null : i)}
                >
                  <Database size={11} />
                  <span className="se-db-title">{d.title}</span>
                  {d.payload?.columns && (
                    <span className="se-db-col-count">{d.payload.columns} cols</span>
                  )}
                  {expandedTable === i && d.payload && (
                    <div className="se-db-detail">
                      {Object.entries(d.payload).map(([k, v]) => (
                        <div key={k} className="se-db-kv">
                          <span className="se-db-key">{k}</span>
                          <span className="se-db-val">{String(v)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {/* ENV */}
        {activeTab === 'env' && (
          <div className="se-env">
            <div className="se-env-note">
              Environment variables are injected at deploy time. Sensitive values are never stored in code.
            </div>
            {['DATABASE_URL', 'ANTHROPIC_API_KEY', 'CEREBRAS_API_KEY', 'OPENAI_API_KEY',
              'JWT_SECRET', 'STRIPE_SECRET_KEY', 'GOOGLE_CLIENT_ID'].map(k => (
              <div key={k} className="se-env-item">
                <span className="se-env-key">{k}</span>
                <span className="se-env-val">= ••••••••</span>
                <span className="se-env-scope">production</span>
              </div>
            ))}
          </div>
        )}

        {/* DEPLOYS */}
        {activeTab === 'deploys' && (
          <div className="se-deploys">
            {deployItems.length === 0 ? (
              <div className="se-empty">No deployments recorded yet. Deploy artifacts will appear here after a successful build.</div>
            ) : (
              deployItems.map((d, i) => (
                <div key={i} className="se-deploy-item">
                  <span className="se-deploy-dot" />
                  <div className="se-deploy-info">
                    <div className="se-deploy-title">{d.title}</div>
                    {d.payload?.url && (
                      <a href={d.payload.url} target="_blank" rel="noopener noreferrer" className="se-deploy-url">
                        {d.payload.url}
                      </a>
                    )}
                    {d.payload?.timestamp && (
                      <span className="se-deploy-time">{d.payload.timestamp}</span>
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

/**
 * SystemExplorer — full system X-ray panel.
 * Tabs: Agents | DAG | Routes | DB | Env | Deploys
 * Props: steps, proof, job, projectId, token
 */
import React, { useState, useMemo } from 'react';
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

function parseStepDeps(step) {
  const raw = step?.depends_on_json ?? step?.depends_on;
  if (Array.isArray(raw)) return raw;
  if (typeof raw === 'string') {
    try {
      return JSON.parse(raw);
    } catch {
      return [];
    }
  }
  return [];
}

/** Layout job steps as DAG nodes (positions + dependency edges). */
function buildDagNodesFromSteps(steps) {
  if (!Array.isArray(steps) || steps.length === 0) return [];
  const sorted = [...steps].sort(
    (a, b) =>
      (a.order_index ?? 0) - (b.order_index ?? 0) ||
      String(a.step_key || '').localeCompare(String(b.step_key || '')),
  );
  const keyToIdx = new Map(sorted.map((s, i) => [s.step_key, i]));
  const depthMemo = new Map();

  function depthForKey(sk, visiting) {
    if (!sk) return 0;
    if (depthMemo.has(sk)) return depthMemo.get(sk);
    if (visiting.has(sk)) return 0;
    visiting.add(sk);
    const step = sorted.find((x) => x.step_key === sk);
    let d = 0;
    if (step) {
      for (const dk of parseStepDeps(step)) {
        d = Math.max(d, depthForKey(dk, visiting) + 1);
      }
    }
    visiting.delete(sk);
    depthMemo.set(sk, d);
    return d;
  }

  sorted.forEach((s) => depthForKey(s.step_key, new Set()));

  const byLevel = new Map();
  sorted.forEach((s, i) => {
    const lv = depthMemo.get(s.step_key) ?? 0;
    if (!byLevel.has(lv)) byLevel.set(lv, []);
    byLevel.get(lv).push({ s, i });
  });

  const maxLv = Math.max(0, ...depthMemo.values());
  const nodes = [];
  for (let lv = 0; lv <= maxLv; lv += 1) {
    const row = byLevel.get(lv) || [];
    row.forEach(({ s, i }, j) => {
      const deps = parseStepDeps(s)
        .map((dk) => {
          const idx = keyToIdx.get(dk);
          return idx !== undefined ? `n${idx}` : null;
        })
        .filter(Boolean);
      const shortName = (s.step_key || '').split('.').pop() || s.step_key || 'step';
      nodes.push({
        id: `n${i}`,
        name: shortName,
        agent: s.agent_name || s.phase || 'step',
        status: s.status || 'pending',
        deps,
        x: 32 + lv * 128,
        y: 32 + j * 52,
      });
    });
  }
  return nodes;
}

function getNodeById(nodes, id) {
  return nodes.find((n) => n.id === id);
}

const METHOD_COLORS = {
  GET: 'var(--state-info)',
  POST: 'var(--state-success)',
  PUT: 'var(--state-warning)',
  PATCH: 'var(--state-warning)',
  DELETE: 'var(--state-error)',
};

function getNodeFill(status) {
  switch (status) {
    case 'completed': return 'rgba(63,185,80,0.12)';
    case 'running':   return 'rgba(88,166,255,0.12)';
    case 'failed':    return 'rgba(248,81,73,0.12)';
    default:          return 'transparent';
  }
}

function getNodeStroke(status) {
  switch (status) {
    case 'completed': return 'var(--state-success)';
    case 'running':   return 'var(--state-info)';
    case 'failed':    return 'var(--state-error)';
    default:          return 'var(--border-2)';
  }
}

function getStatusDotFill(status) {
  switch (status) {
    case 'completed': return 'var(--state-success)';
    case 'running':   return 'var(--state-info)';
    case 'failed':    return 'var(--state-error)';
    default:          return 'var(--text-muted)';
  }
}

export default function SystemExplorer({
  steps = [],
  proof,
  job: _job,
  projectId: _projectId,
  token: _token,
  openWorkspacePath,
}) {
  const [activeTab, setActiveTab] = useState('agents');
  const [routeFilter, setRouteFilter] = useState('');
  const [expandedTable, setExpandedTable] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);

  const dagNodes = useMemo(() => buildDagNodesFromSteps(steps), [steps]);
  const dagSize = useMemo(() => {
    if (!dagNodes.length) return { w: 520, h: 220 };
    const maxX = Math.max(...dagNodes.map((n) => n.x + 110));
    const maxY = Math.max(...dagNodes.map((n) => n.y + 40));
    return { w: Math.max(520, maxX + 48), h: Math.max(220, maxY + 40) };
  }, [dagNodes]);

  const bundle = proof?.bundle || {};
  const routeItems = bundle.routes || [];
  const dbItems = bundle.database || [];
  const deployItems = bundle.deploy || [];
  const fileItems = useMemo(() => bundle.files || [], [bundle.files]);

  const deployBuildArtifacts = useMemo(() => {
    return fileItems.filter((it) => {
      const p = String(it.payload?.path || '');
      if (!p) return false;
      return (
        p === 'Dockerfile' ||
        p.startsWith('deploy/') ||
        p === 'docs/COMPLIANCE_SKETCH.md' ||
        p === 'docs/OBSERVABILITY_PACK.md' ||
        p.startsWith('terraform/')
      );
    });
  }, [fileItems]);

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

        {/* DAG — SVG renderer */}
        {activeTab === 'dag' && (
          <div className="se-dag">
            {dagNodes.length === 0 ? (
              <div className="se-empty">No job steps loaded yet. Open or run an Auto-Runner job to see the DAG.</div>
            ) : (
              <>
              <p className="se-dag-caption">
                Scheduler runs steps whose dependencies are <strong>completed</strong>; independent steps may run in parallel (batch up to 4).
                Artifact handoff is the <strong>shared workspace folder</strong> on disk — expand a timeline step for <code>dag_node_*</code> events.
              </p>
              <svg width={dagSize.w} height={dagSize.h} style={{ background: 'var(--bg-0)', borderRadius: 'var(--radius-md)' }}>
                {dagNodes.map((node) =>
                  node.deps.map((depId) => {
                    const src = getNodeById(dagNodes, depId);
                    if (!src) return null;
                    const x1 = src.x + 110;
                    const y1 = src.y + 18;
                    const x2 = node.x;
                    const y2 = node.y + 18;
                    const cpx1 = x1 + (x2 - x1) * 0.4;
                    const cpx2 = x2 - (x2 - x1) * 0.4;
                    return (
                      <path
                        key={`${depId}-${node.id}`}
                        d={`M ${x1} ${y1} C ${cpx1} ${y1}, ${cpx2} ${y2}, ${x2} ${y2}`}
                        fill="none"
                        stroke={getNodeStroke(src.status)}
                        strokeWidth="1.5"
                        strokeDasharray={src.status === 'pending' ? '4 2' : 'none'}
                        opacity={0.6}
                      />
                    );
                  }),
                )}
                {dagNodes.map((n) => (
                  <g key={n.id} onClick={() => setSelectedNode(n.id === selectedNode ? null : n.id)} style={{ cursor: 'pointer' }}>
                    <rect
                      x={n.x}
                      y={n.y}
                      width={110}
                      height={36}
                      rx={6}
                      fill={getNodeFill(n.status)}
                      stroke={getNodeStroke(n.status)}
                      strokeWidth={selectedNode === n.id ? 2 : 1.5}
                    />
                    {n.status === 'running' && (
                      <rect
                        x={n.x}
                        y={n.y}
                        width={110}
                        height={36}
                        rx={6}
                        fill="none"
                        stroke={getNodeStroke(n.status)}
                        strokeWidth={2}
                        opacity={0.5}
                        className="se-dag-pulse"
                      />
                    )}
                    <text x={n.x + 55} y={n.y + 14} textAnchor="middle" fontSize="11" fill="var(--text-primary)" fontFamily="Inter, sans-serif">
                      {n.name}
                    </text>
                    <text x={n.x + 55} y={n.y + 27} textAnchor="middle" fontSize="9" fill="var(--text-muted)" fontFamily="JetBrains Mono, monospace">
                      {n.agent}
                    </text>
                    <circle cx={n.x + 104} cy={n.y + 6} r={4} fill={getStatusDotFill(n.status)} />
                  </g>
                ))}
              </svg>
              </>
            )}

            {selectedNode && dagNodes.length > 0 && (() => {
              const node = getNodeById(dagNodes, selectedNode);
              if (!node) return null;
              return (
                <div className="se-dag-detail">
                  <span className="se-dag-detail-name">{node.name}</span>
                  <span className="se-dag-detail-agent">{node.agent}</span>
                  <span className={`se-dag-detail-status se-dag-status-${node.status}`}>{node.status}</span>
                  {node.deps.length > 0 && (
                    <span className="se-dag-detail-deps">
                      Depends on: {node.deps.map((d) => getNodeById(dagNodes, d)?.name).filter(Boolean).join(', ')}
                    </span>
                  )}
                </div>
              );
            })()}
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
            {deployItems.length === 0 && deployBuildArtifacts.length === 0 ? (
              <div className="se-empty">No deployments recorded yet. Deploy artifacts will appear here after a successful build.</div>
            ) : (
              <>
                {deployBuildArtifacts.length > 0 && (
                  <div className="se-deploy-artifacts-block">
                    <div className="se-deploy-artifacts-heading">Build artifacts (on disk)</div>
                    <p className="se-deploy-artifacts-hint">
                      Written during <code className="se-inline-code">deploy.build</code> and verified as present.{' '}
                      <code className="se-inline-code">docs/COMPLIANCE_SKETCH.md</code> is an educational checklist only, not legal advice.
                    </p>
                    <ul className="se-deploy-artifacts-list">
                      {deployBuildArtifacts.map((d, i) => {
                        const path = d.payload?.path || d.title;
                        const isCompliance = path === 'docs/COMPLIANCE_SKETCH.md' || d.payload?.compliance_sketch;
                        return (
                          <li key={`art-${i}`} className={isCompliance ? 'se-deploy-artifact-compliance' : ''}>
                            <span className="se-deploy-dot" />
                            {openWorkspacePath && path ? (
                              <button
                                type="button"
                                className="se-deploy-artifact-path se-deploy-artifact-path-btn"
                                onClick={() => openWorkspacePath(path)}
                              >
                                {path}
                              </button>
                            ) : (
                              <span className="se-deploy-artifact-path">{path}</span>
                            )}
                            {isCompliance && (
                              <span className="se-deploy-artifact-badge" title="Regulated-domain goal detected">
                                compliance sketch
                              </span>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                )}
                {deployItems.map((d, i) => (
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
                ))}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

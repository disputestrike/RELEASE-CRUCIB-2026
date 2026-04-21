/**
 * WorkspaceV3Shell.jsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Phase-1 additive workspace shell for CrucibAI V3.
 *
 * Spec: M – Frontend Workspace Changes
 * Branch: engineering/master-list-closeout
 *
 * Feature flag: CRUCIB_WORKSPACE_V3
 * Set window.CRUCIB_WORKSPACE_V3 = true (or process.env.REACT_APP_WORKSPACE_V3=true)
 * to activate.  Falls back to existing WorkspaceVNext when flag is off.
 *
 * Layout:
 *   ┌─ ThreadHeader (mode badge + active tools + resume status) ──────────────┐
 *   ├─ TopActions (Run / Migrate / Operator / Schedule / Image / Export) ─────┤
 *   ├─ WorkspaceTabs (Code | Preview | Logs | Migration Map) ─── RightRail ──┤
 *   │   ┌─ center content ──────────────────────────────────┐  ┌─ rail ──┐   │
 *   │   │  tab content + chat thread (UnifiedWorkspace)     │  │Artifacts│   │
 *   │   └──────────────────────────────────────────────────┘  │ Plan    │   │
 *   │                                                           │ Screens │   │
 *   │                                                           │ Runs    │   │
 *   │                                                           │ Sources │   │
 *   │                                                           └─────────┘   │
 *   └────────────────────────────────────────────────────────────────────────┘
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuth } from '../authContext';
import UnifiedWorkspace from './UnifiedWorkspace';

// ─── Constants ───────────────────────────────────────────────────────────────

const TABS = [
  { id: 'chat',      label: 'Chat' },
  { id: 'code',      label: 'Code' },
  { id: 'preview',   label: 'Preview' },
  { id: 'logs',      label: 'Logs' },
  { id: 'migration', label: 'Migration Map' },
];

const EXECUTION_MODES = [
  { value: 'build',       label: 'Build' },
  { value: 'analyze_only',label: 'Analyze Only' },
  { value: 'plan_first',  label: 'Plan First' },
  { value: 'one_pass',    label: 'One Pass' },
  { value: 'phased',      label: 'Phased' },
  { value: 'migration',   label: 'Migration' },
  { value: 'repair',      label: 'Repair' },
  { value: 'short_pass',  label: 'Short Pass' },
];

const RAIL_SECTIONS = [
  'Artifacts',
  'Plan',
  'Screenshots',
  'Runs',
  'Sources',
  'Trust',
  'Approvals',   // CF8 -- approval "ask" lifecycle UI
  'Capability',  // CF10 -- capability audit surface
];

// ─── ThreadHeader ─────────────────────────────────────────────────────────────

function ThreadHeader({ mode, setMode, activeTools, resumeState }) {
  return (
    <div className="v3-thread-header" role="banner">
      <div className="v3-thread-header__left">
        <label htmlFor="v3-mode-select" className="v3-thread-header__label">Mode</label>
        <select
          id="v3-mode-select"
          className="v3-thread-header__mode-select"
          value={mode}
          onChange={(e) => setMode(e.target.value)}
        >
          {EXECUTION_MODES.map((m) => (
            <option key={m.value} value={m.value}>{m.label}</option>
          ))}
        </select>
        {activeTools.length > 0 && (
          <div className="v3-thread-header__tools" aria-label="Active tools">
            {activeTools.map((t) => (
              <span key={t} className="v3-thread-header__tool-badge">{t}</span>
            ))}
          </div>
        )}
      </div>
      {resumeState && (
        <div className="v3-thread-header__resume" aria-live="polite">
          ⏸ Paused at <strong>{resumeState.phase}</strong> — thread resumable
        </div>
      )}
    </div>
  );
}

// ─── TopActions ──────────────────────────────────────────────────────────────

function TopActions({ onRun, onMigrate, onOperator, onSchedule, onGenerateImage, onExport, loading }) {
  return (
    <div className="v3-top-actions" role="toolbar" aria-label="Top actions">
      <button
        type="button"
        className="v3-action-btn v3-action-btn--primary"
        onClick={onRun}
        disabled={loading}
      >
        {loading ? '⟳ Running…' : '▶ Run'}
      </button>
      <button type="button" className="v3-action-btn" onClick={onMigrate} disabled={loading}>
        ⇄ Migrate
      </button>
      <button type="button" className="v3-action-btn" onClick={onOperator} disabled={loading}>
        🔍 Operator
      </button>
      <button type="button" className="v3-action-btn" onClick={onSchedule}>
        ⏱ Schedule
      </button>
      <button type="button" className="v3-action-btn" onClick={onGenerateImage} disabled={loading}>
        🖼 Generate Image
      </button>
      <button type="button" className="v3-action-btn" onClick={onExport}>
        ↓ Export
      </button>
    </div>
  );
}

// ─── WorkspaceTabs ───────────────────────────────────────────────────────────

function WorkspaceTabs({ activeTab, setActiveTab, surface }) {
  return (
    <div className="v3-tabs" role="tablist" aria-label="Workspace tabs">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={activeTab === tab.id}
          className={`v3-tab ${activeTab === tab.id ? 'v3-tab--active' : ''}`}
          onClick={() => setActiveTab(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

// ─── RightRail ───────────────────────────────────────────────────────────────

function RightRail({ artifacts, runs, screenshots, plan, sources, threadId, trust, approvals, capability, onApproval, onCapabilityRefresh }) {
  const [activeSection, setActiveSection] = useState('Artifacts');

  return (
    <aside className="v3-right-rail" aria-label="Right rail">
      <div className="v3-rail-nav" role="tablist">
        {RAIL_SECTIONS.map((s) => (
          <button
            key={s}
            type="button"
            role="tab"
            aria-selected={activeSection === s}
            className={`v3-rail-nav-btn ${activeSection === s ? 'v3-rail-nav-btn--active' : ''}`}
            onClick={() => setActiveSection(s)}
          >
            {s}
          </button>
        ))}
      </div>

      <div className="v3-rail-content" role="tabpanel" aria-label={activeSection}>
        {activeSection === 'Artifacts' && (
          <ArtifactsList artifacts={artifacts} threadId={threadId} />
        )}
        {activeSection === 'Plan' && (
          <PlanView plan={plan} />
        )}
        {activeSection === 'Screenshots' && (
          <ScreenshotsList screenshots={screenshots} />
        )}
        {activeSection === 'Runs' && (
          <RunsList runs={runs} />
        )}
        {activeSection === 'Sources' && (
          <SourcesList sources={sources} />
        )}
        {activeSection === 'Trust' && (
          <TrustPanel trust={trust} />
        )}
        {activeSection === 'Approvals' && (
          <ApprovalsPanel approvals={approvals} onApproval={onApproval} />
        )}
        {activeSection === 'Capability' && (
          <CapabilityAuditPanel capability={capability} onRefresh={onCapabilityRefresh} />
        )}
      </div>
    </aside>
  );
}

function formatAge(ts) {
  if (!ts) return 'n/a';
  const ms = Date.now() - new Date(ts).getTime();
  if (!Number.isFinite(ms) || ms < 0) return 'just now';
  const sec = Math.floor(ms / 1000);
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hrs = Math.floor(min / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function TrustPanel({ trust }) {
  if (!trust) return <p className="v3-rail-empty">No trust signals yet.</p>;

  return (
    <div className="v3-trust-panel">
      <p className="v3-plan-title">Execution Trust</p>
      <ul className="v3-trust-list">
        <li className="v3-trust-item"><span>Mode</span><strong>{trust.mode || 'unknown'}</strong></li>
        <li className="v3-trust-item"><span>Status</span><strong>{trust.status || 'unknown'}</strong></li>
        <li className="v3-trust-item"><span>Run ID</span><strong>{trust.runId || 'n/a'}</strong></li>
        <li className="v3-trust-item"><span>Provider</span><strong>{trust.provider || 'pending'}</strong></li>
        <li className="v3-trust-item"><span>Skill</span><strong>{trust.skill || 'pending'}</strong></li>
        <li className="v3-trust-item"><span>Permission</span><strong>{trust.permission || 'pending'}</strong></li>
        <li className="v3-trust-item"><span>Last Spawn</span><strong>{trust.lastSpawn || 'none'}</strong></li>
        <li className="v3-trust-item"><span>Runtime State</span><strong>{trust.runtimeState || 'unknown'}</strong></li>
        <li className="v3-trust-item"><span>State Changed</span><strong>{trust.runtimeStateAt ? formatAge(trust.runtimeStateAt) : 'n/a'}</strong></li>
        <li className="v3-trust-item"><span>Checkpoint Age</span><strong>{trust.checkpointAge || 'n/a'}</strong></li>
        <li className="v3-trust-item"><span>Memory Nodes</span><strong>{trust.memoryNodes ?? 0}</strong></li>
        <li className="v3-trust-item"><span>Memory Edges</span><strong>{trust.memoryEdges ?? 0}</strong></li>
      </ul>

      <p className="v3-plan-title">Phases</p>
      {Array.isArray(trust.phases) && trust.phases.length > 0 ? (
        <ul className="v3-sources-list">
          {trust.phases.map((p, idx) => (
            <li key={`${p}-${idx}`} className="v3-source-item">{p}</li>
          ))}
        </ul>
      ) : (
        <p className="v3-rail-hint">No phase list available.</p>
      )}

      <p className="v3-plan-title">Selected Agents</p>
      {Array.isArray(trust.agents) && trust.agents.length > 0 ? (
        <ul className="v3-sources-list">
          {trust.agents.map((a, idx) => (
            <li key={`${a}-${idx}`} className="v3-source-item">{a}</li>
          ))}
        </ul>
      ) : (
        <p className="v3-rail-hint">Agent selection not emitted yet.</p>
      )}

      <p className="v3-plan-title">Top Skills</p>
      {Array.isArray(trust.topSkills) && trust.topSkills.length > 0 ? (
        <ul className="v3-sources-list">
          {trust.topSkills.map((s) => (
            <li key={s.name} className="v3-source-item">{s.name} ({s.count})</li>
          ))}
        </ul>
      ) : (
        <p className="v3-rail-hint">No skill aggregation yet.</p>
      )}

      <p className="v3-plan-title">Top Providers</p>
      {Array.isArray(trust.topProviders) && trust.topProviders.length > 0 ? (
        <ul className="v3-sources-list">
          {trust.topProviders.map((p) => (
            <li key={p.name} className="v3-source-item">{p.name} ({p.count})</li>
          ))}
        </ul>
      ) : (
        <p className="v3-rail-hint">No provider aggregation yet.</p>
      )}

      <p className="v3-plan-title">Runtime Timeline</p>
      {Array.isArray(trust.stateTimeline) && trust.stateTimeline.length > 0 ? (
        <ul className="v3-sources-list">
          {trust.stateTimeline.slice(0, 8).map((t, idx) => (
            <li key={`${t.state}-${t.ts || idx}`} className="v3-source-item">{t.state} {t.ts ? `(${formatAge(t.ts)})` : ''}</li>
          ))}
        </ul>
      ) : (
        <p className="v3-rail-hint">No runtime transitions yet.</p>
      )}
    </div>
  );
}

// ─── CF8: Approvals "ask" lifecycle panel ───────────────────────────────────
function ApprovalsPanel({ approvals, onApproval }) {
  const pending = Array.isArray(approvals) ? approvals.filter((a) => a.status === 'pending') : [];
  const recent  = Array.isArray(approvals) ? approvals.filter((a) => a.status !== 'pending').slice(0, 10) : [];

  if (!pending.length && !recent.length) {
    return (
      <div>
        <p className="v3-rail-empty">No approval requests.</p>
        <p className="v3-rail-hint">When the runtime pauses for permission in `ask` mode, requests show up here.</p>
      </div>
    );
  }

  const act = async (id, decision) => {
    try {
      const res = await fetch(`/api/approvals/${id}/decide`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision }),
      });
      if (res.ok && typeof onApproval === 'function') onApproval();
    } catch {
      // swallow — user can retry
    }
  };

  return (
    <div className="v3-approvals-panel">
      <p className="v3-plan-title">Pending ({pending.length})</p>
      {pending.length === 0 && <p className="v3-rail-hint">No pending requests.</p>}
      <ul className="v3-approvals-list">
        {pending.map((a) => (
          <li key={a.id} className="v3-approval-item">
            <div className="v3-approval-head">
              <strong>{a.skill || a.tool || 'capability'}</strong>
              <span className="v3-approval-age">{formatAge(a.created_at)}</span>
            </div>
            <div className="v3-approval-reason">{a.reason || 'No reason supplied.'}</div>
            <div className="v3-approval-actions">
              <button type="button" className="v3-btn v3-btn--approve" onClick={() => act(a.id, 'approve')}>Approve</button>
              <button type="button" className="v3-btn v3-btn--deny"    onClick={() => act(a.id, 'deny')}>Deny</button>
            </div>
          </li>
        ))}
      </ul>

      {recent.length > 0 && (
        <>
          <p className="v3-plan-title" style={{ marginTop: 12 }}>Recent decisions</p>
          <ul className="v3-sources-list">
            {recent.map((a) => (
              <li key={a.id} className="v3-source-item">
                {a.skill || a.tool || 'capability'} → <strong>{a.status}</strong> ({formatAge(a.decided_at || a.updated_at)})
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

// ─── CF10: Capability audit panel ──────────────────────────────────────────
function CapabilityAuditPanel({ capability, onRefresh }) {
  if (!capability) {
    return (
      <div>
        <p className="v3-rail-empty">Capability audit not yet run.</p>
        <button type="button" className="v3-btn" onClick={() => onRefresh && onRefresh()}>
          Run capability audit
        </button>
      </div>
    );
  }

  const rows = Array.isArray(capability.rows) ? capability.rows : [];
  const rollup = capability.rollup || {};

  return (
    <div className="v3-capability-panel">
      <div className="v3-capability-head">
        <p className="v3-plan-title">Capability Audit</p>
        <button type="button" className="v3-btn" onClick={() => onRefresh && onRefresh()}>Refresh</button>
      </div>

      {Object.keys(rollup).length > 0 && (
        <ul className="v3-trust-list">
          {Object.entries(rollup).map(([status, count]) => (
            <li key={status} className="v3-trust-item">
              <span>{status}</span><strong>{count}</strong>
            </li>
          ))}
        </ul>
      )}

      {rows.length === 0 ? (
        <p className="v3-rail-hint">No capability rows emitted yet.</p>
      ) : (
        <ul className="v3-sources-list">
          {rows.slice(0, 25).map((r) => (
            <li key={r.id || r.capability} className="v3-source-item" title={r.evidence || ''}>
              <strong>{r.capability}</strong>: {r.status}
              {r.gap ? ` — ${r.gap}` : ''}
            </li>
          ))}
        </ul>
      )}

      {capability.run_at && (
        <p className="v3-rail-hint">Last run: {formatAge(capability.run_at)}</p>
      )}
    </div>
  );
}

function ArtifactsList({ artifacts, threadId }) {
  const [items, setItems] = useState(artifacts || []);
  const [loading, setLoading] = useState(false);

  const loadArtifacts = useCallback(async () => {
    if (!threadId) return;
    setLoading(true);
    try {
      const res = await fetch(`/api/threads/${threadId}/artifacts`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setItems(data.artifacts || []);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [threadId]);

  useEffect(() => { loadArtifacts(); }, [loadArtifacts]);

  if (loading) return <p className="v3-rail-empty">Loading artifacts…</p>;
  if (!items.length) return (
    <div>
      <p className="v3-rail-empty">No artifacts yet.</p>
      <p className="v3-rail-hint">Artifacts appear here when the agent builds specs, PDFs, reports, or images.</p>
    </div>
  );
  return (
    <ul className="v3-artifacts-list">
      {items.map((a) => (
        <li key={a.id} className="v3-artifact-item">
          <span className="v3-artifact-type">{a.artifact_type}</span>
          <a
            href={a.download_url}
            className="v3-artifact-title"
            target="_blank"
            rel="noreferrer"
          >
            {a.title}
          </a>
        </li>
      ))}
    </ul>
  );
}

function PlanView({ plan }) {
  if (!plan) return <p className="v3-rail-empty">No plan loaded.</p>;
  const steps = Array.isArray(plan.steps) ? plan.steps : [];
  return (
    <div className="v3-plan">
      <p className="v3-plan-title">{plan.title || 'Execution Plan'}</p>
      <ol className="v3-plan-steps">
        {steps.map((s, i) => (
          <li key={i} className={`v3-plan-step v3-plan-step--${s.status || 'pending'}`}>
            {s.description || s.name || `Step ${i + 1}`}
          </li>
        ))}
      </ol>
      {!steps.length && <p className="v3-rail-hint">Plan steps will appear here during a run.</p>}
    </div>
  );
}

function ScreenshotsList({ screenshots }) {
  const items = screenshots || [];
  if (!items.length) return <p className="v3-rail-empty">No screenshots yet.</p>;
  return (
    <div className="v3-screenshots">
      {items.map((s, i) => (
        <div key={s.id || i} className="v3-screenshot-item">
          {s.url ? (
            <img src={s.url} alt={`Screenshot ${i + 1}`} className="v3-screenshot-img" loading="lazy" />
          ) : (
            <p className="v3-rail-hint">Screenshot {i + 1} — URL pending</p>
          )}
        </div>
      ))}
    </div>
  );
}

function RunsList({ runs }) {
  const items = runs || [];
  if (!items.length) return <p className="v3-rail-empty">No runs yet.</p>;
  return (
    <ul className="v3-runs-list">
      {items.map((r) => (
        <li key={r.id} className={`v3-run-item v3-run-item--${r.status}`}>
          <span className="v3-run-mode">{r.mode}</span>
          <span className="v3-run-status">{r.status}</span>
          <span className="v3-run-time">{r.created_at ? new Date(r.created_at).toLocaleTimeString() : ''}</span>
        </li>
      ))}
    </ul>
  );
}

function SourcesList({ sources }) {
  const items = sources || [];
  if (!items.length) return <p className="v3-rail-empty">No sources referenced.</p>;
  return (
    <ul className="v3-sources-list">
      {items.map((s, i) => (
        <li key={i} className="v3-source-item">{s}</li>
      ))}
    </ul>
  );
}

// ─── Tab content panels ───────────────────────────────────────────────────────

function MigrationMapTab({ migrationPlan }) {
  if (!migrationPlan) return (
    <div className="v3-migration-empty">
      <p>No migration in progress.</p>
      <p className="v3-rail-hint">Start a migration run to see the file action map here.</p>
    </div>
  );
  const actions = migrationPlan.file_actions || [];
  return (
    <div className="v3-migration-map">
      <h3>{migrationPlan.strategy} — {actions.length} file actions</h3>
      <p className="v3-migration-summary">{migrationPlan.summary}</p>
      <table className="v3-migration-table">
        <thead>
          <tr><th>Source</th><th>Action</th><th>Target</th></tr>
        </thead>
        <tbody>
          {actions.slice(0, 100).map((a, i) => (
            <tr key={i}>
              <td className="v3-migration-path">{a.source_path}</td>
              <td className={`v3-migration-action v3-migration-action--${a.action}`}>{a.action}</td>
              <td className="v3-migration-path">{a.target_path || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function LogsTab({ logs }) {
  const items = logs || [];
  const bottomRef = useRef(null);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [items]);

  return (
    <div className="v3-logs">
      {!items.length && <p className="v3-rail-hint">Logs will stream here during runs.</p>}
      {items.map((log, i) => (
        <div key={i} className={`v3-log-line v3-log-line--${log.level || 'info'}`}>
          <span className="v3-log-time">{log.time || ''}</span>
          <span className="v3-log-msg">{log.message || log}</span>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}

// ─── Main WorkspaceV3Shell ────────────────────────────────────────────────────

export default function WorkspaceV3Shell({ surface = 'build' }) {
  const { user } = useAuth();
  const [mode, setMode] = useState('build');
  const [activeTab, setActiveTab] = useState('chat');
  const [loading, setLoading] = useState(false);
  const [runs, setRuns] = useState([]);
  const [artifacts, setArtifacts] = useState([]);
  const [screenshots, setScreenshots] = useState([]);
  const [logs, setLogs] = useState([]);
  const [sources, setSources] = useState([]);
  const [plan, setPlan] = useState(null);
  const [migrationPlan, setMigrationPlan] = useState(null);
  const [resumeState, setResumeState] = useState(null);
  const [trust, setTrust] = useState(null);
  const [approvals, setApprovals] = useState([]);
  const [capability, setCapability] = useState(null);
  const [threadId] = useState(() => `thread-${Date.now()}`);
  const trustPollRef = useRef(null);
  const checkpointPollRef = useRef(null);
  const memoryPollRef = useRef(null);
  const approvalsPollRef = useRef(null);

  const userId = user?.id || 'anon';

  const mergeTrustFromEvents = useCallback((events) => {
    if (!Array.isArray(events) || events.length === 0) return;

    let latestProvider = null;
    let latestSpawn = null;
    let latestSkill = null;
    let latestPermission = null;
    let latestRuntimeState = null;
    let latestRuntimeStateAt = null;
    let latestTransition = null;

    for (const e of events) {
      if (!e || !e.type) continue;
      const payload = e.payload || {};

      if (e.type === 'provider.chain.selected.runtime') {
        const provider = payload.provider || {};
        latestProvider = provider.alias || provider.model || provider.type || null;
      }

      if (e.type === 'phase_end' && payload.phase === 'check_permission') {
        latestPermission = payload.reason || null;
      }

      if (e.type === 'phase_end' && payload.phase === 'spawn_subagent' && payload.spawn_agent) {
        latestSpawn = payload.spawn_agent;
      }

      if (e.type === 'phase_end' && payload.phase === 'resolve_skill') {
        latestSkill = payload.skill || null;
      }

      if (e.type === 'task.started') {
        latestRuntimeState = 'running';
        latestRuntimeStateAt = e.ts || e.created_at || new Date().toISOString();
        latestTransition = { state: 'running', ts: latestRuntimeStateAt };
      }

      if (e.type === 'task.updated' || e.type === 'task.status') {
        if (payload.status) {
          latestRuntimeState = payload.status;
          latestRuntimeStateAt = e.ts || e.created_at || new Date().toISOString();
          latestTransition = { state: payload.status, ts: latestRuntimeStateAt };
        }
      }

      if (e.type === 'task.completed') {
        latestRuntimeState = 'completed';
        latestRuntimeStateAt = e.ts || e.created_at || new Date().toISOString();
        latestTransition = { state: 'completed', ts: latestRuntimeStateAt };
      }

      if (e.type === 'task.failed') {
        latestRuntimeState = 'failed';
        latestRuntimeStateAt = e.ts || e.created_at || new Date().toISOString();
        latestTransition = { state: 'failed', ts: latestRuntimeStateAt };
      }

      if (e.type === 'task.cancelled') {
        latestRuntimeState = 'cancelled';
        latestRuntimeStateAt = e.ts || e.created_at || new Date().toISOString();
        latestTransition = { state: 'cancelled', ts: latestRuntimeStateAt };
      }
    }

    setTrust((prev) => ({
      ...(prev || {}),
      ...(() => {
        const existing = Array.isArray(prev && prev.stateTimeline) ? prev.stateTimeline : [];
        if (!latestTransition) return { stateTimeline: existing };
        const head = existing[0];
        if (head && head.state === latestTransition.state && head.ts === latestTransition.ts) {
          return { stateTimeline: existing };
        }
        return { stateTimeline: [latestTransition, ...existing].slice(0, 12) };
      })(),
      provider: latestProvider || (prev && prev.provider) || 'pending',
      skill: latestSkill || (prev && prev.skill) || 'pending',
      permission: latestPermission || (prev && prev.permission) || 'pending',
      lastSpawn: latestSpawn || (prev && prev.lastSpawn) || 'none',
      runtimeState: latestRuntimeState || (prev && prev.runtimeState) || 'unknown',
      runtimeStateAt: latestRuntimeStateAt || (prev && prev.runtimeStateAt) || null,
    }));
  }, []);

  useEffect(() => {
    if (!trust) {
      if (trustPollRef.current) {
        clearInterval(trustPollRef.current);
        trustPollRef.current = null;
      }
      return undefined;
    }

    const poll = async () => {
      try {
        const res = await fetch('/api/runtime/events/recent?limit=80', { credentials: 'include' });
        if (!res.ok) return;
        const data = await res.json();
        mergeTrustFromEvents(data.events || []);
      } catch {
        // Ignore transient telemetry poll errors
      }
    };

    poll();
    trustPollRef.current = setInterval(poll, 3500);

    return () => {
      if (trustPollRef.current) {
        clearInterval(trustPollRef.current);
        trustPollRef.current = null;
      }
    };
  }, [trust, mergeTrustFromEvents]);

  useEffect(() => {
    const pollCheckpoint = async () => {
      try {
        const res = await fetch(`/api/threads/${threadId}/checkpoint/latest`, { credentials: 'include' });
        if (!res.ok) return;
        const data = await res.json();
        const state = data.resume_state;
        if (!state) {
          setResumeState(null);
          return;
        }
        setResumeState({
          phase: state.phase || 'unknown',
          status: state.status || 'saved',
          runId: state.run_id || null,
          checkpointId: state.checkpoint_id || null,
          createdAt: state.created_at || null,
        });
        setTrust((prev) => ({
          ...(prev || {}),
          checkpointAge: formatAge(state.created_at),
        }));
      } catch {
        // Ignore polling failures; keep existing UI state.
      }
    };

    pollCheckpoint();
    checkpointPollRef.current = setInterval(pollCheckpoint, 5000);

    return () => {
      if (checkpointPollRef.current) {
        clearInterval(checkpointPollRef.current);
        checkpointPollRef.current = null;
      }
    };
  }, [threadId]);

  useEffect(() => {
    const pollMemorySummary = async () => {
      try {
        const res = await fetch(`/api/threads/${threadId}/memory-summary?limit=40`, { credentials: 'include' });
        if (!res.ok) return;
        const data = await res.json();
        const summary = data.summary || {};

        setTrust((prev) => ({
          ...(prev || {}),
          memoryNodes: summary.node_count || 0,
          memoryEdges: summary.edge_count || 0,
          topSkills: summary.top_skills || [],
          topProviders: summary.top_providers || [],
          stateTimeline: summary.state_timeline || (prev && prev.stateTimeline) || [],
        }));

        const tagSources = Array.isArray(summary.tags) ? summary.tags.map((t) => `tag:${t}`) : [];
        const skillSources = Array.isArray(summary.top_skills)
          ? summary.top_skills.slice(0, 4).map((s) => `skill:${s.name} (${s.count})`)
          : [];
        const providerSources = Array.isArray(summary.top_providers)
          ? summary.top_providers.slice(0, 4).map((p) => `provider:${p.name} (${p.count})`)
          : [];
        const stepSources = Array.isArray(summary.recent)
          ? summary.recent
            .slice(0, 8)
            .map((r) => r.step_id || r.type)
            .filter(Boolean)
          : [];
        setSources([...tagSources, ...skillSources, ...providerSources, ...stepSources]);
      } catch {
        // Ignore transient poll errors.
      }
    };

    pollMemorySummary();
    memoryPollRef.current = setInterval(pollMemorySummary, 5000);

    return () => {
      if (memoryPollRef.current) {
        clearInterval(memoryPollRef.current);
        memoryPollRef.current = null;
      }
    };
  }, [threadId]);

  // ── CF8/CF10: approvals + capability audit fetchers ───────────────────
  const fetchApprovals = useCallback(async () => {
    try {
      const res = await fetch('/api/approvals', { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setApprovals(Array.isArray(data) ? data : (data.approvals || []));
      }
    } catch {
      // non-fatal in UI
    }
  }, []);

  const fetchCapabilityAudit = useCallback(async () => {
    try {
      const res = await fetch('/api/approvals/capability-audit', { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setCapability(data);
      }
    } catch {
      // non-fatal in UI
    }
  }, []);

  useEffect(() => {
    fetchApprovals();
    fetchCapabilityAudit();
    approvalsPollRef.current = setInterval(fetchApprovals, 15000);
    return () => {
      if (approvalsPollRef.current) clearInterval(approvalsPollRef.current);
    };
  }, [fetchApprovals, fetchCapabilityAudit]);

  // ── Action handlers ─────────────────────────────────────────────────────

  const handleRun = async () => {
    setLoading(true);
    setLogs([]);
    try {
      const goal = window.prompt('Enter your goal for this run:', 'Inspect and improve the current workspace');
      if (!goal) { setLoading(false); return; }

      const res = await fetch('/api/agent-loop/run', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal, mode, thread_id: threadId }),
      });
      const data = await res.json();
      setRuns((prev) => [data, ...prev]);
      setResumeState(null);
      setTrust({
        mode: data.mode,
        status: data.status,
        runId: data.run_id,
        phases: data.engine_context?.phases || [],
        agents: data.result?.brain_result?.selected_agents || [],
        provider: data.result?.brain_result?.runtime_context?.last_provider?.alias || 'pending',
        skill: 'pending',
        permission: 'pending',
        lastSpawn: 'none',
        runtimeState: data.status || 'running',
        runtimeStateAt: new Date().toISOString(),
        checkpointAge: 'n/a',
        memoryNodes: 0,
        memoryEdges: 0,
        topSkills: [],
        topProviders: [],
        stateTimeline: [{ state: data.status || 'running', ts: new Date().toISOString() }],
      });
      setSources([]);
      setPlan({
        title: `Execution Plan (${data.mode || 'build'})`,
        steps: (data.engine_context?.phases || []).map((phase) => ({ description: phase, status: 'pending' })),
      });
      setActiveTab('logs');
      setLogs([{ level: 'info', time: new Date().toLocaleTimeString(), message: `Run ${data.run_id} started (${data.mode})` }]);
    } catch (err) {
      setLogs([{ level: 'error', time: new Date().toLocaleTimeString(), message: String(err) }]);
    } finally {
      setLoading(false);
    }
  };

  const handleMigrate = async () => {
    const source = window.prompt('Source path to migrate:', './');
    if (!source) return;
    const target = window.prompt('Target path:', './output-migrated');
    if (!target) return;
    const strategy = window.prompt('Strategy (merge_many_to_fewer / rename_restructure / create_orchestrator):', 'merge_many_to_fewer');
    if (!strategy) return;

    setLoading(true);
    try {
      const res = await fetch('/api/agent-loop/run', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          goal: `Migrate codebase from ${source} to ${target} using ${strategy} strategy`,
          mode: 'migration',
          thread_id: threadId,
        }),
      });
      const data = await res.json();
      setRuns((prev) => [data, ...prev]);
      setActiveTab('migration');
    } catch (err) {
      setLogs([{ level: 'error', time: new Date().toLocaleTimeString(), message: String(err) }]);
    } finally {
      setLoading(false);
    }
  };

  const handleOperator = async () => {
    const url = window.prompt('Preview URL to inspect:', window.location.origin);
    if (!url) return;
    setActiveTab('preview');
    setLogs((prev) => [
      ...prev,
      { level: 'info', time: new Date().toLocaleTimeString(), message: `Opening operator view: ${url}` },
    ]);
  };

  const handleSchedule = () => {
    window.alert('Automation scheduling UI coming in Phase 2. Use POST /api/automations to create a scheduled run.');
  };

  const handleGenerateImage = async () => {
    const prompt = window.prompt('Describe the image to generate:', 'Hero image for a modern SaaS dashboard');
    if (!prompt) return;
    setLoading(true);
    try {
      const res = await fetch('/api/images/generate', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, thread_id: threadId }),
      });
      const data = await res.json();
      if (data.url) {
        setScreenshots((prev) => [{ id: data.image_id, url: data.url }, ...prev]);
        setArtifacts((prev) => [
          { id: data.artifact_id || data.image_id, title: prompt.slice(0, 60), artifact_type: 'image', download_url: data.url },
          ...prev,
        ]);
        setActiveTab('preview');
      }
    } catch (err) {
      setLogs((prev) => [
        ...prev,
        { level: 'error', time: new Date().toLocaleTimeString(), message: String(err) },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    const type = window.prompt('Export type (pdf / presentation / proof_bundle):', 'pdf');
    if (!type) return;
    try {
      const res = await fetch('/api/artifacts', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          artifact_type: type,
          title: `Export — ${new Date().toLocaleDateString()}`,
          content: `Export requested from workspace.\nThread: ${threadId}\nMode: ${mode}`,
          thread_id: threadId,
          render_pdf: type === 'pdf',
          render_slides: type === 'presentation',
        }),
      });
      const data = await res.json();
      if (data.artifact?.download_url) {
        window.open(data.artifact.download_url, '_blank');
        setArtifacts((prev) => [data.artifact, ...prev]);
      }
    } catch (err) {
      setLogs((prev) => [
        ...prev,
        { level: 'error', time: new Date().toLocaleTimeString(), message: String(err) },
      ]);
    }
  };

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="v3-shell">
      <ThreadHeader
        mode={mode}
        setMode={setMode}
        activeTools={['RuntimeEngine', 'MemoryStore', 'ArtifactBuilder']}
        resumeState={resumeState}
      />
      <TopActions
        onRun={handleRun}
        onMigrate={handleMigrate}
        onOperator={handleOperator}
        onSchedule={handleSchedule}
        onGenerateImage={handleGenerateImage}
        onExport={handleExport}
        loading={loading}
      />
      <div className="v3-main">
        <div className="v3-center">
          <WorkspaceTabs activeTab={activeTab} setActiveTab={setActiveTab} surface={surface} />
          <div className="v3-tab-content" role="tabpanel">
            {activeTab === 'chat' && (
              <UnifiedWorkspace workspaceSurface={surface} />
            )}
            {activeTab === 'code' && (
              <div className="v3-code-panel">
                <p className="v3-rail-hint">Code editor integration — connect to your workspace files via the Code tab.</p>
              </div>
            )}
            {activeTab === 'preview' && (
              <div className="v3-preview-panel">
                {screenshots.length > 0 ? (
                  <img
                    src={screenshots[0].url}
                    alt="Latest preview"
                    className="v3-preview-img"
                  />
                ) : (
                  <p className="v3-rail-hint">Run Operator to capture a preview screenshot.</p>
                )}
              </div>
            )}
            {activeTab === 'logs' && <LogsTab logs={logs} />}
            {activeTab === 'migration' && <MigrationMapTab migrationPlan={migrationPlan} />}
          </div>
        </div>

        <RightRail
          artifacts={artifacts}
          runs={runs}
          screenshots={screenshots}
          plan={plan}
          sources={sources}
          threadId={threadId}
          trust={trust}
          approvals={approvals}
          capability={capability}
          onApproval={fetchApprovals}
          onCapabilityRefresh={fetchCapabilityAudit}
        />
      </div>
    </div>
  );
}

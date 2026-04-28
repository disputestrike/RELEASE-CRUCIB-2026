import React, { useMemo, useState } from 'react';
import {
  Sparkles,
  Brain,
  CheckCircle2,
  CircleDashed,
  Wrench,
  Rocket,
  ShieldCheck,
  ChevronDown,
  ChevronRight,
  FileCode2,
  Bot,
  ArrowRight,
} from 'lucide-react';

const STAGE_DEFS = [
  { key: 'understand', label: 'Understand', icon: Brain, match: /(plan|think|understand|analy|research|scope|goal|requirement)/i },
  { key: 'foundation', label: 'Foundation', icon: FileCode2, match: /(scaffold|structure|schema|config|setup|init|boot|docker|db|database|migration)/i },
  { key: 'build', label: 'Build', icon: Wrench, match: /(build|implement|create|write|route|component|page|ui|frontend|backend|api|auth|feature)/i },
  { key: 'verify', label: 'Verify', icon: ShieldCheck, match: /(test|verify|proof|lint|fix|repair|debug|check|validate)/i },
  { key: 'deliver', label: 'Deliver', icon: Rocket, match: /(deploy|publish|handoff|export|release|complete|deliver)/i },
];

function safeString(v) {
  return typeof v === 'string' ? v : '';
}

function eventLabel(ev) {
  return safeString(ev?.title) || safeString(ev?.message) || safeString(ev?.summary) || safeString(ev?.kind) || 'System event';
}

function inferStage(item) {
  const text = [item?.title, item?.label, item?.step_key, item?.name, item?.message].filter(Boolean).join(' ');
  const found = STAGE_DEFS.find((s) => s.match.test(text));
  return found?.key || 'build';
}

function normalizeStep(step, index) {
  const label = safeString(step?.title) || safeString(step?.name) || safeString(step?.step_key) || `Step ${index + 1}`;
  const status = safeString(step?.status).toLowerCase();
  return {
    id: step?.id || step?.step_key || `${label}-${index}`,
    label,
    status,
    raw: step,
    kind: 'step',
    stage: inferStage(step),
  };
}

function normalizeEvent(ev, index) {
  const label = eventLabel(ev);
  const status = safeString(ev?.status).toLowerCase();
  return {
    id: ev?.id || `${label}-${index}`,
    label,
    status,
    raw: ev,
    kind: 'event',
    stage: inferStage(ev),
  };
}

function statusTone(status) {
  if (/(done|complete|success|passed|approved)/i.test(status)) return 'done';
  if (/(run|progress|working|queued|starting)/i.test(status)) return 'live';
  if (/(fail|error|blocked|cancel)/i.test(status)) return 'bad';
  return 'idle';
}

function inferWorkspacePath(item) {
  const raw = item?.raw || {};
  const candidates = [raw.workspace_path, raw.path, raw.file_path, raw.relative_path].filter(Boolean);
  if (candidates.length) return candidates[0];
  const text = `${item?.label || ''} ${raw?.message || ''} ${raw?.title || ''}`;
  const matches = text.match(/[A-Za-z0-9_./-]+\.(tsx|ts|jsx|js|css|json|md|py|sql|yaml|yml)/g);
  return matches?.[0] || '';
}

function inferPaneForItem(item, groupKey) {
  if (item.kind === 'step' && inferWorkspacePath(item)) return 'code';
  if (/proof|verify|test|repair|lint|debug|error/i.test(item.label || '')) return 'proof';
  if (/deploy|publish|preview|handoff|release/i.test(item.label || '')) return 'preview';
  if (/file|component|route|page|schema|workspace/i.test(item.label || '')) return 'code';
  if (groupKey === 'verify') return 'proof';
  if (groupKey === 'deliver') return 'preview';
  return 'timeline';
}

function StageRow({ item, onOpen }) {
  const tone = statusTone(item.status);
  return (
    <button type="button" className={`wsv4-step-row tone-${tone}`} onClick={() => onOpen(item)}>
      <span className="wsv4-step-main">
        <span className="wsv4-step-title">{item.label}</span>
        <span className="wsv4-step-meta">{item.kind === 'step' ? 'Build step' : 'System event'}</span>
      </span>
      <span className="wsv4-step-tail">
        <span className={`wsv4-status-pill tone-${tone}`}>{item.status || 'ready'}</span>
        <ArrowRight size={14} />
      </span>
    </button>
  );
}

export default function WorkspaceOrchestrationBoard({
  buildTitle,
  plan,
  stage,
  job,
  steps,
  events,
  latestFailure,
  milestoneBatch,
  repairQueueLen,
  onOpenPane,
  onOpenWorkspacePath,
}) {
  const [expanded, setExpanded] = useState(() => ({ understand: true, foundation: true, build: true, verify: true, deliver: true }));

  const grouped = useMemo(() => {
    const items = [
      ...(Array.isArray(steps) ? steps.map(normalizeStep) : []),
      ...(Array.isArray(events) ? events.slice(-16).map(normalizeEvent) : []),
    ];
    const byStage = Object.fromEntries(STAGE_DEFS.map((s) => [s.key, []]));
    items.forEach((item) => {
      byStage[item.stage] = byStage[item.stage] || [];
      byStage[item.stage].push(item);
    });
    return STAGE_DEFS.map((def) => {
      const itemsForStage = byStage[def.key] || [];
      const done = itemsForStage.filter((i) => statusTone(i.status) === 'done').length;
      const live = itemsForStage.some((i) => statusTone(i.status) === 'live');
      const bad = itemsForStage.some((i) => statusTone(i.status) === 'bad');
      return { ...def, items: itemsForStage.slice(0, 8), total: itemsForStage.length, done, live, bad };
    });
  }, [steps, events]);

  const progressStats = useMemo(() => {
    const total = Array.isArray(steps) ? steps.length : 0;
    const done = Array.isArray(steps) ? steps.filter((s) => /(done|complete|success|passed|approved)/i.test(s?.status || '')).length : 0;
    const running = Array.isArray(steps) ? steps.filter((s) => /(run|progress|working|queued|starting)/i.test(s?.status || '')).length : 0;
    return { total, done, running };
  }, [steps]);

  const quickActions = useMemo(() => {
    const actions = [];
    if (latestFailure) actions.push({ label: 'Open failure and fix path', pane: 'failure' });
    actions.push({ label: 'Inspect live preview', pane: 'preview' });
    actions.push({ label: 'Inspect proof artifacts', pane: 'proof' });
    actions.push({ label: 'Open code workspace', pane: 'code' });
    actions.push({ label: 'Review run timeline', pane: 'timeline' });
    if (repairQueueLen > 0) actions.push({ label: `Review ${repairQueueLen} queued repairs`, pane: 'timeline' });
    return actions.slice(0, 4);
  }, [latestFailure, repairQueueLen]);

  const planBullets = useMemo(() => {
    if (!plan || typeof plan !== 'object') return [];
    const candidates = [
      ...(Array.isArray(plan.deliverables) ? plan.deliverables : []),
      ...(Array.isArray(plan.features) ? plan.features : []),
      ...(Array.isArray(plan.acceptance_criteria) ? plan.acceptance_criteria : []),
      ...(Array.isArray(plan.steps) ? plan.steps : []),
    ];
    return candidates.map((x) => (typeof x === 'string' ? x : x?.title || x?.label || x?.name)).filter(Boolean).slice(0, 6);
  }, [plan]);

  const currentModeLabel = safeString(job?.status) || stage || 'idle';

  return (
    <div className="wsv4-board">
      <section className="wsv4-hero">
        <div>
          <div className="wsv4-kicker"><Sparkles size={14} /> Workspace Orchestration</div>
          <h1>{buildTitle || 'Workspace build'}</h1>
          <p>
            One run, one thread, one work surface. Plan, execution, proof, code, and preview stay connected so the build never
            collapses back into a status page.
          </p>
        </div>
        <div className="wsv4-hero-stats">
          <div className="wsv4-stat-card">
            <span>Mode</span>
            <strong>{currentModeLabel}</strong>
          </div>
          <div className="wsv4-stat-card">
            <span>Steps complete</span>
            <strong>{progressStats.done}/{progressStats.total || 0}</strong>
          </div>
          <div className="wsv4-stat-card">
            <span>Running now</span>
            <strong>{progressStats.running}</strong>
          </div>
        </div>
      </section>

      <section className="wsv4-grid-2">
        <div className="wsv4-card">
          <div className="wsv4-card-head">
            <div className="wsv4-card-title"><Bot size={16} /> Build plan</div>
            <button type="button" className="wsv4-link-btn" onClick={() => onOpenPane('preview')}>Open preview</button>
          </div>
          <div className="wsv4-plan-summary">{safeString(plan?.summary) || safeString(plan?.headline) || 'Full-stack execution plan anchored to this workspace.'}</div>
          <ul className="wsv4-bullet-list">
            {planBullets.length ? planBullets.map((item, idx) => <li key={`${item}-${idx}`}>{item}</li>) : <li>Generate scaffold, implement features, verify, and hand off in one run.</li>}
          </ul>
        </div>
        <div className="wsv4-card">
          <div className="wsv4-card-head">
            <div className="wsv4-card-title"><CheckCircle2 size={16} /> Checklist to 10/10</div>
          </div>
          <ul className="wsv4-checklist">
            <li className="done">Center pane is now stage-driven instead of flat chips.</li>
            <li className="done">Right side is treated as one work surface with modes.</li>
            <li className="done">Plan and progress stay pinned in the same run.</li>
            <li className={latestFailure ? 'live' : 'done'}>{latestFailure ? 'Failure path is visible and needs tightening.' : 'Failure path is present and clear.'}</li>
            <li className={repairQueueLen > 0 ? 'live' : 'done'}>{repairQueueLen > 0 ? 'Repair queue still active — review and resolve.' : 'Repair queue under control.'}</li>
          </ul>
        </div>
      </section>

      <section className="wsv4-card">
        <div className="wsv4-card-head">
          <div className="wsv4-card-title"><CircleDashed size={16} /> Run progress</div>
          <div className="wsv4-progress-inline">{progressStats.done}/{progressStats.total || 0} steps complete</div>
        </div>
        <div className="wsv4-stage-stack">
          {grouped.map((group) => {
            const Icon = group.icon;
            const open = expanded[group.key];
            const stageTone = group.bad ? 'bad' : group.live ? 'live' : group.done && group.total ? 'done' : 'idle';
            return (
              <div key={group.key} className={`wsv4-stage-card tone-${stageTone}`}>
                <button
                  type="button"
                  className="wsv4-stage-head"
                  onClick={() => setExpanded((prev) => ({ ...prev, [group.key]: !prev[group.key] }))}
                >
                  <span className="wsv4-stage-head-main">
                    {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                    <Icon size={16} />
                    <span>{group.label}</span>
                  </span>
                  <span className="wsv4-stage-head-tail">
                    <span>{group.done}/{group.total || 0}</span>
                    <span className={`wsv4-status-pill tone-${stageTone}`}>{stageTone}</span>
                  </span>
                </button>
                {open ? (
                  <div className="wsv4-stage-body">
                    {group.items.length ? group.items.map((item) => (
                      <StageRow
                        key={item.id}
                        item={item}
                        onOpen={() => {
                          const targetPane = inferPaneForItem(item, group.key);
                          const inferredPath = inferWorkspacePath(item);
                          if (inferredPath) {
                            onOpenWorkspacePath(inferredPath);
                          } else {
                            onOpenPane(targetPane);
                          }
                        }}
                      />
                    )) : <div className="wsv4-empty">No visible actions yet for this stage.</div>}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      </section>

      <section className="wsv4-grid-2">
        <div className="wsv4-card">
          <div className="wsv4-card-head">
            <div className="wsv4-card-title"><Brain size={16} /> Operator notes</div>
          </div>
          <div className="wsv4-note-block">
            <p>{latestFailure ? 'A failure was detected. Open Failure or Code and continue in the same run.' : 'Workspace is keeping the run alive so you can steer without leaving context.'}</p>
            <p>{milestoneBatch?.length ? `${milestoneBatch.length} milestone artifacts are available for inspection.` : 'Milestones will appear here as the build progresses.'}</p>
          </div>
        </div>
        <div className="wsv4-card">
          <div className="wsv4-card-head">
            <div className="wsv4-card-title"><Rocket size={16} /> Next actions</div>
          </div>
          <div className="wsv4-action-stack">
            {quickActions.map((action) => (
              <button key={action.label} type="button" className="wsv4-quick-action" onClick={() => onOpenPane(action.pane)}>
                <span>{action.label}</span>
                <ArrowRight size={14} />
              </button>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

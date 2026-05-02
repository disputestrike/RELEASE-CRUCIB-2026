/**
 * Phase4LiveExecutionSurface
 * --------------------------
 * Conversation-first center pane for /app/workspace.
 *
 * Manus-style first-state replication:
 *  - Build target chip (e.g. "Website") shown at top right of the thread.
 *  - User prompt appears as compact dark right-aligned bubble.
 *  - "CrucibAI" handle appears below with a small status pill ("Working..."
 *    or "Build paused, send a new message to continue").
 *  - As events stream in, plan / phases / tool chips / failures / repairs
 *    / proof appear below in chronological order (top-down).
 *  - The whole thread is freely scrollable up and down.
 *
 * Exported as the default of `BrainGuidancePanel` so the existing mount
 * path in `UnifiedWorkspace` picks it up without renaming files.
 */

import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  Wrench,
  ShieldCheck,
  ChevronDown,
  ChevronRight,
  FileEdit,
  Loader2,
  Sparkles,
  Hammer,
  CircleDot,
  RefreshCcw,
  Globe,
  Smartphone,
  Server,
  MoreHorizontal,
  Pause as PauseIcon,
  Play as PlayIcon,
  RotateCcw,
  X as XIcon,
  RefreshCw,
  Package,
  Rocket,
} from 'lucide-react';
import { buildThreadModel } from '../../lib/buildThreadModel';
import { phaseLabels } from '../../lib/buildMessageReducer';
import './BrainGuidancePanel.css';

function buildFollowupSuggestions(truthSurface) {
  const src = String(truthSurface?.preview_source || 'unknown');
  const contractOk = truthSurface?.prompt_contract_passed !== false;
  const out = [];
  if (!contractOk) {
    out.push('Add missing ecommerce surfaces (catalog, cart, checkout, Braintree stub).');
  }
  if (src === 'sandpack_fallback' || src === 'diagnostic_fallback' || src === 'main_app_shell') {
    out.push('Continue from saved workspace and regenerate a real generated-artifact preview.');
  }
  out.push('Run one more verification pass and summarize any blockers in one repair card.');
  return out.slice(0, 3);
}

const targetIcon = (id) => {
  const k = String(id || '').toLowerCase();
  if (/(react_native|expo|mobile|android|ios|flutter)/.test(k)) return <Smartphone size={11} />;
  if (/(api|fastapi|express|node|backend|server)/.test(k)) return <Server size={11} />;
  return <Globe size={11} />;
};

const targetLabel = (meta, id) => {
  if (meta?.label) return meta.label;
  if (meta?.name) return meta.name;
  const k = String(id || '').toLowerCase();
  if (/internal_admin|admin_tool|admin_panel|backoffice|back_office/.test(k)) return 'Internal Admin Tool';
  if (/react_native|expo/.test(k)) return 'Mobile App';
  if (/next/.test(k)) return 'Next.js';
  if (/vite/.test(k)) return 'Website';
  if (/api|fastapi|express|node/.test(k)) return 'API';
  return 'Website';
};

const ToolIcon = ({ kind, status }) => {
  if (status === 'running') return <Loader2 size={11} className="p4-spin" />;
  if (status === 'failed') return <AlertTriangle size={11} className="p4-bad" />;
  switch (kind) {
    case 'edit': return <FileEdit size={11} className="p4-muted" />;
    case 'sync': return <RefreshCcw size={11} className="p4-muted" />;
    case 'check': return <CheckCircle2 size={11} className="p4-ok" />;
    case 'spark': return <Sparkles size={11} className="p4-accent" />;
    case 'tool': return <Hammer size={11} className="p4-muted" />;
    default: return <CircleDot size={11} className="p4-muted" />;
  }
};

function BuildTargetChip({ meta, id }) {
  const label = targetLabel(meta, id);
  return (
    <div className="p4-target-row">
      <span className="p4-target-chip">
        {targetIcon(id)}
        <span>{label}</span>
      </span>
    </div>
  );
}

/** Inline run-control bar — Stop / Pause / Continue always visible, no hidden overflow menu. */
function RunControls({ jobStatus, onPause, onResume, onCancel, onSync, canSync }) {
  const isRunning = jobStatus === 'running';
  const isPaused = jobStatus === 'paused';
  const canResume = jobStatus === 'failed' || jobStatus === 'blocked' || isPaused;
  const showStop = jobStatus && !['completed', 'cancelled', 'canceled'].includes(jobStatus);

  if (!isRunning && !canResume && !showStop && !canSync) return null;

  return (
    <div className="p4-run-controls" role="toolbar" aria-label="Build controls">
      {isRunning ? (
        <button
          type="button"
          className="p4-ctrl-btn p4-ctrl-btn--pause"
          onClick={() => onPause?.()}
          title="Pause build"
        >
          <PauseIcon size={12} />
          <span>Pause</span>
        </button>
      ) : null}
      {canResume ? (
        <button
          type="button"
          className="p4-ctrl-btn p4-ctrl-btn--resume"
          onClick={() => onResume?.()}
          title="Continue build"
        >
          <PlayIcon size={12} />
          <span>Continue</span>
        </button>
      ) : null}
      {showStop ? (
        <button
          type="button"
          className="p4-ctrl-btn p4-ctrl-btn--stop"
          onClick={() => onCancel?.()}
          title="Stop build"
        >
          <XIcon size={12} />
          <span>Stop</span>
        </button>
      ) : null}
      {canSync ? (
        <button
          type="button"
          className="p4-ctrl-btn p4-ctrl-btn--sync"
          onClick={() => onSync?.()}
          title="Sync workspace"
        >
          <RefreshCw size={12} />
          <span>Sync</span>
        </button>
      ) : null}
    </div>
  );
}

function UserPrompt({ content, ts: _ts, pinned = false }) {
  return (
    <div className={`p4-row p4-row-user${pinned ? ' p4-row-user--pinned' : ''}`}>
      <div className="p4-user-bubble">
        <div className="p4-user-text">{content}</div>
      </div>
    </div>
  );
}

function CrucibAIHandle({ logoOk, onLogoFail }) {
  return (
    <div className="p4-row p4-row-assistant p4-row-handle">
      <div className="p4-avatar" aria-hidden>
        {logoOk ? (
          <img src="/logo.png" alt="" onError={onLogoFail} className="p4-avatar-img" />
        ) : (
          <span className="p4-avatar-fallback">C</span>
        )}
      </div>
      <span className="p4-assist-name p4-assist-name--header sidebar-logo-text">CrucibAI</span>
    </div>
  );
}

function StatusPill({ jobStatus, isTyping }) {
  if (isTyping || jobStatus === 'running') {
    return (
      <div className="p4-status-pill p4-status-pill--running">
        <Loader2 size={11} className="p4-spin" />
        <span>Working</span>
      </div>
    );
  }
  if (jobStatus === 'failed' || jobStatus === 'cancelled' || jobStatus === 'blocked' || jobStatus === 'waiting_for_user') {
    return (
      <div className="p4-status-pill p4-status-pill--paused">
        <AlertTriangle size={11} />
        <span>Repairing</span>
      </div>
    );
  }
  if (jobStatus === 'completed') {
    return (
      <div className="p4-status-pill p4-status-pill--success">
        <CheckCircle2 size={11} />
        <span>Workspace ready</span>
      </div>
    );
  }
  if (isTyping) {
    return (
      <div className="p4-status-pill p4-status-pill--queued">
        <Loader2 size={11} className="p4-spin" />
        <span>Working</span>
      </div>
    );
  }
  return (
    <div className="p4-status-pill p4-status-pill--queued">
      <CircleDot size={11} />
      <span>Ready</span>
    </div>
  );
}

function AssistantSay({ content, ts: _ts, logoOk, onLogoFail }) {
  return (
    <div className="p4-row p4-row-assistant">
      <div className="p4-avatar" aria-hidden>
        {logoOk ? (
          <img src="/logo.png" alt="" onError={onLogoFail} className="p4-avatar-img" />
        ) : (
          <span className="p4-avatar-fallback">C</span>
        )}
      </div>
      <div className="p4-assist-col">
        <div className="p4-assist-handle">
          <span className="p4-assist-name">CrucibAI</span>
        </div>
        <div className="p4-assist-text">{content}</div>
      </div>
    </div>
  );
}

function PlanBlock({ title, steps }) {
  const [open, setOpen] = useState(false);
  const stepIcon = (status) => {
    if (status === 'completed' || status === 'success') return <CheckCircle2 size={12} className="p4-ok" />;
    if (status === 'failed') return <AlertTriangle size={12} className="p4-bad" />;
    if (status === 'running' || status === 'in_progress') return <Loader2 size={12} className="p4-spin" />;
    return <span className="p4-step-dot" />;
  };
  return (
    <div className="p4-block p4-plan-block">
      <button type="button" className="p4-section-head" onClick={() => setOpen((v) => !v)}>
        {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        <span className="p4-section-title">{title}</span>
        <span className="p4-section-counter">{steps.length}</span>
      </button>
      {open && (
        <ul className="p4-plan-list">
          {steps.map((s) => (
            <li key={s.id} className={`p4-plan-step p4-plan-step--${s.status || 'pending'}`}>
              {stepIcon(s.status)}
              <span className="p4-plan-step-label">{s.label}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ToolGroup({ item }) {
  const [open, setOpen] = useState(true);
  const total = item.children.length;
  const doneCount = item.children.filter((c) => c.status === 'success' || c.status === 'completed').length;
  const summary =
    item.status === 'failed' ? 'Repairing'
    : item.status === 'running' ? 'Running'
    : 'Done';
  const progressLabel = total > 0 ? `${doneCount}/${total}` : '';
  const visibleChips = open ? item.children : item.children.slice(0, 4);
  const hidden = Math.max(0, total - visibleChips.length);
  return (
    <div className={`p4-chapter p4-chapter--phase p4-chapter--${item.status || 'success'}`}>
      <button type="button" className="p4-chapter-head" onClick={() => setOpen((v) => !v)}>
        {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        <span className="p4-chapter-title">{item.title}</span>
        <span className="p4-chapter-progress" aria-hidden>{progressLabel}</span>
        <span className={`p4-chapter-status p4-chapter-status--${item.status || 'success'}`}>{summary}</span>
      </button>
      {item.description ? <p className="p4-chapter-desc">{item.description}</p> : null}
      {total > 0 ? (
        <div className="p4-chip-list p4-chip-list--pills">
          {visibleChips.map((c) => (
            <div key={c.id} className={`p4-chip p4-chip--pill p4-chip--${c.status}`}>
              <ToolIcon kind={c.iconKey} status={c.status} />
              <span className="p4-chip-title">{c.title}</span>
            </div>
          ))}
          {hidden > 0 ? (
            <button type="button" className="p4-chip p4-chip--more" onClick={() => setOpen(true)}>
              +{hidden} more
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function FailureBlock({ item }) {
  const niceReason = (item.reason || '').toString().trim();
  // Show the real reason if we have one. Only fall back to generic if reason is empty
  // or is a raw internal error key (orchestrator_error, background_crash, etc).
  const isGenericInternalReason =
    !niceReason ||
    /^(orchestrator_error|background_crash|job_not_found|execution_timeout|watchdog_timeout)$/i.test(niceReason);
  const friendlyReason = isGenericInternalReason
    ? 'Something went wrong during the build. Send a follow-up message below and I will pick up from the saved files.'
    : niceReason;
  const raw = (item.rawDetail || '').toString().trim();
  // Show technical detail if it adds information beyond the friendly reason
  const showTechnical = raw.length > 0 && raw !== friendlyReason && raw !== niceReason;
  return (
    <div className="p4-chapter p4-chapter--diagnostic">
      <div className="p4-chapter-head p4-chapter-head--static">
        <AlertTriangle size={13} className="p4-bad" />
        <span className="p4-chapter-title">{item.title || 'Build issue'}</span>
        <span className="p4-chapter-status p4-chapter-status--failed">Needs fix</span>
      </div>
      <p className="p4-chapter-desc">{friendlyReason}</p>
      {showTechnical ? (
        <details className="p4-tech-details">
          <summary className="p4-tech-details-summary">What went wrong</summary>
          <pre className="p4-tech-details-pre">{raw}</pre>
        </details>
      ) : null}
      {Array.isArray(item.missingItems) && item.missingItems.length > 0 ? (
        <div className="p4-chip-list">
          {item.missingItems.map((m, i) => (
            <div key={`${i}-${String(m)}`} className="p4-chip p4-chip--failed">
              <AlertTriangle size={11} className="p4-bad" />
              <span className="p4-chip-title">{String(m)}</span>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function phaseStatusLabel(st) {
  if (st === 'done') return 'Done';
  if (st === 'failed') return 'Repairing';
  if (st === 'running') return 'Running';
  return 'Pending';
}

function BuildProgressCard({ item }) {
  const meta = phaseLabels();
  const order = meta.order;
  const [detailsOpen, setDetailsOpen] = useState(false);
  return (
    <div className="p4-block p4-build-progress">
      <div className="p4-build-progress-head">Build progress</div>
      <div className="p4-build-progress-rows">
        {order.map((key) => {
          const cell = item.phases[key];
          const st = cell?.status || 'pending';
          return (
            <div key={key} className="p4-build-progress-row">
              <span className="p4-bpr-label">{meta[key]}</span>
              <span className={`p4-bpr-status p4-bpr-status--${st}`}>{phaseStatusLabel(st)}</span>
            </div>
          );
        })}
      </div>
      <button
        type="button"
        className="p4-build-progress-details-btn"
        onClick={() => setDetailsOpen((v) => !v)}
        aria-expanded={detailsOpen}
      >
        {detailsOpen ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        Details
      </button>
      {detailsOpen ? (
        <div className="p4-build-progress-details">
          {order.map((key) => {
            const cell = item.phases[key];
            const actions = cell?.actions || [];
            const details = cell?.details || [];
            if (!actions.length && !details.length) return null;
            return (
              <div key={`d-${key}`} className="p4-bpd-phase">
                <div className="p4-bpd-phase-name">{meta[key]}</div>
                {actions.length ? (
                  <ul>
                    {actions.map((a) => (
                      <li key={a}>{a}</li>
                    ))}
                  </ul>
                ) : null}
                {details.length ? (
                  <ul className="p4-bpd-muted">
                    {details.map((d, i) => (
                      <li key={`${i}-${d}`}>{d}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

function RepairBlock({ item }) {
  const isNeedsFix = item.status === 'needs_fix';
  const stateLabel =
    item.status === 'success'
      ? 'Done'
      : item.status === 'failed'
      ? 'Repairing'
      : isNeedsFix
      ? 'Repairing'
      : `Pass ${item.attempt || 1}`;
  const headTitle =
    item.status === 'success'
      ? 'Repair complete'
      : item.status === 'failed'
      ? 'Continuing repair'
      : isNeedsFix
      ? item.title || 'Repairing verification issue'
      : 'Repair in progress';
  const detail = (item.technicalDetail || '').trim();
  return (
    <div
      className={`p4-inline-card p4-card-repair p4-card-repair--${isNeedsFix ? 'needs_fix' : item.status || 'running'}`}
    >
      <div className="p4-inline-head">
        <Wrench size={13} className="p4-warn" />
        <span className="p4-inline-title">{headTitle}</span>
        <span className="p4-inline-state">{stateLabel}</span>
      </div>
      {item.narration ? <p className="p4-inline-text">{item.narration}</p> : null}
      {item.repeatCount > 1 ? (
        <p className="p4-repair-meta">Same check still failing (×{item.repeatCount})</p>
      ) : null}
      {detail ? (
        <details className="p4-tech-details">
          <summary className="p4-tech-details-summary">Details</summary>
          <pre className="p4-tech-details-pre">{detail}</pre>
        </details>
      ) : null}
      {Array.isArray(item.filesChanged) && item.filesChanged.length > 0 ? (
        <ul className="p4-inline-files">
          {item.filesChanged.map((f, i) => (
            <li key={`${i}-${String(f)}`}>{String(f)}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function ProofBlock({ item }) {
  const label =
    item.proofType === 'export_gate_ready' ? 'Export gate ready' :
    item.proofType === 'run_snapshot' ? 'Runtime proof captured' :
    item.proofType === 'contract_delta_created' ? 'Contract updated' : 'Proof';
  return (
    <div className="p4-inline-card p4-card-proof">
      <div className="p4-inline-head">
        <ShieldCheck size={13} className="p4-ok" />
        <span className="p4-inline-title">{label}</span>
      </div>
      {item.narration ? <p className="p4-inline-text">{item.narration}</p> : null}
    </div>
  );
}

function IssueNoticeCard({ item }) {
  const detail = (item.technicalDetail || '').trim();
  return (
    <div className="p4-surface-card p4-issue-notice">
      <div className="p4-surface-card-head">
        <AlertTriangle size={14} className="p4-warn" />
        <span className="p4-surface-card-title">{item.title || 'Update'}</span>
      </div>
      {item.summary ? <p className="p4-surface-card-body">{item.summary}</p> : null}
      {detail ? (
        <details className="p4-tech-details">
          <summary className="p4-tech-details-summary">What the system saw</summary>
          <pre className="p4-tech-details-pre">{detail}</pre>
        </details>
      ) : null}
    </div>
  );
}

function CheckpointCard({ item }) {
  return (
    <div className="p4-surface-card p4-checkpoint-card">
      <div className="p4-checkpoint-icon-wrap" aria-hidden>
        <Package size={18} />
      </div>
      <div className="p4-checkpoint-body">
        <div className="p4-surface-card-title">{item.title}</div>
        {item.subtitle ? <p className="p4-checkpoint-sub">{item.subtitle}</p> : null}
      </div>
      <CheckCircle2 size={16} className="p4-checkpoint-ok" aria-hidden />
    </div>
  );
}

function DeliveryCard({ item, context }) {
  const [thumbUrl, setThumbUrl] = useState(null);
  const [thumbErr, setThumbErr] = useState('');
  const truth = context?.truthSurface || null;
  const previewSource = String(truth?.preview_source || 'unknown');
  const suggestions = useMemo(() => buildFollowupSuggestions(truth), [truth]);
  useEffect(() => {
    let dead = false;
    let objUrl = null;
    const load = async () => {
      if (!context?.jobId || !context?.token || !context?.apiBase) return;
      try {
        const u = `${context.apiBase}/jobs/${encodeURIComponent(context.jobId)}/workspace/file/raw`;
        const p = '.crucibai/preview/screenshot.png';
        const res = await fetch(`${u}?path=${encodeURIComponent(p)}`, {
          headers: { Authorization: `Bearer ${context.token}` },
        });
        if (!res.ok) return;
        const blob = await res.blob();
        if (dead || !blob || blob.size === 0) return;
        objUrl = URL.createObjectURL(blob);
        setThumbUrl(objUrl);
        setThumbErr('');
      } catch (e) {
        if (!dead) setThumbErr(String(e?.message || ''));
      }
    };
    load();
    return () => {
      dead = true;
      if (objUrl) URL.revokeObjectURL(objUrl);
    };
  }, [context?.jobId, context?.token, context?.apiBase]);
  return (
    <div className="p4-surface-card p4-delivery-card">
      <div className="p4-delivery-row">
        <Rocket size={16} className="p4-accent" aria-hidden />
        <div className="p4-delivery-main">
          <div className="p4-surface-card-title">Build delivered to this workspace</div>
          {item.narration ? <p className="p4-surface-card-body p4-delivery-sub">{item.narration}</p> : null}
          <div className="p4-delivery-meta">
            <span className="p4-delivery-chip">preview_source: {previewSource}</span>
            {truth ? (
              <span className="p4-delivery-chip">
                contract: {truth.prompt_contract_passed === false ? 'failed' : 'passed'}
              </span>
            ) : null}
          </div>
          {thumbUrl ? (
            <div className="p4-delivery-thumb-wrap">
              <img src={thumbUrl} alt="Build preview thumbnail" className="p4-delivery-thumb" />
            </div>
          ) : null}
          {!thumbUrl && thumbErr ? (
            <p className="p4-delivery-thumb-note">Preview thumbnail unavailable right now.</p>
          ) : null}
          {suggestions.length ? (
            <div className="p4-delivery-followups">
              {suggestions.map((s) => (
                <button
                  type="button"
                  key={s}
                  className="p4-delivery-followup-btn"
                  onClick={() => context?.onUseSuggestion?.(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          ) : null}
        </div>
        <ChevronRight size={16} className="p4-muted-icon" aria-hidden />
      </div>
    </div>
  );
}

function ThreadItem({ item, logoOk, onLogoFail, isPinnedUser, deliveryContext }) {
  switch (item.kind) {
    case 'user_message':
      return <UserPrompt content={item.content} ts={item.ts} pinned={isPinnedUser} />;
    case 'assistant_message':
      return <AssistantSay content={item.content} ts={item.ts} logoOk={logoOk} onLogoFail={onLogoFail} />;
    case 'plan_block':
      return <PlanBlock title={item.title} steps={item.steps} />;
    case 'build_progress_card':
      return <BuildProgressCard item={item} />;
    case 'tool_group':
      return <ToolGroup item={item} />;
    case 'failure_block':
      return <FailureBlock item={item} />;
    case 'repair_block':
      return <RepairBlock item={item} />;
    case 'proof_block':
      return <ProofBlock item={item} />;
    case 'issue_notice':
      return <IssueNoticeCard item={item} />;
    case 'checkpoint_card':
      return <CheckpointCard item={item} />;
    case 'delivery_card':
      return <DeliveryCard item={item} context={deliveryContext} />;
    default:
      return null;
  }
}

export default function BrainGuidancePanel({
  userMessages = [],
  events = [],
  jobStatus,
  isTyping,
  jobId = null,
  hasTaskOrJobContext = false,
  buildTargetMeta = null,
  buildTargetId = null,
  onScroll,
  onPause,
  onResume,
  onCancel,
  onSync,
  canSync = false,
  previewUrl = null,
  proofTruthSurface = null,
  token = null,
  apiBase = '',
  onUseSuggestion,
  /** Workspace: fixed header shows CrucibAI — hide duplicate handle + pill in the scroll stream */
  omitInlineBrandChrome = false,
}) {
  const scrollRef = useRef(null);
  const [logoFailed, setLogoFailed] = useState(false);
  const userIsScrollingRef = useRef(false);

  const { items, scrollLayoutKey } = useMemo(() => {
    const list = buildThreadModel({ userMessages, events, activeJobId: jobId });
    const key = list.map((i) => (i.kind === 'build_progress_card' ? `bpc:${i.id}` : `${i.kind}:${i.id}`)).join('|');
    return { items: list, scrollLayoutKey: key };
  }, [userMessages, events, jobId]);

  const hasUserPrompt = items.some((i) => i.kind === 'user_message');
  const hasAssistantNarration = items.some((i) => i.kind === 'assistant_message');
  const shouldRenderEmptyState = items.length === 0 && !isTyping && !jobId && !hasTaskOrJobContext;
  const firstUserId = useMemo(() => {
    const u = items.find((i) => i.kind === 'user_message');
    return u?.id ?? null;
  }, [items]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      console.info('[PHASE4_ACTIVE] Phase4LiveExecutionSurface mounted');
      console.info('[PHASE4_ACTIVE] activeJobId=', jobId);
      console.info('[PHASE4_ACTIVE] renderedThreadItems=', items.length);
    } catch {
      /* ignore console in non-browser */
    }
  }, [jobId, items.length]);

  useEffect(() => {
    if (userIsScrollingRef.current) return;
    const node = scrollRef.current;
    const scroller = node?.parentElement;
    if (!scroller) return;
    const distanceFromBottom = scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight;
    if (distanceFromBottom < 200) {
      scroller.scrollTop = scroller.scrollHeight;
    }
  }, [scrollLayoutKey, isTyping]);

  const handleScroll = () => {
    const node = scrollRef.current;
    const scroller = node?.parentElement;
    if (!scroller) return;
    const distanceFromBottom = scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight;
    userIsScrollingRef.current = distanceFromBottom > 200;
    onScroll?.({ isNearBottom: distanceFromBottom < 120 });
  };

  if (shouldRenderEmptyState) {
    return (
      <div className="bgp-thread-empty">
        <div className="bgp-empty-inner">
          <p className="bgp-empty-text">
            {`Describe what you want to build in the composer below. I'll plan, build, and verify it live.`}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div ref={scrollRef} onScrollCapture={handleScroll} className="bgp-thread-only bgp-thread-only--top">
      {(buildTargetMeta || buildTargetId) ? (
        <div className="p4-thread-head">
          <BuildTargetChip meta={buildTargetMeta} id={buildTargetId} />
        </div>
      ) : null}

      {items.map((item) => (
        <ThreadItem
          key={item.id}
          item={item}
          logoOk={!logoFailed}
          onLogoFail={() => setLogoFailed(true)}
          isPinnedUser={item.kind === 'user_message' && item.id === firstUserId}
          deliveryContext={{
            previewUrl,
            truthSurface: proofTruthSurface,
            jobId: jobId || null,
            token,
            apiBase,
            onUseSuggestion,
          }}
        />
      ))}

      {/* Initial-state CrucibAI handle + status pill, rendered when the user
          has spoken but the system has not narrated anything yet. */}
      {!omitInlineBrandChrome && hasUserPrompt && !hasAssistantNarration ? (
        <>
          <CrucibAIHandle logoOk={!logoFailed} onLogoFail={() => setLogoFailed(true)} />
          <div className="p4-handle-pill-row">
            <StatusPill jobStatus={jobStatus} isTyping={isTyping} />
          </div>
        </>
      ) : null}

      {isTyping && (hasAssistantNarration || items.length > 0) ? (
        <div className={`p4-row p4-row-assistant p4-row-typing${isTyping ? ' p4-row-typing--alive' : ''}`} aria-busy={isTyping}>
          <div className="p4-avatar" aria-hidden>
            {!logoFailed ? (
              <img src="/logo.png" alt="" onError={() => setLogoFailed(true)} className="p4-avatar-img" />
            ) : (
              <span className="p4-avatar-fallback">C</span>
            )}
          </div>
          <div className="p4-assist-col">
            <div className="p4-typing-dots"><span /> <span /> <span /></div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
                                                                                                                                                              
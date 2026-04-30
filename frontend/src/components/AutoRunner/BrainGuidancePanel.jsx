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
} from 'lucide-react';
import { buildThreadModel } from '../../lib/buildThreadModel';
import './BrainGuidancePanel.css';

const formatTime = (ts) => {
  if (!ts) return '';
  try {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
};

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

function ThreadOverflow({ jobStatus, onPause, onResume, onCancel, onSync, canSync }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    const onDoc = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [open]);
  const isRunning = jobStatus === 'running';
  const canResume = jobStatus === 'failed' || jobStatus === 'blocked';
  const showCancel = jobStatus && !['completed', 'cancelled'].includes(jobStatus);
  const hasAny = isRunning || canResume || showCancel || canSync;
  if (!hasAny) return null;
  return (
    <div className="p4-overflow-wrap" ref={ref}>
      <button
        type="button"
        className="p4-overflow-btn"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        title="Run controls"
      >
        <MoreHorizontal size={14} />
      </button>
      {open ? (
        <div className="p4-overflow-menu" role="menu">
          {isRunning ? (
            <button type="button" className="p4-overflow-item" onClick={() => { setOpen(false); onPause?.(); }}>
              <PauseIcon size={12} /> Pause
            </button>
          ) : null}
          {canResume ? (
            <button type="button" className="p4-overflow-item" onClick={() => { setOpen(false); onResume?.(); }}>
              <PlayIcon size={12} /> Continue
            </button>
          ) : null}
          {showCancel ? (
            <button type="button" className="p4-overflow-item p4-overflow-item--danger" onClick={() => { setOpen(false); onCancel?.(); }}>
              <XIcon size={12} /> Stop
            </button>
          ) : null}
          {canSync ? (
            <button type="button" className="p4-overflow-item" onClick={() => { setOpen(false); onSync?.(); }}>
              <RefreshCw size={12} /> Sync workspace
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function UserPrompt({ content, ts }) {
  return (
    <div className="p4-row p4-row-user">
      <div className="p4-user-bubble">
        <div className="p4-user-text">{content}</div>
        {ts ? <div className="p4-meta-time">{formatTime(ts)}</div> : null}
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
      <span className="p4-assist-name p4-assist-name--header">CrucibAI</span>
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
  return (
    <div className="p4-status-pill p4-status-pill--queued">
      <Loader2 size={11} className="p4-spin" />
      <span>Thinking</span>
    </div>
  );
}

function AssistantSay({ content, ts, logoOk, onLogoFail }) {
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
          {ts ? <span className="p4-assist-time">{formatTime(ts)}</span> : null}
        </div>
        <div className="p4-assist-text">{content}</div>
      </div>
    </div>
  );
}

function PlanBlock({ title, steps }) {
  const [open, setOpen] = useState(true);
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
  const [open, setOpen] = useState(false);
  const total = item.children.length;
  const summary =
    item.status === 'failed' ? 'Needs attention'
    : item.status === 'running' ? 'Running'
    : 'Done';
  const visibleChips = open ? item.children : item.children.slice(0, 4);
  const hidden = Math.max(0, total - visibleChips.length);
  return (
    <div className={`p4-chapter p4-chapter--${item.status || 'success'}`}>
      <button type="button" className="p4-chapter-head" onClick={() => setOpen((v) => !v)}>
        {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        <span className="p4-chapter-title">{item.title}</span>
        <span className={`p4-chapter-status p4-chapter-status--${item.status || 'success'}`}>{summary}</span>
      </button>
      {item.description ? <p className="p4-chapter-desc">{item.description}</p> : null}
      {total > 0 ? (
        <div className="p4-chip-list">
          {visibleChips.map((c) => (
            <div key={c.id} className={`p4-chip p4-chip--${c.status}`}>
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
  // Diagnostic block: title is "what", reason is "why", actions are "what next".
  const niceReason = (item.reason || '').toString().trim();
  const friendlyReason =
    niceReason && !/orchestrator_error/i.test(niceReason)
      ? niceReason
      : 'I need another pass to finish this workspace. Send a note below and I will keep going from the saved files.';
  return (
    <div className="p4-chapter p4-chapter--diagnostic">
      <div className="p4-chapter-head p4-chapter-head--static">
        <AlertTriangle size={13} className="p4-bad" />
        <span className="p4-chapter-title">{item.title || 'Checking the workspace'}</span>
        <span className="p4-chapter-status p4-chapter-status--failed">Needs attention</span>
      </div>
      <p className="p4-chapter-desc">{friendlyReason}</p>
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

function RepairBlock({ item }) {
  const stateLabel =
    item.status === 'success' ? 'Repaired'
    : item.status === 'failed' ? 'Another pass needed'
    : `Attempt ${item.attempt || 1}`;
  const headTitle =
    item.status === 'success' ? 'Repair complete'
    : item.status === 'failed' ? 'Repair needs another pass'
    : 'Repairing the workspace';
  return (
    <div className={`p4-inline-card p4-card-repair p4-card-repair--${item.status || 'running'}`}>
      <div className="p4-inline-head">
        <Wrench size={13} className="p4-warn" />
        <span className="p4-inline-title">{headTitle}</span>
        <span className="p4-inline-state">{stateLabel}</span>
      </div>
      {item.narration ? <p className="p4-inline-text">{item.narration}</p> : null}
      {Array.isArray(item.filesChanged) && item.filesChanged.length > 0 ? (
        <ul className="p4-inline-files">
          {item.filesChanged.map((f, i) => (<li key={`${i}-${String(f)}`}>{String(f)}</li>))}
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

function ThreadItem({ item, logoOk, onLogoFail }) {
  switch (item.kind) {
    case 'user_message':
      return <UserPrompt content={item.content} ts={item.ts} />;
    case 'assistant_message':
      return <AssistantSay content={item.content} ts={item.ts} logoOk={logoOk} onLogoFail={onLogoFail} />;
    case 'plan_block':
      return <PlanBlock title={item.title} steps={item.steps} />;
    case 'tool_group':
      return <ToolGroup item={item} />;
    case 'failure_block':
      return <FailureBlock item={item} />;
    case 'repair_block':
      return <RepairBlock item={item} />;
    case 'proof_block':
      return <ProofBlock item={item} />;
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
  /** Same job stream as Preview / Proof / Timeline (single effectiveJobId in workspace) */
  streamConnected = false,
  connectionMode = 'sse',
  eventCount = 0,
  onScroll,
  onPause,
  onResume,
  onCancel,
  onSync,
  canSync = false,
}) {
  const scrollRef = useRef(null);
  const [logoFailed, setLogoFailed] = useState(false);
  const userIsScrollingRef = useRef(false);

  const items = useMemo(
    () => buildThreadModel({ userMessages, events, activeJobId: jobId }),
    [userMessages, events, jobId]
  );

  const hasUserPrompt = items.some((i) => i.kind === 'user_message');
  const hasAssistantNarration = items.some((i) => i.kind === 'assistant_message');
  const shouldRenderEmptyState = items.length === 0 && !isTyping && !jobId && !hasTaskOrJobContext;

  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      console.info('[PHASE4_ACTIVE] Phase4LiveExecutionSurface mounted');
      console.info('[PHASE4_ACTIVE] activeJobId=', jobId);
      console.info('[PHASE4_ACTIVE] renderedThreadItems=', items.length);
    } catch {}
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
  }, [items, isTyping]);

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
      <div className="p4-thread-head">
        {(buildTargetMeta || buildTargetId) ? (
          <BuildTargetChip meta={buildTargetMeta} id={buildTargetId} />
        ) : <span />}
        {jobId ? (
          <span
            className={`p4-stream-badge ${streamConnected ? 'p4-stream-badge--live' : 'p4-stream-badge--wait'}`}
            title={`Job stream (${connectionMode || 'sse'}) - ${eventCount} events`}
          >
            {streamConnected ? 'Live' : 'Connecting...'}
          </span>
        ) : null}
        <ThreadOverflow
          jobStatus={jobStatus}
          onPause={onPause}
          onResume={onResume}
          onCancel={onCancel}
          onSync={onSync}
          canSync={canSync}
        />
      </div>

      {items.map((item) => (
        <ThreadItem
          key={item.id}
          item={item}
          logoOk={!logoFailed}
          onLogoFail={() => setLogoFailed(true)}
        />
      ))}

      {/* Initial-state CrucibAI handle + status pill, rendered when the user
          has spoken but the system has not narrated anything yet. */}
      {hasUserPrompt && !hasAssistantNarration ? (
        <>
          <CrucibAIHandle logoOk={!logoFailed} onLogoFail={() => setLogoFailed(true)} />
          <div className="p4-handle-pill-row">
            <StatusPill jobStatus={jobStatus} isTyping={isTyping} />
          </div>
        </>
      ) : null}

      {isTyping && (hasAssistantNarration || items.length > 0) ? (
        <div className="p4-row p4-row-assistant p4-row-typing">
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

/**
 * Phase4LiveExecutionSurface
 * --------------------------
 * Conversation-first center pane for /app/workspace.
 *
 * Visual model: Manus / Kimi style with CrucibAI brand tokens.
 *  - User prompt renders FIRST always (no event can render above it).
 *  - Assistant text renders as plain text on the left, NO bubble border.
 *  - Phases render as collapsible chevron sections.
 *  - Tool calls render as small inline pill chips with an icon + title.
 *  - Failures / repairs / proof render as inline accent cards (not modals).
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

const ToolIcon = ({ kind, status }) => {
  if (status === 'running') return <Loader2 size={11} className="p4-spin" />;
  if (status === 'failed') return <AlertTriangle size={11} className="p4-bad" />;
  switch (kind) {
    case 'edit':
      return <FileEdit size={11} className="p4-muted" />;
    case 'sync':
      return <RefreshCcw size={11} className="p4-muted" />;
    case 'check':
      return <CheckCircle2 size={11} className="p4-ok" />;
    case 'spark':
      return <Sparkles size={11} className="p4-accent" />;
    case 'tool':
      return <Hammer size={11} className="p4-muted" />;
    default:
      return <CircleDot size={11} className="p4-muted" />;
  }
};

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
    if (status === 'running' || status === 'in_progress')
      return <Loader2 size={12} className="p4-spin" />;
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
  const [open, setOpen] = useState(item.status === 'running');
  const total = item.children.length;
  const summary =
    item.status === 'failed'
      ? 'Failed'
      : item.status === 'running'
      ? `${total} step${total === 1 ? '' : 's'} running`
      : `${total} step${total === 1 ? '' : 's'}`;
  return (
    <div className={`p4-block p4-tool-group p4-tg--${item.status || 'success'}`}>
      <button type="button" className="p4-section-head" onClick={() => setOpen((v) => !v)}>
        {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        <span className="p4-section-title">{item.title}</span>
        {item.agent ? <span className="p4-section-agent">{item.agent}</span> : null}
        <span className="p4-section-counter">{summary}</span>
      </button>
      {open && (
        <div className="p4-chip-list">
          {item.children.map((c) => (
            <div key={c.id} className={`p4-chip p4-chip--${c.status}`}>
              <ToolIcon kind={c.iconKey} status={c.status} />
              <span className="p4-chip-title">{c.title}</span>
              {c.ts ? <span className="p4-chip-time">{formatTime(c.ts)}</span> : null}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function FailureBlock({ item }) {
  return (
    <div className="p4-inline-card p4-card-failure">
      <div className="p4-inline-head">
        <AlertTriangle size={13} className="p4-bad" />
        <span className="p4-inline-title">{item.title}</span>
      </div>
      {item.reason ? <p className="p4-inline-text">{item.reason}</p> : null}
      {Array.isArray(item.missingItems) && item.missingItems.length > 0 ? (
        <ul className="p4-inline-list">
          {item.missingItems.map((m, i) => (
            <li key={`${i}-${String(m)}`}>{String(m)}</li>
          ))}
        </ul>
      ) : null}
      {Array.isArray(item.actions) && item.actions.length > 0 ? (
        <div className="p4-inline-actions">
          {item.actions.map((a) => (
            <span key={a} className="p4-action-chip">{a}</span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function RepairBlock({ item }) {
  const stateLabel =
    item.status === 'success' ? 'Repaired'
    : item.status === 'failed' ? 'Failed'
    : `Attempt ${item.attempt || 1}`;
  return (
    <div className={`p4-inline-card p4-card-repair p4-card-repair--${item.status || 'running'}`}>
      <div className="p4-inline-head">
        <Wrench size={13} className="p4-warn" />
        <span className="p4-inline-title">{item.agent || 'RepairAgent'}</span>
        <span className="p4-inline-state">{stateLabel}</span>
      </div>
      {item.narration ? <p className="p4-inline-text">{item.narration}</p> : null}
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

function ThreadItem({ item, logoOk, onLogoFail }) {
  switch (item.kind) {
    case 'user_message':
      return <UserPrompt content={item.content} ts={item.ts} />;
    case 'assistant_message':
      return (
        <AssistantSay
          content={item.content}
          ts={item.ts}
          logoOk={logoOk}
          onLogoFail={onLogoFail}
        />
      );
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
  onScroll,
}) {
  const scrollRef = useRef(null);
  const [logoFailed, setLogoFailed] = useState(false);

  const items = useMemo(
    () => buildThreadModel({ userMessages, events, activeJobId: jobId }),
    [userMessages, events, jobId]
  );

  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      console.info('[PHASE4_ACTIVE] Phase4LiveExecutionSurface mounted');
      console.info('[PHASE4_ACTIVE] activeJobId=', jobId);
      console.info('[PHASE4_ACTIVE] renderedThreadItems=', items.length);
    } catch {}
  }, [jobId, items.length]);

  useEffect(() => {
    const node = scrollRef.current;
    const scroller = node?.parentElement;
    if (scroller) scroller.scrollTop = scroller.scrollHeight;
  }, [items, isTyping]);

  const handleScroll = () => {
    const container = scrollRef.current;
    if (!container) return;
    const { scrollTop, scrollHeight, clientHeight } = container;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 120;
    onScroll?.({ isNearBottom });
  };

  if (items.length === 0 && !isTyping) {
    return (
      <div className="bgp-thread-empty">
        <div className="bgp-empty-inner">
          <p className="bgp-empty-text">
            Describe what you want to build in the composer below. I’ll plan, build, and verify it live.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div ref={scrollRef} onScroll={handleScroll} className="bgp-thread-only">
      {items.map((item) => (
        <ThreadItem
          key={item.id}
          item={item}
          logoOk={!logoFailed}
          onLogoFail={() => setLogoFailed(true)}
        />
      ))}

      {isTyping ? (
        <div className="p4-row p4-row-assistant p4-row-typing">
          <div className="p4-avatar" aria-hidden>
            {!logoFailed ? (
              <img
                src="/logo.png"
                alt=""
                onError={() => setLogoFailed(true)}
                className="p4-avatar-img"
              />
            ) : (
              <span className="p4-avatar-fallback">C</span>
            )}
          </div>
          <div className="p4-assist-col">
            <div className="p4-typing-dots">
              <span /> <span /> <span />
            </div>
          </div>
        </div>
      ) : null}

      {jobStatus === 'completed' ? (
        <div className="p4-status-line">Build complete</div>
      ) : null}
    </div>
  );
}

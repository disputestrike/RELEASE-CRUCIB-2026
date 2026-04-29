/**
 * Phase4LiveExecutionSurface
 * --------------------------
 * Conversation-first center pane for /app/workspace.
 *
 * Order is enforced (NOT styled):
 *   1. user prompt
 *   2. assistant acknowledgement
 *   3. plan / checklist
 *   4. tool/agent activity grouped under the relevant phase
 *   5. failure / repair / proof inline
 *
 * Events from a different jobId are filtered out.
 *
 * Exported as the default of BrainGuidancePanel so the existing mount path in
 * UnifiedWorkspace continues to work without renaming files.
 */

import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  Wrench,
  ShieldCheck,
  ChevronDown,
  ChevronRight,
  FileCode2,
  Loader2,
  Sparkles,
  ArrowRight,
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

function UserBubble({ content, ts }) {
  return (
    <div className="p4-row p4-row-user">
      <div className="p4-bubble p4-bubble-user">
        <div className="p4-bubble-text">{content}</div>
        {ts ? <div className="p4-meta-time">{formatTime(ts)}</div> : null}
      </div>
    </div>
  );
}

function AssistantBubble({ content, ts, logoOk, onLogoFail }) {
  return (
    <div className="p4-row p4-row-assistant">
      <div className="p4-avatar" aria-hidden>
        {logoOk ? (
          <img src="/logo.png" alt="" onError={onLogoFail} className="p4-avatar-img" />
        ) : (
          <span className="p4-avatar-fallback">C</span>
        )}
      </div>
      <div className="p4-bubble p4-bubble-assistant">
        <div className="p4-bubble-text">{content}</div>
        {ts ? <div className="p4-meta-time">{formatTime(ts)}</div> : null}
      </div>
    </div>
  );
}

function PlanBlock({ title, steps }) {
  const [open, setOpen] = useState(true);
  const stepIcon = (status) => {
    if (status === 'completed' || status === 'success') return <CheckCircle2 size={13} className="p4-ok" />;
    if (status === 'failed') return <AlertTriangle size={13} className="p4-bad" />;
    if (status === 'running' || status === 'in_progress')
      return <Loader2 size={13} className="p4-spin" />;
    return <span className="p4-step-dot" />;
  };
  return (
    <div className="p4-block p4-plan-block">
      <button
        type="button"
        className="p4-block-head"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        <Sparkles size={13} className="p4-plan-icon" />
        <span className="p4-block-title">{title}</span>
        <span className="p4-block-counter">{steps.length} steps</span>
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
  const statusClass = `p4-tg--${item.status || 'success'}`;
  const childIcon = (s) => {
    if (s === 'failed') return <AlertTriangle size={12} className="p4-bad" />;
    if (s === 'running') return <Loader2 size={12} className="p4-spin" />;
    return <CheckCircle2 size={12} className="p4-ok" />;
  };
  return (
    <div className={`p4-block p4-tool-group ${statusClass}`}>
      <button
        type="button"
        className="p4-block-head"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        <FileCode2 size={13} className="p4-tg-icon" />
        <span className="p4-block-title">{item.title}</span>
        {item.agent ? <span className="p4-tg-agent">{item.agent}</span> : null}
        <span className="p4-block-counter">{item.children.length}</span>
        <span className={`p4-tg-state p4-tg-state--${item.status || 'success'}`}>
          {item.status === 'failed'
            ? 'Failed'
            : item.status === 'running'
            ? 'Running'
            : 'Done'}
        </span>
      </button>
      {open && (
        <ul className="p4-tg-list">
          {item.children.map((c) => (
            <li key={c.id} className={`p4-tg-row p4-tg-row--${c.status}`}>
              {childIcon(c.status)}
              <span className="p4-tg-row-title">{c.title}</span>
              {c.agent ? <span className="p4-tg-row-agent">{c.agent}</span> : null}
              {c.ts ? <span className="p4-tg-row-time">{formatTime(c.ts)}</span> : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function FailureBlock({ item }) {
  return (
    <div className="p4-block p4-failure-block">
      <div className="p4-block-head p4-block-head-static">
        <AlertTriangle size={14} className="p4-bad" />
        <span className="p4-block-title">{item.title}</span>
      </div>
      {item.reason ? <p className="p4-failure-reason">{item.reason}</p> : null}
      {Array.isArray(item.missingItems) && item.missingItems.length > 0 ? (
        <ul className="p4-failure-missing">
          {item.missingItems.map((m, i) => (
            <li key={`${i}-${String(m)}`}>{String(m)}</li>
          ))}
        </ul>
      ) : null}
      {Array.isArray(item.actions) && item.actions.length > 0 ? (
        <div className="p4-failure-actions">
          {item.actions.map((a) => (
            <span key={a} className="p4-action-chip">
              {a}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function RepairBlock({ item }) {
  const stateLabel =
    item.status === 'success'
      ? 'Repaired'
      : item.status === 'failed'
      ? 'Failed'
      : `Attempt ${item.attempt || 1}`;
  return (
    <div className={`p4-block p4-repair-block p4-repair--${item.status || 'running'}`}>
      <div className="p4-block-head p4-block-head-static">
        <Wrench size={14} className="p4-warn" />
        <span className="p4-block-title">
          {item.agent || 'RepairAgent'}
          <span className="p4-repair-state">{stateLabel}</span>
        </span>
      </div>
      {item.narration ? <p className="p4-repair-narration">{item.narration}</p> : null}
      {Array.isArray(item.filesChanged) && item.filesChanged.length > 0 ? (
        <ul className="p4-repair-files">
          {item.filesChanged.map((f, i) => (
            <li key={`${i}-${String(f)}`}>
              <FileCode2 size={11} /> {String(f)}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function ProofBlock({ item }) {
  return (
    <div className="p4-block p4-proof-block">
      <div className="p4-block-head p4-block-head-static">
        <ShieldCheck size={14} className="p4-ok" />
        <span className="p4-block-title">
          {item.proofType === 'export_gate' ? 'Export gate ready' :
            item.proofType === 'run_snapshot' ? 'Runtime proof captured' :
            item.proofType === 'contract_delta_created' ? 'Contract updated' : 'Proof'}
        </span>
      </div>
      {item.narration ? <p className="p4-proof-narration">{item.narration}</p> : null}
    </div>
  );
}

function ThreadItem({ item, logoOk, onLogoFail }) {
  switch (item.kind) {
    case 'user_message':
      return <UserBubble content={item.content} ts={item.ts} />;
    case 'assistant_message':
      return (
        <AssistantBubble
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
          <div className="p4-bubble p4-bubble-assistant">
            <div className="p4-typing-dots">
              <span /> <span /> <span />
            </div>
          </div>
        </div>
      ) : null}

      {jobStatus === 'completed' ? (
        <div className="p4-status-line">
          <ArrowRight size={12} /> Build complete
        </div>
      ) : null}
    </div>
  );
}

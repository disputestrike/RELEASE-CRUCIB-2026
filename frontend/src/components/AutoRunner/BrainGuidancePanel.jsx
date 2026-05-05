import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CircleDot,
  Edit3,
  FileText,
  Globe,
  ListChecks,
  Loader2,
  Pause as PauseIcon,
  Play as PlayIcon,
  Search,
  Server,
  ShieldCheck,
  Smartphone,
  SquareTerminal,
  Wrench,
  X as XIcon,
  RefreshCw,
} from 'lucide-react';
import { buildThreadModel } from '../../lib/buildThreadModel';
import './BrainGuidancePanel.css';

const targetIcon = (id) => {
  const k = String(id || '').toLowerCase();
  if (/(react_native|expo|mobile|android|ios|flutter)/.test(k)) return <Smartphone size={12} />;
  if (/(api|fastapi|express|node|backend|server)/.test(k)) return <Server size={12} />;
  return <Globe size={12} />;
};

const targetLabel = (meta, id) => {
  if (meta?.label) return meta.label;
  if (meta?.name) return meta.name;
  const k = String(id || '').toLowerCase();
  if (/react_native|expo/.test(k)) return 'Mobile app';
  if (/api|fastapi|express|node/.test(k)) return 'API';
  if (/next/.test(k)) return 'Next.js app';
  return 'Web app';
};

const compactText = (value, max = 520) => {
  const raw = String(value || '').trim();
  if (raw.length <= max) return { preview: raw, overflow: '' };
  return {
    preview: `${raw.slice(0, max).trimEnd()}...`,
    overflow: raw,
  };
};

const looksLikeCode = (value) => {
  const s = String(value || '');
  return s.includes('\n') && (/[{};]/.test(s) || /^\s*(import|export|const|let|function|class|<\w+)/m.test(s));
};

function ToolResult({ text, detail }) {
  const { preview, overflow } = compactText(text);
  if (!preview && !detail?.length) return null;
  return (
    <>
      {preview ? (
        looksLikeCode(preview) ? (
          <pre className="cc-tool-code">{preview}</pre>
        ) : (
          <div className="cc-tool-result">{preview}</div>
        )
      ) : null}
      {(overflow || detail?.length) ? (
        <details className="cc-tool-details">
          <summary>Details</summary>
          {overflow ? <pre>{overflow}</pre> : null}
          {detail?.length ? (
            <div className="cc-tool-detail-stack">
              {detail.map((line, i) => (
                <div key={`${line}-${i}`}>{line}</div>
              ))}
            </div>
          ) : null}
        </details>
      ) : null}
    </>
  );
}

function BuildTargetChip({ meta, id }) {
  return (
    <span className="cc-target-chip">
      {targetIcon(id)}
      <span>{targetLabel(meta, id)}</span>
    </span>
  );
}

function RunControls({ jobStatus, onPause, onResume, onCancel, onSync, canSync }) {
  const isRunning = jobStatus === 'running';
  const canResume = ['failed', 'blocked', 'paused', 'waiting_for_user'].includes(String(jobStatus || ''));
  const showStop = jobStatus && !['completed', 'cancelled', 'canceled'].includes(String(jobStatus));

  if (!isRunning && !canResume && !showStop && !canSync) return null;

  return (
    <div className="cc-run-controls" role="toolbar" aria-label="Run controls">
      {isRunning ? (
        <button type="button" className="cc-icon-btn" onClick={() => onPause?.()} title="Pause">
          <PauseIcon size={13} />
        </button>
      ) : null}
      {canResume ? (
        <button type="button" className="cc-icon-btn" onClick={() => onResume?.()} title="Continue">
          <PlayIcon size={13} />
        </button>
      ) : null}
      {showStop ? (
        <button type="button" className="cc-icon-btn cc-icon-btn--danger" onClick={() => onCancel?.()} title="Stop">
          <XIcon size={13} />
        </button>
      ) : null}
      {canSync ? (
        <button type="button" className="cc-icon-btn" onClick={() => onSync?.()} title="Sync workspace">
          <RefreshCw size={13} />
        </button>
      ) : null}
    </div>
  );
}

function Avatar({ logoOk, onLogoFail }) {
  return (
    <span className="cc-avatar" aria-hidden>
      {logoOk ? (
        <img src="/logo.png" alt="" onError={onLogoFail} className="cc-avatar-img" />
      ) : (
        <span className="cc-avatar-fallback">C</span>
      )}
    </span>
  );
}

function UserMessage({ item, pinned }) {
  return (
    <div className={`cc-row cc-row--user${pinned ? ' cc-row--pinned' : ''}`}>
      <div className="cc-user-text">{item.content}</div>
    </div>
  );
}

function AssistantMessage({ item, logoOk, onLogoFail }) {
  return (
    <div className="cc-row cc-row--assistant">
      <Avatar logoOk={logoOk} onLogoFail={onLogoFail} />
      <div className="cc-message-col">
        <div className="cc-name">CrucibAI</div>
        <div className="cc-assistant-text">{item.content}</div>
      </div>
    </div>
  );
}

function StatusPill({ status }) {
  const label =
    status === 'running' ? 'Running'
    : status === 'failed' ? 'Needs fix'
    : status === 'success' ? 'Done'
    : 'Queued';
  return <span className={`cc-tool-status cc-tool-status--${status || 'queued'}`}>{label}</span>;
}

function ToolIcon({ tool, status }) {
  if (status === 'running') return <Loader2 size={14} className="cc-spin" />;
  if (status === 'failed') return <AlertTriangle size={14} className="cc-bad" />;
  const t = String(tool || '').toLowerCase();
  if (/bash|terminal/.test(t)) return <SquareTerminal size={14} />;
  if (/edit|write|file/.test(t)) return <Edit3 size={14} />;
  if (/read/.test(t)) return <FileText size={14} />;
  if (/grep|glob|search/.test(t)) return <Search size={14} />;
  if (/todo|task/.test(t)) return <ListChecks size={14} />;
  if (/proof|check/.test(t)) return <ShieldCheck size={14} />;
  if (/fix/.test(t)) return <Wrench size={14} />;
  return <CircleDot size={14} />;
}

function ToolUseBlock({ item, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen || item.status === 'failed' || item.status === 'running');
  return (
    <div className={`cc-tool cc-tool--${item.status || 'queued'}`}>
      <button type="button" className="cc-tool-head" onClick={() => setOpen((v) => !v)}>
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        <ToolIcon tool={item.tool} status={item.status} />
        <span className="cc-tool-name">{item.tool}</span>
        <span className="cc-tool-title">{item.title}</span>
        <StatusPill status={item.status} />
      </button>
      {open ? (
        <div className="cc-tool-body">
          <ToolResult text={item.result} detail={item.detail} />
        </div>
      ) : null}
    </div>
  );
}

function ToolGroup({ item }) {
  const [open, setOpen] = useState(false);
  const tool = item.tool || 'Progress';
  return (
    <div className={`cc-tool cc-tool--${item.status || 'success'}`}>
      <button type="button" className="cc-tool-head" onClick={() => setOpen((v) => !v)}>
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        <ToolIcon tool={tool} status={item.status} />
        <span className="cc-tool-name">{tool}</span>
        <span className="cc-tool-title">{item.title}</span>
        <StatusPill status={item.status} />
      </button>
      {open ? (
        <div className="cc-tool-body cc-tool-body--stack">
          {item.children.map((child) => (
            <ToolUseBlock key={child.id} item={child} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

function TodoList({ item }) {
  return (
    <div className="cc-tool cc-tool--todo">
      <div className="cc-tool-head cc-tool-head--static">
        <ListChecks size={14} />
        <span className="cc-tool-name">{item.title}</span>
      </div>
      <ul className="cc-todo-list">
        {item.steps.map((step) => {
          const done = ['completed', 'success', 'done'].includes(String(step.status || '').toLowerCase());
          const running = ['running', 'in_progress', 'active'].includes(String(step.status || '').toLowerCase());
          return (
            <li key={step.id} className={`cc-todo-item${done ? ' cc-todo-item--done' : ''}${running ? ' cc-todo-item--running' : ''}`}>
              {done ? <CheckCircle2 size={13} /> : running ? <Loader2 size={13} className="cc-spin" /> : <CircleDot size={13} />}
              <span>{step.label}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function Checkpoint({ item }) {
  return (
    <div className={`cc-checkpoint cc-checkpoint--${item.tone || 'proof'}`}>
      <ShieldCheck size={15} />
      <div>
        <div className="cc-checkpoint-title">{item.title}</div>
        {item.body ? <div className="cc-checkpoint-body">{item.body}</div> : null}
      </div>
    </div>
  );
}

function Delivery({ item, context }) {
  return (
    <div className="cc-checkpoint cc-checkpoint--success">
      <CheckCircle2 size={15} />
      <div>
        <div className="cc-checkpoint-title">{item.title}</div>
        {item.body ? <div className="cc-checkpoint-body">{item.body}</div> : null}
        {context?.truthSurface ? (
          <div className="cc-proof-row">
            <span>contract: {context.truthSurface.prompt_contract_passed === false ? 'needs fix' : 'tracked'}</span>
            <span>preview: {context.previewUrl ? 'live URL' : context.truthSurface.preview_source || 'pending'}</span>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function ThinkingRow({ logoOk, onLogoFail }) {
  return (
    <div className="cc-row cc-row--assistant cc-row--thinking" aria-busy="true">
      <Avatar logoOk={logoOk} onLogoFail={onLogoFail} />
      <div className="cc-message-col">
        <div className="cc-thinking">
          <Loader2 size={14} className="cc-spin" />
          <span>Thinking</span>
        </div>
      </div>
    </div>
  );
}

function ThreadItem({ item, logoOk, onLogoFail, pinnedUserId, deliveryContext }) {
  switch (item.kind) {
    case 'user_message':
      return <UserMessage item={item} pinned={item.id === pinnedUserId} />;
    case 'assistant_message':
      return <AssistantMessage item={item} logoOk={logoOk} onLogoFail={onLogoFail} />;
    case 'tool_use':
      return <ToolUseBlock item={item} />;
    case 'tool_group':
      return <ToolGroup item={item} />;
    case 'todo_list':
      return <TodoList item={item} />;
    case 'checkpoint':
      return <Checkpoint item={item} />;
    case 'delivery':
      return <Delivery item={item} context={deliveryContext} />;
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
  token: _token = null,
  apiBase: _apiBase = '',
  onUseSuggestion: _onUseSuggestion,
  omitInlineBrandChrome: _omitInlineBrandChrome = false,
}) {
  const scrollRef = useRef(null);
  const userIsScrollingRef = useRef(false);
  const [logoFailed, setLogoFailed] = useState(false);

  const { items, scrollLayoutKey } = useMemo(() => {
    const list = buildThreadModel({ userMessages, events, activeJobId: jobId });
    const key = list.map((i) => `${i.kind}:${i.id}:${i.status || ''}`).join('|');
    return { items: list, scrollLayoutKey: key };
  }, [userMessages, events, jobId]);

  const firstUserId = useMemo(() => items.find((i) => i.kind === 'user_message')?.id ?? null, [items]);
  const shouldRenderEmptyState = items.length === 0 && !isTyping && !jobId && !hasTaskOrJobContext;

  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      console.info('[CRUCIBAI_TRANSCRIPT_ACTIVE] supplied-code transcript surface mounted', {
        activeJobId: jobId,
        renderedThreadItems: items.length,
      });
    } catch {
      /* browser console only */
    }
  }, [jobId, items.length]);

  useEffect(() => {
    if (userIsScrollingRef.current) return;
    const node = scrollRef.current;
    const scroller = node?.parentElement;
    if (!scroller) return;
    const distanceFromBottom = scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight;
    if (distanceFromBottom < 220) scroller.scrollTop = scroller.scrollHeight;
  }, [scrollLayoutKey, isTyping]);

  const handleScroll = () => {
    const node = scrollRef.current;
    const scroller = node?.parentElement;
    if (!scroller) return;
    const distanceFromBottom = scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight;
    userIsScrollingRef.current = distanceFromBottom > 220;
    onScroll?.({ isNearBottom: distanceFromBottom < 120 });
  };

  if (shouldRenderEmptyState) {
    return (
      <div className="cc-thread-empty">
        <div className="cc-empty-title">What should CrucibAI build?</div>
      </div>
    );
  }

  return (
    <div ref={scrollRef} onScrollCapture={handleScroll} className="cc-thread">
      <div className="cc-thread-topbar">
        {(buildTargetMeta || buildTargetId) ? <BuildTargetChip meta={buildTargetMeta} id={buildTargetId} /> : <span />}
        <RunControls
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
          pinnedUserId={firstUserId}
          deliveryContext={{
            previewUrl,
            truthSurface: proofTruthSurface,
          }}
        />
      ))}

      {isTyping ? <ThinkingRow logoOk={!logoFailed} onLogoFail={() => setLogoFailed(true)} /> : null}
    </div>
  );
}

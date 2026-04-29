/**
 * BrainGuidancePanel  Thread-Only Component
 * 
 * Renders ONLY the conversation/execution thread.
 * NO composer. NO input. NO send button.
 * 
 * The composer is a separate component at the bottom of the workspace.
 * This component receives messages via props and renders them.
 */

import React, { useEffect, useRef, useCallback, useMemo } from 'react';
import { Terminal, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import './BrainGuidancePanel.css';

const prettyList = (value) => {
  if (!Array.isArray(value) || value.length === 0) return '';
  return value.map((v) => `- ${String(v)}`).join('\n');
};

const normalizeEvent = (event, idx) => {
  const type = event.type || '';
  const payload = event.payload || {};
  const failed = /failed|error|blocked/i.test(type);
  const running = /started|running|progress|in_progress/i.test(type);
  const status = failed ? 'failed' : running ? 'running' : 'success';
  const phase = payload.phase || payload.step || payload.step_key || '';
  const agent = payload.agent || payload.agent_name || payload.tool || '';

  let title = '';
  let summary = '';

  switch (type) {
    case 'plan_created':
      title = 'Plan created';
      summary = payload.summary || 'Build plan drafted.';
      break;
    case 'phase_started':
      title = `Phase started: ${phase || 'unknown'}`;
      summary = payload.message || 'Execution in progress.';
      break;
    case 'phase_completed':
      title = `Phase completed: ${phase || 'unknown'}`;
      summary = payload.message || 'Completed successfully.';
      break;
    case 'verifier_failed':
    case 'assembly_failed':
    case 'export_gate_blocked':
    case 'error': {
      const missing = payload.missing_routes || payload.missing || payload.missing_items || [];
      title = `Verification failed at ${phase || type}`;
      summary = payload.summary || payload.message || payload.error || 'Verification did not pass.';
      if (missing.length) summary = `${summary}\n${prettyList(missing)}`;
      break;
    }
    case 'repair_started':
      title = `Repair started${agent ? `: ${agent}` : ''}`;
      summary = payload.issue || payload.message || 'Starting repair.';
      break;
    case 'repair_completed':
      title = `Repair completed${agent ? `: ${agent}` : ''}`;
      summary = payload.message || 'Repair succeeded and execution continues.';
      break;
    case 'repair_failed':
      title = `Repair failed${agent ? `: ${agent}` : ''}`;
      summary = payload.message || payload.error || 'Repair attempt failed.';
      break;
    case 'tool_call':
      title = `Tool call: ${agent || 'tool'}`;
      summary = payload.command || payload.message || 'Running tool call.';
      break;
    case 'tool_result':
      title = `Tool result: ${agent || 'tool'}`;
      summary = payload.output || payload.message || 'Tool returned.';
      break;
    case 'run_snapshot':
      title = 'Runtime snapshot captured';
      summary = payload.status || payload.message || 'Runtime evidence updated.';
      break;
    case 'code_mutation':
      title = 'Code mutation applied';
      summary = payload.file || payload.path || payload.message || 'Files updated.';
      break;
    case 'export_gate_ready':
      title = 'Export gate ready';
      summary = payload.message || 'All required checks passed.';
      break;
    default:
      title = type || `event_${idx}`;
      summary = payload.message || payload.summary || '';
      break;
  }

  return {
    id: event.id || `ev_${idx}_${event.created_at || Date.now()}`,
    type,
    role: 'assistant',
    title,
    summary: summary || null,
    phase,
    agent,
    status,
    timestamp: event.created_at ? new Date(event.created_at).getTime() : Date.now(),
    payload,
    raw: event,
  };
};

export default function BrainGuidancePanel({
  userMessages = [], // Array of {id, body, role, ts}
  events = [], // backend job events
  jobStatus,
  isTyping,
  onScroll,
}) {
  const scrollRef = useRef(null);
  const [expanded, setExpanded] = React.useState(new Set());
  const [logoFailed, setLogoFailed] = React.useState(false);
  const threadMessages = useMemo(() => {
    const fromUser = (userMessages || [])
      .filter((m) => (m?.body || '').trim().length > 0)
      .map((m) => ({
        id: m.id || `user_${m.ts || Date.now()}`,
        role: m.role === 'assistant' ? 'assistant' : 'user',
        content: String(m.body || '').trim(),
        ts: m.ts || Date.now(),
      }));

    const fromEvents = (events || [])
      .filter((ev) => ev && ev.type !== 'user_instruction')
      .map((ev, idx) => {
        const n = normalizeEvent(ev, idx);
        return {
          id: n.id,
          role: 'assistant',
          content: n.summary || n.title,
          event: ev,
          normalized: n,
          status: n.status,
          ts: n.timestamp,
        };
      })
      .filter(Boolean);

    return [...fromUser, ...fromEvents].sort((a, b) => (a.ts || 0) - (b.ts || 0));
  }, [userMessages, events]);

  // Auto-scroll to bottom
  const handleScroll = useCallback(() => {
    const container = scrollRef.current;
    if (!container) return;
    const { scrollTop, scrollHeight, clientHeight } = container;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
    onScroll?.({ isNearBottom });
  }, [onScroll]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [threadMessages, isTyping]);

  const toggleExpand = (id) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // Empty state - minimal, no input
  if (threadMessages.length === 0 && !isTyping) {
    return (
      <div className="bgp-thread-empty">
        <div className="bgp-empty-inner">
          <p className="bgp-empty-text">Start by describing what you want in the composer below.</p>
        </div>
      </div>
    );
  }

  return (
    <div 
      ref={scrollRef}
      onScroll={handleScroll}
      className="bgp-thread-only"
    >
      {threadMessages.map((msg) => {
        const isUser = msg.role === 'user';
        const isExpanded = expanded.has(msg.id);
        const actionLabel = msg.normalized?.agent || msg.normalized?.phase || null;
        
        return (
          <div key={msg.id} className={`bgp-msg ${isUser ? 'bgp-msg-user' : 'bgp-msg-assistant'}`}>
            {/* Avatar */}
            <div className="bgp-avatar">
              {isUser ? (
                <span className="bgp-avatar-text">You</span>
              ) : (
                !logoFailed ? (
                  <img
                    src="/logo.png"
                    alt=""
                    aria-hidden
                    className="bgp-avatar-logo"
                    onError={() => setLogoFailed(true)}
                  />
                ) : (
                  <span className="bgp-avatar-fallback">C</span>
                )
              )}
            </div>

            {/* Content */}
            <div className="bgp-msg-body">
              {/* Main text */}
              {msg.normalized?.title && (
                <div className="bgp-msg-text" style={{ fontWeight: 600 }}>{msg.normalized.title}</div>
              )}

              {msg.content && (
                <div className="bgp-msg-text">{msg.content}</div>
              )}

              {/* Action pill */}
              {actionLabel && (
                <div className="bgp-action">
                  <Terminal size={12} />
                  <span>{actionLabel}</span>
                  {msg.status === 'running' && <Loader2 size={12} className="bgp-spin" />}
                </div>
              )}

              {/* Tool details - collapsed by default */}
              {msg.event?.payload?.command && (
                <div className="bgp-tool">
                  <button 
                    className="bgp-tool-toggle"
                    onClick={() => toggleExpand(msg.id)}
                  >
                    {isExpanded ? 'Hide' : 'Details'}
                  </button>
                  {isExpanded && (
                    <div className="bgp-tool-code">
                      <code>$ {msg.event.payload.command}</code>
                      {msg.event.payload.output && (
                        <pre>{msg.event.payload.output}</pre>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Repair status */}
              {msg.event?.type?.includes('repair') && (
                <div className={`bgp-repair ${msg.event.type.includes('completed') ? 'success' : ''}`}>
                  {msg.event.type.includes('completed') ? (
                    <><CheckCircle size={14} /> Fixed</>
                  ) : (
                    <><AlertCircle size={14} /> Repairing...</>
                  )}
                </div>
              )}
            </div>
          </div>
        );
      })}

      {/* Typing indicator */}
      {isTyping && (
        <div className="bgp-msg bgp-msg-assistant bgp-typing">
          <div className="bgp-avatar">
            {!logoFailed ? (
              <img
                src="/logo.png"
                alt=""
                aria-hidden
                className="bgp-avatar-logo"
                onError={() => setLogoFailed(true)}
              />
            ) : (
              <span className="bgp-avatar-fallback">C</span>
            )}
          </div>
          <div className="bgp-msg-body">
            <div className="bgp-dots"><span /><span /><span /></div>
          </div>
        </div>
      )}
    </div>
  );
}

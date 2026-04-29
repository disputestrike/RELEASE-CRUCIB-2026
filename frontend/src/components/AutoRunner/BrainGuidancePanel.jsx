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

// Human-readable narration for events
const getNarration = (event) => {
  const type = event.type || '';
  const payload = event.payload || {};
  
  if (type === 'user_instruction') return null; // User messages shown separately
  if (type.includes('plan_created')) return 'Planning your build...';
  if (type.includes('thinking')) return payload.message || 'Thinking...';
  if (type.includes('tool_call')) return `Running ${payload.tool || 'tool'}...`;
  if (type.includes('repair_started')) return `Found issue: ${payload.issue || 'repair needed'}. Fixing...`;
  if (type.includes('repair_completed')) return 'Issue fixed. Continuing...';
  if (type.includes('phase_started')) return `Starting ${payload.phase || 'phase'}...`;
  if (type.includes('phase_completed')) return `${payload.phase || 'Phase'} complete.`;
  if (type.includes('export_gate_ready')) return 'Build verified. Ready to export.';
  if (type.includes('image')) return `Generating ${payload.target || 'image'}...`;
  
  return payload.message || null;
};

// Get compact action label
const getActionLabel = (event) => {
  const type = event.type || '';
  const payload = event.payload || {};
  
  if (type.includes('tool_call')) return payload.tool;
  if (type.includes('file_write')) return payload.file || 'Write file';
  if (type.includes('repair')) return 'Repair';
  if (type.includes('verifier')) return 'Verify';
  if (type.includes('image')) return 'Image';
  
  return null;
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
        const content = getNarration(ev);
        if (!content) return null;
        return {
          id: ev.id || `ev_${idx}_${ev.created_at || Date.now()}`,
          role: 'assistant',
          content,
          event: ev,
          status: ev.status || 'completed',
          ts: ev.created_at ? new Date(ev.created_at).getTime() : Date.now(),
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
        const actionLabel = msg.event ? getActionLabel(msg.event) : null;
        
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

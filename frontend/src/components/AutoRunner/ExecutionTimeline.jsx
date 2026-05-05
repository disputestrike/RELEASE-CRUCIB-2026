/**
 * ExecutionTimeline — real-time step-by-step build view.
 * SVG/CSS status icons, filter tabs, expandable inline logs + deep detail.
 * Props: steps, events, job, onRetryStep, onJumpToCode, isConnected
 */
import React, { useState, useEffect, useMemo, useRef } from 'react';
import { RefreshCw, Code2, ChevronDown, ChevronRight } from 'lucide-react';
import './ExecutionTimeline.css';

const FILTERS = ['All', 'Active', 'Errors', 'Retries'];

const TOOL_RUNTIME_EVENTS = new Set([
  'runtime_backend_selected',
  'pipeline_dispatch',
  'pipeline_started',
  'runtime_steps_cleared',
  'runtime_resume_prepared',
  'plan_created',
  'tool_call',
  'tool_result',
  'file_written',
  'code_mutation',
  'verifier_started',
  'verifier_passed',
  'verifier_failed',
  'repair_started',
  'repair_completed',
  'repair_failed',
  'job_completed',
  'job_failed',
]);

const payloadOf = (event) => {
  if (event?.payload && typeof event.payload === 'object') return event.payload;
  try {
    return JSON.parse(event?.payload_json || '{}');
  } catch {
    return {};
  }
};

const typeOf = (event) => event?.type || event?.event_type || '';

const isToolRuntimeEvent = (event) => {
  const payload = payloadOf(event);
  return TOOL_RUNTIME_EVENTS.has(typeOf(event)) || payload.engine === 'single_tool_runtime';
};

const isLegacyAgentStep = (step) => {
  const key = String(step?.step_key || '').toLowerCase();
  const agent = String(step?.agent_name || '').toLowerCase();
  const phase = String(step?.phase || '').toLowerCase();
  return key.startsWith('agents.') || agent.startsWith('agents.') || phase === 'orchestration';
};

const compact = (value, max = 220) => {
  const text = String(value || '').replace(/\s+/g, ' ').trim();
  if (text.length <= max) return text;
  return `${text.slice(0, max - 1)}...`;
};

const titleCase = (value) =>
  String(value || '')
    .replace(/[._-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());

const eventStatus = (type, payload) => {
  if (type === 'tool_result' && payload.success === false) return 'failed';
  if (/failed|error|blocked/i.test(type)) return 'failed';
  if (/started|call|dispatch/i.test(type)) return 'running';
  return 'completed';
};

const eventTitle = (type, payload) => {
  if (type === 'plan_created') return 'Build plan ready';
  if (type === 'pipeline_started') return 'Runtime started';
  if (type === 'runtime_backend_selected') return 'Runtime selected';
  if (type === 'runtime_steps_cleared') return 'Runtime rows refreshed';
  if (type === 'runtime_resume_prepared') return 'Runtime resumed';
  if (type === 'tool_call') return `${payload.title || payload.label || payload.tool || payload.name || 'Working'} ${compact(payload.input || payload.command || payload.path, 80)}`.trim();
  if (type === 'tool_result') return `${payload.title || payload.label || payload.tool || payload.name || 'Work'} complete`;
  if (type === 'file_written') return `Saved ${String(payload.path || 'file').split('/').pop()}`;
  if (type === 'code_mutation') return `Updated ${String(payload.path || 'file').split('/').pop()}`;
  if (type === 'verifier_started') return payload.title || 'Run proof checks';
  if (type === 'verifier_passed') return 'Proof checks passed';
  if (type === 'verifier_failed') return 'Proof check failed';
  if (type === 'repair_started') return 'Fix pass started';
  if (type === 'repair_completed') return 'Fix pass completed';
  if (type === 'job_completed') return 'Workspace ready';
  if (type === 'job_failed') return 'Proof failed - checking error';
  return titleCase(type) || 'Runtime event';
};

const buildToolRuntimeRows = (events) =>
  (events || [])
    .filter(isToolRuntimeEvent)
    .map((event, index) => {
      const payload = payloadOf(event);
      const type = typeOf(event);
      const status = eventStatus(type, payload);
      const input = payload.input || payload.command || payload.path || payload.pattern || '';
      const output =
        payload.output ||
        payload.summary ||
        payload.message ||
        payload.failure_reason ||
        payload.stderr ||
        '';
      return {
        id: event.id || `${type}-${index}`,
        is_event: true,
        status,
        step_key: eventTitle(type, payload),
        agent_name: payload.category || payload.tool || payload.name || payload.tool_name || 'Runtime',
        phase: 'runtime',
        input,
        output: compact(output, 1400),
        result_json: payload,
        created_at: (() => {
          const ts = event.created_at || event.ts || event.timestamp;
          return typeof ts === 'number' && ts < 1e12 ? ts * 1000 : ts;
        })(),
        order_index: index,
      };
    });

function StatusIcon({ status }) {
  switch (status) {
    case 'pending':
      return <span className="et-icon et-icon-pending" />;
    case 'running':
      return <span className="et-icon et-icon-running animate-spin" />;
    case 'verifying':
      return <span className="et-icon et-icon-verifying animate-pulse-ring" />;
    case 'retrying':
      return <span className="et-icon et-icon-retrying animate-spin" />;
    case 'completed':
      return (
        <span className="et-icon et-icon-completed">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <circle cx="6" cy="6" r="5.5" fill="var(--state-success)" />
            <path d="M3.5 6L5.5 8L8.5 4" stroke="var(--bg-0)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
      );
    case 'failed':
      return (
        <span className="et-icon et-icon-failed">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <circle cx="6" cy="6" r="5.5" fill="var(--state-error)" />
            <path d="M4 4L8 8M8 4L4 8" stroke="var(--bg-0)" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </span>
      );
    case 'blocked':
      return (
        <span className="et-icon et-icon-blocked">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <rect x="3" y="3" width="2" height="6" rx="0.5" fill="var(--text-muted)" />
            <rect x="7" y="3" width="2" height="6" rx="0.5" fill="var(--text-muted)" />
          </svg>
        </span>
      );
    default:
      return <span className="et-icon et-icon-pending" />;
  }
}

export default function ExecutionTimeline({
  steps = [],
  events = [],
  job,
  onRetryStep,
  onJumpToCode,
  connectionMode = 'offline',
}) {
  const [filter, setFilter] = useState('All');
  const [expandedSteps, setExpandedSteps] = useState(new Set());
  const [userScrolled, setUserScrolled] = useState(false);
  const scrollRef = useRef(null);
  const bottomRef = useRef(null);
  const toolRuntimeActive = useMemo(() => events.some(isToolRuntimeEvent), [events]);
  const timelineRows = useMemo(
    () => (toolRuntimeActive ? buildToolRuntimeRows(events) : steps.filter((step) => !isLegacyAgentStep(step))),
    [toolRuntimeActive, events, steps],
  );

  // Auto-expand every in-flight step (parallel batches can have multiple running)
  useEffect(() => {
    const runningIds = timelineRows.filter(s => s.status === 'running').map(s => s.id);
    if (!runningIds.length) return;
    setExpandedSteps(prev => {
      const next = new Set(prev);
      runningIds.forEach(id => next.add(id));
      return next;
    });
  }, [timelineRows]);

  useEffect(() => {
    if (!userScrolled) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [events.length, userScrolled]);

  const handleScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    setUserScrolled(!atBottom);
  };

  const toggleExpanded = (stepId) => {
    setExpandedSteps(prev => {
      const next = new Set(prev);
      if (next.has(stepId)) next.delete(stepId);
      else next.add(stepId);
      return next;
    });
  };

  const currentPhase = toolRuntimeActive ? 'Runtime proof flow' : (job?.current_phase || 'planning');

  const filteredSteps = timelineRows.filter(s => {
    switch (filter) {
      case 'Active': return ['running', 'verifying'].includes(s.status);
      case 'Errors': return ['failed', 'blocked'].includes(s.status);
      case 'Retries': return (s.retry_count || 0) > 0;
      default: return true;
    }
  });

  const completedCount = timelineRows.filter(s => s.status === 'completed').length;
  const totalCount = timelineRows.length;

  const getStepLogs = (stepId) =>
    events
      .filter(e => e.step_id === stepId || e.payload?.step_id === stepId)
      .filter(e =>
        [
          'step_log',
          'step_started',
          'step_completed',
          'step_failed',
          'dag_node_started',
          'dag_node_completed',
          'dag_node_failed',
        ].includes(e.type || e.event_type),
      )
      .slice(-12);

  const connectionLabel =
    connectionMode === 'stream' ? 'Live' : connectionMode === 'polling' ? 'Polling' : 'Disconnected';

  return (
    <div className="execution-timeline">
      <div className="et-header">
        <div className="et-title-row">
          <span className="et-title">Execution Timeline</span>
          <span className={`et-conn ${connectionMode === 'offline' ? 'offline' : 'live'}`}>
            <span className="et-conn-dot" />
            {connectionLabel}
          </span>
        </div>
        <div className="et-progress-row">
          <span className="et-phase-label">Phase: <strong>{currentPhase}</strong></span>
          <span className="et-step-count">{completedCount} / {totalCount} steps</span>
        </div>
        <div className="et-progress-bar">
          <div
            className="et-progress-fill"
            style={{ width: `${totalCount ? (completedCount / totalCount) * 100 : 0}%` }}
          />
        </div>
      </div>

      {/* Filters */}
      <div className="et-filters">
        {FILTERS.map(f => (
          <button
            key={f}
            className={`et-filter-btn ${filter === f ? 'active' : ''}`}
            onClick={() => setFilter(f)}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Steps */}
      <div className="et-steps" ref={scrollRef} onScroll={handleScroll}>
        {filteredSteps.length === 0 ? (
          <div className="et-empty">
            {timelineRows.length === 0
              ? 'Waiting for build activity.'
              : 'No events match the current filter.'}
          </div>
        ) : (
          filteredSteps.map(step => {
            const logs = getStepLogs(step.id);
            const isDetailExpanded = expandedSteps.has(step.id);
            const isFailed = ['failed', 'blocked'].includes(step.status);
            const timestamp = step.started_at || step.created_at;
            return (
              <div
                key={step.id}
                className={`et-step et-step-${step.status}`}
              >
                <div className="et-step-row" onClick={() => toggleExpanded(step.id)}>
                  <button className="et-chevron-btn" onClick={(e) => { e.stopPropagation(); toggleExpanded(step.id); }}>
                    {isDetailExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                  </button>
                  <StatusIcon status={step.status} />
                  <div className="et-step-info">
                    <span className="et-step-name">{step.step_key}</span>
                    {step.agent_name && (
                      <span className="et-agent-badge">{step.agent_name}</span>
                    )}
                  </div>
                  <div className="et-step-right">
                    {step.narrative && (
                      <span className="et-narrative">{step.narrative}</span>
                    )}
                    {step.retry_count > 0 && (
                      <span className="et-retry-badge">retry {step.retry_count}</span>
                    )}
                    {timestamp && (
                      <span className="et-timestamp">
                        {new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    )}
                  </div>
                </div>

                {/* Expanded detail */}
                {isDetailExpanded && (
                  <div className="tl-expanded">
                    {(step.input || step.result_json?.input) && (
                      <div className="tl-block">
                        <span className="tl-block-label">Input</span>
                        <pre className="tl-mono">{step.input || step.result_json?.input}</pre>
                      </div>
                    )}
                    <div className="tl-block">
                      <span className="tl-block-label success">Output</span>
                      <pre className="tl-mono">
                        {step.output ||
                          step.result_json?.output ||
                          step.narrative ||
                          (step.status === 'completed' ? '—' : 'Pending…')}
                      </pre>
                    </div>
                    {step.decision && (
                      <div className="tl-block">
                        <span className="tl-block-label">Decision</span>
                        <p className="tl-decision">{step.decision}</p>
                      </div>
                    )}
                    {(step.tokens_used != null || step.result_json?.tokens_used != null) && (
                      <div className="tl-tokens">
                        {step.tokens_used ?? step.result_json?.tokens_used} tokens used
                      </div>
                    )}

                    {/* Inline logs */}
                    {logs.length > 0 && (
                      <div className="et-logs">
                        {logs.map((ev, i) => (
                          <div key={i} className="et-log-line">
                            <span className="et-log-type">{ev.type || ev.event_type}</span>
                            <span className="et-log-msg et-log-msg-json">
                              {JSON.stringify(ev.payload || {}, null, 0).slice(0, 420)}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Actions for failed steps */}
                {isFailed && !step.is_event && (
                  <div className="et-step-actions">
                    <button
                      className="et-action-btn"
                      onClick={e => { e.stopPropagation(); onRetryStep?.(step); }}
                    >
                      <RefreshCw size={11} /> Retry Step
                    </button>
                    <button
                      className="et-action-btn"
                      onClick={e => { e.stopPropagation(); onJumpToCode?.(step); }}
                    >
                      <Code2 size={11} /> Jump to Code
                    </button>
                  </div>
                )}
              </div>
            );
          })
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

/**
 * ExecutionTimeline — real-time step-by-step build view.
 * Shows live events from SSE stream grouped by phase.
 * Props: steps, events, job, onRetryStep, onJumpToCode, isConnected
 */
import React, { useState, useEffect, useRef } from 'react';
import { RefreshCw, Code2, Filter, CheckCircle2, XCircle, Clock, Loader2 } from 'lucide-react';
import './ExecutionTimeline.css';

const STATUS_ICONS = {
  pending:    <Clock size={13} className="et-icon et-icon-pending" />,
  running:    <Loader2 size={13} className="et-icon et-icon-running et-spin" />,
  verifying:  <Loader2 size={13} className="et-icon et-icon-verifying et-spin" />,
  retrying:   <RefreshCw size={13} className="et-icon et-icon-retrying et-spin" />,
  completed:  <CheckCircle2 size={13} className="et-icon et-icon-done" />,
  failed:     <XCircle size={13} className="et-icon et-icon-fail" />,
  blocked:    <XCircle size={13} className="et-icon et-icon-blocked" />,
  skipped:    <Clock size={13} className="et-icon et-icon-skip" />,
};

const FILTERS = ['all', 'errors', 'current phase', 'agent only'];

export default function ExecutionTimeline({
  steps = [],
  events = [],
  job,
  onRetryStep,
  onJumpToCode,
  isConnected,
}) {
  const [filter, setFilter] = useState('all');
  const [expandedStep, setExpandedStep] = useState(null);
  const bottomRef = useRef(null);

  // Auto-scroll to bottom on new events
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events.length]);

  const currentPhase = job?.current_phase || 'planning';

  const filteredSteps = steps.filter(s => {
    if (filter === 'errors') return ['failed', 'blocked'].includes(s.status);
    if (filter === 'current phase') return s.phase === currentPhase;
    if (filter === 'agent only') return !['verification', 'deploy'].includes(s.phase);
    return true;
  });

  const completedCount = steps.filter(s => s.status === 'completed').length;
  const totalCount = steps.length;

  // Recent logs from events (step_log type)
  const getStepLogs = (stepId) =>
    events
      .filter(e => e.step_id === stepId || e.payload?.step_id === stepId)
      .filter(e => ['step_log', 'step_started', 'step_completed', 'step_failed'].includes(e.type || e.event_type))
      .slice(-5);

  return (
    <div className="execution-timeline">
      <div className="et-header">
        <div className="et-title-row">
          <span className="et-title">Execution Timeline</span>
          <span className={`et-conn ${isConnected ? 'et-conn-live' : 'et-conn-offline'}`}>
            {isConnected ? '● live' : '○ reconnecting'}
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
      <div className="et-steps">
        {filteredSteps.length === 0 ? (
          <div className="et-empty">
            {steps.length === 0 ? 'Waiting for plan to start...' : 'No steps match filter'}
          </div>
        ) : (
          filteredSteps.map(step => {
            const logs = getStepLogs(step.id);
            const isExpanded = expandedStep === step.id;
            const isFailed = ['failed', 'blocked'].includes(step.status);

            return (
              <div
                key={step.id}
                className={`et-step et-step-${step.status}`}
                onClick={() => setExpandedStep(isExpanded ? null : step.id)}
              >
                <div className="et-step-row">
                  {STATUS_ICONS[step.status] || STATUS_ICONS.pending}
                  <div className="et-step-info">
                    <span className="et-step-name">{step.agent_name}</span>
                    <span className="et-step-key">{step.step_key}</span>
                  </div>
                  <div className="et-step-right">
                    {step.verifier_score > 0 && (
                      <span className="et-score">{step.verifier_score}</span>
                    )}
                    {step.retry_count > 0 && (
                      <span className="et-retry-badge">retry {step.retry_count}</span>
                    )}
                  </div>
                </div>

                {/* Inline logs */}
                {isExpanded && logs.length > 0 && (
                  <div className="et-logs">
                    {logs.map((ev, i) => (
                      <div key={i} className="et-log-line">
                        <span className="et-log-type">{ev.type || ev.event_type}</span>
                        <span className="et-log-msg">
                          {JSON.stringify(ev.payload || {}).slice(0, 120)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Action buttons for failed steps */}
                {isFailed && (
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

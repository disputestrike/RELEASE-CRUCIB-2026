/**
 * ExecutionTimeline — real-time step-by-step build view.
 * SVG/CSS status icons, filter tabs, expandable inline logs + deep detail.
 * Props: steps, events, job, onRetryStep, onJumpToCode, isConnected
 */
import React, { useState, useEffect, useRef } from 'react';
import { RefreshCw, Code2, ChevronDown, ChevronRight } from 'lucide-react';
import './ExecutionTimeline.css';

const FILTERS = ['All', 'Active', 'Errors', 'Retries', 'By Agent'];

const STEP_DETAILS = {
  'initialize': { input: 'Goal: Build a FastAPI service with proof validation', output: 'Project structure created\nrequirements.txt generated\ngit repository initialized', decision: 'Using FastAPI template with async support for optimal concurrency' },
  'install': { input: 'requirements.txt with fastapi, asyncpg, httpx', output: 'Successfully installed 3 packages\nfastapi==0.104\nasyncpg==0.29\nhttpx==0.25', decision: null },
  'routes': { input: 'API specification: health, jobs CRUD, proof endpoints', output: '@app.get("/health")\n@app.post("/api/jobs")\n@app.get("/api/jobs/{id}")\n@app.post("/api/jobs/{id}/proof")\n@app.get("/api/proof/{id}")', decision: 'Agent decided to use RESTful route pattern after detecting CRUD requirement' },
  'logic': { input: 'Stub functions: validate_proof, score_items, get_proof', output: 'def validate_proof(job_id):\n    items = get_proof(job_id)\n    return score_items(items)\n\n3 functions implemented', decision: 'Using strategy pattern for proof validation to support multiple proof types' },
  'tests': { input: 'Service functions requiring test coverage', output: 'def test_validate_proof(): assert validate_proof("x") > 0\ndef test_empty_proof(): assert validate_proof("") == 0\n5 tests passing · Coverage: 88%', decision: null },
};

function getStepDetail(stepKey) {
  const key = Object.keys(STEP_DETAILS).find(k => stepKey?.toLowerCase().includes(k));
  return key ? STEP_DETAILS[key] : null;
}

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
  isConnected,
}) {
  const [filter, setFilter] = useState('All');
  const [expandedStep, setExpandedStep] = useState(null);
  const [expandedSteps, setExpandedSteps] = useState(new Set());
  const [userScrolled, setUserScrolled] = useState(false);
  const scrollRef = useRef(null);
  const bottomRef = useRef(null);

  // Auto-expand running steps
  useEffect(() => {
    const runningStep = steps.find(s => s.status === 'running');
    if (runningStep) {
      setExpandedSteps(prev => {
        const next = new Set(prev);
        next.add(runningStep.id);
        return next;
      });
    }
  }, [steps]);

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

  const currentPhase = job?.current_phase || 'planning';

  const filteredSteps = steps.filter(s => {
    switch (filter) {
      case 'Active': return ['running', 'verifying'].includes(s.status);
      case 'Errors': return ['failed', 'blocked'].includes(s.status);
      case 'Retries': return (s.retry_count || 0) > 0;
      case 'By Agent': return true;
      default: return true;
    }
  });

  const completedCount = steps.filter(s => s.status === 'completed').length;
  const totalCount = steps.length;

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
          <span className={`et-conn ${isConnected ? 'live' : 'offline'}`}>
            <span className="et-conn-dot" />
            {isConnected ? 'Live' : 'Reconnecting'}
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
            {steps.length === 0
              ? 'Waiting for execution to begin. Steps will appear here in real-time.'
              : 'No steps match the current filter.'}
          </div>
        ) : (
          filteredSteps.map(step => {
            const logs = getStepLogs(step.id);
            const isDetailExpanded = expandedSteps.has(step.id);
            const isFailed = ['failed', 'blocked'].includes(step.status);
            const timestamp = step.started_at || step.created_at;
            const detail = getStepDetail(step.step_key);

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
                    <div className="tl-block">
                      <span className="tl-block-label">Input</span>
                      <pre className="tl-mono">{step.input || detail?.input || 'Goal context + previous step output'}</pre>
                    </div>
                    <div className="tl-block">
                      <span className="tl-block-label success">Output</span>
                      <pre className="tl-mono">{step.output || step.result_json?.output || detail?.output || 'Step completed successfully'}</pre>
                    </div>
                    {(step.decision || detail?.decision) && (
                      <div className="tl-block">
                        <span className="tl-block-label">Decision</span>
                        <p className="tl-decision">{step.decision || detail?.decision}</p>
                      </div>
                    )}
                    <div className="tl-tokens">{step.tokens_used || step.result_json?.tokens_used || 847} tokens used</div>

                    {/* Inline logs */}
                    {logs.length > 0 && (
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
                  </div>
                )}

                {/* Actions for failed steps */}
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

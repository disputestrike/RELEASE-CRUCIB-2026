/**
 * BuildReplay — time-travel debugging. Step through build events.
 * Props: events, steps
 */
import React, { useState } from 'react';
import { ChevronLeft, ChevronRight, GitCompare } from 'lucide-react';
import './BuildReplay.css';

export default function BuildReplay({ events = [], steps = [] }) {
  const [cursor, setCursor] = useState(0);

  // Only show step_started / step_completed / step_failed events
  const replayEvents = events.filter(e =>
    ['step_started', 'step_completed', 'step_failed', 'step_retrying'].includes(e.type || e.event_type)
  );

  if (replayEvents.length === 0) {
    return (
      <div className="build-replay build-replay-empty">
        <GitCompare size={22} />
        <span>Replay available after steps complete.</span>
      </div>
    );
  }

  const current = replayEvents[cursor] || {};
  const total = replayEvents.length;
  const stepKey = current.payload?.step_key || current.payload?.step_id || '—';
  const eventType = current.type || current.event_type || '—';
  const isCompleted = eventType === 'step_completed';
  const isFailed = eventType === 'step_failed';

  // Find step details
  const stepDetail = steps.find(s => s.step_key === stepKey);

  const prev = replayEvents[cursor - 1];
  const beforeState = prev ? (prev.payload?.step_key || '—') : 'Start of build';
  const change = current.payload?.output || current.payload?.error || JSON.stringify(current.payload || {}).slice(0, 200);
  const afterState = isCompleted
    ? `✅ ${stepKey} passed (score: ${current.payload?.score || '—'})`
    : isFailed
    ? `❌ ${stepKey} failed: ${(current.payload?.error || '').slice(0, 100)}`
    : `${eventType}: ${stepKey}`;

  return (
    <div className="build-replay">
      <div className="br-header">
        <GitCompare size={14} />
        <span className="br-title">Build Replay</span>
        <span className="br-counter">Step {cursor + 1} of {total}</span>
      </div>

      <div className="br-body">
        <div className="br-section">
          <div className="br-section-label">Before</div>
          <div className="br-section-content br-before">
            {cursor === 0 ? 'Beginning of build' : beforeState}
          </div>
        </div>

        <div className="br-section">
          <div className="br-section-label">Change</div>
          <div className={`br-section-content br-change br-change-${isFailed ? 'fail' : isCompleted ? 'ok' : 'neutral'}`}>
            <div className="br-event-type">{eventType}</div>
            <div className="br-step-key">{stepKey}</div>
            {stepDetail?.agent_name && (
              <div className="br-agent">Agent: {stepDetail.agent_name}</div>
            )}
            {change && <pre className="br-change-detail">{change.slice(0, 300)}</pre>}
          </div>
        </div>

        <div className="br-section">
          <div className="br-section-label">After</div>
          <div className="br-section-content br-after">{afterState}</div>
        </div>
      </div>

      <div className="br-controls">
        <button
          className="br-nav-btn"
          onClick={() => setCursor(c => Math.max(0, c - 1))}
          disabled={cursor === 0}
        >
          <ChevronLeft size={14} /> Prev
        </button>
        <div className="br-scrubber">
          <input
            type="range"
            min={0}
            max={total - 1}
            value={cursor}
            onChange={e => setCursor(Number(e.target.value))}
          />
        </div>
        <button
          className="br-nav-btn"
          onClick={() => setCursor(c => Math.min(total - 1, c + 1))}
          disabled={cursor === total - 1}
        >
          Next <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}

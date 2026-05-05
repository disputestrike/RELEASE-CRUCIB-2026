/**
 * BuildReplay — real job replay from persisted runtime events.
 * Three-column: Before | Change | After.
 */
import React, { useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight, GitCompare, Copy } from 'lucide-react';
import './BuildReplay.css';

function payloadOf(event) {
  if (event?.payload && typeof event.payload === 'object') return event.payload;
  if (typeof event?.payload === 'string' && event.payload.trim()) {
    try {
      const parsed = JSON.parse(event.payload);
      return parsed && typeof parsed === 'object' ? parsed : {};
    } catch {
      return {};
    }
  }
  try {
    const parsed = JSON.parse(event?.payload_json || '{}');
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function typeOf(event) {
  return event?.type || event?.event_type || '';
}

function shortPath(path) {
  const s = String(path || '').trim();
  return s.split('/').pop() || s || 'workspace';
}

function compact(value, max = 420) {
  const s = String(value || '').replace(/\r\n/g, '\n').trim();
  if (s.length <= max) return s;
  return `${s.slice(0, max - 14)}\n[truncated]`;
}

function eventToReplayStep(event, index) {
  const type = typeOf(event);
  const payload = payloadOf(event);
  const path = payload.path || payload.file || payload.file_path || payload.target || '';
  const file = shortPath(path);

  if (type === 'plan_created') {
    const steps = payload.steps || payload.plan_steps || payload.checklist || [];
    const lines = Array.isArray(steps)
      ? steps.map((step) => `+ ${typeof step === 'string' ? step : step?.label || step?.title || step?.name || 'Planned task'}`)
      : [];
    return {
      name: 'Build plan',
      before: 'User goal received',
      change: lines.length ? lines.join('\n') : '+ Build scope prepared',
      after: 'Plan is available to the runtime',
    };
  }

  if (type === 'file_written' || type === 'file_write') {
    return {
      name: `Saved ${file}`,
      before: path ? `${path}\nprevious snapshot not captured` : 'Workspace file pending',
      change: `+ ${path || file}`,
      after: path ? `${path}\navailable in workspace` : 'File available in workspace',
    };
  }

  if (type === 'code_mutation' || type === 'workspace_files_updated') {
    const summary = payload.summary || payload.message || payload.diff || '';
    return {
      name: `Updated ${file}`,
      before: path ? `${path}\nbefore patch` : 'Workspace before patch',
      change: compact(summary || `+ Applied update to ${path || file}`),
      after: path ? `${path}\nafter patch` : 'Workspace updated',
    };
  }

  if (type === 'tool_result' && payload.success === false) {
    return {
      name: 'Check needs work',
      before: payload.command || payload.input || 'Proof command',
      change: compact(payload.error || payload.output || payload.summary || 'Proof returned a failure'),
      after: 'Fix pass queued',
    };
  }

  if (type === 'verifier_started') {
    return {
      name: 'Proof check',
      before: 'Workspace files ready for validation',
      change: payload.command || payload.check_id || 'Running proof checks',
      after: 'Waiting for proof result',
    };
  }

  if (type === 'verifier_passed') {
    return {
      name: 'Proof passed',
      before: payload.command || payload.check_id || 'Proof check',
      change: payload.summary || payload.message || '+ Check passed',
      after: 'Workspace can move forward',
    };
  }

  if (type === 'verifier_failed' || type === 'job_failed') {
    return {
      name: 'Proof needs fix',
      before: payload.command || payload.check_id || 'Proof check',
      change: compact(payload.failure_reason || payload.message || payload.summary || payload.stderr || 'Build proof did not pass'),
      after: 'Next fix pass continuing',
    };
  }

  if (type === 'repair_started') {
    return {
      name: 'Fix pass',
      before: compact(payload.errors_preview || payload.failure_reason || 'Proof issue detected'),
      change: '+ Applying repair',
      after: 'Proof will run again',
    };
  }

  if (type === 'repair_completed') {
    const files = Array.isArray(payload.files_changed) ? payload.files_changed : Array.isArray(payload.files) ? payload.files : [];
    return {
      name: 'Fix applied',
      before: 'Workspace before fix',
      change: files.length ? files.map((f) => `+ ${f}`).join('\n') : '+ Fix completed',
      after: payload.passed === false ? 'Proof still needs work' : 'Proof rerun complete',
    };
  }

  if (type === 'job_completed') {
    return {
      name: 'Workspace ready',
      before: 'Build in progress',
      change: '+ Preview, files, and proof prepared',
      after: 'Ready for handoff',
    };
  }

  if (/stage_(started|completed|failed)/.test(type)) {
    const label = payload.label || payload.stage || type;
    return {
      name: String(label).replace(/\b\w/g, (c) => c.toUpperCase()),
      before: 'Previous runtime state',
      change: type.endsWith('failed') ? compact(payload.error || 'Stage failed') : `+ ${String(label)}`,
      after: type.endsWith('failed') ? 'Fix required' : 'Stage recorded',
    };
  }

  return null;
}

function buildReplayData(events = [], steps = []) {
  const fromEvents = (events || [])
    .map(eventToReplayStep)
    .filter(Boolean);

  if (fromEvents.length) return fromEvents.slice(-40);

  return (steps || [])
    .filter((step) => step && step.status && step.status !== 'pending')
    .map((step) => ({
      name: step.step_key || step.agent_name || 'Runtime step',
      before: 'Step queued',
      change: step.error_message || step.output_ref || step.status,
      after: `Status: ${step.status}`,
    }));
}

function copyToClipboard(text) {
  navigator.clipboard?.writeText(text).catch(() => {
    /* ignore clipboard errors */
  });
}

export default function BuildReplay({ events = [], steps = [] }) {
  const replayData = useMemo(() => buildReplayData(events, steps), [events, steps]);
  const [currentStep, setCurrentStep] = useState(0);
  const total = replayData.length;
  const safeIndex = Math.min(currentStep, Math.max(total - 1, 0));
  const current = replayData[safeIndex];

  if (total === 0) {
    return (
      <div className="build-replay build-replay-empty">
        <GitCompare size={22} />
        <span className="br-empty-title">No recorded changes yet</span>
        <span className="br-empty-desc">Replay will appear from this job's real build events.</span>
      </div>
    );
  }

  return (
    <div className="build-replay">
      <div className="br-header">
        <GitCompare size={14} />
        <span className="br-title">Build Replay</span>
        <span className="br-counter">Step {safeIndex + 1} of {total}</span>
      </div>

      <div className="br-step-label">{current.name}</div>

      <div className="br-columns">
        <div className="br-column">
          <div className="br-col-header">
            <div className="br-col-label">BEFORE</div>
            <button className="br-copy-btn" onClick={() => copyToClipboard(current.before)} title="Copy">
              <Copy size={10} />
            </button>
          </div>
          <div className="br-col-content br-before">
            <pre className="br-col-code">{current.before}</pre>
          </div>
        </div>

        <div className="br-column br-column-change">
          <div className="br-col-header">
            <div className="br-col-label">CHANGE</div>
            <button className="br-copy-btn" onClick={() => copyToClipboard(current.change)} title="Copy">
              <Copy size={10} />
            </button>
          </div>
          <div className="br-col-content br-change br-change-ok">
            <pre className="br-col-code">{current.change}</pre>
          </div>
        </div>

        <div className="br-column">
          <div className="br-col-header">
            <div className="br-col-label">AFTER</div>
            <button className="br-copy-btn" onClick={() => copyToClipboard(current.after)} title="Copy">
              <Copy size={10} />
            </button>
          </div>
          <div className="br-col-content br-after">
            <pre className="br-col-code">{current.after}</pre>
          </div>
        </div>
      </div>

      <div className="br-controls">
        <button
          className="br-nav-btn"
          onClick={() => setCurrentStep((c) => Math.max(0, c - 1))}
          disabled={safeIndex === 0}
        >
          <ChevronLeft size={14} /> Previous
        </button>
        <div className="br-scrubber">
          <input
            type="range"
            min={0}
            max={total - 1}
            value={safeIndex}
            onChange={(e) => setCurrentStep(Number(e.target.value))}
          />
          <div className="br-scrubber-labels">
            {replayData.map((s, i) => (
              <span
                key={`${s.name}-${i}`}
                className={`br-scrubber-tick ${i === safeIndex ? 'active' : ''} ${i < safeIndex ? 'past' : ''}`}
                title={s.name}
              />
            ))}
          </div>
          <div className="br-scrubber-names">
            {replayData.map((s, i) => (
              <span
                key={`${s.name}-name-${i}`}
                className={`br-scrubber-name ${i === safeIndex ? 'active' : ''}`}
                onClick={() => setCurrentStep(i)}
              >
                {s.name.split(' ')[0]}
              </span>
            ))}
          </div>
        </div>
        <button
          className="br-nav-btn"
          onClick={() => setCurrentStep((c) => Math.min(total - 1, c + 1))}
          disabled={safeIndex === total - 1}
        >
          Next <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}

export const __test__ = { buildReplayData, eventToReplayStep };

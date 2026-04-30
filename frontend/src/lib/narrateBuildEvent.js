/**
 * narrateBuildEvent — produce safe human narration for a backend job event.
 * Pure function. No React, no fetch, no state.
 */

const readPayload = (event) => {
  if (event?.payload && typeof event.payload === 'object') return event.payload;
  if (event?.payload_json) {
    try {
      const parsed = JSON.parse(event.payload_json);
      return parsed && typeof parsed === 'object' ? parsed : {};
    } catch {
      return {};
    }
  }
  return {};
};

const prettyPhase = (phase) => {
  if (!phase || typeof phase !== 'string') return 'execution';
  return phase
    .replace(/^[-_.]+|[-_.]+$/g, '')
    .replace(/[._-]+/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
};

const list = (xs) => {
  if (!Array.isArray(xs) || xs.length === 0) return '';
  if (xs.length <= 3) return xs.join(', ');
  return `${xs.slice(0, 3).join(', ')}, +${xs.length - 3} more`;
};

/** Show the file name in chips and prose; full path stays in payload. */
export function fileBasename(path) {
  if (!path || typeof path !== 'string') return '';
  const n = path.replace(/\\/g, '/').split('/').filter(Boolean).pop();
  return n || path;
}

/** Narration deliberately avoids surfacing agent names. The thread shows what
 * is being done, not who is doing it. Agent identities stay in the backend. */
export function narrateBuildEvent(event) {
  if (!event) return null;
  const type = event.type || event.event_type || '';
  const p = readPayload(event);
  const phase = prettyPhase(p.phase || p.step || p.step_key || '');
  const missing = p.missing || p.missing_routes || p.missing_items || [];
  const qScore =
    typeof p.quality_score === 'number'
      ? p.quality_score
      : typeof p.qualityScore === 'number'
        ? p.qualityScore
        : null;

  switch (type) {
    case 'job_started':
      return 'Starting this run: planning, implementation, and verification will follow in order.';
    case 'user_steering':
      return 'Your new instruction is merged into the run; downstream steps will follow it.';
    case 'job_completed': {
      if (qScore != null && qScore > 0) {
        return `Build finished. Quality check scored ${Math.round(qScore)}/100 — you can review the preview and proof tabs next.`;
      }
      return 'Build finished. Open the preview when you are ready, and check proof for export readiness.';
    }
    case 'job_failed': {
      const r = (p.reason || p.failure_reason || p.error || p.message || '').trim();
      const short = r.length > 160 ? `${r.slice(0, 157)}…` : r;
      return short ? `This run stopped: ${short}` : 'This run stopped before completion. You can adjust the goal and try again.';
    }
    case 'step_failed': {
      const name = (p.name || p.step_key || phase || 'a step').trim();
      const err = (p.error_message || p.error || '').trim();
      const errShort = err.length > 120 ? `${err.slice(0, 117)}…` : err;
      return errShort ? `${name} hit an issue: ${errShort}` : `${name} did not complete successfully.`;
    }
    case 'plan_created':
      return "Here is the plan: screens and routes, data shape, and how we'll verify the build before you ship it.";
    case 'phase_started':
      return phase
        ? `Moving into ${phase.toLowerCase()} — this is where the scaffold and core files take shape.`
        : 'Moving into the next execution phase.';
    case 'phase_completed':
      return phase
        ? `${phase} is wrapped; continuing with whatever is next in the pipeline.`
        : 'That phase is complete.';
    case 'phase_blocked':
      return `${phase || 'A phase'} is blocked and waiting for the next decision.`;
    case 'phase_advanced':
      return `Moving on to ${phase || 'the next phase'}.`;
    case 'step_started':
    case 'dag_node_started': {
      const label = (p.name || phase || 'the next step').trim();
      return `Working on ${label} — this shows up in your activity timeline as it finishes.`;
    }
    case 'step_completed':
    case 'dag_node_completed': {
      const label = (p.name || phase || 'That step').trim();
      return `${label} is done; wiring continues toward preview and verification.`;
    }
    case 'tool_call':
      return `Running ${p.name || 'the requested tool'}.`;
    case 'tool_result':
      return 'The tool returned; continuing the run.';
    case 'verifier_started':
      return `Running checks for ${phase ? phase.toLowerCase() : 'this stage'} before moving on.`;
    case 'verifier_passed':
      return `${phase ? `${phase} checks` : 'Verification'} passed — moving forward.`;
    case 'verifier_failed':
      return missing.length
        ? `Verification failed because the contract is missing ${list(missing)}.`
        : `Verification failed at ${phase || 'a step'}. I'll repair this.`;
    case 'assembly_failed':
      return 'Assembly failed. I am inspecting what is missing.';
    case 'export_gate_blocked':
      return 'Export gate is blocked. I will fix the missing requirements before exporting.';
    case 'export_gate_ready':
      return 'Export gate passed. This build is ready.';
    case 'repair_started':
      return 'Applying a focused repair instead of restarting the whole run.';
    case 'repair_completed':
      return 'Repair landed; re-running verification to confirm the fix.';
    case 'repair_failed':
      return 'That repair path did not clear the failure — trying another approach.';
    case 'circuit_breaker_escalated':
      return 'I tried multiple repairs without success. Escalating for guidance.';
    case 'contract_delta_created':
      return 'Contract updated based on the new instruction.';
    case 'run_snapshot':
      return 'Runtime snapshot captured.';
    case 'code_mutation': {
      const b = fileBasename(p.file || p.path);
      return b ? `Edited ${b}.` : 'Applied a code change.';
    }
    case 'file_written':
    case 'file_write': {
      const b = fileBasename(p.file || p.path);
      return b ? `Added ${b} to the workspace.` : 'Wrote a new file into the workspace.';
    }
    case 'workspace_files_updated':
      return 'Workspace synced from the latest generation pass.';
    case 'brain_guidance':
      return [p.headline, p.summary].filter(Boolean).join(' — ');
    default:
      return p.message || p.summary || '';
  }
}

export const __test__ = { readPayload, prettyPhase };

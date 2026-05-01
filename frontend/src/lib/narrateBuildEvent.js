/**
 * narrateBuildEvent — produce safe human narration for a backend job event.
 * Pure function. No React, no fetch, no state.
 */

import {
  humanIssueSummary,
  narrationJobStarted,
  narrationRepairCompleted,
  narrationRepairStarted,
  narrationVerifierPassed,
} from './presentBuildThread';

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
  if (!phase || typeof phase !== 'string') return 'this step';
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

/** Narration avoids surfacing agent names. The thread shows what is being
 * done, not who is doing it. Agent identities stay in the backend. */
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
      return narrationJobStarted();

    case 'user_steering':
      return "Got it — I've folded your new instruction into the run. Downstream steps will follow it.";

    case 'job_completed': {
      if (qScore != null && qScore > 0) {
        return `Build complete. Quality score: ${Math.round(qScore)}/100 — take a look at Preview and Proof when you're ready.`;
      }
      return "The build is done. Take a look at Preview — and if anything needs adjusting, just tell me.";
    }

    case 'job_failed':
      return humanIssueSummary(event) || "Something needs attention before we can ship. Check below or send a follow-up.";

    case 'step_failed':
      return humanIssueSummary(event) || "A step hit an issue. I'm fixing it and continuing.";

    case 'plan_created':
      return "Here's what I'm going to build. I've broken it into clear steps — let me know if you want to change anything before I start.";

    case 'phase_started':
      return phase
        ? `Working on ${phase.toLowerCase()} now.`
        : 'Moving into the next phase.';

    case 'phase_completed':
      return phase
        ? `${phase} done. Continuing.`
        : 'That phase is complete.';

    case 'phase_blocked':
      return `${phase || 'A phase'} is blocked — waiting on the next decision.`;

    case 'phase_advanced':
      return `On to ${phase || 'the next phase'}.`;

    case 'step_started':
    case 'dag_node_started': {
      const label = (p.name || phase || 'the next step').trim();
      return `Working on ${label}.`;
    }

    case 'step_completed':
    case 'dag_node_completed': {
      const label = (p.name || phase || 'That step').trim();
      return `${label} done.`;
    }

    case 'tool_call':
      return `Running ${p.name || 'tool'}.`;

    case 'tool_result':
      return null; // too noisy — suppress

    case 'verifier_started':
      return `Running checks${phase ? ` on ${phase.toLowerCase()}` : ''}.`;

    case 'verifier_passed':
      return narrationVerifierPassed(phase ? `${phase} checks` : '');

    case 'verifier_failed':
      return missing.length
        ? `Verification found missing pieces (${list(missing)}). I'm filling them in and continuing.`
        : `Verification hit a snag${phase ? ` on ${phase.toLowerCase()}` : ''}. I'm applying a fix.`;

    case 'assembly_failed':
      return "Assembly didn't complete. I'm looking at what's missing.";

    case 'export_gate_blocked':
      return "The export gate is blocked. I'll fix the missing requirements before exporting.";

    case 'export_gate_ready':
      return "Export gate passed. This build is ready to ship.";

    case 'repair_started':
      return narrationRepairStarted();

    case 'repair_completed':
      return narrationRepairCompleted();

    case 'repair_failed':
      return "That fix didn't take — trying a different approach.";

    case 'circuit_breaker_escalated':
      return "I've tried several fixes and I'm still stuck. I need your input to move forward.";

    case 'contract_delta_created':
      return "Contract updated based on your instruction.";

    case 'run_snapshot':
      return null; // internal — suppress

    case 'code_mutation': {
      const b = fileBasename(p.file || p.path);
      return b ? `Edited ${b}.` : 'Applied a code change.';
    }

    case 'file_written':
    case 'file_write': {
      const b = fileBasename(p.file || p.path);
      return b ? `Created ${b}.` : 'Added a file to the workspace.';
    }

    case 'workspace_files_updated':
      return null; // internal — suppress

    case 'brain_guidance':
      return [p.headline, p.summary].filter(Boolean).join(' — ') || null;

    default:
      return p.message || p.summary || null;
  }
}

export const __test__ = { readPayload, prettyPhase };

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

export function narrateBuildEvent(event) {
  if (!event) return null;
  const type = event.type || event.event_type || '';
  const p = readPayload(event);
  const phase = prettyPhase(p.phase || p.step || p.step_key || '');
  const agent = p.agent || p.agent_name || p.tool || '';
  const missing = p.missing || p.missing_routes || p.missing_items || [];

  switch (type) {
    case 'plan_created':
      return "I created the build plan and identified the required screens, routes, and verification steps.";
    case 'phase_started':
      return `I'm starting ${phase || 'execution'} now.`;
    case 'phase_completed':
      return `${phase || 'A phase'} is complete.`;
    case 'phase_blocked':
      return `${phase || 'A phase'} is blocked and waiting for the next decision.`;
    case 'phase_advanced':
      return `Moving on to ${phase || 'the next phase'}.`;
    case 'step_started':
    case 'dag_node_started':
      return `${agent ? `${agent} is` : 'Starting'} ${p.name || phase || 'a step'} now.`;
    case 'step_completed':
    case 'dag_node_completed':
      return `${agent ? `${agent}` : 'A step'} completed${p.name ? `: ${p.name}` : ''}.`;
    case 'tool_call':
      return `Running ${agent || p.name || 'a tool'}.`;
    case 'tool_result':
      return `${agent || 'Tool'} returned a result.`;
    case 'verifier_started':
      return `Running ${phase || 'verification'} now.`;
    case 'verifier_passed':
      return `${phase || 'Verification'} passed.`;
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
      return `Starting repair${agent ? ` with ${agent}` : ''}.`;
    case 'repair_completed':
      return `Repair completed${agent ? ` (${agent})` : ''}. Re-running verification.`;
    case 'repair_failed':
      return `Repair failed${agent ? ` (${agent})` : ''}. Trying another approach.`;
    case 'circuit_breaker_escalated':
      return 'I tried multiple repairs without success. Escalating for guidance.';
    case 'contract_delta_created':
      return 'Contract updated based on the new instruction.';
    case 'run_snapshot':
      return 'Runtime snapshot captured.';
    case 'code_mutation':
      return p.file ? `Updated ${p.file}.` : 'Applied a code change.';
    case 'file_written':
    case 'file_write':
      return p.file ? `Wrote ${p.file}.` : 'Wrote a workspace file.';
    case 'workspace_files_updated':
      return 'Workspace files updated.';
    case 'brain_guidance':
      return [p.headline, p.summary].filter(Boolean).join(' — ');
    default:
      return p.message || p.summary || '';
  }
}

export const __test__ = { readPayload, prettyPhase };

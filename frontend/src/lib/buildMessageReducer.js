/**
 * buildMessageReducer — dedupe keys and pipeline-stage routing for workspace thread.
 * Pure helpers; no React.
 *
 * Phases now match the 5-stage pipeline:
 *   plan → generate → assemble → verify → repair (conditional)
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

/** Short stable signature for deduping repeated failures. */
export function errorSignature(ev) {
  const p = readPayload(ev);
  const err = String(p.error || p.error_message || p.failure_reason || p.detail || '').trim();
  const head = err.slice(0, 200).replace(/\s+/g, ' ');
  const fr = String(p.failure_reason || '').trim();
  return `${fr}|${head}`;
}

/**
 * Failure dedupe key — keyed to JOB only so all failures for one job share one card.
 */
export function failureDedupeKey(ev, jobId) {
  const jid = String(jobId || readPayload(ev).job_id || 'nojob');
  return `${jid}::failure`;
}

/**
 * Repair dedupe key — all repairs for a job share one card.
 */
export function repairDedupeKey(ev, jobId) {
  const jid = String(jobId || readPayload(ev).job_id || 'nojob');
  return `${jid}::repair`;
}

const HIGH = {
  PLAN:     'plan',
  GENERATE: 'generate',
  ASSEMBLE: 'assemble',
  VERIFY:   'verify',
  REPAIR:   'repair',
};

const PHASE_ORDER = [HIGH.PLAN, HIGH.GENERATE, HIGH.ASSEMBLE, HIGH.VERIFY, HIGH.REPAIR];

const LABELS = {
  [HIGH.PLAN]:     'Planning',
  [HIGH.GENERATE]: 'Building',
  [HIGH.ASSEMBLE]: 'Setting up',
  [HIGH.VERIFY]:   'Verifying',
  [HIGH.REPAIR]:   'Fixing',
};

function emptyPhases() {
  const o = {};
  for (const k of PHASE_ORDER) {
    o[k] = { status: 'pending', actions: [], details: [] };
  }
  return o;
}

/**
 * Route backend event type to the correct pipeline stage.
 * Handles both new pipeline events (stage_started/stage_completed)
 * and legacy DAG events for backward compatibility.
 */
export function routeEventToHighPhase(t, p, phaseRaw) {
  const ph = String(phaseRaw || p?.phase || p?.stage || p?.step_key || '').toLowerCase();

  // ── New pipeline events ──────────────────────────────────────────────────
  if (t === 'pipeline_started') return HIGH.PLAN;
  if (t === 'stage_started' || t === 'stage_completed') {
    const stage = ph || String(p?.stage || '').toLowerCase();
    if (stage === 'plan')     return HIGH.PLAN;
    if (stage === 'generate') return HIGH.GENERATE;
    if (stage === 'assemble') return HIGH.ASSEMBLE;
    if (stage === 'verify')   return HIGH.VERIFY;
    if (stage === 'repair')   return HIGH.REPAIR;
    return HIGH.GENERATE;
  }
  if (t === 'generate_started') return HIGH.GENERATE;
  if (t === 'verify_started')   return HIGH.VERIFY;
  if (t === 'repair_started' || t === 'repair_completed' || t === 'repair_failed') return HIGH.REPAIR;

  // ── Legacy DAG events (still emitted by non-pipeline path) ───────────────
  if (t === 'job_started' || t === 'plan_created') return HIGH.PLAN;
  if (/^repair_|step_failed|job_failed|export_gate_blocked/.test(t)) return HIGH.REPAIR;
  if (/verifier_|verification\.|assembly_failed/.test(t) || ph.includes('verif')) return HIGH.VERIFY;
  if (/export_gate_ready|job_completed|run_snapshot|contract_delta/.test(t)) return HIGH.VERIFY;
  if (/file_written|file_write|code_mutation|workspace_files_updated|tool_call|dag_node_|step_/.test(t)) {
    if (ph.includes('plan')) return HIGH.PLAN;
    if (ph.includes('verif')) return HIGH.VERIFY;
    return HIGH.GENERATE;
  }
  return HIGH.GENERATE;
}

export function phaseLabels() {
  return { ...LABELS, order: [...PHASE_ORDER] };
}

export function recordPhaseAction(phases, highKey, label, detailLine) {
  const cell = phases[highKey];
  if (!cell) return;
  const L = String(label || '').trim();
  if (!L) return;
  if (cell.actions.length < 3) {
    if (!cell.actions.includes(L)) cell.actions.push(L);
  } else if (detailLine) {
    const d = String(detailLine).trim();
    if (d && cell.details.length < 40) cell.details.push(d);
  } else if (!cell.details.includes(L) && cell.details.length < 40) {
    cell.details.push(L);
  }
}

export function bumpPhaseStatus(phases, highKey, next) {
  const cell = phases[highKey];
  if (!cell) return;
  const cur = cell.status || 'pending';
  if (next === 'running' && cur === 'failed') {
    cell.status = 'running';
    return;
  }
  const rank = { pending: 0, running: 1, done: 2, failed: 2 };
  if (rank[next] >= rank[cur] || next === 'failed') {
    cell.status = next;
  }
}

export function createBuildProgressCard(id, ts) {
  return {
    kind: 'build_progress_card',
    id,
    ts,
    phases: emptyPhases(),
  };
}

export const __test__ = { readPayload, routeEventToHighPhase, failureDedupeKey };

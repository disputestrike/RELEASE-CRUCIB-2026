/**
 * buildMessageReducer — dedupe keys and high-level phase routing for workspace thread.
 * Pure helpers; no React.
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

/** Short stable signature for deduping repeated failures (same check + same error class). */
export function errorSignature(ev) {
  const p = readPayload(ev);
  const err = String(p.error || p.error_message || p.failure_reason || p.detail || '').trim();
  const head = err.slice(0, 200).replace(/\s+/g, ' ');
  const fr = String(p.failure_reason || '').trim();
  return `${fr}|${head}`;
}

/**
 * Dedupe key: job_id + step_key + error signature.
 * Same compile/preview failure repeating updates one card, not a new thread row.
 */
export function failureDedupeKey(ev, jobId) {
  const p = readPayload(ev);
  const jid = String(jobId || p.job_id || p.jobId || 'nojob');
  const ck = String(p.check_id || p.checkId || '').trim();
  const sk = String(p.step_key || p.step || p.name || 'unknown').trim();
  return `${jid}::${ck}::${sk}::${errorSignature(ev)}`;
}

export function repairDedupeKey(ev, jobId) {
  const p = readPayload(ev);
  const jid = String(jobId || p.job_id || p.jobId || 'nojob');
  const hint = String(p.step_key || p.failure_reason || p.repair_target || 'repair').trim();
  return `${jid}::repair::${hint}`;
}

const HIGH = {
  PLANNING: 'planning',
  BUILDING: 'building',
  VERIFYING: 'verifying',
  REPAIRING: 'repairing',
  DELIVERING: 'delivering',
};

const PHASE_ORDER = [HIGH.PLANNING, HIGH.BUILDING, HIGH.VERIFYING, HIGH.REPAIRING, HIGH.DELIVERING];

const LABELS = {
  [HIGH.PLANNING]: 'Planning',
  [HIGH.BUILDING]: 'Building',
  [HIGH.VERIFYING]: 'Verifying',
  [HIGH.REPAIRING]: 'Repairing',
  [HIGH.DELIVERING]: 'Delivering',
};

function emptyPhases() {
  const o = {};
  for (const k of PHASE_ORDER) {
    o[k] = { status: 'pending', actions: [], details: [] };
  }
  return o;
}

/** Route backend event type + payload to one of five high-level phases. */
export function routeEventToHighPhase(t, p, phaseRaw) {
  const ph = String(phaseRaw || p.phase || p.step_key || '').toLowerCase();
  if (t === 'plan_created' || t === 'job_started') return HIGH.PLANNING;
  if (/^repair_|step_failed|job_failed/.test(t)) return HIGH.REPAIRING;
  if (t === 'export_gate_blocked') return HIGH.REPAIRING;
  if (/verifier_|verification\.|assembly_failed|export_gate/.test(t) || ph.includes('verif')) return HIGH.VERIFYING;
  if (/export_gate_ready|job_completed|run_snapshot|contract_delta/.test(t)) return HIGH.DELIVERING;
  if (
    /file_written|file_write|code_mutation|workspace_files_updated|tool_call|tool_result|dag_node_|step_|phase_/.test(t) &&
    !ph.includes('verif')
  ) {
    return HIGH.BUILDING;
  }
  if (/phase_started|phase_completed|phase_advanced/.test(t)) {
    if (ph.includes('plan') || ph.includes('requirement')) return HIGH.PLANNING;
    if (ph.includes('verif') || ph.includes('preview')) return HIGH.VERIFYING;
    return HIGH.BUILDING;
  }
  return HIGH.BUILDING;
}

export function phaseLabels() {
  return { ...LABELS, order: [...PHASE_ORDER] };
}

/**
 * Push a short action label into phase.actions (max 3). Longer trail goes to details.
 */
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

/** Bump phase status: pending < running < done | failed */
export function bumpPhaseStatus(phases, highKey, next) {
  const cell = phases[highKey];
  if (!cell) return;
  const cur = cell.status || 'pending';
  // After a failed check, a rerun should show "running" again (not stuck on failed).
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

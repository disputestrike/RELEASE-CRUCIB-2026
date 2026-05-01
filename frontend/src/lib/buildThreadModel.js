/**
 * buildThreadModel — turn raw user messages + backend job events into an ordered
 * conversation-first thread for the workspace center pane.
 *
 * Output kinds:
 *  - user_message
 *  - assistant_message
 *  - plan_block
 *  - build_progress_card (five high-level phases; noisy tool steps folded into Details)
 *  - repair_block (merged failure + repair pass; deduped by failure key / repair hint)
 *  - delivery_card (real job_completed)
 *  - issue_notice / tool_group / failure_block / proof_block — legacy; omitted from default compile path
 *
 * Hard guarantees:
 *  - The first user message of the active job ALWAYS appears at index 0.
 *    No backend event, regardless of ts, can render above it.
 *  - Events with a job_id that does not match activeJobId are filtered out.
 *  - Tool/step events update build_progress_card phases only (no per-event thread rows).
 *  - Failures, repairs, proof events render inline at their actual time.
 *
 * Also exposes deriveCurrentActivity({ events, activeJobId }) used by the
 * "Active step" banner pinned above the composer.
 */

import { narrateBuildEvent, fileBasename } from './narrateBuildEvent';
import {
  friendlyStepLabel,
  humanIssueSummary,
  humanVerificationFailureSummary,
  issueCardTitle,
  technicalDetailLines,
  narrationJobStarted,
} from './presentBuildThread';
import {
  bumpPhaseStatus,
  createBuildProgressCard,
  failureDedupeKey,
  recordPhaseAction,
  routeEventToHighPhase,
  repairDedupeKey,
} from './buildMessageReducer';

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

const parseTs = (event) => {
  const c = event?.created_at;
  if (typeof c === 'number') return c < 1e12 ? c * 1000 : c;
  if (typeof c === 'string') {
    const t = new Date(c).getTime();
    if (!Number.isNaN(t)) return t;
  }
  return Date.now();
};

/** Map raw backend phase keys (often "agents.foo" / "Agents Phase 01") to
 * an activity-oriented label. Agent names are intentionally not surfaced in
 * the thread - the user does not need to see "Agents X" for every step. */
const PHASE_FRIENDLY = {
  planner: 'Planning the build',
  planning: 'Planning the build',
  requirements_clarifier: 'Planning the build',
  requirements: 'Planning the build',
  phase_01: 'Planning the build',
  phase_02: 'Planning the build',
  phase_03: 'Setting up the project',
  scaffold: 'Setting up the project',
  scaffolding: 'Setting up the project',
  routing: 'Building the frontend',
  navigation: 'Building the frontend',
  frontend: 'Building the frontend',
  backend: 'Building the backend',
  database: 'Setting up the database',
  styling: 'Building the frontend',
  ui: 'Building the frontend',
  ux: 'Building the frontend',
  testing: 'Verifying the build',
  verification: 'Verifying the build',
  preview_verification: 'Verifying the build',
  assembly: 'Finalizing the app',
  final_assembly: 'Finalizing the app',
  export: 'Preparing delivery',
  export_gate: 'Preparing delivery',
  repair: 'Repairing the build',
  deploy: 'Preparing delivery',
  deployment: 'Preparing delivery',
  file_tool: 'Building the frontend',
};

const stripAgentPrefix = (s) =>
  String(s || '')
    .replace(/^[-_.\s]+|[-_.\s]+$/g, '')
    // remove a leading "agents", "agent", or trailing "agent" word so we never
    // surface "Agents Planner" / "Agents Phase 01" / "File Tool Agent"
    .replace(/^agents?[\s._-]+/i, '')
    .replace(/[\s._-]+agents?$/i, '')
    .replace(/[._-]+/g, ' ')
    .trim();

const prettyPhase = (phase) => {
  if (!phase || typeof phase !== 'string') return 'Build progress';
  const stripped = stripAgentPrefix(phase);
  if (!stripped) return 'Build progress';
  const key = stripped.toLowerCase().replace(/\s+/g, '_');
  if (PHASE_FRIENDLY[key]) return PHASE_FRIENDLY[key];
  for (const k of Object.keys(PHASE_FRIENDLY)) {
    if (key.includes(k)) return PHASE_FRIENDLY[k];
  }
  return stripped.replace(/\b\w/g, (c) => c.toUpperCase());
};

const getPhase = (ev) => {
  const p = readPayload(ev);
  return p.phase || p.step || p.step_key || p.node_id || ev.step_key || '';
};

/** Intentionally returns empty string. We do not surface agent names in
 * the thread per product direction; the orchestrator/agent identities stay
 * in the backend. Kept as a helper so callers stay structurally consistent. */
const getAgent = () => '';

const extractPlanSteps = (ev) => {
  const p = readPayload(ev);
  const candidate =
    p.steps || p.plan_steps || p.checklist || (p.plan && (p.plan.steps || p.plan.checklist));
  if (!Array.isArray(candidate)) return [];
  return candidate
    .map((s, i) => {
      if (typeof s === 'string') return { id: `s${i}`, label: s, status: 'pending' };
      if (s && typeof s === 'object') {
        return {
          id: s.id || `s${i}`,
          label: String(s.label || s.title || s.name || s.text || `Step ${i + 1}`),
          status: s.status || 'pending',
        };
      }
      return null;
    })
    .filter(Boolean);
};

const deriveToolTitle = (ev) => {
  const t = ev.type || ev.event_type || '';
  const p = readPayload(ev);
  const agent = getAgent(ev);
  const phase = prettyPhase(getPhase(ev));
  if (t === 'file_written' || t === 'file_write') {
    const base = fileBasename(p.file || p.path);
    return base ? `Create ${base}` : 'Create file';
  }
  if (t === 'workspace_files_updated') return 'Sync workspace';
  if (t === 'tool_call') return `Run ${agent || p.name || 'tool'}`;
  if (t === 'tool_result') return `${agent || 'Tool'} returned`;
  if (t === 'verifier_started') {
    const v = friendlyStepLabel(p.step_key, phase);
    return v ? `Verify ${v}` : 'Run verification';
  }
  if (t === 'verifier_passed') return `${phase || 'Verification'} passed`;
  if (t === 'step_started' || t === 'dag_node_started') {
    const sk = p.step_key || '';
    return friendlyStepLabel(sk, p.name) || p.name || phase || 'Step started';
  }
  if (t === 'step_completed' || t === 'dag_node_completed') {
    const sk = p.step_key || '';
    return `${friendlyStepLabel(sk, p.name) || p.name || phase || 'Step'} done`;
  }
  if (t === 'code_mutation') {
    const base = fileBasename(p.file || p.path);
    return base ? `Edit ${base}` : 'Apply edit';
  }
  return phase || (t ? t.replace(/_/g, ' ') : 'Activity');
};

const isToolEvent = (t) =>
  [
    'tool_call',
    'tool_result',
    'step_started',
    'step_completed',
    'dag_node_started',
    'dag_node_completed',
    'phase_started',
    'phase_completed',
    'phase_advanced',
    'verifier_started',
    'verifier_passed',
    'file_written',
    'file_write',
    'workspace_files_updated',
    'code_mutation',
  ].includes(t);

const FAILURE_EVENT_TYPES =
  /^(step_failed|job_failed|verifier_failed|assembly_failed|export_gate_blocked|error)$/;

/** Match an in-flight merged repair card to a repair_started event by step_key. */
const findFailureCardByStepKey = (frMap, jobId, stepKey) => {
  const sk = String(stepKey || '').trim();
  if (!jobId || !sk) return null;
  const needle = `::${sk}::`;
  for (const [k, item] of frMap.entries()) {
    if (String(k).startsWith(`${jobId}::`) && k.includes(needle)) return item;
  }
  return null;
};

const filterEventsForJob = (events, activeJobId) =>
  (events || []).filter((ev) => {
    if (!ev) return false;
    if (!activeJobId) return true;
    const evJob = ev.job_id || ev.jobId;
    return !evJob || evJob === activeJobId;
  });

export function buildThreadModel({ userMessages = [], events = [], activeJobId = null } = {}) {
  const idCounter = { n: 0 };
  const newId = (prefix) => `${prefix}_${idCounter.n++}`;

  const filteredEvents = filterEventsForJob(events, activeJobId);

  const userMsgs = (userMessages || [])
    .filter((m) => !activeJobId || !m?.jobId || m.jobId === activeJobId)
    .filter((m) => (m?.body || '').trim().length > 0)
    .map((m) => ({
      ...m,
      ts: m.ts || Date.now(),
      role: m.role === 'assistant' ? 'assistant' : 'user',
    }))
    .sort((a, b) => (a.ts || 0) - (b.ts || 0));

  /**
   * HARD GUARANTEE: the first user message renders at index 0.
   * - We pin the first message whose role is 'user' (assistant brain_guidance
   *   messages can be timestamped earlier than the goal in some races - they
   *   must NEVER be promoted to the top user prompt).
   * - All other messages (subsequent user steering + assistant chat) flow
   *   through restItems and are sorted by ts.
   */
  const firstUserIdx = userMsgs.findIndex((m) => m.role === 'user');
  const firstUser = firstUserIdx >= 0 ? userMsgs[firstUserIdx] : null;
  const restUserMsgs = userMsgs.filter((_, i) => i !== firstUserIdx);

  const restItems = [];

  /**
   * Dedupe consecutive assistant messages with identical content. The backend
   * emits brain_guidance both as a chat message (via UnifiedWorkspace's
   * brainEvents effect) and as a job event - we only want to surface it once.
   */
  const lastAssistantContentRef = { value: null };
  const pushAssistantOnce = (content, ts, id) => {
    const trimmed = (content || '').trim();
    if (!trimmed) return;
    if (lastAssistantContentRef.value === trimmed) return;
    lastAssistantContentRef.value = trimmed;
    restItems.push({ kind: 'assistant_message', role: 'assistant', content: trimmed, ts, id });
  };

  for (const m of restUserMsgs) {
    if (m.role === 'assistant') {
      pushAssistantOnce(m.body, m.ts, m.id || newId('am'));
    } else {
      restItems.push({
        kind: 'user_message',
        role: 'user',
        content: m.body,
        ts: m.ts,
        id: m.id || newId('um'),
      });
    }
  }

  /**
   * Timeline compiler: one build_progress_card (five phases) plus deduped
   * repair_block rows keyed by failureDedupeKey / repairDedupeKey. Tool and
   * phase micro-events update the card only — they are not rendered as pills.
   */
  let progressCard = null;
  const failureRepairByKey = new Map();

  const ensureProgress = (ts) => {
    if (!progressCard) {
      progressCard = createBuildProgressCard(newId('bpc'), ts);
      restItems.push(progressCard);
    }
    return progressCard;
  };

  const applyProgressForEvent = (ev, ts) => {
    const t = ev.type || ev.event_type || '';
    const p = readPayload(ev);
    const card = ensureProgress(ts);
    const hi = routeEventToHighPhase(t, p, getPhase(ev));

    if (t === 'job_started') {
      bumpPhaseStatus(card.phases, 'planning', 'running');
      recordPhaseAction(card.phases, 'planning', 'Run queued', '');
      return;
    }
    if (t === 'plan_created') {
      bumpPhaseStatus(card.phases, 'planning', 'done');
      bumpPhaseStatus(card.phases, 'building', 'running');
      recordPhaseAction(card.phases, 'planning', 'Plan saved', '');
      return;
    }
    if (t === 'verifier_started') {
      bumpPhaseStatus(card.phases, 'building', 'done');
      bumpPhaseStatus(card.phases, 'verifying', 'running');
      recordPhaseAction(card.phases, 'verifying', deriveToolTitle(ev), '');
      return;
    }
    if (t === 'verifier_passed') {
      bumpPhaseStatus(card.phases, 'verifying', 'done');
      return;
    }
    if (FAILURE_EVENT_TYPES.test(t)) {
      bumpPhaseStatus(card.phases, 'verifying', 'failed');
      bumpPhaseStatus(card.phases, 'repairing', 'running');
      return;
    }
    if (/^repair_/.test(t)) {
      if (t === 'repair_started') bumpPhaseStatus(card.phases, 'repairing', 'running');
      if (t === 'repair_completed') {
        bumpPhaseStatus(card.phases, 'repairing', 'done');
        bumpPhaseStatus(card.phases, 'verifying', 'running');
      }
      if (t === 'repair_failed') bumpPhaseStatus(card.phases, 'repairing', 'failed');
      return;
    }
    if (t === 'export_gate_ready' || t === 'run_snapshot' || t === 'contract_delta_created') {
      bumpPhaseStatus(card.phases, 'building', 'done');
      bumpPhaseStatus(card.phases, 'verifying', 'done');
      bumpPhaseStatus(card.phases, 'delivering', 'running');
      const delLabel =
        t === 'export_gate_ready'
          ? 'Export gate'
          : t === 'run_snapshot'
          ? 'Runtime snapshot'
          : 'Contract update';
      recordPhaseAction(card.phases, 'delivering', delLabel, '');
      return;
    }
    if (t === 'job_completed') {
      bumpPhaseStatus(card.phases, 'planning', 'done');
      bumpPhaseStatus(card.phases, 'building', 'done');
      bumpPhaseStatus(card.phases, 'verifying', 'done');
      bumpPhaseStatus(card.phases, 'repairing', 'done');
      bumpPhaseStatus(card.phases, 'delivering', 'done');
      return;
    }
    if (isToolEvent(t)) {
      if (hi === 'planning') {
        bumpPhaseStatus(card.phases, 'planning', 'running');
        recordPhaseAction(card.phases, 'planning', deriveToolTitle(ev), t);
        return;
      }
      if (hi === 'verifying') {
        bumpPhaseStatus(card.phases, 'verifying', 'running');
        recordPhaseAction(card.phases, 'verifying', deriveToolTitle(ev), t);
        return;
      }
      bumpPhaseStatus(card.phases, 'building', 'running');
      recordPhaseAction(card.phases, 'building', deriveToolTitle(ev), t);
    }
  };

  const sorted = [...filteredEvents]
    .map((ev) => ({ ev, ts: parseTs(ev) }))
    .sort((a, b) => a.ts - b.ts);

  for (const { ev, ts } of sorted) {
    const t = ev.type || ev.event_type || '';
    if (!t) continue;
    if (t === 'user_instruction' || t === 'workspace_transcript') continue;
    if (t === 'dag_node_failed') continue;
    if (t === 'brain_guidance' || t === 'message') continue;

    applyProgressForEvent(ev, ts);

    if (t === 'job_started') {
      pushAssistantOnce(narrationJobStarted(), ts, newId('am'));
      continue;
    }

    if (FAILURE_EVENT_TYPES.test(t)) {
      const key = failureDedupeKey(ev, activeJobId);
      const title = issueCardTitle(ev);
      const summary =
        t === 'verifier_failed'
          ? humanVerificationFailureSummary(readPayload(ev))
          : humanIssueSummary(ev);
      const detail = technicalDetailLines(ev);
      let item = failureRepairByKey.get(key);
      if (item) {
        item.repeatCount = (item.repeatCount || 1) + 1;
        item.title = title;
        item.narration = summary;
        item.technicalDetail = detail;
        if (item.status === 'success') item.status = 'needs_fix';
      } else {
        item = {
          kind: 'repair_block',
          id: newId('rb'),
          ts,
          agent: '',
          attempt: 0,
          filesChanged: [],
          status: 'needs_fix',
          narration: summary,
          title,
          technicalDetail: detail,
          repeatCount: 1,
          dedupeKey: key,
        };
        failureRepairByKey.set(key, item);
        restItems.push(item);
      }
      continue;
    }

    if (t === 'repair_started') {
      const p = readPayload(ev);
      const rk = repairDedupeKey(ev, activeJobId);
      let item =
        findFailureCardByStepKey(failureRepairByKey, activeJobId, p.step_key || p.repair_target) ||
        failureRepairByKey.get(rk);
      const startNarration =
        "Something came up during verification — I'm fixing it and will rerun the check.";
      if (!item) {
        item = {
          kind: 'repair_block',
          id: newId('rb'),
          ts,
          agent: '',
          attempt: Number(p.attempt || 1),
          filesChanged: [],
          status: 'running',
          narration: startNarration,
          title: issueCardTitle(ev) || 'Repair pass',
          technicalDetail: '',
          repeatCount: 1,
          dedupeKey: rk,
        };
        failureRepairByKey.set(rk, item);
        restItems.push(item);
      } else {
        if (item.dedupeKey && item.dedupeKey !== rk) failureRepairByKey.set(rk, item);
        item.status = 'running';
        const fromPayload = Number(p.attempt);
        item.attempt = Number.isFinite(fromPayload) && fromPayload > 0
          ? fromPayload
          : (item.attempt || 0) + 1;
        item.narration = item.narration?.trim() ? item.narration : startNarration;
        failureRepairByKey.set(rk, item);
      }
      continue;
    }

    if (t === 'repair_completed' || t === 'repair_failed') {
      const p = readPayload(ev);
      const rk = repairDedupeKey(ev, activeJobId);
      const fc = Array.isArray(p.files_changed) ? p.files_changed : Array.isArray(p.files) ? p.files : [];
      let item =
        failureRepairByKey.get(rk) ||
        findFailureCardByStepKey(failureRepairByKey, activeJobId, p.step_key || p.repair_target);
      if (item) {
        item.status = t === 'repair_completed' ? 'success' : 'failed';
        if (fc.length) {
          const prev = new Set((item.filesChanged || []).map(String));
          for (const f of fc) prev.add(String(f));
          item.filesChanged = [...prev];
        }
        const extra = narrateBuildEvent(ev);
        if (extra && t === 'repair_completed' && !item.narration?.trim()) item.narration = extra;
      }
      continue;
    }

    if (t === 'job_completed') {
      pushAssistantOnce(narrateBuildEvent(ev) || 'The build is done. Take a look at Preview — and if anything needs adjusting, just tell me.', ts, newId('am'));
      restItems.push({
        kind: 'delivery_card',
        narration:
          'Your app is ready in Preview. Hit Proof to see what\'s export-ready — and send a follow-up whenever you want changes.',
        ts,
        id: newId('dl'),
      });
      continue;
    }

    if (t === 'plan_created') {
      pushAssistantOnce(
        narrateBuildEvent(ev) || "Here's what I'm going to build — let me know if you want to change anything before I start.",
        ts,
        newId('am'),
      );
      const steps = extractPlanSteps(ev);
      if (steps.length) {
        restItems.push({ kind: 'plan_block', title: 'Build plan', steps, ts, id: newId('pb') });
      }
      continue;
    }

    if (t === 'export_gate_ready' || t === 'run_snapshot' || t === 'contract_delta_created') {
      continue;
    }

    if (isToolEvent(t)) {
      continue;
    }

    const fallback = narrateBuildEvent(ev);
    if (fallback && /^(phase_|workspace_|goal_)/.test(t)) {
      pushAssistantOnce(fallback, ts, newId('am'));
    }
  }

  restItems.sort((a, b) => (a.ts || 0) - (b.ts || 0));

  const out = [];
  if (firstUser) {
    out.push({
      kind: 'user_message',
      role: 'user',
      content: firstUser.body,
      ts: firstUser.ts,
      id: firstUser.id || newId('um'),
    });
  }
  for (const item of restItems) out.push(item);

  return out;
}

/**
 * deriveCurrentActivity — what is the system doing right NOW?
 * Returns null if nothing active.
 * Used by the pinned ActiveStepBanner above the composer.
 */
export function deriveCurrentActivity({ events = [], activeJobId = null } = {}) {
  const filtered = filterEventsForJob(events, activeJobId);
  if (!filtered.length) return null;

  const sorted = [...filtered]
    .map((ev) => ({ ev, ts: parseTs(ev) }))
    .sort((a, b) => b.ts - a.ts);

  // Walk back to find the latest meaningful active event.
  let activePhase = null;
  let runningTitle = null;
  let runningStatus = 'running';
  const recentFiles = [];
  let totalSteps = 0;
  let stepIndex = 0;
  let detailLine = '';

  for (const { ev } of sorted) {
    const t = ev.type || ev.event_type || '';
    const p = readPayload(ev);
    if (!t) continue;

    if (!activePhase && (t === 'phase_started' || t === 'dag_node_started' || t === 'step_started')) {
      activePhase = prettyPhase(getPhase(ev));
      runningTitle = p.name || activePhase || 'Working';
      runningStatus = 'running';
    }

    if (!runningTitle && (t === 'verifier_started' || t === 'repair_started')) {
      runningTitle = t === 'repair_started' ? 'Repairing the build' : 'Verifying the build';
      runningStatus = 'running';
    }

    if (t === 'verifier_started' || t === 'verifier_failed') {
      const hint = String(p.file || p.path || p.proof_path || p.check_id || p.step_key || '').trim();
      if (hint && !detailLine) detailLine = hint;
    }

    if (recentFiles.length < 3 && (t === 'file_written' || t === 'file_write' || t === 'code_mutation')) {
      const f = p.file || p.path;
      if (f && !recentFiles.includes(f)) recentFiles.push(f);
    }

    if (!totalSteps && Array.isArray(p.steps)) totalSteps = p.steps.length;
    if (!stepIndex && typeof p.step_index === 'number') stepIndex = p.step_index + 1;
  }

  // Detect "complete" / "failed" terminal states from the most recent event
  const latest = sorted[0]?.ev;
  if (latest) {
    const lt = latest.type || latest.event_type || '';
    if (/^(export_gate_ready|run_snapshot|done|job_completed)$/.test(lt)) {
      runningTitle = runningTitle || 'Build complete';
      runningStatus = 'success';
    } else if (/(failed|blocked|error)$/.test(lt)) {
      runningTitle = runningTitle || 'Repairing the build';
      runningStatus = 'running';
    }
  }

  if (!runningTitle && !activePhase && recentFiles.length === 0) return null;

  return {
    title: runningTitle || activePhase || 'Working',
    phase: activePhase || '',
    agent: '',
    files: recentFiles,
    status: runningStatus,
    stepIndex: stepIndex || 0,
    totalSteps: totalSteps || 0,
    detailLine,
  };
}

export const __test__ = { readPayload, parseTs, prettyPhase, getPhase, getAgent, isToolEvent };

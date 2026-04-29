/**
 * buildThreadModel — turn raw user messages + backend job events into an ordered
 * conversation-first thread for the workspace center pane.
 *
 * Output kinds:
 *  - user_message
 *  - assistant_message
 *  - plan_block
 *  - tool_group
 *  - failure_block
 *  - repair_block
 *  - proof_block
 *
 * Hard guarantees:
 *  - The first user message of the active job ALWAYS appears at index 0.
 *    No backend event, regardless of ts, can render above it.
 *  - Events with a job_id that does not match activeJobId are filtered out.
 *  - Tool/step events are grouped consecutively by phase into a single tool_group.
 *  - Failures, repairs, proof events render inline at their actual time.
 *
 * Also exposes deriveCurrentActivity({ events, activeJobId }) used by the
 * "Active step" banner pinned above the composer.
 */

import { narrateBuildEvent } from './narrateBuildEvent';

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

const prettyPhase = (phase) => {
  if (!phase || typeof phase !== 'string') return 'Execution';
  return phase
    .replace(/^[-_.]+|[-_.]+$/g, '')
    .replace(/[._-]+/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
};

const getPhase = (ev) => {
  const p = readPayload(ev);
  return p.phase || p.step || p.step_key || p.node_id || ev.step_key || '';
};

const getAgent = (ev) => {
  const p = readPayload(ev);
  return p.agent || p.agent_name || p.tool || p.agent_id || '';
};

const deriveStatus = (ev) => {
  const t = ev.type || ev.event_type || '';
  if (/failed|error|blocked/i.test(t)) return 'failed';
  if (/completed|passed|ready|done/i.test(t)) return 'success';
  if (/started|running|in_progress|progress/i.test(t)) return 'running';
  return 'success';
};

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
  if (t === 'file_written' || t === 'file_write')
    return `Write ${p.file || p.path || 'file'}`;
  if (t === 'workspace_files_updated') return 'Update workspace files';
  if (t === 'tool_call') return `Run ${agent || p.name || 'tool'}`;
  if (t === 'tool_result') return `${agent || 'Tool'} returned`;
  if (t === 'verifier_started') return `Verify ${phase || ''}`.trim();
  if (t === 'verifier_passed') return `${phase || 'Verification'} passed`;
  if (t === 'step_started' || t === 'dag_node_started') return p.name || phase || 'Step started';
  if (t === 'step_completed' || t === 'dag_node_completed') return p.name || phase || 'Step completed';
  if (t === 'code_mutation') return p.file ? `Edit ${p.file}` : 'Apply edit';
  return phase || (t ? t.replace(/_/g, ' ') : 'Activity');
};

const toolIconKey = (ev) => {
  const t = ev.type || ev.event_type || '';
  if (t === 'file_written' || t === 'file_write' || t === 'code_mutation') return 'edit';
  if (t === 'workspace_files_updated') return 'sync';
  if (/^verifier_/.test(t)) return 'check';
  if (/^step_|^dag_node_|^phase_/.test(t)) return 'spark';
  if (t === 'tool_call' || t === 'tool_result') return 'tool';
  return 'dot';
};

const deriveGroupStatus = (children) => {
  if (children.some((c) => c.status === 'failed')) return 'failed';
  if (children.some((c) => c.status === 'running')) return 'running';
  return 'success';
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
   * We split the items into two arrays: [firstUser] and rest. The rest is sorted
   * by ts, and the first user message is unconditionally prepended.
   */
  const firstUser = userMsgs.length ? userMsgs[0] : null;
  const restUserMsgs = userMsgs.slice(1);

  // Process events into thread-rest items
  const restItems = [];

  // Push remaining user messages (steering) into rest by ts
  for (const m of restUserMsgs) {
    restItems.push({
      kind: m.role === 'assistant' ? 'assistant_message' : 'user_message',
      role: m.role,
      content: m.body,
      ts: m.ts,
      id: m.id || newId('um'),
    });
  }

  let bucket = null;
  const flushBucket = () => {
    if (bucket && bucket.children.length) {
      restItems.push({
        kind: 'tool_group',
        title: bucket.title,
        agent: bucket.agent,
        phase: bucket.phase,
        status: deriveGroupStatus(bucket.children),
        children: bucket.children,
        ts: bucket.ts,
        id: newId('tg'),
      });
    }
    bucket = null;
  };

  const sorted = [...filteredEvents]
    .map((ev) => ({ ev, ts: parseTs(ev) }))
    .sort((a, b) => a.ts - b.ts);

  for (const { ev, ts } of sorted) {
    const t = ev.type || ev.event_type || '';
    if (!t) continue;
    if (t === 'user_instruction' || t === 'workspace_transcript') continue;

    if (t === 'plan_created') {
      flushBucket();
      restItems.push({
        kind: 'assistant_message',
        role: 'assistant',
        content:
          narrateBuildEvent(ev) ||
          "I've reviewed your request. Here's the plan I'll follow.",
        ts,
        id: newId('am'),
      });
      const steps = extractPlanSteps(ev);
      if (steps.length) {
        restItems.push({ kind: 'plan_block', title: 'Build plan', steps, ts, id: newId('pb') });
      }
      continue;
    }

    if (t === 'brain_guidance' || t === 'message') {
      flushBucket();
      const text = narrateBuildEvent(ev);
      if (text) {
        restItems.push({ kind: 'assistant_message', role: 'assistant', content: text, ts, id: newId('am') });
      }
      continue;
    }

    if (/^(verifier_failed|assembly_failed|export_gate_blocked|error)$/.test(t)) {
      flushBucket();
      const p = readPayload(ev);
      restItems.push({
        kind: 'failure_block',
        title: p.summary || p.message || `Verification failed at ${prettyPhase(getPhase(ev))}`,
        reason: p.error || p.detail || narrateBuildEvent(ev) || '',
        missingItems: p.missing || p.missing_routes || p.missing_items || [],
        actions: ['Retry', 'Add instruction', 'Branch'],
        ts,
        id: newId('fb'),
      });
      continue;
    }

    if (/^(repair_started|repair_completed|repair_failed)$/.test(t)) {
      flushBucket();
      const p = readPayload(ev);
      const status = t === 'repair_completed' ? 'success' : t === 'repair_failed' ? 'failed' : 'running';
      restItems.push({
        kind: 'repair_block',
        agent: p.agent || p.agent_name || 'RepairAgent',
        attempt: Number(p.attempt || 1),
        filesChanged: Array.isArray(p.files_changed)
          ? p.files_changed
          : Array.isArray(p.files)
          ? p.files
          : [],
        status,
        narration: narrateBuildEvent(ev) || '',
        ts,
        id: newId('rb'),
      });
      continue;
    }

    if (t === 'export_gate_ready' || t === 'run_snapshot' || t === 'contract_delta_created') {
      flushBucket();
      restItems.push({
        kind: 'proof_block',
        proofType: t,
        status: 'success',
        narration: narrateBuildEvent(ev) || '',
        ts,
        id: newId('pr'),
      });
      continue;
    }

    if (isToolEvent(t)) {
      const phase = getPhase(ev);
      const agent = getAgent(ev);
      if (!bucket || bucket.phase !== phase) {
        flushBucket();
        bucket = {
          title: prettyPhase(phase) || 'Execution',
          agent,
          phase,
          children: [],
          ts,
        };
      }
      bucket.children.push({
        id: newId('tc'),
        title: deriveToolTitle(ev),
        status: deriveStatus(ev),
        ts,
        type: t,
        iconKey: toolIconKey(ev),
        payload: readPayload(ev),
        agent,
      });
      continue;
    }

    const fallback = narrateBuildEvent(ev);
    if (fallback) {
      flushBucket();
      restItems.push({ kind: 'assistant_message', role: 'assistant', content: fallback, ts, id: newId('am') });
    }
  }

  flushBucket();

  // Sort the rest by ts (does NOT touch the pinned first user message)
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
  let activeAgent = null;
  let runningTitle = null;
  let runningStatus = 'running';
  const recentFiles = [];
  let totalSteps = 0;
  let stepIndex = 0;

  for (const { ev } of sorted) {
    const t = ev.type || ev.event_type || '';
    const p = readPayload(ev);
    if (!t) continue;

    if (!activePhase && (t === 'phase_started' || t === 'dag_node_started' || t === 'step_started')) {
      activePhase = prettyPhase(getPhase(ev));
      activeAgent = getAgent(ev);
      runningTitle = p.name || activePhase || 'Working';
      runningStatus = 'running';
    }

    if (!runningTitle && (t === 'verifier_started' || t === 'repair_started')) {
      runningTitle = t === 'repair_started'
        ? `Repairing${p.agent ? ` with ${p.agent}` : ''}`
        : `Verifying ${prettyPhase(getPhase(ev)) || ''}`.trim();
      activeAgent = activeAgent || getAgent(ev);
      runningStatus = 'running';
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
    if (/^(export_gate_ready|run_snapshot|done)$/.test(lt)) {
      runningTitle = runningTitle || 'Build complete';
      runningStatus = 'success';
    } else if (/(failed|blocked|error)$/.test(lt)) {
      runningTitle = runningTitle || 'Build paused';
      runningStatus = 'failed';
    }
  }

  if (!runningTitle && !activePhase && recentFiles.length === 0) return null;

  return {
    title: runningTitle || activePhase || 'Working',
    phase: activePhase || '',
    agent: activeAgent || '',
    files: recentFiles,
    status: runningStatus,
    stepIndex: stepIndex || 0,
    totalSteps: totalSteps || 0,
  };
}

export const __test__ = { readPayload, parseTs, prettyPhase, getPhase, getAgent, isToolEvent };

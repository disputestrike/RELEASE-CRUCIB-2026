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
 * Rules:
 *  - The first user message of the active job is always pinned to the top.
 *  - Plan + assistant ack always appear immediately after the first user message.
 *  - Tool/step events are grouped consecutively by phase into a single tool_group.
 *  - Failures, repairs, proof events render inline at their actual time.
 *  - Events from a different jobId are filtered out (no leak).
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
    return `Wrote ${p.file || p.path || 'file'}`;
  if (t === 'workspace_files_updated') return 'Workspace files updated';
  if (t === 'tool_call') return `Run ${agent || p.name || 'tool'}`;
  if (t === 'tool_result') return `${agent || 'Tool'} returned`;
  if (t === 'verifier_started') return `Verify ${phase || ''}`.trim();
  if (t === 'verifier_passed') return `${phase || 'Verification'} passed`;
  if (t === 'step_started' || t === 'dag_node_started') return p.name || phase || 'Step started';
  if (t === 'step_completed' || t === 'dag_node_completed') return p.name || phase || 'Step completed';
  if (t === 'code_mutation') return p.file ? `Edit ${p.file}` : 'Apply edit';
  return phase || (t ? t.replace(/_/g, ' ') : 'Activity');
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

export function buildThreadModel({ userMessages = [], events = [], activeJobId = null } = {}) {
  const idCounter = { n: 0 };
  const newId = (prefix) => `${prefix}_${idCounter.n++}`;

  const filteredEvents = (events || []).filter((ev) => {
    if (!ev) return false;
    if (!activeJobId) return true;
    const evJob = ev.job_id || ev.jobId;
    return !evJob || evJob === activeJobId;
  });

  const evTimes = filteredEvents.map(parseTs).filter((t) => t > 0);
  const minEventTs = evTimes.length ? Math.min(...evTimes) : null;

  const userMsgs = (userMessages || [])
    .filter((m) => !activeJobId || !m?.jobId || m.jobId === activeJobId)
    .filter((m) => (m?.body || '').trim().length > 0)
    .map((m) => ({
      ...m,
      ts: m.ts || Date.now(),
      role: m.role === 'assistant' ? 'assistant' : 'user',
    }))
    .sort((a, b) => (a.ts || 0) - (b.ts || 0));

  if (userMsgs.length && minEventTs && userMsgs[0].ts > minEventTs) {
    userMsgs[0] = { ...userMsgs[0], ts: minEventTs - 1 };
  }

  const items = [];

  for (const m of userMsgs) {
    items.push({
      kind: m.role === 'assistant' ? 'assistant_message' : 'user_message',
      role: m.role,
      content: m.body,
      ts: m.ts,
      id: m.id || newId('um'),
    });
  }

  const sorted = [...filteredEvents]
    .map((ev) => ({ ev, ts: parseTs(ev) }))
    .sort((a, b) => a.ts - b.ts);

  let bucket = null;
  const flushBucket = () => {
    if (bucket && bucket.children.length) {
      items.push({
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

  for (const { ev, ts } of sorted) {
    const t = ev.type || ev.event_type || '';
    if (!t) continue;
    if (t === 'user_instruction' || t === 'workspace_transcript') continue;

    if (t === 'plan_created') {
      flushBucket();
      items.push({
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
        items.push({ kind: 'plan_block', title: 'Build plan', steps, ts, id: newId('pb') });
      }
      continue;
    }

    if (t === 'brain_guidance' || t === 'message') {
      flushBucket();
      const text = narrateBuildEvent(ev);
      if (text) {
        items.push({ kind: 'assistant_message', role: 'assistant', content: text, ts, id: newId('am') });
      }
      continue;
    }

    if (/^(verifier_failed|assembly_failed|export_gate_blocked|error)$/.test(t)) {
      flushBucket();
      const p = readPayload(ev);
      items.push({
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
      items.push({
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
      items.push({
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
        payload: readPayload(ev),
        agent,
      });
      continue;
    }

    // Fallback: treat as assistant narration if narration is non-empty
    const fallback = narrateBuildEvent(ev);
    if (fallback) {
      flushBucket();
      items.push({ kind: 'assistant_message', role: 'assistant', content: fallback, ts, id: newId('am') });
    }
  }

  flushBucket();

  // Final chronological sort with stable ordering
  return items.sort((a, b) => (a.ts || 0) - (b.ts || 0));
}

export const __test__ = { readPayload, parseTs, prettyPhase, getPhase, getAgent, isToolEvent };

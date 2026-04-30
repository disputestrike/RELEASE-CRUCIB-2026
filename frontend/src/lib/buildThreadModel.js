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

import { narrateBuildEvent, fileBasename } from './narrateBuildEvent';

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

/** One-paragraph human description per chapter title. Each chapter gets a
 * "what / why / next" sentence the user can read instead of a stack of raw
 * step headers. */
const CHAPTER_DESCRIPTIONS = {
  'Planning the build':
    'Locking scope: routes, data shape, and how we will prove the build before you ship.',
  'Setting up the project':
    'Scaffold, packages, and baseline config so everything downstream has a stable base.',
  'Building the frontend':
    'Pages, layout, navigation, and UI wiring aligned to your goal.',
  'Building the backend':
    'APIs and server logic for the flows you described.',
  'Setting up the database':
    'Schema and seeds for what this app needs to persist.',
  'Verifying the build':
    'Compile, routes, imports, and preview checks before you rely on the artifact.',
  'Finalizing the app':
    'Assembly pass: required files, routes, and contract items accounted for.',
  'Preparing delivery':
    'Proof capture and export gate so the result is checkable, not hand-waved.',
  'Repairing the build':
    'Targeted fix for what verification caught—without restarting the whole run.',
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
  if (!phase || typeof phase !== 'string') return 'Execution';
  const stripped = stripAgentPrefix(phase);
  if (!stripped) return 'Execution';
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
  if (t === 'file_written' || t === 'file_write') {
    const base = fileBasename(p.file || p.path);
    return base ? `Write ${base}` : 'Write file';
  }
  if (t === 'workspace_files_updated') return 'Sync workspace files';
  if (t === 'tool_call') return `Run ${agent || p.name || 'tool'}`;
  if (t === 'tool_result') return `${agent || 'Tool'} returned`;
  if (t === 'verifier_started') return `Verify ${phase || ''}`.trim();
  if (t === 'verifier_passed') return `${phase || 'Verification'} passed`;
  if (t === 'step_started' || t === 'dag_node_started') return p.name || phase || 'Step started';
  if (t === 'step_completed' || t === 'dag_node_completed') return p.name || phase || 'Step completed';
  if (t === 'code_mutation') {
    const base = fileBasename(p.file || p.path);
    return base ? `Edit ${base}` : 'Apply edit';
  }
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
   * Story compiler: instead of one mutable bucket that flushes whenever the
   * raw phase changes, we keep a Map keyed by FRIENDLY title. Non-consecutive
   * events that map to the same chapter merge into the same chapter so the
   * thread reads as a story (Planning -> Setup -> Frontend -> Verification),
   * not a log (Planning x4, Frontend x4, Verification x4).
   *
   * Chapters are inserted into restItems on first appearance so their visual
   * order matches the moment the activity began. Subsequent chips for the
   * same chapter are pushed into the existing chapter in place.
   */
  const chapters = new Map();
  const placeChapter = (key, friendlyTitle, ts) => {
    let ch = chapters.get(key);
    if (ch) return ch;
    ch = {
      id: newId('tg'),
      kind: 'tool_group',
      title: friendlyTitle,
      description: CHAPTER_DESCRIPTIONS[friendlyTitle] || '',
      agent: '',
      phase: key,
      children: [],
      seen: new Set(),
      status: 'running',
      ts,
    };
    chapters.set(key, ch);
    restItems.push(ch);
    return ch;
  };

  const sorted = [...filteredEvents]
    .map((ev) => ({ ev, ts: parseTs(ev) }))
    .sort((a, b) => a.ts - b.ts);

  for (const { ev, ts } of sorted) {
    const t = ev.type || ev.event_type || '';
    if (!t) continue;
    if (t === 'user_instruction' || t === 'workspace_transcript') continue;
    // brain_guidance / generic message events are already pushed into the chat
    // message stream by UnifiedWorkspace - skip them here so we don't duplicate.
    if (t === 'brain_guidance' || t === 'message') continue;

    if (t === 'plan_created') {
      pushAssistantOnce(
        narrateBuildEvent(ev) || "I've reviewed your request. Here's the plan I'll follow.",
        ts,
        newId('am'),
      );
      const steps = extractPlanSteps(ev);
      if (steps.length) {
        restItems.push({ kind: 'plan_block', title: 'Build plan', steps, ts, id: newId('pb') });
      }
      continue;
    }

    if (/^(verifier_failed|assembly_failed|export_gate_blocked|error|step_failed|job_failed)$/.test(t)) {
      const p = readPayload(ev);
      const phaseLabel = prettyPhase(getPhase(ev));
      const titleForFailure = () => {
        if (t === 'job_failed') return p.summary || p.message || 'Build stopped';
        if (t === 'step_failed') return p.name || p.step_key || phaseLabel || 'Step did not complete';
        return p.summary || p.message || `Verification failed at ${phaseLabel}`;
      };
      restItems.push({
        kind: 'failure_block',
        title: titleForFailure(),
        reason:
          p.error ||
          p.error_message ||
          p.detail ||
          p.reason ||
          p.failure_reason ||
          narrateBuildEvent(ev) ||
          '',
        missingItems: p.missing || p.missing_routes || p.missing_items || [],
        actions: ['Retry', 'Add instruction', 'Branch'],
        ts,
        id: newId('fb'),
      });
      continue;
    }

    if (/^(repair_started|repair_completed|repair_failed)$/.test(t)) {
      const p = readPayload(ev);
      const status = t === 'repair_completed' ? 'success' : t === 'repair_failed' ? 'failed' : 'running';
      restItems.push({
        kind: 'repair_block',
        agent: '',
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
      const friendlyTitle = prettyPhase(phase) || 'Working';
      const chapterKey = friendlyTitle.toLowerCase();
      const ch = placeChapter(chapterKey, friendlyTitle, ts);

      const childTitle = deriveToolTitle(ev);
      const evStatus = deriveStatus(ev);
      // Hide chips that just duplicate the chapter header (e.g. a phase_started
      // event for "Planning the build" inside the "Planning the build" chapter).
      const childIsRedundant =
        childTitle === friendlyTitle ||
        childTitle.toLowerCase() === friendlyTitle.toLowerCase();
      if (childIsRedundant && /^(phase|step|dag_node)/.test(t)) {
        if (evStatus === 'failed') ch.status = 'failed';
        else if (evStatus === 'running' && ch.status !== 'failed') ch.status = 'running';
        else if (evStatus === 'success' && ch.status !== 'failed' && ch.status !== 'running') {
          ch.status = 'success';
        }
        continue;
      }
      const childKey = `${childTitle}::${readPayload(ev).file || readPayload(ev).path || ''}`;
      if (ch.seen.has(childKey)) {
        const last = ch.children[ch.children.length - 1];
        if (last) last.status = evStatus;
        if (evStatus === 'failed') ch.status = 'failed';
        continue;
      }
      ch.seen.add(childKey);
      ch.children.push({
        id: newId('tc'),
        title: childTitle,
        status: evStatus,
        ts,
        type: t,
        iconKey: toolIconKey(ev),
        payload: readPayload(ev),
        agent: '',
      });
      if (evStatus === 'failed') ch.status = 'failed';
      continue;
    }

    const fallback = narrateBuildEvent(ev);
    if (fallback) {
      pushAssistantOnce(fallback, ts, newId('am'));
    }
  }

  // Resolve final chapter status from children (and discard empty chapters
  // that exist only because of redundant phase_started events).
  for (const ch of chapters.values()) {
    delete ch.seen;
    ch.status = deriveGroupStatus(ch.children);
  }
  for (let i = restItems.length - 1; i >= 0; i--) {
    const item = restItems[i];
    if (item && item.kind === 'tool_group' && (!item.children || item.children.length === 0)) {
      restItems.splice(i, 1);
    }
  }

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
      runningTitle = p.name || activePhase || 'Working';
      runningStatus = 'running';
    }

    if (!runningTitle && (t === 'verifier_started' || t === 'repair_started')) {
      runningTitle = t === 'repair_started'
        ? 'Repairing the build'
        : `Verifying ${prettyPhase(getPhase(ev)) || ''}`.trim();
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
    if (/^(export_gate_ready|run_snapshot|done|job_completed)$/.test(lt)) {
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
    agent: '',
    files: recentFiles,
    status: runningStatus,
    stepIndex: stepIndex || 0,
    totalSteps: totalSteps || 0,
  };
}

export const __test__ = { readPayload, parseTs, prettyPhase, getPhase, getAgent, isToolEvent };

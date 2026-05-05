/*
 * Builder transcript compiler.
 *
 * The center workspace must behave like a code-agent transcript, not a fixed
 * phase board. This model keeps the user's goal pinned first, then emits the
 * same kinds of blocks the best code builders render: assistant text, thinking,
 * grouped progress, proof, and
 * handoff checkpoints.
 */

import { fileBasename } from './narrateBuildEvent';
import {
  humanIssueSummary,
  humanVerificationFailureSummary,
  technicalDetailLines,
} from './presentBuildThread';

const INSPECTION_TOOLS = new Set(['Inspect', 'Search']);
const FILE_TOOLS = new Set(['Files', 'Edit']);
const FAILURE_EVENT_TYPES =
  /^(step_failed|job_failed|verifier_failed|assembly_failed|export_gate_blocked|error|dag_node_failed)$/;

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
  const c = event?.created_at || event?.ts || event?.timestamp;
  if (typeof c === 'number') return c < 1e12 ? c * 1000 : c;
  if (typeof c === 'string') {
    const t = new Date(c).getTime();
    if (!Number.isNaN(t)) return t;
  }
  return Date.now();
};

const text = (value) => String(value || '').trim();

const compact = (value, max = 240) => {
  const s = text(value).replace(/\s+/g, ' ');
  if (s.length <= max) return s;
  return `${s.slice(0, max - 1)}...`;
};

const titleCase = (value) =>
  text(value)
    .replace(/[._-]+/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());

const firstOf = (...values) => values.map(text).find(Boolean) || '';

const filterEventsForJob = (events, activeJobId) =>
  (events || []).filter((ev) => {
    if (!ev) return false;
    if (!activeJobId) return true;
    const evJob = ev.job_id || ev.jobId || readPayload(ev).job_id || readPayload(ev).jobId;
    return !evJob || evJob === activeJobId;
  });

const pathFromPayload = (p) =>
  firstOf(
    p.file,
    p.path,
    p.file_path,
    p.filePath,
    p.target,
    p.proof_path,
    p.check_id,
    p.step_key,
  );

const stepName = (event) => {
  const p = readPayload(event);
  return firstOf(
    p.name,
    p.title,
    p.label,
    p.step,
    p.step_key,
    p.node_id,
    p.phase,
    event.step_key,
  );
};

const prettyStep = (event, fallback = 'Run task') => {
  const raw = stepName(event);
  if (!raw) return fallback;
  return titleCase(raw)
    .replace(/\bDag\b/g, 'Task')
    .replace(/\bUi\b/g, 'UI')
    .replace(/\bApi\b/g, 'API');
};

const eventStatus = (type) => {
  if (/(started|queued|running|repair_started|tool_call)$/i.test(type)) return 'running';
  if (/(failed|blocked|error)$/i.test(type)) return 'failed';
  if (/(completed|passed|ready|written|updated|result|snapshot|created)$/i.test(type)) return 'success';
  return 'success';
};

const toolNameFromCall = (p) => {
  const raw = firstOf(p.name, p.tool_name, p.tool, p.command_name, p.kind);
  const low = raw.toLowerCase();
  if (/bash|shell|terminal|cmd|command/.test(low)) return 'Checks';
  if (/read|open|cat|glob|list/.test(low)) return 'Inspect';
  if (/write|create/.test(low)) return 'Files';
  if (/edit|patch|mutation|replace/.test(low)) return 'Edit';
  if (/grep|search/.test(low)) return 'Search';
  if (/web/.test(low)) return 'Web';
  if (/todo|plan/.test(low)) return 'Plan';
  return raw ? titleCase(raw) : 'Work';
};

const toolInputFromPayload = (p) =>
  firstOf(
    p.command,
    p.input,
    p.query,
    p.pattern,
    p.path,
    p.file,
    p.file_path,
    p.url,
    p.detail,
    p.summary,
  );

const extractPlanSteps = (event) => {
  const p = readPayload(event);
  const candidate =
    p.steps || p.plan_steps || p.checklist || (p.plan && (p.plan.steps || p.plan.checklist));
  if (!Array.isArray(candidate)) return [];
  return candidate
    .map((s, i) => {
      if (typeof s === 'string') return { id: `todo-${i}`, label: s, status: 'pending' };
      if (s && typeof s === 'object') {
        return {
          id: s.id || `todo-${i}`,
          label: firstOf(s.label, s.title, s.name, s.text, `Task ${i + 1}`),
          status: s.status || 'pending',
        };
      }
      return null;
    })
    .filter(Boolean);
};

const assistantTextForEvent = (event) => {
  const p = readPayload(event);
  const t = event.type || event.event_type || '';
  if (t === 'plan_created' && extractPlanSteps(event).length) {
    return '';
  }
  const body = firstOf(p.message, p.text, p.content, p.narration, p.summary);
  if (body && /i am on it|i will inspect the workspace|use tools to write/i.test(body)) {
    return '';
  }
  if (body) return body;
  if (t === 'job_started') {
    return '';
  }
  if (t === 'plan_created' && !extractPlanSteps(event).length) {
    return '';
  }
  if (t === 'repair_started') {
    return '';
  }
  if (t === 'job_completed') {
    return 'The workspace has been updated and proof is ready to inspect.';
  }
  return '';
};

const failureText = (event) => {
  const t = event.type || event.event_type || '';
  if (t === 'verifier_failed') return humanVerificationFailureSummary(readPayload(event));
  if (t === 'job_failed') {
    const p = readPayload(event);
    const plain = firstOf(p.message, p.summary, p.reason, p.failure_reason);
    if (plain && plain.length < 180 && !/claude|tool loop|npm err|stack trace|stderr|verification\.|steps_failed/i.test(plain)) {
      return plain;
    }
    return 'Proof is still failing. The check output is being used to repair the workspace and rerun proof.';
  }
  return humanIssueSummary(event);
};

const toolBlockForEvent = (event) => {
  const t = event.type || event.event_type || '';
  const p = readPayload(event);
  const status = eventStatus(t);
  const path = pathFromPayload(p);
  const base = fileBasename(path);

  if (t === 'tool_call') {
    const tool = toolNameFromCall(p);
    return {
      tool,
      title: firstOf(p.title, p.label, `${tool} ${compact(toolInputFromPayload(p), 80)}`),
      input: toolInputFromPayload(p),
      status: 'running',
      result: '',
      raw: p,
    };
  }

  if (t === 'tool_result') {
    const tool = toolNameFromCall(p);
    const result = firstOf(p.output, p.result, p.summary, p.message, p.error);
    return {
      tool,
      title: firstOf(p.title, p.label, `${tool} result`),
      input: toolInputFromPayload(p),
      status: p.error ? 'failed' : 'success',
      result,
      raw: p,
    };
  }

  if (t === 'file_written' || t === 'file_write') {
    return {
      tool: 'Files',
      title: base ? `Saved ${base}` : 'Saved file',
      input: path,
      status: 'success',
      result: 'File saved.',
      raw: p,
    };
  }

  if (t === 'code_mutation') {
    return {
      tool: 'Edit',
      title: base ? `Edit ${base}` : 'Apply edit',
      input: path,
      status: 'success',
      result: firstOf(p.summary, p.message, 'Patch applied.'),
      raw: p,
    };
  }

  if (t === 'workspace_files_updated') {
    return {
      tool: 'Files',
      title: 'Updated workspace files',
      input: path,
      status: 'success',
      result: firstOf(p.summary, p.message, 'Workspace files updated.'),
      raw: p,
    };
  }

  if (t === 'verifier_started') {
    return {
      tool: 'Checks',
      title: firstOf(p.title, p.label, 'Running proof checks'),
      input: firstOf(p.command, p.check_id, p.step_key, 'runtime proof'),
      status: 'running',
      result: '',
      raw: p,
    };
  }

  if (t === 'verifier_passed') {
    return {
      tool: 'Checks',
      title: firstOf(p.title, p.label, 'Proof checks passed'),
      input: firstOf(p.command, p.check_id, p.step_key),
      status: 'success',
      result: firstOf(p.summary, p.message, 'Check passed.'),
      raw: p,
    };
  }

  if (FAILURE_EVENT_TYPES.test(t)) {
    return {
      tool: t === 'verifier_failed' ? 'Checks' : 'Work',
      title: firstOf(p.title, p.label, t === 'verifier_failed' ? 'Proof check failed' : 'Proof still failing'),
      input: firstOf(p.command, p.check_id, p.step_key, path),
      status: 'failed',
      result: failureText(event),
      detail: technicalDetailLines(event),
      raw: p,
    };
  }

  if (t === 'repair_started') {
    return {
      tool: 'Fix',
      title: firstOf(p.title, p.label, 'Repairing from proof error'),
      input: firstOf(p.repair_target, p.step_key, p.file, p.path),
      status: 'running',
      result: '',
      raw: p,
    };
  }

  if (t === 'repair_completed') {
    const files = Array.isArray(p.files_changed) ? p.files_changed : Array.isArray(p.files) ? p.files : [];
    return {
      tool: 'Fix',
      title: 'Workspace patched',
      input: files.join('\n'),
      status: 'success',
      result: firstOf(p.summary, p.message, files.length ? `${files.length} file(s) changed.` : 'Fix completed.'),
      raw: p,
    };
  }

  if (t === 'repair_failed') {
    return {
      tool: 'Fix',
      title: 'Fix needs another pass',
      input: firstOf(p.repair_target, p.step_key, p.file, p.path),
      status: 'failed',
      result: failureText(event),
      detail: technicalDetailLines(event),
      raw: p,
    };
  }

  if (/^(step_started|dag_node_started|phase_started)$/.test(t)) {
    return {
      tool: 'Task',
      title: prettyStep(event, 'Start task'),
      input: firstOf(p.description, p.detail, p.step_key, p.node_id),
      status: 'running',
      result: '',
      raw: p,
    };
  }

  if (/^(step_completed|dag_node_completed|phase_completed|phase_advanced)$/.test(t)) {
    return {
      tool: 'Task',
      title: prettyStep(event, 'Task complete'),
      input: firstOf(p.description, p.detail, p.step_key, p.node_id),
      status: 'success',
      result: firstOf(p.summary, p.message, 'Done.'),
      raw: p,
    };
  }

  return null;
};

const checkpointForEvent = (event) => {
  const t = event.type || event.event_type || '';
  const p = readPayload(event);
  if (t === 'run_snapshot') {
    return {
      kind: 'checkpoint',
      title: 'Runtime snapshot captured',
      body: firstOf(p.summary, p.message, p.snapshot_url, 'Preview evidence has been captured.'),
      tone: 'proof',
    };
  }
  if (t === 'contract_delta_created') {
    return {
      kind: 'checkpoint',
      title: 'Prompt contract updated',
      body: firstOf(p.summary, p.message, 'The requested scope is tracked against the generated files.'),
      tone: 'proof',
    };
  }
  if (t === 'export_gate_ready') {
    return {
      kind: 'checkpoint',
      title: 'Workspace handoff ready',
      body: firstOf(p.summary, p.message, 'Export proof is ready.'),
      tone: 'success',
    };
  }
  return null;
};

const dedupeKey = (block) => {
  if (!block) return '';
  if (block.kind === 'user_message') return `${block.kind}:${block.id}`;
  if (block.kind === 'tool_use') {
    return `${block.kind}:${block.tool}:${block.title}:${block.input}:${block.status}:${block.result}`;
  }
  return `${block.kind}:${block.title || ''}:${block.content || block.body || ''}:${block.status || ''}`;
};

const pushUnique = (items, seen, block) => {
  if (!block) return;
  const key = dedupeKey(block);
  if (key && seen.has(key)) return;
  if (key) seen.add(key);
  items.push(block);
};

const collapseProgressGroups = (items) => {
  const out = [];
  let group = null;

  const groupKind = (item) => {
    if (item.kind !== 'tool_use' || item.status === 'running') return '';
    if (INSPECTION_TOOLS.has(item.tool)) return 'inspect';
    if (FILE_TOOLS.has(item.tool) && item.status === 'success') return 'files';
    return '';
  };

  const flush = () => {
    if (!group) return;
    if (group.children.length === 1) out.push(group.children[0]);
    else {
      out.push({
        kind: 'tool_group',
        id: group.id,
        ts: group.ts,
        tool: group.tool,
        title: group.kind === 'files'
          ? `${group.children.length} file updates`
          : `${group.children.length} workspace checks`,
        status: group.children.some((c) => c.status === 'failed') ? 'failed' : 'success',
        children: group.children,
      });
    }
    group = null;
  };

  for (const item of items) {
    const kind = groupKind(item);
    if (kind) {
      if (!group || group.kind !== kind) {
        flush();
        group = {
          id: `${kind}-${item.id}`,
          ts: item.ts,
          kind,
          tool: kind === 'files' ? 'Files' : 'Inspect',
          children: [],
        };
      }
      group.children.push(item);
      continue;
    }
    flush();
    out.push(item);
  }
  flush();
  return out;
};

export function buildThreadModel({ userMessages = [], events = [], activeJobId = null } = {}) {
  const idCounter = { n: 0 };
  const newId = (prefix) => `${prefix}_${idCounter.n++}`;

  const filteredEvents = filterEventsForJob(events, activeJobId);
  const userMsgs = (userMessages || [])
    .filter((m) => !activeJobId || !m?.jobId || m.jobId === activeJobId)
    .filter((m) => text(m?.body).length > 0)
    .map((m) => ({
      ...m,
      ts: m.ts || Date.now(),
      role: m.role === 'assistant' ? 'assistant' : 'user',
    }))
    .sort((a, b) => (a.ts || 0) - (b.ts || 0));

  const firstUserIdx = userMsgs.findIndex((m) => m.role === 'user');
  const firstUser = firstUserIdx >= 0 ? userMsgs[firstUserIdx] : null;
  const restUserMsgs = userMsgs.filter((_, i) => i !== firstUserIdx);

  const restItems = [];
  const seen = new Set();

  for (const m of restUserMsgs) {
    pushUnique(restItems, seen, {
      kind: m.role === 'assistant' ? 'assistant_message' : 'user_message',
      role: m.role,
      content: m.body,
      ts: m.ts,
      id: m.id || newId(m.role === 'assistant' ? 'am' : 'um'),
    });
  }

  const sorted = [...filteredEvents]
    .map((ev) => ({ ev, ts: parseTs(ev) }))
    .sort((a, b) => a.ts - b.ts);

  for (const { ev, ts } of sorted) {
    const t = ev.type || ev.event_type || '';
    if (!t || t === 'user_instruction' || t === 'workspace_transcript') continue;

    if (t === 'brain_guidance' || t === 'message') {
      const content = assistantTextForEvent(ev);
      if (content) {
        pushUnique(restItems, seen, {
          kind: 'assistant_message',
          role: 'assistant',
          content,
          ts,
          id: newId('am'),
        });
      }
      continue;
    }

    if (t === 'job_started' || t === 'repair_started') {
      const content = assistantTextForEvent(ev);
      if (content) {
        pushUnique(restItems, seen, {
          kind: 'assistant_message',
          role: 'assistant',
          content,
          ts,
          id: newId('am'),
        });
      }
    }

    if (t === 'plan_created') {
      const content = assistantTextForEvent(ev);
      if (content) {
        pushUnique(restItems, seen, {
          kind: 'assistant_message',
          role: 'assistant',
          content,
          ts,
          id: newId('am'),
        });
      }
      const steps = extractPlanSteps(ev);
      if (steps.length) {
        pushUnique(restItems, seen, {
          kind: 'todo_list',
          title: 'Work checklist',
          steps,
          ts,
          id: newId('todo'),
        });
      }
      continue;
    }

    const checkpoint = checkpointForEvent(ev);
    if (checkpoint) {
      pushUnique(restItems, seen, { ...checkpoint, ts, id: newId('cp') });
      continue;
    }

    if (t === 'job_completed') {
      const content = assistantTextForEvent(ev);
      if (content) {
        pushUnique(restItems, seen, {
          kind: 'assistant_message',
          role: 'assistant',
          content,
          ts,
          id: newId('am'),
        });
      }
      pushUnique(restItems, seen, {
        kind: 'delivery',
        title: 'Done',
        body: 'Open Preview for the live surface and Proof for the evidence trail.',
        ts,
        id: newId('dl'),
      });
      continue;
    }

    const tool = toolBlockForEvent(ev);
    if (tool) {
      pushUnique(restItems, seen, {
        kind: 'tool_use',
        ts,
        id: newId('tu'),
        ...tool,
      });
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

  for (const item of collapseProgressGroups(restItems)) out.push(item);
  return out;
}

export function deriveCurrentActivity({ events = [], activeJobId = null } = {}) {
  const filtered = filterEventsForJob(events, activeJobId);
  if (!filtered.length) return null;

  const sorted = [...filtered]
    .map((ev) => ({ ev, ts: parseTs(ev) }))
    .sort((a, b) => b.ts - a.ts);

  const files = [];
  for (const { ev } of sorted) {
    const t = ev.type || ev.event_type || '';
    const p = readPayload(ev);
    const path = pathFromPayload(p);
    if (files.length < 3 && path && /file|code_mutation|workspace_files_updated/.test(t)) {
      if (!files.includes(path)) files.push(path);
    }
  }

  for (const { ev } of sorted) {
    const t = ev.type || ev.event_type || '';
    if (!t) continue;
    const p = readPayload(ev);
    if (t === 'job_completed' || t === 'export_gate_ready') {
      return { title: 'Workspace ready', status: 'success', files, phase: '', detailLine: '' };
    }
    if (FAILURE_EVENT_TYPES.test(t) || t === 'repair_failed') {
      return {
        title: 'Reading proof error',
        status: 'running',
        files,
        phase: '',
        detailLine: firstOf(p.check_id, p.step_key, p.error, p.failure_reason),
      };
    }
    const tool = toolBlockForEvent(ev);
    if (tool) {
      return {
        title: tool.status === 'running' ? tool.title : `${tool.tool}: ${tool.title}`,
        status: tool.status === 'failed' ? 'failed' : tool.status === 'success' ? 'success' : 'running',
        files,
        phase: tool.tool,
        detailLine: firstOf(tool.input, tool.result),
      };
    }
  }

  return null;
}

export const __test__ = {
  readPayload,
  parseTs,
  toolBlockForEvent,
  collapseProgressGroups,
  filterEventsForJob,
};

import { buildThreadModel, deriveCurrentActivity } from './buildThreadModel';

const ev = (type, payload = {}, created_at = '2026-05-03T12:00:00.000Z') => ({
  type,
  payload,
  created_at,
  job_id: 'job-1',
});

test('compiles job events into a code-agent transcript instead of a phase card', () => {
  const items = buildThreadModel({
    activeJobId: 'job-1',
    userMessages: [{ id: 'u1', role: 'user', body: 'Build a SaaS dashboard', ts: 1, jobId: 'job-1' }],
    events: [
      ev('job_started', {}, '2026-05-03T12:00:00.000Z'),
      ev('plan_created', { steps: ['Create layout', 'Run checks'] }, '2026-05-03T12:00:01.000Z'),
      ev('file_written', { path: 'src/App.jsx' }, '2026-05-03T12:00:02.000Z'),
      ev('verifier_started', { check_id: 'npm test' }, '2026-05-03T12:00:03.000Z'),
    ],
  });

  expect(items[0]).toMatchObject({ kind: 'user_message', content: 'Build a SaaS dashboard' });
  expect(items.some((item) => item.kind === 'build_progress_card')).toBe(false);
  expect(items.some((item) => item.kind === 'todo_list' && item.title === 'Work checklist')).toBe(true);
  expect(items.some((item) => item.kind === 'tool_use' && item.tool === 'Files')).toBe(true);
  expect(items.some((item) => item.kind === 'tool_use' && item.tool === 'Checks')).toBe(true);
});

test('groups completed read and search activity like the supplied message stream', () => {
  const items = buildThreadModel({
    activeJobId: 'job-1',
    userMessages: [{ id: 'u1', role: 'user', body: 'Inspect files', ts: 1, jobId: 'job-1' }],
    events: [
      ev('tool_result', { tool: 'Read', path: 'src/App.jsx', output: 'ok' }, '2026-05-03T12:00:01.000Z'),
      ev('tool_result', { tool: 'Grep', pattern: 'TODO', output: 'ok' }, '2026-05-03T12:00:02.000Z'),
    ],
  });

  const group = items.find((item) => item.kind === 'tool_group');
  expect(group).toBeTruthy();
  expect(group.children).toHaveLength(2);
});

test('deriveCurrentActivity reports the active tool rather than a generic loop phase', () => {
  const activity = deriveCurrentActivity({
    activeJobId: 'job-1',
    events: [
      ev('file_written', { path: 'src/App.jsx' }, '2026-05-03T12:00:01.000Z'),
      ev('verifier_started', { check_id: 'npm test' }, '2026-05-03T12:00:02.000Z'),
    ],
  });

  expect(activity).toMatchObject({
    title: 'Running proof checks',
    phase: 'Checks',
    status: 'running',
  });
});

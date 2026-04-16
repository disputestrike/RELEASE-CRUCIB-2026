import { buildStreamEventId, listJobToTaskEntry, normalizeJobEvents, normalizeListJobStatus } from './jobState';

describe('jobState', () => {
  test('normalizeListJobStatus coerces complete to completed', () => {
    expect(normalizeListJobStatus('complete')).toBe('completed');
    expect(normalizeListJobStatus('running')).toBe('running');
    expect(normalizeListJobStatus(undefined)).toBe('pending');
  });

  test('listJobToTaskEntry produces stable task shape from backend rows', () => {
    const entry = listJobToTaskEntry({
      id: 'job_123',
      goal: 'Build an app',
      status: 'complete',
      project_id: 'proj_1',
      created_at: '2026-04-16T12:00:00Z',
    });

    expect(entry).toEqual(
      expect.objectContaining({
        id: 'task_job_job_123',
        jobId: 'job_123',
        prompt: 'Build an app',
        status: 'completed',
        type: 'build',
        linkedProjectId: 'proj_1',
      }),
    );
    expect(typeof entry.createdAt).toBe('number');
  });

  test('listJobToTaskEntry falls back to payload goal and returns null without job id', () => {
    const withPayload = listJobToTaskEntry({
      job_id: 'job_456',
      payload: { goal: 'Fix backend' },
      status: 'running',
    });
    expect(withPayload.prompt).toBe('Fix backend');
    expect(listJobToTaskEntry({ status: 'running' })).toBeNull();
  });

  test('buildStreamEventId prefers server id and otherwise creates deterministic fallback', () => {
    expect(buildStreamEventId({ id: 'evt_1', type: 'job_started' })).toBe('evt_1');

    const fallback = buildStreamEventId({
      type: 'step_completed',
      step_id: 'step_1',
      ts: 123,
      payload: { summary: 'done' },
    });

    expect(fallback).toBe('step_completed-step_1-123-{"summary":"done"}');
  });

  test('normalizeJobEvents adds deterministic ids and removes duplicates', () => {
    const rows = [
      { type: 'step_started', step_id: 'a', ts: 1, payload: { status: 'run' } },
      { type: 'step_started', step_id: 'a', ts: 1, payload: { status: 'run' } },
      { id: 'evt_custom', type: 'job_completed', payload: { ok: true } },
    ];

    const normalized = normalizeJobEvents(rows);
    expect(normalized).toHaveLength(2);
    expect(normalized[0].id).toBe('step_started-a-1-{"status":"run"}');
    expect(normalized[1].id).toBe('evt_custom');
  });

  test('normalizeJobEvents keeps latest events within configured cap', () => {
    const rows = [
      { id: 'evt_1', type: 'a' },
      { id: 'evt_2', type: 'b' },
      { id: 'evt_3', type: 'c' },
    ];

    const normalized = normalizeJobEvents(rows, 2);
    expect(normalized).toHaveLength(2);
    expect(normalized.map((r) => r.id)).toEqual(['evt_2', 'evt_3']);
  });
});

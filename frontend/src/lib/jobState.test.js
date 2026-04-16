import { buildStreamEventId, listJobToTaskEntry, normalizeListJobStatus } from './jobState';

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
});

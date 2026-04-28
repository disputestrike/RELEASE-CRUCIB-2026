import {
  bindWorkspaceSearchParams,
  stableTaskIdForJob,
  taskEntryFromJob,
  taskStatusFromJobStatus,
} from './workspaceTaskBinding';

describe('workspaceTaskBinding', () => {
  test('maps durable job statuses into sidebar task statuses', () => {
    expect(taskStatusFromJobStatus('completed')).toBe('completed');
    expect(taskStatusFromJobStatus('failed')).toBe('failed');
    expect(taskStatusFromJobStatus('cancelled')).toBe('failed');
    expect(taskStatusFromJobStatus('running')).toBe('running');
    expect(taskStatusFromJobStatus('planned')).toBe('running');
  });

  test('creates a stable local task id for a job-only workspace URL', () => {
    expect(stableTaskIdForJob('job_123')).toBe('task_job_job_123');
    expect(stableTaskIdForJob('')).toBe('');
  });

  test('hydrates a missing task row from job truth', () => {
    const entry = taskEntryFromJob({
      jobId: 'job_abc',
      job: {
        status: 'completed',
        goal: 'Build a logistics platform\nwith drivers',
        project_id: 'project_1',
        created_at: '2026-04-25T12:00:00.000Z',
      },
    });

    expect(entry).toEqual(
      expect.objectContaining({
        id: 'task_job_job_abc',
        jobId: 'job_abc',
        linkedProjectId: 'project_1',
        name: 'Build a logistics platform',
        prompt: 'Build a logistics platform\nwith drivers',
        status: 'completed',
        type: 'build',
      }),
    );
    expect(typeof entry.createdAt).toBe('number');
  });

  test('preserves existing task title while binding job truth', () => {
    const entry = taskEntryFromJob({
      jobId: 'job_abc',
      taskId: 'task_1',
      existingTask: { id: 'task_1', name: 'Original title', prompt: 'Original prompt', createdAt: 42 },
      job: { status: 'running', goal: 'New server goal' },
    });

    expect(entry).toEqual(
      expect.objectContaining({
        id: 'task_1',
        name: 'Original title',
        prompt: 'New server goal',
        createdAt: 42,
        jobId: 'job_abc',
        status: 'running',
      }),
    );
  });

  test('binds job, task, and project ids into workspace URL params', () => {
    const params = bindWorkspaceSearchParams('panel=live', {
      jobId: 'job_1',
      taskId: 'task_1',
      projectId: 'project_1',
    });

    expect(params.get('panel')).toBe('live');
    expect(params.get('jobId')).toBe('job_1');
    expect(params.get('taskId')).toBe('task_1');
    expect(params.get('projectId')).toBe('project_1');
  });
});

import { normalizeIdentityToken, resolveCanonicalTaskIdentity } from '../../workspace/workspaceCanonicalIdentity';

describe('UnifiedWorkspace canonical identity helpers', () => {
  test('normalizeIdentityToken collapses task_job_ aliases', () => {
    expect(normalizeIdentityToken('task_job_tsk_abc123def456')).toBe('tsk_abc123def456');
    expect(normalizeIdentityToken('tsk_abc123def456')).toBe('tsk_abc123def456');
    expect(normalizeIdentityToken('')).toBe('');
  });

  test('resolveCanonicalTaskIdentity chooses one canonical id and rewrite once', () => {
    const resolved = resolveCanonicalTaskIdentity({
      jobId: 'tsk_abc123def456',
      taskId: 'task_job_tsk_abc123def456',
      sessionTaskId: 'task_job_tsk_abc123def456',
      activeTaskId: 'task_job_tsk_abc123def456',
      serverJob: { id: 'tsk_abc123def456' },
      existingTask: { id: 'task_job_tsk_abc123def456', jobId: 'tsk_abc123def456' },
      existingByJob: { id: 'task_job_tsk_abc123def456', jobId: 'tsk_abc123def456' },
      fallbackTaskId: 'task_job_tsk_abc123def456',
      currentUrlTaskId: 'task_job_tsk_abc123def456',
      lastRewriteKey: '',
    });
    expect(resolved.canonicalId).toBe('task_job_tsk_abc123def456');
    expect(resolved.shouldRewriteUrl).toBe(false);
    expect(resolved.aliases).toContain('task_job_tsk_abc123def456');
  });
});

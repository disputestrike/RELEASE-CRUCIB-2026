import {
  pickOngoingWorkspaceBuildTask,
  setCanonicalWorkspaceTaskId,
  clearCanonicalWorkspaceTaskId,
} from './canonicalWorkspaceTask';

describe('canonicalWorkspaceTask', () => {
  beforeEach(() => clearCanonicalWorkspaceTaskId());

  it('persists canonical first when present', () => {
    setCanonicalWorkspaceTaskId('tid_a');
    const r = pickOngoingWorkspaceBuildTask([
      { id: 'tid_a', type: 'build', status: 'completed', createdAt: 1 },
      { id: 'tid_b', type: 'build', status: 'failed', createdAt: 99 },
    ]);
    expect(r.id).toBe('tid_a');
    expect(r.mode).toBe('canonical');
  });

  it('falls back to newest open build when canonical missing', () => {
    const r = pickOngoingWorkspaceBuildTask([
      { id: 'old', type: 'build', status: 'completed', createdAt: 1 },
      { id: 'new_open', type: 'build', status: 'failed', createdAt: 200 },
    ]);
    expect(r.id).toBe('new_open');
    expect(r.mode).toBe('open_fallback');
  });
});

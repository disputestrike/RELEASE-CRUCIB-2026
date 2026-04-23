import {
  computeDockMeta,
  computeDockMetaPreJob,
  deriveRightRailSubtitle,
  isWorkspaceLiveBuildPhase,
  selectWorkspacePreviewStatus,
} from './workspaceLiveUi';

describe('computeDockMeta', () => {
  test('approved job with no steps shows starting title and state', () => {
    const m = computeDockMeta({
      job: { status: 'approved' },
      steps: [],
      stage: 'running',
      events: [],
    });
    expect(m.title).toBe('Starting your run');
    expect(m.stateKey).toBe('working');
    expect(m.stateLabel).toBe('Starting');
  });

  test('queued job maps to queued state', () => {
    const m = computeDockMeta({
      job: { status: 'queued' },
      steps: [],
      stage: 'running',
      events: [],
    });
    expect(m.stateKey).toBe('queued');
    expect(m.stateLabel).toBe('In queue');
  });

  test('plan stage waits on user even if job row missing', () => {
    const m = computeDockMeta({
      job: null,
      steps: [],
      stage: 'plan',
      events: [],
    });
    expect(m.stateKey).toBe('waiting');
    expect(m.stateLabel).toBe('Waiting for you');
  });
});

describe('computeDockMetaPreJob', () => {
  test('input stage shows ready strip', () => {
    const m = computeDockMetaPreJob({ stage: 'input', loading: false });
    expect(m.stateLabel).toBe('Ready');
    expect(m.title).toContain('build');
  });

  test('loading shows working', () => {
    const m = computeDockMetaPreJob({ stage: 'input', loading: true });
    expect(m.stateKey).toBe('working');
  });
});

describe('deriveRightRailSubtitle', () => {
  test('uses running step when no events', () => {
    const s = deriveRightRailSubtitle([], [
      { order_index: 0, status: 'running', agent_name: 'agents.codegen', step_key: 'x' },
    ]);
    expect(s).toMatch(/Working on/);
  });
});

describe('isWorkspaceLiveBuildPhase', () => {
  test('true for approved even when stage has not flipped yet', () => {
    expect(isWorkspaceLiveBuildPhase({ jobStatus: 'approved', stage: 'input' })).toBe(true);
  });

  test('false during plan review', () => {
    expect(isWorkspaceLiveBuildPhase({ jobStatus: 'planned', stage: 'plan' })).toBe(false);
  });
});

describe('selectWorkspacePreviewStatus', () => {
  test('blocked when job failed', () => {
    expect(
      selectWorkspacePreviewStatus({ jobStatus: 'failed', stage: 'running', isCompleted: false }),
    ).toBe('blocked');
  });

  test('building when approved or queued', () => {
    expect(
      selectWorkspacePreviewStatus({ jobStatus: 'approved', stage: 'running', isCompleted: false }),
    ).toBe('building');
    expect(
      selectWorkspacePreviewStatus({ jobStatus: 'queued', stage: 'input', isCompleted: false }),
    ).toBe('building');
  });

  test('building when stage running even if job row lags', () => {
    expect(
      selectWorkspacePreviewStatus({ jobStatus: undefined, stage: 'running', isCompleted: false }),
    ).toBe('building');
  });

  test('idle during plan review', () => {
    expect(
      selectWorkspacePreviewStatus({ jobStatus: 'planned', stage: 'plan', isCompleted: false }),
    ).toBe('idle');
  });

  test('ready when completed', () => {
    expect(
      selectWorkspacePreviewStatus({ jobStatus: 'completed', stage: 'completed', isCompleted: true }),
    ).toBe('ready');
  });
});

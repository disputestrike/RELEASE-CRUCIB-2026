import {
  computeDockMeta,
  computeDockMetaPreJob,
  deriveRightRailSubtitle,
  derivePreviewReadiness,
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

describe('derivePreviewReadiness', () => {
  test('shows remote URL as live', () => {
    const r = derivePreviewReadiness({ previewUrl: 'https://example.com', hasSandpack: false });
    expect(r.state).toBe('remote_live');
    expect(r.severity).toBe('ok');
  });

  test('prefers Sandpack fallback when files are packable', () => {
    const r = derivePreviewReadiness({ previewStatus: 'building', hasSandpack: true });
    expect(r.state).toBe('sandpack_fallback');
    expect(r.label).toBe('File preview');
  });

  test('reports waiting for index with file count', () => {
    const r = derivePreviewReadiness({
      previewStatus: 'building',
      hasSandpack: false,
      devPreviewStatus: { preview_state: 'waiting_for_index', readiness: { file_count: 7 } },
    });
    expect(r.state).toBe('waiting_for_index');
    expect(r.detail).toContain('7 files');
  });

  test('reports completed build without preview target as warning', () => {
    const r = derivePreviewReadiness({ previewStatus: 'ready', hasSandpack: false });
    expect(r.state).toBe('ready_without_target');
    expect(r.severity).toBe('warn');
  });
});

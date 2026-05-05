import {
  computeDockMeta,
  computeDockMetaPreJob,
  deriveRightRailSubtitle,
  derivePreviewReadiness,
  extractActivityChips,
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

  test('uses shared event formatter for latest high-signal events', () => {
    const s = deriveRightRailSubtitle(
      [
        { type: 'step_started', payload: { agent_name: 'agents.backend' } },
        { type: 'file_written', payload: { path: 'src/App.jsx' } },
      ],
      [],
    );
    expect(s).toBe('Saved file: App.jsx');
  });
});

describe('extractActivityChips', () => {
  test('uses shared event formatter for rich workspace events', () => {
    const chips = extractActivityChips([
      { id: 'a', type: 'artifact_delta', payload: { added: 1, changed: 2, removed: 0 } },
      { id: 'b', type: 'code_repair_applied', payload: { failure_type: 'syntax_error', files: ['src/App.jsx'] } },
      { id: 'c', type: 'step_infrastructure_failure', payload: {} },
    ]);

    expect(chips).toEqual([
      { id: 'a', label: 'Files changed: 1 added, 2 updated, 0 removed', kind: 'info' },
      { id: 'b', label: 'Repair applied after syntax error: App.jsx', kind: 'info' },
      {
        id: 'c',
        label: 'Infrastructure issue: run stopped for a host or dependency failure',
        kind: 'warn',
      },
    ]);
  });

  test('deduplicates events and preserves chronological display order', () => {
    const chips = extractActivityChips(
      [
        { id: 'same', type: 'step_started', payload: { agent_name: 'agents.frontend' } },
        { id: 'same', type: 'step_completed', payload: { agent_name: 'agents.frontend' } },
        { id: 'done', type: 'file_written', payload: { path: 'src/styles.css' } },
      ],
      10,
    );

    expect(chips).toEqual([
      { id: 'same', label: 'Done: Frontend', kind: 'ok' },
      { id: 'done', label: 'Saved file: styles.css', kind: 'ok' },
    ]);
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
    expect(r.label).toBe('Preview URL');
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

  test('reports source-only preview as waiting for build instead of live', () => {
    const r = derivePreviewReadiness({
      previewStatus: 'building',
      hasSandpack: false,
      devPreviewStatus: { preview_state: 'waiting_for_build', readiness: { reason: 'source_index_needs_build' } },
    });
    expect(r.state).toBe('waiting_for_build');
    expect(r.label).toBe('Building preview');
  });

  test('reports failed preview materialization as a real error', () => {
    const r = derivePreviewReadiness({
      hasSandpack: false,
      devPreviewStatus: { status: 'blocked', preview_state: 'build_failed', detail: 'npm run build failed' },
    });
    expect(r.state).toBe('build_failed');
    expect(r.severity).toBe('error');
    expect(r.detail).toContain('npm run build failed');
  });

  test('reports completed build without preview target as warning', () => {
    const r = derivePreviewReadiness({ previewStatus: 'ready', hasSandpack: false });
    expect(r.state).toBe('ready_without_target');
    expect(r.severity).toBe('warn');
  });
});

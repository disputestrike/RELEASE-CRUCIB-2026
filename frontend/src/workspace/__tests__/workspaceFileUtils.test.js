import {
  normalizeWorkspacePath,
  buildTraceIndexFromEvents,
  guessViewerKind,
  pathsToNestedTree,
} from '../workspaceFileUtils';

describe('workspaceFileUtils', () => {
  test('normalizeWorkspacePath', () => {
    expect(normalizeWorkspacePath('/client/src/App.tsx')).toBe('client/src/App.tsx');
    expect(normalizeWorkspacePath('docs\\\\a.md')).toBe('docs/a.md');
  });

  test('guessViewerKind', () => {
    expect(guessViewerKind('a.png')).toBe('image');
    expect(guessViewerKind('x.zip')).toBe('binary');
    expect(guessViewerKind('src/App.tsx')).toBe('text');
  });

  test('buildTraceIndexFromEvents uses dag_node_completed only', () => {
    const steps = [{ id: 's1', agent_name: 'FrontendAgent', step_key: 'frontend.gen' }];
    const events = [
      { type: 'step_started', step_id: 's1', ts: '2026-01-01T00:00:00Z' },
      {
        type: 'dag_node_completed',
        step_id: 's1',
        ts: '2026-01-01T00:00:01Z',
        id: 'e2',
        payload: { output_files: ['client/src/App.tsx'], step_id: 's1' },
      },
    ];
    const ix = buildTraceIndexFromEvents(events, steps);
    expect(ix['client/src/App.tsx']).toEqual(
      expect.objectContaining({
        agent: 'FrontendAgent',
        step_key: 'frontend.gen',
        step_id: 's1',
        event_id: 'e2',
      }),
    );
  });

  test('pathsToNestedTree marks directories vs files', () => {
    const root = pathsToNestedTree(['client/a.js', 'client/b/c.js']);
    expect(root.children.has('client')).toBe(true);
    const client = root.children.get('client');
    expect(client.isFile).toBe(false);
    expect(client.children.get('a.js').isFile).toBe(true);
    expect(client.children.get('b').isFile).toBe(false);
  });
});

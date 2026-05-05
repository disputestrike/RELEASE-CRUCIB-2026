import { formatWorkspaceActivityEvent, humanizeActivityAgentLabel } from './workspaceActivityEvents';

describe('workspaceActivityEvents', () => {
  test('humanizes agent and step names', () => {
    expect(humanizeActivityAgentLabel('agents.frontend_agent')).toBe('Frontend Agent');
    expect(humanizeActivityAgentLabel('verification.preview')).toBe('Verification Preview');
  });

  test('formats file-writing progress from dag events', () => {
    expect(
      formatWorkspaceActivityEvent({
        type: 'dag_node_completed',
        payload: {
          output_files: ['src/App.jsx', 'src/styles.css', 'backend/main.py', 'README.md', 'package.json'],
        },
      }),
    ).toBe('Wrote 5 file(s): App.jsx, styles.css, main.py, README.md...');
  });

  test('formats direct file-written events', () => {
    expect(formatWorkspaceActivityEvent({ type: 'file_written', payload: { path: 'src/App.jsx' } })).toBe(
      'Saved file: App.jsx',
    );
  });

  test('formats events when payload is serialized JSON', () => {
    expect(
      formatWorkspaceActivityEvent({
        type: 'file_written',
        payload: JSON.stringify({ path: 'src/App.jsx' }),
      }),
    ).toBe('Saved file: App.jsx');
    expect(
      formatWorkspaceActivityEvent({
        type: 'verification_result',
        payload: JSON.stringify({ passed: true, score: 92 }),
      }),
    ).toBe('Proof: passed (92)');
  });

  test('falls back to payload_json when payload is absent', () => {
    expect(
      formatWorkspaceActivityEvent({
        type: 'code_repair_applied',
        payload_json: JSON.stringify({ failure_type: 'syntax_error', files: ['src/App.jsx'] }),
      }),
    ).toBe('Fix applied after syntax error: App.jsx');
  });

  test('formats repair and artifact delta events', () => {
    expect(
      formatWorkspaceActivityEvent({
        type: 'code_repair_applied',
        payload: { failure_type: 'syntax_error', files: ['src/App.jsx'] },
      }),
    ).toBe('Fix applied after syntax error: App.jsx');
    expect(formatWorkspaceActivityEvent({ type: 'artifact_delta', payload: { added: 2, changed: 3, removed: 1 } })).toBe(
      'Files changed: 2 added, 3 updated, 1 removed',
    );
  });

  test('formats failure and infrastructure events', () => {
    expect(formatWorkspaceActivityEvent({ type: 'job_failed', payload: { failure_reason: 'preview_gate_failed' } })).toBe(
      'Proof failed - checking error',
    );
    expect(formatWorkspaceActivityEvent({ type: 'step_infrastructure_failure', payload: {} })).toBe(
      'Infrastructure issue: run stopped for a host or dependency failure',
    );
  });
});

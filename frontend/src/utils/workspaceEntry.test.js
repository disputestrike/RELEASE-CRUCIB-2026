import { extractWorkspaceLaunchIntent } from './workspaceEntry';

describe('workspaceEntry', () => {
  test('extracts prompt from initialPrompt and autoStart from state', () => {
    const intent = extractWorkspaceLaunchIntent({
      locationState: { initialPrompt: 'Build a CRM', autoStart: true, handoffNonce: 'abc' },
      search: '',
    });

    expect(intent.prompt).toBe('Build a CRM');
    expect(intent.autoStart).toBe(true);
    expect(intent.shouldSeedComposer).toBe(true);
    expect(intent.handoffKey).toBe('nonce:abc');
  });

  test('uses suggestedPrompt when initialPrompt is absent', () => {
    const intent = extractWorkspaceLaunchIntent({
      locationState: { suggestedPrompt: 'Create a weekday automation' },
      search: '',
    });

    expect(intent.prompt).toBe('Create a weekday automation');
    expect(intent.autoStart).toBe(false);
    expect(intent.shouldSeedComposer).toBe(true);
  });

  test('extracts query prompt and autoStart from search', () => {
    const intent = extractWorkspaceLaunchIntent({
      locationState: null,
      search: '?prompt=Ship%20an%20app&autoStart=true',
    });

    expect(intent.prompt).toBe('Ship an app');
    expect(intent.autoStart).toBe(true);
    expect(intent.hasPromptInQuery).toBe(true);
    expect(intent.handoffKey).toBe('query:Ship an app:1');
  });

  test('returns no seed when no prompt exists', () => {
    const intent = extractWorkspaceLaunchIntent({
      locationState: { newProject: true },
      search: '',
    });

    expect(intent.prompt).toBe('');
    expect(intent.shouldSeedComposer).toBe(false);
    expect(intent.handoffKey).toBeNull();
  });
});

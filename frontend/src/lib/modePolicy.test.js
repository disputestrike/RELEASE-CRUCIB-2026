import { getWorkspaceCapabilities, resolveWorkspaceMode } from './modePolicy';

describe('modePolicy', () => {
  test('defaults to simple mode', () => {
    expect(resolveWorkspaceMode(null)).toBe('simple');
    expect(resolveWorkspaceMode({})).toBe('simple');
    expect(resolveWorkspaceMode({ workspace_mode: 'simple' })).toBe('simple');
  });

  test('enables developer mode capabilities', () => {
    const caps = getWorkspaceCapabilities({ workspace_mode: 'developer' });
    expect(caps.isDeveloperMode).toBe(true);
    expect(caps.canUseAdvancedControls).toBe(true);
    expect(caps.canUseLiveStream).toBe(true);
    expect(caps.canUseTerminal).toBe(true);
  });

  test('internal users get developer capabilities', () => {
    const caps = getWorkspaceCapabilities({ workspace_mode: 'simple', internal_team: true });
    expect(caps.mode).toBe('simple');
    expect(caps.isDeveloperMode).toBe(true);
    expect(caps.canViewDebugLogs).toBe(true);
  });

  test('simple mode keeps advanced capabilities off', () => {
    const caps = getWorkspaceCapabilities({ workspace_mode: 'simple' });
    expect(caps.isDeveloperMode).toBe(false);
    expect(caps.canUseAdvancedControls).toBe(false);
    expect(caps.canUseLiveStream).toBe(false);
    expect(caps.canUseTerminal).toBe(false);
    expect(caps.canRunParallelProbe).toBe(false);
  });
});

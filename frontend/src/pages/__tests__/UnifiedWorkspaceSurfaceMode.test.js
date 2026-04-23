import { paneForWorkspaceSurface } from '../../workspace/workspaceSurfaceMode';

describe('UnifiedWorkspace surface mode mapping', () => {
  it('maps canonical surfaces to expected panes', () => {
    expect(paneForWorkspaceSurface('build', 'pro', false)).toBe('preview');
    expect(paneForWorkspaceSurface('inspect', 'pro', false)).toBe('timeline');
    expect(paneForWorkspaceSurface('what-if', 'pro', false)).toBe('explorer');
    expect(paneForWorkspaceSurface('what-if', 'simple', false)).toBe('timeline');
    expect(paneForWorkspaceSurface('deploy', 'pro', false)).toBe('preview');
    expect(paneForWorkspaceSurface('repair', 'pro', false)).toBe('timeline');
    expect(paneForWorkspaceSurface('repair', 'pro', true)).toBe('failure');
  });

  it('falls back to build-like preview behavior for unknown surfaces', () => {
    expect(paneForWorkspaceSurface('unknown', 'pro', false)).toBe('preview');
  });
});

export function paneForWorkspaceSurface(surface, uxMode, hasFailure) {
  switch (surface) {
    case 'inspect':
      return 'timeline';
    case 'what-if':
      return uxMode === 'pro' ? 'explorer' : 'timeline';
    case 'repair':
      return hasFailure ? 'failure' : 'timeline';
    case 'deploy':
      return 'preview';
    case 'build':
    default:
      return 'preview';
  }
}

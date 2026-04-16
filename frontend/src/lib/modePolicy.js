export function resolveWorkspaceMode(user) {
  const mode = String(user?.workspace_mode || '').toLowerCase();
  if (mode === 'developer') return 'developer';
  return 'simple';
}

export function getWorkspaceCapabilities(user) {
  const mode = resolveWorkspaceMode(user);
  const isInternal = Boolean(user?.internal_team);
  const isDeveloperMode = mode === 'developer' || isInternal;

  return {
    mode,
    isDeveloperMode,
    canUseAdvancedControls: isDeveloperMode,
    canUseLiveStream: isDeveloperMode,
    canUseTerminal: isDeveloperMode,
    canViewDebugLogs: isDeveloperMode,
    canGenerateSkills: isDeveloperMode,
    canRunSimulation: isDeveloperMode,
    canRunParallelProbe: isDeveloperMode,
  };
}

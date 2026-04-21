import React, { createContext, useContext, useMemo } from 'react';

const WorkspaceNavContext = createContext(null);

export function WorkspaceNavProvider({ value, children }) {
  const memo = useMemo(() => value || {}, [value]);
  return <WorkspaceNavContext.Provider value={memo}>{children}</WorkspaceNavContext.Provider>;
}

/**
 * Shared navigation for workspace paths (Code pane, proof, timeline, failures, activity).
 * Returns null fields when used outside UnifiedWorkspace provider.
 */
export function useWorkspaceNav() {
  return useContext(WorkspaceNavContext);
}

import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';

const WorkspaceRailContext = createContext(null);

export function WorkspaceRailProvider({ children }) {
  const [rail, setRailState] = useState(null);
  const setWorkspaceRail = useCallback((node) => {
    setRailState(node);
  }, []);
  const clearWorkspaceRail = useCallback(() => {
    setRailState(null);
  }, []);
  const value = useMemo(
    () => ({ rail, setWorkspaceRail, clearWorkspaceRail }),
    [rail, setWorkspaceRail, clearWorkspaceRail],
  );
  return <WorkspaceRailContext.Provider value={value}>{children}</WorkspaceRailContext.Provider>;
}

export function useWorkspaceRail() {
  const v = useContext(WorkspaceRailContext);
  if (!v) {
    return { rail: null, setWorkspaceRail: () => {}, clearWorkspaceRail: () => {} };
  }
  return v;
}

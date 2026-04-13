/**
 * PHASE 3 — Single layout state authority.
 * Mode syncs from user.workspace_mode (backend). Toggle saves via API.
 */
import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { useAuth } from '../App';

const LayoutContext = createContext(null);

export function LayoutProvider({ children }) {
  const { user } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mode, setModeState] = useState('simple');

  // Sync mode from user.workspace_mode when user loads
  useEffect(() => {
    if (user?.workspace_mode === 'developer') setModeState('dev');
    else if (user?.workspace_mode === 'simple') setModeState('simple');
  }, [user?.workspace_mode]);

  useEffect(() => {
    try {
      localStorage.setItem('crucibai_dev_mode', mode === 'dev' ? 'true' : 'false');
    } catch (_) { void 0; }
  }, [mode]);

  const setMode = useCallback((next) => {
    setModeState(prev => (typeof next === 'function' ? next(prev) : next));
  }, []);

  const toggleSidebar = useCallback(() => {
    setSidebarOpen(prev => !prev);
  }, []);

  const value = {
    sidebarOpen,
    setSidebarOpen,
    toggleSidebar,
    mode,
    setMode,
    isSimple: mode === 'simple',
    isDev: mode === 'dev',
  };

  return (
    <LayoutContext.Provider value={value}>
      {children}
    </LayoutContext.Provider>
  );
}

export function useLayoutStore() {
  const ctx = useContext(LayoutContext);
  if (!ctx) {
    return {
      sidebarOpen: true,
      setSidebarOpen: () => {},
      toggleSidebar: () => {},
      mode: 'simple',
      setMode: () => {},
      isSimple: true,
      isDev: false,
    };
  }
  return ctx;
}

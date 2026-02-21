/**
 * PHASE 3 — Single layout state authority.
 * Sidebar and mode live here only. Persist mode to localStorage.
 */
import { createContext, useContext, useState, useCallback, useEffect } from 'react';

const LAYOUT_STORAGE_KEY = 'crucibai_layout';

const LayoutContext = createContext(null);

export function LayoutProvider({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mode, setModeState] = useState(() => {
    try {
      return localStorage.getItem('crucibai_dev_mode') === 'true' ? 'dev' : 'simple';
    } catch {
      return 'simple';
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem('crucibai_dev_mode', mode === 'dev' ? 'true' : 'false');
    } catch (_) {}
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

import React, { createContext, useContext, useMemo, useState, useEffect } from 'react';

const AuthContext = createContext(null);

const STORAGE_KEY = 'crucibai_demo_token';

/**
 * Client-only auth demo. CRUCIB_INCOMPLETE: exchange credentials with your API.
 */
export function AuthProvider({ children }) {
  const [token, setTokenState] = useState(() => localStorage.getItem(STORAGE_KEY) || '');

  useEffect(() => {
    if (token) localStorage.setItem(STORAGE_KEY, token);
    else localStorage.removeItem(STORAGE_KEY);
  }, [token]);

  const value = useMemo(
    () => ({
      token,
      isAuthenticated: Boolean(token),
      login: (demoUser) => {
        setTokenState(`demo.${(demoUser || 'user').slice(0, 24)}.${Date.now()}`);
      },
      logout: () => setTokenState(''),
    }),
    [token],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

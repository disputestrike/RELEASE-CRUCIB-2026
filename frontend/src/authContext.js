import { createContext, useContext } from 'react';

export const DEFAULT_AUTH_CONTEXT = Object.freeze({
  user: null,
  token: null,
  loading: false,
  login: async () => null,
  register: async () => null,
  logout: () => {},
  refreshUser: async () => null,
  loginWithToken: async () => null,
  verifyMfa: async () => null,
  ensureGuest: async () => null,
  enterDemoMode: () => {},
});

export const AuthContext = createContext(DEFAULT_AUTH_CONTEXT);
export const useAuth = () => useContext(AuthContext) || DEFAULT_AUTH_CONTEXT;

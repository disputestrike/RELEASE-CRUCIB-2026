/**
 * Auth context — separated from App.js to break circular dependencies.
 * App.js re-exports these for backward compat.
 */
import { createContext, useContext } from 'react';

const defaultAuthContext = {
  user: null,
  token: null,
  login: () => {},
  logout: () => {},
  loading: false,
};

export const AuthContext = createContext(defaultAuthContext);
export const useAuth = () => useContext(AuthContext) || defaultAuthContext;

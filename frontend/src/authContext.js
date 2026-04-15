/**
 * Auth context — separated from App.js to break circular dependencies.
 * App.js re-exports these for backward compat.
 */
import { createContext, useContext } from 'react';

export const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

/**
 * Global UI + preferences (persisted to localStorage).
 * CRUCIB_INCOMPLETE: sync with server when you add a real API.
 */
export const useAppStore = create(
  persist(
    (set, get) => ({
      theme: 'dark',
      lastRoute: '/',
      notes: '',
      setTheme: (theme) => set({ theme }),
      setLastRoute: (lastRoute) => set({ lastRoute }),
      setNotes: (notes) => set({ notes }),
      reset: () => set({ theme: 'dark', lastRoute: '/', notes: '' }),
    }),
    {
      name: 'crucibai-app-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({ theme: s.theme, lastRoute: s.lastRoute, notes: s.notes }),
    },
  ),
);

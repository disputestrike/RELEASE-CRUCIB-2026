# Generated app (CrucibAI Auto-Runner)

## Product goal
Build a learning platform with course browsing, learner login, progress dashboard, saved study notes, and export-ready proof.

## What is production-grade here
- File layout: `src/pages`, `src/components`, `src/store`, `src/context`
- **React Router** (`MemoryRouter` for Sandpack iframe safety)
- **Zustand** store with **persist** middleware → `localStorage`
- **AuthContext** with token in `localStorage` (client-only demo — not server session)
- Reusable **ShellLayout** and page components

## Explicitly incomplete (CRUCIB_INCOMPLETE)
- No real OAuth / server session — replace `AuthContext` login with your API
- Backend in `backend/` is a sketch; wire your own API base URL

## Preview
- Workspace **Preview** tab (Sandpack) for interactive editing
- Auto-Runner **preview gate** runs `npm install`, `vite build`, and **Playwright** (headless Chromium) against `dist/` — backend needs `python -m playwright install chromium`

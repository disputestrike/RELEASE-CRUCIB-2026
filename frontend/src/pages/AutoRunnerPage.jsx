/**
 * Back-compat: autonomous build UI is `UnifiedWorkspace` at `/app/workspace`.
 * Route `/app/auto-runner` redirects in App.js; this re-export keeps any legacy import working.
 */
export { default } from './UnifiedWorkspace';

/**
 * Unique nonce for each navigate-to-workspace handoff so UnifiedWorkspace
 * never drops a repeat visit with the same prompt (dedupe used to key only on text).
 */
export function withWorkspaceHandoffNonce(state) {
  if (!state || typeof state !== 'object') return { handoffNonce: Date.now() };
  return { ...state, handoffNonce: Date.now() };
}

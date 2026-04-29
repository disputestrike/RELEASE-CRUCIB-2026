/**
 * Unified Workspace Handoff — Single Source of Truth
 * 
 * RULE: Only React Router navigation state is used.
 * NO sessionStorage fallback.
 * NO query param duplication.
 * 
 * Schema:
 * {
 *   prompt: string,
 *   autoStart: boolean,
 *   source: "landing" | "chat",
 *   handoffNonce: number  // prevents dedupe
 * }
 */

const HANDOFF_SCHEMA_VERSION = 1;

/**
 * Create a validated handoff object for navigation state.
 * This is the ONLY way to pass intent into the workspace.
 */
export function createWorkspaceHandoff({ prompt, autoStart = true, source }) {
  if (!prompt || typeof prompt !== 'string') {
    throw new Error('Workspace handoff requires a valid prompt string');
  }
  
  if (!source || !['landing', 'chat'].includes(source)) {
    throw new Error('Workspace handoff requires source: "landing" or "chat"');
  }
  
  return {
    _handoff: true,
    _version: HANDOFF_SCHEMA_VERSION,
    prompt: prompt.trim(),
    autoStart,
    source,
    handoffNonce: Date.now() + Math.random()
  };
}

/**
 * Validate and extract handoff from navigation state.
 * Returns null if invalid or missing.
 */
export function extractWorkspaceHandoff(state) {
  if (!state || typeof state !== 'object') return null;
  
  // Must have the handoff marker
  if (!state._handoff) return null;
  
  // Version check for future migrations
  if (state._version !== HANDOFF_SCHEMA_VERSION) {
    console.warn(`[UnifiedHandoff] Version mismatch: expected ${HANDOFF_SCHEMA_VERSION}, got ${state._version}`);
    return null;
  }
  
  // Required fields
  if (!state.prompt || typeof state.prompt !== 'string') {
    console.warn('[UnifiedHandoff] Missing or invalid prompt');
    return null;
  }
  
  if (!state.source || !['landing', 'chat'].includes(state.source)) {
    console.warn('[UnifiedHandoff] Missing or invalid source');
    return null;
  }
  
  return {
    prompt: state.prompt,
    autoStart: Boolean(state.autoStart),
    source: state.source,
    handoffNonce: state.handoffNonce
  };
}

/**
 * Check if state contains a valid handoff.
 */
export function hasValidHandoff(state) {
  return extractWorkspaceHandoff(state) !== null;
}

/**
 * Debug helper: log handoff extraction
 */
export function debugHandoff(state, label = '') {
  const handoff = extractWorkspaceHandoff(state);
  if (handoff) {
    console.log(`[UnifiedHandoff${label ? ' ' + label : ''}] Valid:`, {
      source: handoff.source,
      autoStart: handoff.autoStart,
      promptPreview: handoff.prompt.slice(0, 50) + '...'
    });
  } else {
    console.log(`[UnifiedHandoff${label ? ' ' + label : ''}] No valid handoff in state`);
  }
  return handoff;
}

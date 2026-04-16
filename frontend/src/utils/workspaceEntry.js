export function extractWorkspaceLaunchIntent({ locationState, search }) {
  const state = locationState && typeof locationState === 'object' ? locationState : {};
  const params = new URLSearchParams(String(search || ''));

  const statePrompt = typeof state.initialPrompt === 'string' ? state.initialPrompt.trim() : '';
  const queryPrompt = typeof params.get('prompt') === 'string' ? params.get('prompt').trim() : '';

  const prompt = statePrompt || queryPrompt;
  const autoStart = Boolean(
    state.autoStart === true ||
    params.get('autoStart') === '1' ||
    params.get('autoStart') === 'true'
  );

  // Prefer explicit nonce handoff; fallback to deterministic key for query-only links.
  const handoffKey = state.handoffNonce
    ? `nonce:${String(state.handoffNonce)}`
    : prompt
      ? `query:${prompt}:${autoStart ? '1' : '0'}`
      : null;

  return {
    prompt,
    autoStart,
    handoffKey,
    hasPromptInQuery: Boolean(queryPrompt),
  };
}

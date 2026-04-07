/**
 * Backend `model_used` values — keep dev stub visibly non-premium (Fifty-point #2).
 */

export function isDevStubModel(modelUsed) {
  if (modelUsed == null || modelUsed === '') return false;
  const s = String(modelUsed).toLowerCase();
  return s === 'dev-stub' || s.includes('dev_stub') || (s.includes('stub') && s.includes('dev'));
}

/** Short UI line: never imply a paid tier for dev-stub. */
export function formatModelUsageLine(modelUsed) {
  if (!modelUsed) return '';
  if (isDevStubModel(modelUsed)) {
    return 'Local dev preview (no paid model — not billed as premium).';
  }
  return `Model: ${modelUsed}`;
}

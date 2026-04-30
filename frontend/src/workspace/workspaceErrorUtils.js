/**
 * Map API / orchestrator errors to a calm primary message; keep full text for expandable UI.
 * Frontend-only — does not change backend responses.
 */

export function detailToString(detail) {
  if (detail == null) return '';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((x) => (typeof x === 'string' ? x : JSON.stringify(x))).join('; ');
  if (typeof detail === 'object') {
    if (detail.message) return String(detail.message);
    if (Array.isArray(detail.issues)) return detail.issues.join('; ');
    try {
      return JSON.stringify(detail);
    } catch {
      return String(detail);
    }
  }
  return String(detail);
}

const FRIENDLY_MAX = 420;

export function formatWorkspaceBuildError(rawText) {
  const text = (rawText == null ? '' : String(rawText)).trim();
  if (!text) {
    return {
      friendly: 'I need another pass to finish this workspace.',
      raw: '',
    };
  }
  const lower = text.toLowerCase();
  const truncated =
    text.length > FRIENDLY_MAX ? `${text.slice(0, FRIENDLY_MAX)}…` : text;
  let friendly = 'I need another pass to finish this workspace. I kept the current files and can continue from here.';

  if (
    /credit|insufficient|balance|402|payment|quota|billing|anthropic|openai|api key|invalid_api|authentication|401|403|provider/.test(
      lower,
    )
  ) {
    friendly = 'The model provider needs attention before I can continue this pass.';
  } else if (/rate limit|429|timeout|econn|network|fetch failed|connection refused|eai_again/.test(lower)) {
    friendly = 'The provider or network paused this pass. Try again in a moment and I will continue from the same workspace.';
  } else if (/runtime_unsatisfied|python|node\.js|npm/.test(lower)) {
    friendly = 'The server runtime needs attention before preview can finish.';
  }

  return { friendly, raw: text };
}

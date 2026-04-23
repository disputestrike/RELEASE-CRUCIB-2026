const RELOAD_FLAG_KEY = 'crucibai-asset-reload-v1';

function normalizePath(input) {
  try {
    return new URL(input, window.location.origin).pathname;
  } catch {
    return String(input || '');
  }
}

export async function guardAgainstStaleMainChunk() {
  if (typeof window === 'undefined') return;

  const loadedMain = Array.from(document.querySelectorAll('script[src]'))
    .map((script) => script.getAttribute('src') || '')
    .find((src) => src.includes('/static/js/main'));

  if (!loadedMain) return;

  try {
    const response = await fetch('/asset-manifest.json', { cache: 'no-store' });
    if (!response.ok) return;
    const manifest = await response.json();
    const expectedMain = manifest?.files?.['main.js'];
    if (!expectedMain) return;

    const loadedPath = normalizePath(loadedMain);
    const expectedPath = normalizePath(expectedMain);
    if (loadedPath === expectedPath) {
      sessionStorage.removeItem(RELOAD_FLAG_KEY);
      return;
    }

    if (sessionStorage.getItem(RELOAD_FLAG_KEY) === '1') return;
    sessionStorage.setItem(RELOAD_FLAG_KEY, '1');
    window.location.reload();
  } catch {
    // Ignore manifest fetch failures.
  }
}

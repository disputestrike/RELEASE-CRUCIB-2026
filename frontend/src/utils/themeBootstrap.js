const THEME_KEY = 'crucibai-theme';

export function getInitialTheme() {
  try {
    return localStorage.getItem(THEME_KEY) || 'light';
  } catch {
    return 'light';
  }
}

export function applyTheme(theme) {
  try {
    document.documentElement.setAttribute('data-theme', theme || 'light');
    localStorage.setItem(THEME_KEY, theme || 'light');
  } catch {
    // No-op in non-browser contexts.
  }
}

export function bootstrapTheme() {
  applyTheme(getInitialTheme());
}

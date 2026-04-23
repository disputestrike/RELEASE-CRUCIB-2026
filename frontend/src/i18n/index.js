/**
 * i18n loader — CF26
 * Lightweight runtime locale loader with static bundle imports (works with CRA).
 * Exposes: getLocale(), setLocale(code), t(key, fallback)
 */
import en from './en.json';
import es from './es.json';
import fr from './fr.json';
import de from './de.json';
import ptbr from './pt-br.json';
import it from './it.json';
import nl from './nl.json';
import ja from './ja.json';
import ko from './ko.json';
import zhcn from './zh-cn.json';
import zhtw from './zh-tw.json';
import ar from './ar.json';
import hi from './hi.json';
import ru from './ru.json';
import tr from './tr.json';
import pl from './pl.json';

const BUNDLES = {
  'en': en, 'es': es, 'fr': fr, 'de': de, 'pt-br': ptbr, 'it': it, 'nl': nl,
  'ja': ja, 'ko': ko, 'zh-cn': zhcn, 'zh-tw': zhtw, 'ar': ar, 'hi': hi,
  'ru': ru, 'tr': tr, 'pl': pl,
};

export const SUPPORTED = Object.keys(BUNDLES);

const STORAGE_KEY = 'crucibai_locale';

export function getLocale() {
  if (typeof window === 'undefined') return 'en';
  const stored = window.localStorage?.getItem(STORAGE_KEY);
  if (stored && BUNDLES[stored]) return stored;
  const nav = (typeof navigator !== 'undefined' && navigator.language) || 'en';
  const lc = nav.toLowerCase();
  if (BUNDLES[lc]) return lc;
  const short = lc.split('-')[0];
  return BUNDLES[short] ? short : 'en';
}

export function setLocale(code) {
  if (!BUNDLES[code]) throw new Error(`Unsupported locale: ${code}`);
  if (typeof window !== 'undefined') {
    window.localStorage?.setItem(STORAGE_KEY, code);
    try { document.documentElement.lang = code; } catch {}
  }
}

export function t(key, fallback) {
  const code = getLocale();
  const bundle = BUNDLES[code] || en;
  if (bundle[key] != null) return bundle[key];
  if (en[key] != null) return en[key];
  return fallback != null ? fallback : key;
}

export default { getLocale, setLocale, t, SUPPORTED };

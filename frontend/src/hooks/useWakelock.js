/** CF28 — useWakelock: keep-screen-awake hook using the web Lock API.
 *  Falls back to a no-op on unsupported browsers.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

export default function useWakelock() {
  const sentinelRef = useRef(null);
  const [active, setActive] = useState(false);

  const supported = typeof navigator !== 'undefined'
    && 'wakeLock' in navigator
    && typeof navigator.wakeLock?.request === 'function';

  const acquire = useCallback(async () => {
    if (!supported) return false;
    try {
      const sentinel = await navigator.wakeLock.request('screen');
      sentinelRef.current = sentinel;
      setActive(true);
      sentinel.addEventListener('release', () => setActive(false));
      return true;
    } catch {
      setActive(false);
      return false;
    }
  }, [supported]);

  const release = useCallback(async () => {
    try { await sentinelRef.current?.release?.(); } catch {}
    sentinelRef.current = null;
    setActive(false);
  }, []);

  useEffect(() => () => { release(); }, [release]);

  return { supported, active, acquire, release };
}

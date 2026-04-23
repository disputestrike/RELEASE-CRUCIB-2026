/**
 * CrucibAI Performance Budget Utilities
 *
 * Lightweight helpers for measuring sync and async operations and recording
 * them in a global window.__CRUCIB_PERF array for offline inspection or
 * telemetry collection.
 *
 * Usage:
 *   import { measure, measureAsync } from './perfBudget';
 *
 *   const result = measure('render-dashboard', () => buildDashboard());
 *   const data   = await measureAsync('fetch-projects', () => fetchProjects());
 */

/**
 * Measure a synchronous function call.
 *
 * @param {string} name  - Human-readable label for this measurement.
 * @param {Function} fn  - Synchronous function to execute and time.
 * @returns {*} The return value of fn.
 */
export function measure(name, fn) {
  const t0 = performance.now();
  const result = fn();
  const dur = performance.now() - t0;
  (window.__CRUCIB_PERF = window.__CRUCIB_PERF || []).push({
    name,
    dur,
    ts: Date.now(),
  });
  return result;
}

/**
 * Measure an asynchronous function call.
 *
 * @param {string} name        - Human-readable label for this measurement.
 * @param {Function} asyncFn   - Async function (or function returning a Promise) to time.
 * @returns {Promise<*>} Resolves with the return value of asyncFn.
 */
export async function measureAsync(name, asyncFn) {
  const t0 = performance.now();
  const result = await asyncFn();
  const dur = performance.now() - t0;
  (window.__CRUCIB_PERF = window.__CRUCIB_PERF || []).push({
    name,
    dur,
    ts: Date.now(),
  });
  return result;
}

/**
 * Return a copy of all recorded measurements.
 * @returns {Array<{name: string, dur: number, ts: number}>}
 */
export function getRecordings() {
  return [...(window.__CRUCIB_PERF || [])];
}

/**
 * Clear all recorded measurements.
 */
export function clearRecordings() {
  window.__CRUCIB_PERF = [];
}

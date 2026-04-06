/**
 * Target-honest copy for plan review (keeps "What this run will actually build" aligned with execution target).
 */

const DEFAULT_TARGET = 'vite_react';

export function normalizePlanBuildTarget(raw) {
  if (raw == null || String(raw).trim() === '') return DEFAULT_TARGET;
  return String(raw).trim().replace(/-/g, '_');
}

/**
 * @param {string} [buildTargetId] plan.crucib_build_target
 * @param {object|null} [meta] buildTargetMeta from API (label, tagline, …)
 * @returns {{ bounded: string, targetDetail: string }}
 */
export function specGapCopy(buildTargetId, meta) {
  const tid = normalizePlanBuildTarget(buildTargetId);
  const label =
    (meta && typeof meta.label === 'string' && meta.label.trim()) ||
    {
      vite_react: 'Full-stack web (Vite + React)',
      next_app_router: 'Next.js App Router (track)',
      static_site: 'Marketing / static site',
      api_backend: 'API & backend-first',
      agent_workflow: 'Agents & automation',
    }[tid] ||
    'This execution target';

  const bounded =
    'The Auto-Runner runs a bounded DAG: it emits the artifact set for your execution target and runs ' +
    'verification gates. It does not implement an arbitrary enterprise or mega-spec end-to-end. ' +
    'A passing run means the emitted bundle plus checks succeeded—not that every bullet in your prompt ' +
    'shipped as a separate production subsystem.';

  const byId = {
    vite_react: `For “${label}”, expect a Vite + React (JS) scaffold, a Python FastAPI sketch when the goal implies a backend, SQL migration stubs, and the proof/preview gates described above.`,
    next_app_router: `For “${label}”, the root Vite workspace still drives Sandpack preview and today’s verify path, while a Next.js App Router starter is emitted under next-app-stub/ for you to grow. This run does not promise a full Next-first production platform in one shot.`,
    static_site: `For “${label}”, expect a Vite-oriented landing/marketing scaffold (pages and sections). Campaign tools, full CMS wiring, and every SEO edge case are not guaranteed in a single run.`,
    api_backend: `For “${label}”, the emphasis is Python API routes, OpenAPI-shaped sketches, and SQL stubs; the UI bundle may be thin or placeholder so preview stays valid. It does not ship every integration, queue, or scale pattern implied by a long spec.`,
    agent_workflow: `For “${label}”, expect workflow and agent sketches (files, docs, hooks) inside the same DAG bundle—not a hosted LangGraph/Crew runtime or an unbounded custom multi-agent system.`,
  };

  return {
    bounded,
    targetDetail: byId[tid] || byId.vite_react,
  };
}

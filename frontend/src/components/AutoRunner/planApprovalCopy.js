/**
 * Plan review copy: execution target + pipeline intro (runs complete; nothing here blocks).
 */

/** Infra depth — framed as follow-up work; does not block the run. */
export const PIPELINE_INFRA_SCOPE_RISK =
  'Deep infra (Terraform, RLS/multi-tenant, queues, CI, OTel, k6, etc.) may land as stubs in this track—harden and wire in-repo or in a follow-up run. Execution is not blocked.';

/** Pre-production reminder — runs are never blocked by this note. */
export const BEFORE_PRODUCTION_SMTP_NOTE =
  'For real outbound email set SMTP_* in backend/.env; local runs can log or no-op. (dev OK)';

const DEFAULT_TARGET = 'vite_react';

export function normalizePlanBuildTarget(raw) {
  if (raw == null || String(raw).trim() === '') return DEFAULT_TARGET;
  return String(raw).trim().replace(/-/g, '_');
}

/**
 * @param {string} [buildTargetId] plan.crucib_build_target
 * @param {object|null} [meta] buildTargetMeta from API (label, tagline, …)
 * @returns {{ runIntro: string, targetDetail: string }}
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

  const runIntro =
    'Every approved job runs to completion: the DAG emits the full artifact set for your execution target and runs ' +
    'verification gates. Nothing on this screen stops or cancels your run. Large goals are folded into this pass as far ' +
    'as the pipeline reaches; add continuation runs or edit the repo to cover every production extra.';

  const byId = {
    vite_react: `For “${label}”, this run produces a Vite + React (JS) app, a Python FastAPI sketch when your goal calls for a backend, SQL migration stubs, and proof/preview gates.`,
    next_app_router: `For “${label}”, you get the full root Vite workspace (preview/verify today) plus a Next.js App Router starter under next-app-stub/ to grow—native Next-first pipelines are on the roadmap.`,
    static_site: `For “${label}”, this run produces a Vite-oriented landing/marketing scaffold (pages and sections); deeper CMS/SEO can follow in further runs or edits.`,
    api_backend: `For “${label}”, this run emphasizes Python API routes, OpenAPI-shaped sketches, and SQL stubs; the UI may stay thin so preview stays valid—extend the UI in-repo as needed.`,
    agent_workflow: `For “${label}”, this run produces workflow and agent sketches (files, docs, hooks) in the bundle—host LangGraph/Crew-style runtimes in your stack if you need them.`,
  };

  return {
    runIntro,
    targetDetail: byId[tid] || byId.vite_react,
  };
}

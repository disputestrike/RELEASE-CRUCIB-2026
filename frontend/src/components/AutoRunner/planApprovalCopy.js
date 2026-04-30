export const PIPELINE_INFRA_SCOPE_RISK =
  'Deep infrastructure can continue as follow-up work. The workspace stays editable and resumable.';

export const BEFORE_PRODUCTION_SMTP_NOTE =
  'For real outbound email, set SMTP_* in backend/.env. Local work can log or no-op.';

const DEFAULT_TARGET = 'vite_react';

export function normalizePlanBuildTarget(raw) {
  if (raw == null || String(raw).trim() === '') return DEFAULT_TARGET;
  return String(raw).trim().replace(/-/g, '_');
}

export function specGapCopy(buildTargetId, meta) {
  const tid = normalizePlanBuildTarget(buildTargetId);
  const label =
    (meta && typeof meta.label === 'string' && meta.label.trim()) ||
    {
      vite_react: 'Full-stack web',
      next_app_router: 'Next.js App Router',
      static_site: 'Marketing site',
      internal_admin_tool: 'Internal admin tool',
      api_backend: 'API and backend',
      agent_workflow: 'Agents and automation',
    }[tid] ||
    'This workspace';

  const runIntro =
    'I will turn your request into one workspace, keep the files attached to this conversation, and let you keep steering as it evolves.';

  const byId = {
    vite_react: `For "${label}", I will create the app interface and wire backend/database pieces when your request calls for them.`,
    next_app_router: `For "${label}", I will prepare the app workspace and keep it previewable while the project evolves.`,
    static_site: `For "${label}", I will create the pages, sections, navigation, styling, and previewable site structure.`,
    internal_admin_tool: `For "${label}", I will create an internal operations workspace with data tables, forms, approval flows, API contracts, and database schema.`,
    api_backend: `For "${label}", I will focus on routes, schemas, data contracts, and service structure.`,
    agent_workflow: `For "${label}", I will create workflow definitions, action surfaces, run history, and guarded execution pieces.`,
  };

  return {
    runIntro,
    targetDetail: byId[tid] || byId.vite_react,
  };
}

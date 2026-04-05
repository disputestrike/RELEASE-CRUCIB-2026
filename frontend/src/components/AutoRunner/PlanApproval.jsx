/**
 * PlanApproval — flight plan review before execution.
 * Shows goal, build kind, phases, risks, acceptance criteria, cost estimate.
 * Props: plan, estimate, onApprove, onEdit, onRunAuto, loading
 */
import React, { useState } from 'react';
import { AlertTriangle, CheckCircle2, ChevronRight, ChevronDown } from 'lucide-react';
import './PlanApproval.css';

/** Backend sends snake_case keys; map known flags to clearer copy. */
const RISK_FLAG_LABELS = {
  goal_too_vague: 'Goal is very short — a bit more detail usually improves the build',
  goal_too_long_consider_splitting:
    'Unusually long goal — split only if a run fails or times out',
  stripe_keys_missing: 'Stripe mentioned in goal but Stripe keys are not configured in the server environment',
  goal_spec_nextjs_autorunner_template_is_vite_react:
    'Your spec mentions Next.js — Auto-Runner still generates Vite + React (not Next.js App Router)',
  goal_spec_ts_node_api_autorunner_backend_is_python_sketch:
    'Your spec mentions a TypeScript Node API — Auto-Runner still writes a Python FastAPI sketch',
  goal_spec_orm_autorunner_writes_sql_sketch_not_orm:
    'Your spec mentions Prisma/Drizzle — Auto-Runner only emits SQL file sketches, not ORM projects',
  goal_spec_infra_or_tenancy_not_generated_by_autorunner:
    'Your spec mentions Terraform, RLS/multi-tenant, queues, CI, OTel, k6, etc. — those are not produced by this pipeline (scaffold only)',
};

function riskFlagLabel(key) {
  return RISK_FLAG_LABELS[key] || key.replace(/_/g, ' ');
}

/** Human labels for planner `required_integrations` / `dependencies`. */
const INTEGRATION_LABELS = {
  stripe: 'Stripe / payments',
  auth: 'Authentication',
  database: 'Database',
  email: 'Email / SMTP',
  llm: 'LLM / AI features',
  multi_tenant: 'Multi-tenancy (SQL + API sketch, not full RLS)',
  compliance_sensitive:
    'Regulated-domain keywords — deploy.build adds docs/COMPLIANCE_SKETCH.md (educational; not legal advice)',
  observability:
    'Observability keywords — deploy.build adds OTel/Prometheus/Grafana stubs under deploy/observability + docs/OBSERVABILITY_PACK.md',
  multiregion_terraform:
    'Multi-region / cloud + Terraform-style goal — deploy.build adds terraform/multiregion_sketch + aws/gcp/azure module stubs',
};

function integrationLabel(key) {
  return INTEGRATION_LABELS[key] || key.replace(/_/g, ' ');
}

export default function PlanApproval({ plan, estimate, onApprove, onEdit, onRunAuto, loading }) {
  const [openPhase, setOpenPhase] = useState(null);
  if (!plan) return null;

  const riskFlags = plan.risk_flags || [];
  const specGapFlags = riskFlags.filter(
    f =>
      typeof f === 'string' &&
      (f.startsWith('goal_spec_') || f.includes('autorunner')),
  );
  const missingInputs = plan.missing_inputs || [];
  /** Pre-launch reminders only — runs are never blocked here (dev uses mocks; wire secrets before prod). */
  const hasPreLaunchNotes = missingInputs.length > 0;
  const phases = plan.phases || [];
  const integrations = plan.required_integrations?.length
    ? plan.required_integrations
    : plan.dependencies || [];

  const estTokens = estimate?.estimated_tokens;
  const estSteps = estimate?.estimated_steps ?? plan.estimated_steps;
  const typicalCredits = estimate?.cost_range?.typical_credits ?? estimate?.estimated_credits;
  const usdHint =
    typicalCredits != null ? Math.max(0.001, (typicalCredits * 0.00035)).toFixed(3) : null;
  const timeHint =
    estSteps != null ? `~${Math.max(15, Math.min(300, estSteps * 12))}s` : '—';

  return (
    <div className="plan-approval animate-fade-up">
      {/* Header */}
      <div className="pa-header">
        <div className="pa-goal-text">{plan.goal}</div>
        <div className="pa-meta">
          <span className="pa-badge">{plan.build_kind}</span>
          <span className="pa-badge">{plan.estimated_steps} steps</span>
        </div>
      </div>

      {specGapFlags.length > 0 && (
        <div className="pa-section pa-spec-gap-notice">
          <div className="pa-section-label">What this run will actually build</div>
          <p className="pa-premier-hint">
            The DAG completes a <strong>fixed scaffold</strong> (Vite + React frontend, Python API sketch, SQL files,
            verification). It does <strong>not</strong> implement an arbitrary enterprise spec end-to-end. High
            “quality” in the UI means that scaffold + checks passed — not that every line of your prompt was delivered.
          </p>
        </div>
      )}

      {/* Risk flags */}
      {riskFlags.length > 0 && (
        <div className="pa-section">
          <div className="pa-section-label">Risks</div>
          <div className="pa-risks">
            {riskFlags.map(f => (
              <div key={f} className="pa-risk-item">
                <AlertTriangle size={12} />
                <span>{riskFlagLabel(f)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Pre-launch checklist — informational; Approve & Run always allowed */}
      {hasPreLaunchNotes && (
        <div className="pa-section">
          <div className="pa-section-label">Before production</div>
          <p className="pa-premier-hint">
            Fix these before go-live. For local testing you can run anyway — builds use mocks or placeholders where needed.
          </p>
          {missingInputs.map(m => (
            <div
              key={m.key}
              className={`pa-missing-item pa-missing-advisory ${m.blocking ? 'blocking' : ''}`}
            >
              <span className="pa-missing-key">{m.key}</span>
              <span className="pa-missing-desc">{m.description}</span>
              <span className="pa-advisory-tag">{m.blocking ? 'required if strict' : 'dev OK'}</span>
            </div>
          ))}
        </div>
      )}

      {integrations.length > 0 && (
        <div className="pa-section">
          <div className="pa-section-label">Detected integrations</div>
          <p className="pa-premier-hint pa-integrations-hint">
            Inferred from your goal — controls optional SQL sketches, deploy docs, and acceptance criteria.
          </p>
          <ul className="pa-integrations-list">
            {integrations.map((key) => (
              <li key={key} className="pa-integration-chip">
                <span className="pa-integration-key">{key}</span>
                <span className="pa-integration-desc">{integrationLabel(key)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Phases */}
      <div className="pa-section">
        <div className="pa-section-label">Phases</div>
        <div className="pa-phases">
          {phases.map((phase, i) => {
            const n = phase.steps?.length || 0;
            const expanded = openPhase === i;
            return (
              <div key={phase.key || i} className={`pa-phase ${expanded ? 'pa-phase-open' : ''}`}>
                <button
                  type="button"
                  className="pa-phase-head"
                  onClick={() => setOpenPhase(expanded ? null : i)}
                >
                  <span className="pa-phase-num">{i + 1}</span>
                  <span className="pa-phase-label">{phase.label || phase.key}</span>
                  <span className="pa-phase-count">{n} steps</span>
                  {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                </button>
                {expanded && n > 0 && (
                  <ul className="pa-phase-steps">
                    {phase.steps.map((s, j) => (
                      <li key={s.key || j}>{s.name || s.label || s.key || `Step ${j + 1}`}</li>
                    ))}
                  </ul>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Acceptance criteria */}
      {plan.acceptance_criteria?.length > 0 && (
        <div className="pa-section">
          <div className="pa-section-label">Acceptance Criteria</div>
          {plan.acceptance_criteria.map((c, i) => (
            <div key={i} className="pa-criteria-item">
              <CheckCircle2 size={11} />
              <span>{c}</span>
            </div>
          ))}
        </div>
      )}

      {/* Resource estimation (spec §5.2) */}
      {estimate && (
        <div className="pa-resource-card">
          <div className="pa-resource-cell">
            <span className="pa-resource-k">Tokens</span>
            <span className="pa-resource-v">{estTokens != null ? estTokens.toLocaleString() : '—'}</span>
          </div>
          <div className="pa-resource-cell">
            <span className="pa-resource-k">Cost</span>
            <span className="pa-resource-v">{usdHint != null ? `~$${usdHint}` : '—'}</span>
          </div>
          <div className="pa-resource-cell">
            <span className="pa-resource-k">Steps</span>
            <span className="pa-resource-v">{estSteps ?? '—'}</span>
          </div>
          <div className="pa-resource-cell">
            <span className="pa-resource-k">Time</span>
            <span className="pa-resource-v">{timeHint}</span>
          </div>
        </div>
      )}
      {estimate && (
        <div className="pa-estimate pa-estimate-inline">
          <span className="pa-est-label">Credits</span>
          <span className="pa-est-range">
            {estimate.cost_range?.min_credits}–{estimate.cost_range?.max_credits}
          </span>
          <span className="pa-est-typical">typical {estimate.cost_range?.typical_credits}</span>
        </div>
      )}

      {/* Actions */}
      <div className="pa-actions">
        <button
          className="pa-btn pa-btn-approve"
          onClick={onApprove}
          disabled={loading}
        >
          <ChevronRight size={13} />
          Approve & Run
        </button>
        <button className="pa-btn pa-btn-edit" onClick={onEdit} disabled={loading}>
          Edit Plan
        </button>
        <button
          className="pa-btn pa-btn-auto"
          onClick={onRunAuto}
          disabled={loading}
        >
          Run in Auto Mode
        </button>
      </div>

      {hasPreLaunchNotes && (
        <div className="pa-premier-note" role="note">
          Pre-launch items above are reminders only — they do not block runs. Set{' '}
          <code className="pa-code-inline">CRUCIBAI_STRICT_PLAN_BLOCKERS=1</code> on the API if you ever need
          hard gates (advanced).
        </div>
      )}
    </div>
  );
}

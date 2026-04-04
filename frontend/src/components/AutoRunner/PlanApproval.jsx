/**
 * PlanApproval — pre-execution plan review screen.
 * Shows goal, phases, risk flags, missing inputs, cost estimate.
 * Props: plan, estimate, onApprove, onEdit, onRunAuto, loading
 */
import React from 'react';
import { AlertTriangle, CheckCircle2, Zap, ChevronRight } from 'lucide-react';
import './PlanApproval.css';

const PHASE_ICONS = {
  planning:     '🧠',
  frontend:     '🎨',
  backend:      '⚙️',
  database:     '🗄️',
  verification: '✅',
  deploy:       '🚀',
};

export default function PlanApproval({ plan, estimate, onApprove, onEdit, onRunAuto, loading }) {
  if (!plan) return null;

  const riskFlags = plan.risk_flags || [];
  const missingInputs = plan.missing_inputs || [];
  const hasBlockers = missingInputs.some(m => m.blocking);
  const phases = plan.phases || [];

  return (
    <div className="plan-approval">
      <div className="pa-header">
        <div className="pa-goal">
          <span className="pa-goal-label">Goal</span>
          <span className="pa-goal-text">{plan.goal}</span>
        </div>
        <div className="pa-meta">
          <span className="pa-badge">{plan.build_kind}</span>
          <span className="pa-badge">{plan.estimated_steps} steps</span>
        </div>
      </div>

      {/* Risk flags */}
      {riskFlags.length > 0 && (
        <div className="pa-risks">
          {riskFlags.map(f => (
            <div key={f} className="pa-risk-item">
              <AlertTriangle size={12} />
              <span>{f.replace(/_/g, ' ')}</span>
            </div>
          ))}
        </div>
      )}

      {/* Missing inputs */}
      {missingInputs.length > 0 && (
        <div className="pa-missing">
          <div className="pa-section-label">Missing Inputs</div>
          {missingInputs.map(m => (
            <div key={m.key} className={`pa-missing-item ${m.blocking ? 'blocking' : ''}`}>
              <span className="pa-missing-key">{m.key}</span>
              <span className="pa-missing-desc">{m.description}</span>
              {m.blocking && <span className="pa-blocking-tag">blocking</span>}
            </div>
          ))}
        </div>
      )}

      {/* Phases */}
      <div className="pa-phases">
        <div className="pa-section-label">Build Plan</div>
        {phases.map((phase, i) => (
          <div key={phase.key} className="pa-phase">
            <div className="pa-phase-header">
              <span className="pa-phase-icon">{PHASE_ICONS[phase.key] || '📋'}</span>
              <span className="pa-phase-label">{phase.label || phase.key}</span>
              <span className="pa-phase-count">{phase.steps?.length || 0} steps</span>
            </div>
          </div>
        ))}
      </div>

      {/* Acceptance criteria */}
      {plan.acceptance_criteria?.length > 0 && (
        <div className="pa-criteria">
          <div className="pa-section-label">Acceptance Criteria</div>
          {plan.acceptance_criteria.map((c, i) => (
            <div key={i} className="pa-criteria-item">
              <CheckCircle2 size={11} />
              <span>{c}</span>
            </div>
          ))}
        </div>
      )}

      {/* Cost estimate */}
      {estimate && (
        <div className="pa-estimate">
          <Zap size={12} />
          <span>Estimated cost: </span>
          <span className="pa-est-range">
            {estimate.cost_range?.min_credits}–{estimate.cost_range?.max_credits} credits
          </span>
          <span className="pa-est-note">(typical: {estimate.cost_range?.typical_credits})</span>
        </div>
      )}

      {/* Actions */}
      <div className="pa-actions">
        <button
          className="pa-btn pa-btn-auto"
          onClick={onRunAuto}
          disabled={loading || hasBlockers}
        >
          <Zap size={13} />
          Run in Auto Mode
        </button>
        <button
          className="pa-btn pa-btn-approve"
          onClick={onApprove}
          disabled={loading || hasBlockers}
        >
          <ChevronRight size={13} />
          Approve & Run
        </button>
        <button className="pa-btn pa-btn-edit" onClick={onEdit} disabled={loading}>
          Edit Plan
        </button>
      </div>

      {hasBlockers && (
        <div className="pa-blocker-note">
          Resolve blocking inputs before running.
        </div>
      )}
    </div>
  );
}

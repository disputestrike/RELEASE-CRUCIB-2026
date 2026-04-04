/**
 * GoalComposer — large goal input with quick-start chips and live interpretation.
 * Props: goal, onGoalChange, onSubmit, loading, error, token, onEstimateReady
 */
import React from 'react';
import CostEstimator from './CostEstimator';
import './GoalComposer.css';

const QUICK_CHIPS = [
  'Build an app',
  'Automate a workflow',
  'Fix an existing project',
  'Add a feature',
];

export default function GoalComposer({ goal, onGoalChange, onSubmit, loading, error, token, onEstimateReady }) {
  const detectedType = goal.length > 15
    ? (goal.toLowerCase().includes('api') ? 'API Service'
      : goal.toLowerCase().includes('dashboard') ? 'Dashboard'
      : goal.toLowerCase().includes('app') ? 'Full-Stack App'
      : goal.toLowerCase().includes('workflow') ? 'Automation'
      : goal.toLowerCase().includes('fix') ? 'Bug Fix'
      : 'Custom Build')
    : null;

  const needsBackend = goal.toLowerCase().includes('api') || goal.toLowerCase().includes('auth') || goal.toLowerCase().includes('backend');
  const needsAuth = goal.toLowerCase().includes('auth') || goal.toLowerCase().includes('login') || goal.toLowerCase().includes('signup');
  const needsDB = goal.toLowerCase().includes('database') || goal.toLowerCase().includes('db') || goal.toLowerCase().includes('postgres') || goal.toLowerCase().includes('table');

  return (
    <div className="goal-composer">
      <div className="gc-header">
        <h2 className="gc-title">What do you want to build?</h2>
        <p className="gc-subtitle">Describe your project goal. CrucibAI will plan, build, verify, and deploy.</p>
      </div>

      <textarea
        className="gc-input"
        placeholder="Describe what you want to build..."
        value={goal}
        onChange={e => onGoalChange(e.target.value)}
        rows={5}
      />

      {/* Quick-start chips */}
      <div className="gc-chips">
        {QUICK_CHIPS.map(chip => (
          <button
            key={chip}
            className="gc-chip"
            onClick={() => onGoalChange(chip)}
          >
            {chip}
          </button>
        ))}
      </div>

      {/* Live interpretation strip */}
      {goal.length > 15 && (
        <div className="gc-interpretation">
          {detectedType && <span className="gc-interp-badge">{detectedType}</span>}
          {needsBackend && <span className="gc-interp-badge gc-interp-backend">Backend</span>}
          {needsAuth && <span className="gc-interp-badge gc-interp-auth">Auth</span>}
          {needsDB && <span className="gc-interp-badge gc-interp-db">Database</span>}
        </div>
      )}

      {/* Cost estimator */}
      <CostEstimator goal={goal} token={token} onEstimateReady={onEstimateReady} />

      {/* Error */}
      {error && <div className="gc-error">{error}</div>}

      {/* Submit */}
      <button
        className="gc-submit"
        onClick={onSubmit}
        disabled={loading || !goal.trim()}
      >
        {loading ? 'Generating plan...' : 'Generate Plan'}
      </button>
    </div>
  );
}

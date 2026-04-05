/**
 * GoalComposer — Auto-Runner goal input (spec §5.1).
 */
import React, { useMemo } from 'react';
import CostEstimator from './CostEstimator';
import './GoalComposer.css';

const QUICK_CHIPS = [
  'Build an app',
  'Automate workflow',
  'Fix project',
  'Add a feature',
];

function smartTags(goal) {
  const g = goal.toLowerCase();
  const tags = [];
  if (/microservice|service api|small service/.test(g)) tags.push('microservice');
  if (/rest|graphql|api route|endpoint/.test(g)) tags.push('REST API');
  if (/postgres|postgresql|sql|prisma|typeorm|database/.test(g)) tags.push('PostgreSQL');
  if (/railway|deploy|docker|kubernetes|ci\/cd/.test(g)) tags.push('Railway deploy');
  if (/test|jest|vitest|pytest/.test(g)) tags.push('Tests');
  return [...new Set(tags)];
}

export default function GoalComposer({
  goal,
  onGoalChange,
  onSubmit,
  loading,
  error,
  token,
  onEstimateReady,
  authLoading = false,
  onRetrySession,
}) {
  const tags = useMemo(() => (goal.length >= 12 ? smartTags(goal) : []), [goal]);

  return (
    <div className="goal-composer">
      <div className="gc-header">
        <h2 className="gc-title">Auto-Runner</h2>
        <p className="gc-subtitle">Describe your goal… CrucibAI will plan, build, verify, and deploy.</p>
      </div>

      <textarea
        className="gc-input"
        placeholder="e.g. Build a proof-validation microservice with REST API, database persistence, tests, and deploy to Railway."
        value={goal}
        onChange={(e) => onGoalChange(e.target.value)}
        rows={5}
      />

      <div className="gc-chips">
        {QUICK_CHIPS.map((chip) => (
          <button key={chip} type="button" className="gc-chip" onClick={() => onGoalChange(chip)}>
            {chip}
          </button>
        ))}
      </div>

      {tags.length > 0 && (
        <div className="gc-detect-row">
          <span className="gc-detect-label">Detected</span>
          <div className="gc-detect-tags">
            {tags.map((t) => (
              <span key={t} className="gc-detect-pill">
                {t}
              </span>
            ))}
          </div>
        </div>
      )}

      <CostEstimator goal={goal} token={token} onEstimateReady={onEstimateReady} />

      {authLoading && <div className="gc-hint">Starting your session…</div>}
      {!authLoading && !token && (
        <div className="gc-hint gc-hint-warn">
          No API session yet — plans and jobs need a signed-in or guest token.{' '}
          {onRetrySession && (
            <button type="button" className="gc-linkish" onClick={onRetrySession}>
              Start guest session
            </button>
          )}
        </div>
      )}

      {error && <div className="gc-error">{error}</div>}

      <button
        type="button"
        className="gc-submit"
        onClick={onSubmit}
        disabled={loading || !goal.trim() || authLoading || !token}
      >
        {loading ? 'Generating plan...' : 'Generate Plan'}
      </button>
    </div>
  );
}

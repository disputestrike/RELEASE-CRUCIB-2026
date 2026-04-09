/**
 * FailureDrawer — failure details and recovery UI with before/after visualization.
 * Props: step, onRetry, onOpenCode, onPauseJob, onClose
 */
import React, { useState } from 'react';
import { X, RefreshCw, Code2, PauseCircle, AlertTriangle } from 'lucide-react';
import './FailureDrawer.css';

const FAILURE_LABELS = {
  compile_error:        'COMPILE_ERROR',
  runtime_error:        'RUNTIME_ERROR',
  api_contract_error:   'API_CONTRACT_ERROR',
  db_error:             'DATABASE_ERROR',
  integration_error:    'INTEGRATION_ERROR',
  verification_error:   'VERIFICATION_ERROR',
  missing_file:         'MISSING_FILE',
  syntax_error:         'SYNTAX_ERROR',
  unknown:              'UNKNOWN_ERROR',
};

const RETRY_STRATEGIES = {
  compile_error:      'Retrying with corrected import paths and dependency resolution',
  syntax_error:       'Retrying with validated template strategy (prose stripped)',
  api_contract_error: 'Retrying with schema alignment verification',
  db_error:           'Retrying with idempotent migration strategy',
  missing_file:       'Retrying with file regeneration and reference update',
  runtime_error:      'Retrying with targeted function patch and null guards',
  integration_error:  'Retrying with env var and integration config check',
  verification_error: 'Retrying with targeted verification patch',
  unknown:            'Diagnostic agent analyzing root cause — targeted patch queued',
};

/** Keep aligned with backend/orchestration/fixer.py MAX_RETRIES (retries after first failure). */
const MAX_STEP_RETRIES = 8;
const MAX_ATTEMPTS = MAX_STEP_RETRIES + 1; // 9 total attempts

const BROKEN_CODE = `@app.post("/api/jobs")
async def create_job(data: dict)
    job = await db.create(data)`;

const FIXED_CODE = `@app.post("/api/jobs")
async def create_job(data: dict):
    job = await db.create(data)
+   return {"id": job.id, "status": "created"}`;

export default function FailureDrawer({ step, onRetry, onOpenCode, onPauseJob, onClose }) {
  const [retryState, setRetryState] = useState(null);
  const [attempts, setAttempts] = useState([]);

  if (!step) return null;

  const failureType = step.failure_type || 'unknown';
  const label = FAILURE_LABELS[failureType] || failureType.toUpperCase();
  const errorMsg = step.error_message || 'No diagnostic output available.';
  const outputFiles = step.output_files || [];
  const retryCount = step.retry_count || 0;
  const retryStrategy = RETRY_STRATEGIES[failureType] || RETRY_STRATEGIES.unknown;

  const handleRetryAuto = () => {
    setRetryState('in_progress');
    setAttempts(prev => [...prev, { id: prev.length + 1, status: 'in_progress', time: new Date().toLocaleTimeString() }]);
    setTimeout(() => {
      setRetryState('recovered');
      setAttempts(prev => prev.map((a, i) => i === prev.length - 1 ? { ...a, status: 'recovered' } : a));
    }, 2000);
    onRetry?.(step);
  };

  return (
    <div className="failure-drawer animate-fade-up">
      <div className="fd-header">
        <AlertTriangle size={14} className="fd-alert-icon" />
        <span className="fd-title">Step Failed</span>
        <button className="fd-close" onClick={onClose}><X size={14} /></button>
      </div>

      <div className="fd-body">
        <div className="fd-step-name">{step.step_key}</div>

        <div className="fd-row">
          <span className="fd-label">Failure Type</span>
          <span className="fd-failure-badge">{label}</span>
        </div>

        <div className="fd-row">
          <span className="fd-label">Root Cause</span>
          <pre className="fd-error-msg">{errorMsg}</pre>
        </div>

        {step.diagnosis && (
          <div className="fd-row">
            <span className="fd-label">Diagnosis</span>
            <div className="fd-diagnosis">
              <span className="fd-diagnosis-class">{step.diagnosis.failure_class?.toUpperCase()}</span>
              {step.diagnosis.specific_file && (
                <span className="fd-diagnosis-file">
                  {step.diagnosis.specific_file}{step.diagnosis.specific_line ? `:${step.diagnosis.specific_line}` : ''}
                </span>
              )}
              <p className="fd-diagnosis-desc">{step.diagnosis.explanation}</p>
            </div>
          </div>
        )}

        {outputFiles.length > 0 && (
          <div className="fd-row">
            <span className="fd-label">Impacted Files</span>
            <div className="fd-files">
              {outputFiles.map(f => (
                <span key={f} className="fd-file">{f}</span>
              ))}
            </div>
          </div>
        )}

        <div className="fd-row">
          <span className="fd-label">Retry Strategy</span>
          <span className="fd-strategy">{retryStrategy}</span>
        </div>

        <div className="fd-retry-info">
          Attempt {Math.min(retryCount + 1, MAX_ATTEMPTS)} of {MAX_ATTEMPTS}
          {' '}
          <span className="fd-retry-meta">({MAX_STEP_RETRIES} auto-retries max)</span>
        </div>

        {/* Recovery section */}
        {retryState && (
          <div className="fd-recovery">
            <div className="fd-recovery-header">RECOVERY ATTEMPT</div>
            <div className="fd-recovery-label">Applying fix: rewrite_with_linter</div>

            <div className="fd-diff-before">
              <span className="fd-diff-label">Before</span>
              <pre className="fd-diff-code">{BROKEN_CODE}</pre>
            </div>

            <div className="fd-diff-after">
              <span className="fd-diff-label">After</span>
              <pre className="fd-diff-code">{FIXED_CODE}</pre>
            </div>

            <div className="fd-diff-stat">+ 3 lines changed</div>

            <div className={`fd-recovery-status fd-recovery-${retryState}`}>
              {retryState === 'in_progress' && `Attempt 1 of ${MAX_ATTEMPTS} — In Progress (demo)`}
              {retryState === 'recovered' && `Attempt 1 of ${MAX_ATTEMPTS} — Recovered (demo)`}
              {retryState === 'exhausted' && `All ${MAX_ATTEMPTS} attempts exhausted`}
            </div>

            {/* Attempt timeline */}
            {attempts.length > 0 && (
              <div className="fd-attempts">
                {attempts.map((a) => (
                  <div key={a.id} className={`fd-attempt-dot fd-attempt-${a.status}`} title={`Attempt ${a.id}: ${a.status} at ${a.time}`} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="fd-actions">
        <button className="fd-btn fd-btn-retry" onClick={handleRetryAuto}>
          <RefreshCw size={12} /> Retry Automatically
        </button>
        <button className="fd-btn fd-btn-code" onClick={() => onOpenCode?.(step)}>
          <Code2 size={12} /> Open Code
        </button>
        <button className="fd-btn fd-btn-pause" onClick={() => onPauseJob?.()}>
          <PauseCircle size={12} /> Pause Job
        </button>
      </div>
    </div>
  );
}

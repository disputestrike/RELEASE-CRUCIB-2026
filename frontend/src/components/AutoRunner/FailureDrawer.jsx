/**
 * FailureDrawer — failure details and recovery UI.
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

export default function FailureDrawer({ step, onRetry, onOpenCode, onPauseJob, onClose }) {
  const [retryTriggered, setRetryTriggered] = useState(false);

  if (!step) return null;

  const failureType = step.failure_type || 'unknown';
  const label = FAILURE_LABELS[failureType] || failureType.toUpperCase();
  const errorMsg = step.error_message || 'No diagnostic output available.';
  const outputFiles = step.output_files || [];
  const retryCount = step.retry_count || 0;
  const retryStrategy = RETRY_STRATEGIES[failureType] || RETRY_STRATEGIES.unknown;
  const diagnosis = step.diagnosis || {};
  const repairActions = diagnosis.repair_actions || step.retry_plan || [];
  const fixStrategy = step.fix_strategy || diagnosis.fix_strategy || 'targeted_patch';
  const canRetry = retryCount < MAX_STEP_RETRIES;

  const handleRetryAuto = () => {
    setRetryTriggered(true);
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

        {(diagnosis.explanation || repairActions.length > 0 || retryTriggered) && (
          <div className="fd-recovery">
            <div className="fd-recovery-header">RECOVERY PLAN</div>
            <div className="fd-recovery-label">Fix strategy: {fixStrategy}</div>

            {diagnosis.explanation && (
              <pre className="fd-diff-code">{diagnosis.explanation}</pre>
            )}

            {repairActions.length > 0 && (
              <div className="fd-repair-actions">
                {repairActions.map((action, index) => (
                  <div key={`${index}-${action}`} className="fd-repair-action">
                    {index + 1}. {action}
                  </div>
                ))}
              </div>
            )}

            <div className={`fd-recovery-status ${canRetry ? 'fd-recovery-in_progress' : 'fd-recovery-exhausted'}`}>
              {canRetry
                ? `Next retry will be attempt ${Math.min(retryCount + 2, MAX_ATTEMPTS)} of ${MAX_ATTEMPTS}`
                : `All ${MAX_ATTEMPTS} attempts exhausted`}
            </div>

            {retryTriggered && canRetry && (
              <div className="fd-diff-stat">Retry requested — waiting for live execution result.</div>
            )}
          </div>
        )}
      </div>

      <div className="fd-actions">
        <button className="fd-btn fd-btn-retry" onClick={handleRetryAuto} disabled={!canRetry}>
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

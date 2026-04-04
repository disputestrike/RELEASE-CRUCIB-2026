/**
 * FailureDrawer — failure details and recovery UI.
 * Engineering-precise copy: "Syntax error detected in generated route handler"
 * Props: step, onRetry, onOpenCode, onPauseJob, onClose
 */
import React from 'react';
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
  syntax_error:       'Retrying with validated template strategy',
  api_contract_error: 'Retrying with schema alignment verification',
  db_error:           'Retrying with idempotent migration strategy',
  missing_file:       'Retrying with file regeneration and reference update',
  unknown:            'Retrying with conservative patch strategy',
};

export default function FailureDrawer({ step, onRetry, onOpenCode, onPauseJob, onClose }) {
  if (!step) return null;

  const failureType = step.failure_type || 'unknown';
  const label = FAILURE_LABELS[failureType] || failureType.toUpperCase();
  const errorMsg = step.error_message || 'No diagnostic output available.';
  const outputFiles = step.output_files || [];
  const retryCount = step.retry_count || 0;
  const retryStrategy = RETRY_STRATEGIES[failureType] || RETRY_STRATEGIES.unknown;

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
          Attempt {retryCount + 1} of 3
        </div>
      </div>

      <div className="fd-actions">
        <button className="fd-btn fd-btn-retry" onClick={() => onRetry?.(step)}>
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

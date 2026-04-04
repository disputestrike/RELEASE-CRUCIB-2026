/**
 * FailureDrawer — shown when a step fails. Shows failure type, root cause, retry plan.
 * Props: step, onRetry, onOpenCode, onPauseJob, onClose
 */
import React from 'react';
import { X, RefreshCw, Code2, PauseCircle, AlertTriangle } from 'lucide-react';
import './FailureDrawer.css';

const FAILURE_LABELS = {
  compile_error:        'Compile Error',
  runtime_error:        'Runtime Error',
  api_contract_error:   'API Contract Error',
  db_error:             'Database Error',
  integration_error:    'Integration Error',
  verification_error:   'Verification Error',
  missing_file:         'Missing File',
  syntax_error:         'Syntax Error',
  unknown:              'Unknown Error',
};

export default function FailureDrawer({ step, onRetry, onOpenCode, onPauseJob, onClose }) {
  if (!step) return null;

  const failureType = step.failure_type || 'unknown';
  const label = FAILURE_LABELS[failureType] || failureType;
  const errorMsg = step.error_message || 'No details available.';
  const outputFiles = step.output_files || [];
  const retryCount = step.retry_count || 0;

  // Derive retry plan from failure type
  const retryPlans = {
    compile_error:      ['Fix import paths and missing deps', 'Re-run compile check'],
    syntax_error:       ['Identify syntax error in file', 'Apply minimal patch', 'Re-verify'],
    api_contract_error: ['Compare frontend call to backend route', 'Fix schema mismatch'],
    db_error:           ['Check migration for missing table/column', 'Re-run with IF NOT EXISTS'],
    missing_file:       ['Re-generate the missing file', 'Update import references'],
    unknown:            ['Inspect error output', 'Apply conservative fix', 'Re-verify'],
  };
  const plan = retryPlans[failureType] || retryPlans.unknown;

  return (
    <div className="failure-drawer">
      <div className="fd-header">
        <AlertTriangle size={14} className="fd-alert" />
        <span className="fd-title">Step Failed: <span className="fd-step-key">{step.step_key}</span></span>
        <button className="fd-close" onClick={onClose}><X size={14} /></button>
      </div>

      <div className="fd-body">
        <div className="fd-row">
          <span className="fd-label">Failure Type</span>
          <span className="fd-failure-badge">{label}</span>
        </div>

        <div className="fd-row">
          <span className="fd-label">Error</span>
          <pre className="fd-error-msg">{errorMsg}</pre>
        </div>

        {outputFiles.length > 0 && (
          <div className="fd-row">
            <span className="fd-label">Files Involved</span>
            <div className="fd-files">
              {outputFiles.map(f => (
                <span key={f} className="fd-file">{f}</span>
              ))}
            </div>
          </div>
        )}

        <div className="fd-row">
          <span className="fd-label">Retry Plan</span>
          <div className="fd-plan">
            {plan.map((p, i) => (
              <div key={i} className="fd-plan-item">
                <span className="fd-plan-num">{i + 1}</span>
                <span>{p}</span>
              </div>
            ))}
          </div>
        </div>

        {retryCount > 0 && (
          <div className="fd-retry-info">
            Attempted {retryCount} time{retryCount !== 1 ? 's' : ''} already.
          </div>
        )}
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

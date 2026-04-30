/**
 * EnhancedProofPanel — comprehensive proof artifact viewer.
 *
 * Consumes the full proof payload from GET /api/jobs/:job_id/proof and renders
 * 8 sub-tabs: Overview, Agents, Files, Validation, Runtime, Repairs, What-If, Downloads.
 *
 * Props:
 *   proof              — Full proof object from the API
 *   jobId              — Job identifier string
 *   jobStatus          — Current job status (string)
 *   openWorkspacePath  — (path: string) => void  — navigate to code pane
 *   onRepair           — () => void  — "Repair From Proof" action
 *   onReplay           — () => void  — "Replay Build" action
 */
import React, { useState, useCallback, useMemo } from 'react';
import {
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  AlertOctagon,
  ShieldCheck,
  Bot,
  FileCode2,
  FileTree,
  Activity,
  Server,
  Wrench,
  FlaskConical,
  Download,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  Info,
  RotateCcw,
  Zap,
  FileJson,
  FileText,
  ScrollText,
  FolderTree,
} from 'lucide-react';
import { useAuth } from '../../authContext';
import { API_BASE as API } from '../../apiBase';
import './EnhancedProofPanel.css';

/* ---------------------------------------------------------------------------
   Constants
   --------------------------------------------------------------------------- */

/** Sub-tab definitions with icon, label, and optional badge accessor. */
const TABS = [
  { key: 'overview',    label: 'Overview',    Icon: Info },
  { key: 'agents',      label: 'Agents',      Icon: Bot },
  { key: 'files',       label: 'Files',       Icon: FileCode2 },
  { key: 'validation',  label: 'Validation',  Icon: ShieldCheck },
  { key: 'runtime',     label: 'Runtime',     Icon: Server },
  { key: 'repairs',     label: 'Repairs',     Icon: Wrench },
  { key: 'whatif',      label: 'What-If',     Icon: FlaskConical },
  { key: 'downloads',   label: 'Downloads',   Icon: Download },
];

/** Files considered "important" and should be highlighted in the tree. */
const HIGHLIGHTED_FILES = new Set([
  'package.json',
  'main.py',
  'app.py',
  'App.jsx',
  'App.tsx',
  'index.tsx',
  'index.jsx',
  'requirements.txt',
  'Dockerfile',
  'docker-compose.yml',
  'docker-compose.yaml',
  '.env',
  '.env.example',
  'Makefile',
  'tsconfig.json',
  'vite.config.ts',
  'next.config.js',
]);

/* ---------------------------------------------------------------------------
   Utility helpers
   --------------------------------------------------------------------------- */

/** Safely read a nested property without throwing. */
function get(obj, path, fallback) {
  if (!obj) return fallback;
  const keys = Array.isArray(path) ? path : path.split('.');
  let cur = obj;
  for (const k of keys) {
    if (cur == null || typeof cur !== 'object') return fallback;
    cur = cur[k];
  }
  return cur ?? fallback;
}

/** Format bytes to human-readable string. */
function formatBytes(bytes) {
  if (typeof bytes !== 'number' || bytes < 0) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Format milliseconds to human-readable. */
function formatDuration(ms) {
  if (typeof ms !== 'number' || ms < 0) return 'N/A';
  if (ms < 1000) return `${ms} ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)} s`;
  const mins = Math.floor(ms / 60_000);
  const secs = ((ms % 60_000) / 1000).toFixed(0);
  return `${mins}m ${secs}s`;
}

/** Compute depth of a file path (number of separators). */
function pathDepth(p) {
  if (!p) return 0;
  return (p.match(/[\/\\]/g) || []).length;
}

/** Get just the filename from a path. */
function basename(p) {
  if (!p) return '';
  const parts = p.replace(/\\/g, '/').split('/');
  return parts[parts.length - 1] || p;
}

/** Determine indentation class for a file path. */
function indentClass(p) {
  const d = pathDepth(p);
  if (d <= 1) return '';
  if (d <= 2) return 'epp-file-indent';
  if (d <= 3) return 'epp-file-indent-2';
  return 'epp-file-indent-3';
}

/** Trigger a browser download for text content. */
function downloadText(filename, text, mimeType = 'text/plain') {
  const blob = new Blob([text], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/* ---------------------------------------------------------------------------
   Status helpers
   --------------------------------------------------------------------------- */

/** Map final_status to CSS class and display label. */
function statusInfo(status) {
  const s = String(status || '').trim().toLowerCase();
  if (s === 'pass') return { cls: 'epp-status-pass', label: 'Pass', Icon: CheckCircle2 };
  if (s === 'fail') return { cls: 'epp-status-fail', label: 'Fail', Icon: XCircle };
  if (s === 'warning') return { cls: 'epp-status-warning', label: 'Warning', Icon: AlertTriangle };
  return { cls: 'epp-status-pending', label: 'Pending', Icon: Clock };
}

/** Map confidence score to CSS class. */
function confidenceCls(score) {
  if (score >= 0.75) return 'epp-confidence-high';
  if (score >= 0.55) return 'epp-confidence-medium';
  return 'epp-confidence-low';
}

/** Map confidence tier to label. */
function confidenceLabel(tier) {
  const t = String(tier || '').trim().toLowerCase();
  if (t === 'production') return 'Production';
  if (t === 'prototype') return 'Prototype';
  if (t === 'experimental') return 'Experimental';
  return t || 'Unknown';
}

/** Map risk to CSS class. */
function riskCls(risk) {
  const r = String(risk || '').trim().toLowerCase();
  if (r === 'high') return 'high';
  if (r === 'medium') return 'medium';
  return 'low';
}

/* ---------------------------------------------------------------------------
   Sub-tab renderers
   --------------------------------------------------------------------------- */

/** Tab: Overview — verdict, trust language, build info. */
function OverviewTab({ proof, jobId }) {
  const verdict = get(proof, 'explanations.final_verdict', '');
  const stackExplain = get(proof, 'explanations.stack_choice', '');
  const buildCmds = get(proof, 'build_commands', []);
  const testResults = get(proof, 'test_results', null);
  const durationMs = get(proof, 'duration_ms', null);
  const timestamp = get(proof, 'timestamp', '');
  const failureReason = get(proof, 'failure_reason', null);
  const finalStatus = get(proof, 'final_status', '');
  const validation = get(proof, 'validation', null);
  const stages = get(validation, 'stages', {});
  const hasRepairs = (get(proof, 'repair_attempts', []) || []).length > 0;
  const hasWhatIf = (get(proof, 'what_if_results', []) || []).length > 0;

  /* Build trust language */
  const checks = [];
  if (get(stages, 'syntax.passed')) checks.push('syntax');
  if (get(stages, 'build.passed')) checks.push('build');
  if (get(stages, 'runtime.passed')) checks.push('runtime');
  if (get(stages, 'integration.passed')) checks.push('API integration');
  if (hasRepairs) checks.push('repair loop');
  if (hasWhatIf) checks.push('What-If simulation');

  const isFailure = finalStatus === 'fail';

  return (
    <div className="epp-animate-in">
      {/* Trust verdict */}
      {verdict ? (
        <div className={`epp-overview-verdict ${isFailure ? 'epp-overview-failure' : ''}`}>
          <span className="epp-overview-verdict-title">Final Verdict</span>
          {verdict}
        </div>
      ) : null}

      {/* Trust language callout */}
      {checks.length > 0 && !isFailure && (
        <div className="epp-trust-callout">
          <ShieldCheck size={16} />
          <div>
            <strong>CrucibAI did not just generate this app. It validated it.</strong>
            <div className="epp-trust-checks">
              {checks.map((c) => (
                <span key={c} className="epp-trust-check">
                  <CheckCircle2 size={12} />
                  {c}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Failure message */}
      {isFailure && failureReason ? (
        <div className="epp-trust-callout" style={{ borderColor: 'var(--state-error)' }}>
          <AlertOctagon size={16} style={{ color: 'var(--state-error)' }} />
          <div>
            <strong>This build was blocked because {failureReason}.</strong>
          </div>
        </div>
      ) : null}

      {/* Stack choice explanation */}
      {stackExplain ? (
        <div className="epp-reasoning">
          <strong>Stack reasoning:</strong> {stackExplain}
        </div>
      ) : null}

      <div className="epp-divider" />

      {/* Meta grid */}
      <div className="epp-meta-grid">
        <div className="epp-meta-row">
          <span className="epp-meta-label">Duration</span>
          <span className="epp-meta-value">
            {durationMs != null ? formatDuration(durationMs) : 'Not available yet.'}
          </span>
        </div>
        <div className="epp-meta-row">
          <span className="epp-meta-label">Timestamp</span>
          <span className="epp-meta-value">
            {timestamp || 'Not available yet.'}
          </span>
        </div>
      </div>

      {/* Build commands */}
      {buildCmds && buildCmds.length > 0 ? (
        <>
          <div className="epp-divider" />
          <div className="epp-section-title">Build Commands</div>
          <ul className="epp-build-cmds">
            {buildCmds.map((cmd, i) => (
              <li key={i}>{String(cmd)}</li>
            ))}
          </ul>
        </>
      ) : null}

      {/* Test results */}
      {testResults && typeof testResults === 'object' ? (
        <>
          <div className="epp-divider" />
          <div className="epp-section-title">Test Results</div>
          <div className="epp-test-block">
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>
              {JSON.stringify(testResults, null, 2)}
            </pre>
          </div>
        </>
      ) : null}
    </div>
  );
}

/** Tab: Agents — list agents that participated. */
function AgentsTab({ proof }) {
  const agentsUsed = get(proof, 'agents_used', []);

  if (!agentsUsed || agentsUsed.length === 0) {
    return (
      <div className="epp-not-available">
        <Info size={14} />
        Not available yet.
      </div>
    );
  }

  return (
    <div className="epp-animate-in">
      <div className="epp-section-title">
        {agentsUsed.length} agent{agentsUsed.length !== 1 ? 's' : ''} used
      </div>
      <div className="epp-agents-list">
        {agentsUsed.map((agent, i) => (
          <div key={i} className="epp-agent-card">
            <div className="epp-agent-icon">
              <Bot size={14} />
            </div>
            <div>
              <div className="epp-agent-name">{String(agent)}</div>
              <div className="epp-agent-status-label active">Participated</div>
            </div>
            <span className="epp-agent-status-dot active" />
          </div>
        ))}
      </div>
    </div>
  );
}

/** Tab: Files — file tree with highlighting. */
function FilesTab({ proof, openWorkspacePath }) {
  const generatedFiles = get(proof, 'generated_files', null);
  const count = get(generatedFiles, 'count', 0);
  const totalBytes = get(generatedFiles, 'total_bytes', 0);
  const tree = get(generatedFiles, 'tree', []);

  if (!generatedFiles || tree.length === 0) {
    return (
      <div className="epp-not-available">
        <Info size={14} />
        Not available yet.
      </div>
    );
  }

  return (
    <div className="epp-animate-in">
      <div className="epp-files-header">
        <span className="epp-files-stat">
          Files: <span>{count}</span>
        </span>
        <span className="epp-files-stat">
          Total: <span>{formatBytes(totalBytes)}</span>
        </span>
      </div>
      <ul className="epp-file-tree">
        {tree.map((filePath, i) => {
          const name = basename(filePath);
          const highlighted = HIGHLIGHTED_FILES.has(name);
          return (
            <li
              key={i}
              className={`epp-file-item ${highlighted ? 'highlighted' : ''} ${indentClass(filePath)}`}
              onClick={() => openWorkspacePath && openWorkspacePath(filePath)}
              style={openWorkspacePath ? { cursor: 'pointer' } : undefined}
              role={openWorkspacePath ? 'button' : undefined}
              tabIndex={openWorkspacePath ? 0 : undefined}
              onKeyDown={(e) => {
                if (openWorkspacePath && (e.key === 'Enter' || e.key === ' ')) {
                  e.preventDefault();
                  openWorkspacePath(filePath);
                }
              }}
            >
              {highlighted ? (
                <FileCode2 size={13} className="epp-file-icon highlighted" />
              ) : (
                <FileTree size={13} className="epp-file-icon" />
              )}
              <span className="epp-file-name">{filePath}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/** Tab: Validation — timeline of all validation steps. */
function ValidationTab({ proof }) {
  const validation = get(proof, 'validation', null);
  const stages = get(validation, 'stages', {});
  const overallPassed = get(validation, 'overall_passed', null);
  const totalDuration = get(validation, 'total_duration_ms', 0);

  /* Build timeline entries */
  const steps = [];

  /* Early pipeline steps (always shown) */
  steps.push({
    label: 'Intent parsed',
    status: proof.user_intent ? 'pass' : 'skip',
    detail: proof.user_intent ? `Parsed: "${String(proof.user_intent).substring(0, 80)}${String(proof.user_intent).length > 80 ? '…' : ''}"` : 'No user intent recorded.',
  });

  steps.push({
    label: 'Stack selected',
    status: proof.selected_stack ? 'pass' : 'skip',
    detail: proof.selected_stack ? `${get(proof, 'selected_stack.product_type', 'unknown')} · ${get(proof, 'selected_stack.frontend.framework', '?')} + ${get(proof, 'selected_stack.backend.framework', '?')}` : 'No stack selected.',
  });

  steps.push({
    label: 'Templates applied',
    status: 'pass',
    detail: 'Templates selected based on chosen stack.',
  });

  const genFiles = get(proof, 'generated_files', null);
  steps.push({
    label: 'Files generated',
    status: genFiles && genFiles.count > 0 ? 'pass' : 'skip',
    detail: genFiles ? `${genFiles.count} files (${formatBytes(genFiles.total_bytes)})` : 'No files recorded.',
  });

  /* Validation stages from the proof payload */
  const stageNames = ['syntax', 'build', 'runtime', 'integration'];

  for (const stage of stageNames) {
    const s = stages[stage];
    if (!s) {
      steps.push({
        label: `${stage.charAt(0).toUpperCase() + stage.slice(1)} validation`,
        status: 'skip',
        detail: 'Not run.',
      });
      continue;
    }
    const passed = s.passed;
    const duration = s.duration_ms;
    const errors = s.errors || [];
    steps.push({
      label: `${stage.charAt(0).toUpperCase() + stage.slice(1)} validation`,
      status: passed ? 'pass' : 'fail',
      detail: passed ? 'Passed.' : `${errors.length} error(s).`,
      duration,
      errors,
    });
  }

  /* Repair loop */
  const repairs = get(proof, 'repair_attempts', []);
  steps.push({
    label: 'Repair loop',
    status: repairs.length === 0 ? 'pass' : 'warn',
    detail: repairs.length === 0 ? 'No repairs needed.' : `${repairs.length} repair attempt(s) executed.`,
  });

  /* What-If simulation */
  const whatIf = get(proof, 'what_if_results', []);
  steps.push({
    label: 'What-If simulation',
    status: whatIf.length === 0 ? 'skip' : 'pass',
    detail: whatIf.length === 0 ? 'Not run.' : `${whatIf.length} scenario(s) simulated.`,
  });

  /* Proof artifact saved */
  steps.push({
    label: 'Proof artifact saved',
    status: proof.final_status ? 'pass' : 'pending',
    detail: proof.timestamp ? `Saved at ${proof.timestamp}` : 'Not saved yet.',
  });

  return (
    <div className="epp-animate-in">
      {overallPassed !== null && (
        <div style={{ marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)' }}>Overall:</span>
          {overallPassed ? (
            <span className="epp-confidence-badge epp-confidence-high">PASSED</span>
          ) : (
            <span className="epp-confidence-badge epp-confidence-low">FAILED</span>
          )}
          {totalDuration > 0 && (
            <span className="epp-mono epp-text-xs epp-text-muted">
              ({formatDuration(totalDuration)})
            </span>
          )}
        </div>
      )}

      <div className="epp-timeline">
        {steps.map((step, i) => (
          <div key={i} className="epp-timeline-step">
            <div className={`epp-timeline-icon ${step.status}`}>
              {step.status === 'pass' && <CheckCircle2 size={14} />}
              {step.status === 'fail' && <XCircle size={14} />}
              {step.status === 'warn' && <AlertTriangle size={14} />}
              {step.status === 'skip' && <Clock size={14} />}
              {step.status === 'pending' && <Clock size={14} />}
            </div>
            <div className="epp-timeline-body">
              <div className="epp-timeline-title">{step.label}</div>
              <div className="epp-timeline-detail">{step.detail}</div>
              {step.duration != null && step.duration > 0 && (
                <div className="epp-timeline-duration">{formatDuration(step.duration)}</div>
              )}
              {step.errors && step.errors.length > 0 && (
                <div className="epp-timeline-errors">
                  {step.errors.map((err, j) => (
                    <div key={j} className="epp-timeline-error">{String(err)}</div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Tab: Runtime — readiness checks and deployment info. */
function RuntimeTab({ proof }) {
  const readiness = get(proof, 'deployment.readiness', {});
  const previewUrl = get(proof, 'deployment.preview_url', '');
  const deployUrl = get(proof, 'deployment.deploy_url', '');
  const validation = get(proof, 'validation', null);
  const warnings = get(validation, 'warnings', []);
  const errors = get(validation, 'errors', []);

  const checks = [
    {
      label: 'Backend started',
      value: readiness.backend_starts,
      icon: Server,
    },
    {
      label: 'Frontend built',
      value: readiness.frontend_builds,
      icon: FileCode2,
    },
    {
      label: '/health responds',
      value: readiness.health_responds,
      icon: Activity,
    },
    {
      label: '/api/items responds',
      value: readiness.api_responds,
      icon: Zap,
    },
    {
      label: 'Not stub code',
      value: readiness.not_stub_code,
      icon: ShieldCheck,
    },
  ];

  return (
    <div className="epp-animate-in">
      <div className="epp-runtime-grid">
        {checks.map((check) => {
          const val = check.value;
          const status = val === true ? 'pass' : val === false ? 'fail' : 'skip';
          const StatusIcon = val === true ? CheckCircle2 : val === false ? XCircle : Clock;
          return (
            <div key={check.label} className={`epp-runtime-check ${status}`}>
              <div className={`epp-runtime-check-icon ${status}`}>
                <StatusIcon size={16} />
              </div>
              <span className="epp-runtime-check-label">{check.label}</span>
              <span className={`epp-runtime-check-status ${status}`}>
                {val === true ? 'PASS' : val === false ? 'FAIL' : 'WAIT'}
              </span>
            </div>
          );
        })}

        {/* Preview URL */}
        {previewUrl ? (
          <div className="epp-runtime-url">
            <ExternalLink size={14} />
            <div>
              <div className="epp-runtime-url-label">Preview</div>
              <a href={previewUrl} target="_blank" rel="noopener noreferrer">
                {previewUrl}
              </a>
            </div>
          </div>
        ) : null}

        {/* Deploy URL */}
        {deployUrl ? (
          <div className="epp-runtime-url">
            <ExternalLink size={14} />
            <div>
              <div className="epp-runtime-url-label">Deployment</div>
              <a href={deployUrl} target="_blank" rel="noopener noreferrer">
                {deployUrl}
              </a>
            </div>
          </div>
        ) : null}
      </div>

      {/* Logs (validation warnings/errors) */}
      {(warnings.length > 0 || errors.length > 0) && (
        <div className="epp-runtime-logs">
          <div className="epp-runtime-logs-title">Build &amp; Runtime Logs</div>
          {warnings.map((w, i) => (
            <div key={`w-${i}`} className="epp-runtime-log-entry warning">
              {String(w)}
            </div>
          ))}
          {errors.map((e, i) => (
            <div key={`e-${i}`} className="epp-runtime-log-entry error">
              {String(e)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/** Tab: Repairs — repair attempt history. */
function RepairsTab({ proof }) {
  const repairs = get(proof, 'repair_attempts', []);
  const [expandedIdx, setExpandedIdx] = useState(null);

  if (!repairs || repairs.length === 0) {
    return (
      <div className="epp-repairs-empty">
        <CheckCircle2 size={14} />
        No repairs were needed.
      </div>
    );
  }

  return (
    <div className="epp-animate-in">
      <div className="epp-section-title">
        {repairs.length} repair attempt{repairs.length !== 1 ? 's' : ''}
      </div>
      {repairs.map((repair, i) => {
        const isExpanded = expandedIdx === i;
        const result = String(get(repair, 'result', '')).toLowerCase();
        return (
          <div key={i} className="epp-repair-card">
            <div
              className="epp-repair-header"
              role="button"
              tabIndex={0}
              onClick={() => setExpandedIdx(isExpanded ? null : i)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  setExpandedIdx(isExpanded ? null : i);
                }
              }}
            >
              <span className="epp-repair-attempt-num">#{get(repair, 'attempt', i + 1)}</span>
              <span className="epp-repair-type">{get(repair, 'error_type', 'unknown')}</span>
              <span className="epp-repair-agent">{get(repair, 'agent_used', '')}</span>
              <span className={`epp-repair-result-badge ${result === 'pass' ? 'pass' : 'fail'}`}>
                {result === 'pass' ? 'PASS' : 'FAIL'}
              </span>
              <ChevronDown
                size={14}
                className={`epp-repair-chevron ${isExpanded ? 'expanded' : ''}`}
              />
            </div>
            {isExpanded && (
              <div className="epp-repair-detail">
                <div className="epp-repair-detail-label">Error Log</div>
                <div className="epp-repair-log-block">
                  {get(repair, 'error_log', 'No log available.')}
                </div>
                <div className="epp-repair-detail-label">Files Changed</div>
                {repair.files_changed && repair.files_changed.length > 0 ? (
                  <ul className="epp-repair-files-list">
                    {repair.files_changed.map((f, j) => (
                      <li key={j} className="epp-repair-file-item">
                        <FileCode2 size={10} />
                        {String(f)}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="epp-text-xs epp-text-muted">No files recorded.</div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/** Tab: What-If — failure simulation results. */
function WhatIfTab({ proof }) {
  const results = get(proof, 'what_if_results', []);

  if (!results || results.length === 0) {
    return (
      <div className="epp-whatif-empty">
        <Info size={14} />
        No failure simulation was run.
      </div>
    );
  }

  return (
    <div className="epp-animate-in">
      <div className="epp-section-title">
        {results.length} scenario{results.length !== 1 ? 's' : ''} simulated
      </div>
      {results.map((item, i) => {
        const risk = riskCls(get(item, 'risk', 'low'));
        return (
          <div key={i} className={`epp-whatif-card risk-${risk}`}>
            <div className="epp-whatif-header">
              <span className="epp-whatif-scenario">
                {get(item, 'scenario', `Scenario ${i + 1}`)}
              </span>
              <span className={`epp-risk-badge ${risk}`}>
                {String(get(item, 'risk', 'low')).toUpperCase()}
              </span>
            </div>
            <div className="epp-whatif-result">
              {get(item, 'result', 'No result available.')}
            </div>
            {get(item, 'recommended_fix') ? (
              <div className="epp-whatif-fix">
                <Wrench size={12} />
                <span className="epp-whatif-fix-label">Fix:</span>
                {String(item.recommended_fix)}
              </div>
            ) : null}
            {get(item, 'auto_fix_available') ? (
              <div className="epp-whatif-autofix">
                <Zap size={10} />
                Auto-fix available
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

/** Tab: Downloads — 4 download buttons. */
function DownloadsTab({ proof, jobId }) {
  /** Download proof.json */
  const handleDownloadProof = useCallback(() => {
    if (!proof) return;
    downloadText(
      `proof-${jobId || 'unknown'}.json`,
      JSON.stringify(proof, null, 2),
      'application/json',
    );
  }, [proof, jobId]);

  /** Download build logs (validation warnings/errors as text). */
  const handleDownloadLogs = useCallback(() => {
    if (!proof) return;
    const lines = [];
    const validation = get(proof, 'validation', {});
    const warnings = get(validation, 'warnings', []);
    const errors = get(validation, 'errors', []);
    if (warnings.length > 0) {
      lines.push('=== WARNINGS ===');
      warnings.forEach((w) => lines.push(String(w)));
    }
    if (errors.length > 0) {
      lines.push('=== ERRORS ===');
      errors.forEach((e) => lines.push(String(e)));
    }
    if (lines.length === 0) {
      lines.push('No warnings or errors recorded.');
    }
    downloadText(`build-logs-${jobId || 'unknown'}.txt`, lines.join('\n'));
  }, [proof, jobId]);

  /** Download What-If report. */
  const handleDownloadWhatIf = useCallback(() => {
    const results = get(proof, 'what_if_results', []);
    if (!results || results.length === 0) {
      downloadText(`whatif-${jobId || 'unknown'}.txt`, 'No What-If results available.');
      return;
    }
    const lines = ['What-If Failure Simulation Report', '=====================================\n'];
    results.forEach((item, i) => {
      lines.push(`Scenario ${i + 1}: ${get(item, 'scenario', 'unknown')}`);
      lines.push(`Risk: ${get(item, 'risk', 'unknown')}`);
      lines.push(`Result: ${get(item, 'result', 'N/A')}`);
      lines.push(`Recommended Fix: ${get(item, 'recommended_fix', 'N/A')}`);
      lines.push(`Auto-fix Available: ${get(item, 'auto_fix_available', false)}`);
      lines.push('');
    });
    downloadText(`whatif-${jobId || 'unknown'}.txt`, lines.join('\n'));
  }, [proof, jobId]);

  /** Download file tree. */
  const handleDownloadTree = useCallback(() => {
    const tree = get(proof, 'generated_files.tree', []);
    if (!tree || tree.length === 0) {
      downloadText(`file-tree-${jobId || 'unknown'}.txt`, 'No file tree available.');
      return;
    }
    const header = `File Tree (${tree.length} files)\n${'='.repeat(40)}\n`;
    downloadText(`file-tree-${jobId || 'unknown'}.txt`, header + tree.join('\n'));
  }, [proof, jobId]);

  const downloads = [
    {
      Icon: FileJson,
      title: 'Download proof.json',
      desc: 'Full proof artifact as formatted JSON.',
      onClick: handleDownloadProof,
      actionLabel: 'JSON',
    },
    {
      Icon: FileText,
      title: 'Download build logs',
      desc: 'Validation warnings and errors as plain text.',
      onClick: handleDownloadLogs,
      actionLabel: 'TXT',
    },
    {
      Icon: ScrollText,
      title: 'Download What-If report',
      desc: 'Failure simulation results as formatted text.',
      onClick: handleDownloadWhatIf,
      actionLabel: 'TXT',
    },
    {
      Icon: FolderTree,
      title: 'Download file tree',
      desc: 'Generated file paths as plain text.',
      onClick: handleDownloadTree,
      actionLabel: 'TXT',
    },
  ];

  return (
    <div className="epp-animate-in">
      <div className="epp-downloads-grid">
        {downloads.map((dl, i) => (
          <div
            key={i}
            className="epp-download-card"
            role="button"
            tabIndex={0}
            onClick={dl.onClick}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                dl.onClick();
              }
            }}
          >
            <div className="epp-download-icon">
              <dl.Icon size={18} />
            </div>
            <div className="epp-download-info">
              <div className="epp-download-title">{dl.title}</div>
              <div className="epp-download-desc">{dl.desc}</div>
            </div>
            <div className="epp-download-action">
              <Download size={12} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------------
   Main Component
   --------------------------------------------------------------------------- */

export default function EnhancedProofPanel({
  proof,
  jobId,
  jobStatus,
  openWorkspacePath,
  onRepair,
  onReplay,
}) {
  const { token } = useAuth();
  const [activeTab, setActiveTab] = useState('overview');

  /**
   * Determine whether the "Repair From Proof" button should be shown.
   * Visible if final_status is fail, any validation stage failed, or any
   * What-If scenario has risk=high.
   */
  const showRepairButton = useMemo(() => {
    if (!proof) return false;
    const status = get(proof, 'final_status', '').toLowerCase();
    if (status === 'fail') return true;

    const stages = get(proof, 'validation.stages', {});
    for (const key of Object.keys(stages)) {
      if (stages[key] && stages[key].passed === false) return true;
    }

    const whatIf = get(proof, 'what_if_results', []);
    if (whatIf.some((w) => String(get(w, 'risk', '')).toLowerCase() === 'high')) return true;

    return false;
  }, [proof]);

  /** Replay button is disabled while job is still running. */
  const normalizedStatus = String(jobStatus || '').trim().toLowerCase();
  const isJobRunning = ['running', 'pending', 'queued', 'in_progress', 'inprogress'].includes(normalizedStatus);

  /* Early return: no proof loaded */
  if (!proof) {
    return (
      <div className="enhanced-proof-panel epp-empty">
        <ShieldCheck size={28} />
        <span className="epp-empty-title">{jobId ? 'Loading proof…' : 'No proof yet'}</span>
        <span className="epp-empty-desc">
          {jobId
            ? 'Proof artifact is being generated. This panel will populate once the build completes validation.'
            : 'Select a job to view its proof artifact with full validation details.'}
        </span>
      </div>
    );
  }

  /* Destructure top-level fields for the overview section */
  const finalStatus = get(proof, 'final_status', 'pending');
  const stInfo = statusInfo(finalStatus);
  const confidence = get(proof, 'confidence.score', null);
  const confidenceTier = get(proof, 'confidence.tier', '');
  const confCls = confidence != null ? confidenceCls(confidence) : '';
  const projectId = get(proof, 'project_id', '');
  const stack = get(proof, 'selected_stack', {});
  const productType = get(stack, 'product_type', '');
  const frontendFw = get(stack, 'frontend.framework', '');
  const backendFw = get(stack, 'backend.framework', '');
  const stackReasoning = get(stack, 'reasoning', '');

  /* Render the active tab content */
  function renderTabContent() {
    switch (activeTab) {
      case 'overview':
        return <OverviewTab proof={proof} jobId={jobId} />;
      case 'agents':
        return <AgentsTab proof={proof} />;
      case 'files':
        return <FilesTab proof={proof} openWorkspacePath={openWorkspacePath} />;
      case 'validation':
        return <ValidationTab proof={proof} />;
      case 'runtime':
        return <RuntimeTab proof={proof} />;
      case 'repairs':
        return <RepairsTab proof={proof} />;
      case 'whatif':
        return <WhatIfTab proof={proof} />;
      case 'downloads':
        return <DownloadsTab proof={proof} jobId={jobId} />;
      default:
        return null;
    }
  }

  return (
    <div className="enhanced-proof-panel">
      {/* Section 1: Build Overview — always visible at top */}
      <div className="epp-overview">
        {/* Status badge + confidence */}
        <div className="epp-status-row">
          <span className={`epp-status-badge ${stInfo.cls}`}>
            <stInfo.Icon size={12} />
            {stInfo.label}
          </span>
          {confidence != null && (
            <span className={`epp-confidence-badge ${confCls}`}>
              {(confidence * 100).toFixed(0)}% confidence
              {confidenceTier ? ` · ${confidenceLabel(confidenceTier)}` : ''}
            </span>
          )}
        </div>

        {/* Job & Project IDs */}
        <div className="epp-ids-row">
          <span>
            <span className="epp-id-label">Job:</span>
            <span className="epp-id-value">{jobId || 'N/A'}</span>
          </span>
          {projectId && (
            <span>
              <span className="epp-id-label">Project:</span>
              <span className="epp-id-value">{projectId}</span>
            </span>
          )}
        </div>

        {/* Selected stack summary */}
        {(productType || frontendFw || backendFw) && (
          <div className="epp-stack-row">
            {productType && (
              <span className="epp-stack-tag">
                <FileCode2 size={10} />
                {String(productType)}
              </span>
            )}
            {frontendFw && (
              <span className="epp-stack-tag">
                <FileCode2 size={10} />
                {String(frontendFw)}
              </span>
            )}
            {frontendFw && backendFw && (
              <span className="epp-stack-separator">+</span>
            )}
            {backendFw && (
              <span className="epp-stack-tag">
                <Server size={10} />
                {String(backendFw)}
              </span>
            )}
          </div>
        )}

        {/* Stack reasoning */}
        {stackReasoning && (
          <div className="epp-reasoning">{stackReasoning}</div>
        )}

        {/* Explanations.stack_choice */}
        {get(proof, 'explanations.stack_choice') && (
          <div className="epp-reasoning">
            <strong>Why this stack:</strong> {get(proof, 'explanations.stack_choice')}
          </div>
        )}
      </div>

      {/* Section 2: Sub-tab navigation */}
      <div className="epp-tabs-nav" role="tablist">
        {TABS.map(({ key, label, Icon }) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={activeTab === key}
            className={`epp-tab-btn ${activeTab === key ? 'active' : ''}`}
            onClick={() => setActiveTab(key)}
          >
            <Icon size={13} />
            {label}
            {/* Optional tab badges */}
            {key === 'files' && (() => {
              const c = get(proof, 'generated_files.count', 0);
              return c > 0 ? <span className="epp-tab-badge">{c}</span> : null;
            })()}
            {key === 'agents' && (() => {
              const a = get(proof, 'agents_used', []);
              return a.length > 0 ? <span className="epp-tab-badge">{a.length}</span> : null;
            })()}
            {key === 'repairs' && (() => {
              const r = get(proof, 'repair_attempts', []);
              return r.length > 0 ? <span className="epp-tab-badge">{r.length}</span> : null;
            })()}
            {key === 'whatif' && (() => {
              const w = get(proof, 'what_if_results', []);
              return w.length > 0 ? <span className="epp-tab-badge">{w.length}</span> : null;
            })()}
          </button>
        ))}
      </div>

      {/* Action buttons bar */}
      <div className="epp-actions-bar">
        {showRepairButton && onRepair && (
          <button
            type="button"
            className="epp-action-btn epp-action-repair"
            onClick={onRepair}
            title="Attempt to repair the build using proof data"
          >
            <Wrench size={13} />
            Repair From Proof
          </button>
        )}
        {onReplay && (
          <button
            type="button"
            className="epp-action-btn epp-action-replay"
            onClick={onReplay}
            disabled={isJobRunning}
            title={isJobRunning ? 'Cannot replay while job is running' : 'Replay the build from scratch'}
          >
            <RotateCcw size={13} />
            Replay Build
          </button>
        )}
      </div>

      {/* Tab content area */}
      <div className="epp-content" role="tabpanel">
        {renderTabContent()}
      </div>
    </div>
  );
}

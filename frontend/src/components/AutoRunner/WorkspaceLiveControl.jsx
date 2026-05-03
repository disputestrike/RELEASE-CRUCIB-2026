import React, { useMemo } from 'react';
import {
  Activity,
  CheckCircle2,
  CircleAlert,
  CircleDot,
  Download,
  Eye,
  FileText,
  Mic,
  Paperclip,
  ShieldCheck,
  TerminalSquare,
} from 'lucide-react';
import './WorkspaceLiveControl.css';

function normalizeStatus(value) {
  if (value === 'ready' || value === 'ok' || value === 'passed') return 'ok';
  if (value === 'warn' || value === 'partial' || value === 'waiting') return 'warn';
  if (value === 'error' || value === 'failed' || value === 'blocked') return 'error';
  return 'idle';
}

function StatusIcon({ status }) {
  const s = normalizeStatus(status);
  if (s === 'ok') return <CheckCircle2 size={14} />;
  if (s === 'error') return <CircleAlert size={14} />;
  if (s === 'warn') return <CircleDot size={14} />;
  return <Activity size={14} />;
}

function LiveRow({ icon, label, value, status = 'idle', detail, actionLabel, onAction }) {
  const s = normalizeStatus(status);
  return (
    <div className={`wlc-row wlc-row--${s}`}>
      <div className="wlc-row-icon">{icon}</div>
      <div className="wlc-row-main">
        <div className="wlc-row-line">
          <span className="wlc-row-label">{label}</span>
          <span className="wlc-row-value">{value}</span>
        </div>
        {detail ? <div className="wlc-row-detail">{detail}</div> : null}
      </div>
      <div className="wlc-row-state" aria-label={s}>
        <StatusIcon status={s} />
      </div>
      {actionLabel && typeof onAction === 'function' ? (
        <button type="button" className="wlc-row-action" onClick={onAction}>
          {actionLabel}
        </button>
      ) : null}
    </div>
  );
}

function latestEventSummary(events) {
  if (!Array.isArray(events) || !events.length) return 'No events yet';
  const ev = events[events.length - 1] || {};
  const type = ev.type || ev.event_type || 'event';
  const payload = ev.payload && typeof ev.payload === 'object' ? ev.payload : {};
  const label =
    payload.agent ||
    payload.agent_name ||
    payload.step_key ||
    payload.file ||
    payload.path ||
    payload.headline ||
    '';
  return label ? `${type}: ${String(label).slice(0, 80)}` : type;
}

function compactFailure(latestFailure, fallback) {
  if (latestFailure && typeof latestFailure === 'object') {
    const issues = Array.isArray(latestFailure.issues) ? latestFailure.issues : [];
    const firstIssue = issues.find(Boolean);
    const message = latestFailure.error_message || firstIssue || latestFailure.step_key;
    if (message) return String(message).slice(0, 160);
  }
  return fallback ? String(fallback).slice(0, 160) : '';
}

export default function WorkspaceLiveControl({
  job = null,
  stage = 'input',
  steps = [],
  events = [],
  proof = null,
  previewStatus = 'idle',
  previewUrl = null,
  hasSandpack = false,
  workspacePathCount = 0,
  latestFailure = null,
  blockedDetail = null,
  connectionMode = 'idle',
  isConnected = false,
  proofItemCount = 0,
  activeAgentCount = 0,
  healthLatencyMs = null,
  onOpenPreview,
  onOpenProof,
  onOpenCode,
  onOpenFailure,
}) {
  const totalSteps = Array.isArray(steps) ? steps.length : 0;
  const completedSteps = steps.filter((s) => s.status === 'completed').length;
  const failedSteps = steps.filter((s) => s.status === 'failed' || s.status === 'blocked').length;
  const runningSteps = steps.filter((s) => s.status === 'running').length;
  const jobStatus = job?.status || stage || 'idle';
  const hasJob = Boolean(job?.id || job?.job_id);
  const proofBackedPaths = useMemo(() => {
    const rows = proof?.bundle?.files;
    if (!Array.isArray(rows)) return 0;
    const set = new Set();
    for (const row of rows) {
      const pl = row?.payload && typeof row.payload === 'object' ? row.payload : {};
      const p = pl.path || pl.file || row?.title;
      if (typeof p === 'string' && p.includes('.') && !p.startsWith('http')) {
        set.add(p.replace(/^\/+/, ''));
      }
    }
    return set.size;
  }, [proof]);
  const displayFileCount = Math.max(workspacePathCount || 0, proofBackedPaths || 0);
  const hasFiles = displayFileCount > 0;
  const hasProof = proofItemCount > 0 || Boolean(proof?.bundle);
  const hasPreview = Boolean(previewUrl) || hasSandpack || previewStatus === 'ready' || previewStatus === 'building';
  const hasFailure = jobStatus === 'failed' || failedSteps > 0 || Boolean(latestFailure);

  const overall = useMemo(() => {
    if (hasFailure) return 'error';
    if (jobStatus === 'completed' && hasFiles && hasProof && hasPreview) return 'ok';
    if (hasJob || runningSteps || events.length) return 'warn';
    return 'idle';
  }, [events.length, hasFailure, hasFiles, hasJob, hasPreview, hasProof, jobStatus, runningSteps]);

  const streamDetail = isConnected
    ? `${connectionMode || 'stream'} connected`
    : events.length
      ? `${connectionMode || 'poll'} receiving updates`
      : 'Waiting for first job event';

  return (
    <section className="wlc-root" aria-label="Live build control">
      <div className={`wlc-summary wlc-summary--${normalizeStatus(overall)}`}>
        <div>
          <div className="wlc-kicker">Live control</div>
          <h3 className="wlc-title">{job?.goal || 'Workspace readiness'}</h3>
        </div>
        <div className="wlc-summary-pill">
          <StatusIcon status={overall} />
              <span>{hasFailure ? 'Fixing' : jobStatus}</span>
        </div>
      </div>

      <div className="wlc-metrics">
        <div><span>{completedSteps}/{totalSteps || 0}</span><small>steps</small></div>
        <div><span>{events.length}</span><small>events</small></div>
        <div><span>{displayFileCount}</span><small>files</small></div>
        <div><span>{proofItemCount}</span><small>proof</small></div>
      </div>

      <div className="wlc-section">
        <LiveRow
          icon={<Mic size={15} />}
          label="Input"
          value="Text, mic, files"
          status="ok"
          detail="Composer accepts typed goals, browser speech input, and attached context files."
        />
        <LiveRow
          icon={<Activity size={15} />}
          label="Job"
          value={hasJob ? String(job?.id || job?.job_id).slice(0, 12) : 'Not bound'}
          status={hasJob ? 'ok' : 'waiting'}
          detail={hasJob ? `Status: ${jobStatus}` : 'A build must bind to a durable job before work becomes truth.'}
        />
        <LiveRow
          icon={<CircleDot size={15} />}
          label="Stream"
          value={streamDetail}
          status={events.length ? 'ok' : hasJob ? 'waiting' : 'idle'}
          detail={latestEventSummary(events)}
        />
        <LiveRow
          icon={<FileText size={15} />}
          label="Files"
          value={hasFiles ? `${displayFileCount} paths (workspace + proof)` : 'No files yet'}
          status={hasFiles ? 'ok' : hasJob ? 'waiting' : 'idle'}
          detail={hasFiles ? 'File tree, code pane, preview, and export should share this workspace.' : 'Waiting for generated files.'}
          actionLabel={hasFiles ? 'Code' : null}
          onAction={onOpenCode}
        />
        <LiveRow
          icon={<Eye size={15} />}
          label="Preview"
          value={previewUrl ? 'Live URL' : hasSandpack ? 'Sandpack fallback' : previewStatus}
          status={hasPreview ? 'ok' : hasJob ? 'waiting' : 'idle'}
          detail={previewUrl ? previewUrl : hasSandpack ? 'Rendering from generated workspace files.' : 'Preview starts after files or a dev server are ready.'}
          actionLabel="Preview"
          onAction={onOpenPreview}
        />
        <LiveRow
          icon={<ShieldCheck size={15} />}
          label="Proof"
          value={hasProof ? `${proofItemCount} items` : 'No proof yet'}
          status={hasProof ? 'ok' : jobStatus === 'completed' ? 'error' : hasJob ? 'waiting' : 'idle'}
            detail={hasProof ? 'Proof evidence is attached to this run.' : 'Completion must produce proof before claims are safe.'}
          actionLabel="Proof"
          onAction={onOpenProof}
        />
        <LiveRow
          icon={<Download size={15} />}
          label="Export"
          value={hasFiles ? (jobStatus === 'completed' ? 'Verified ZIP available' : 'Draft workspace available') : 'Waiting for files'}
          status={hasFiles && jobStatus === 'completed' ? 'ok' : hasJob ? 'waiting' : 'idle'}
          detail={jobStatus === 'completed' ? 'Final handoff export includes source, context, and proof artifacts.' : 'Final export is gated until contract, preview, and proof checks pass.'}
        />
        <LiveRow
          icon={<TerminalSquare size={15} />}
          label="Terminal"
          value={activeAgentCount > 0 ? `${activeAgentCount} active agents` : healthLatencyMs == null ? 'Policy gated' : `${healthLatencyMs}ms API`}
          status={healthLatencyMs == null && hasJob ? 'waiting' : 'ok'}
          detail="Terminal output and build commands belong in the same evidence chain."
        />
        {hasFailure ? (
          <LiveRow
            icon={<CircleAlert size={15} />}
            label="Failure"
            value="Preserved"
            status="error"
            detail={compactFailure(latestFailure, blockedDetail)}
            actionLabel="Failure"
            onAction={onOpenFailure}
          />
        ) : null}
      </div>
    </section>
  );
}

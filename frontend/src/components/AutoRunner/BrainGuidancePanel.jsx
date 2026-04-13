/**
 * Shows the latest brain_guidance event (failure coach or resume coach) as readable next steps.
 * When proof includes verification_failed / step_exception rows, surfaces that text here (plain language).
 */
import React from 'react';
import { Lightbulb, ListOrdered } from 'lucide-react';
import './BrainGuidancePanel.css';

function parseGuidancePayload(raw) {
  const p =
    raw?.payload && typeof raw.payload === 'object'
      ? raw.payload
      : typeof raw?.payload_json === 'string'
        ? (() => {
            try {
              return JSON.parse(raw.payload_json);
            } catch {
              return {};
            }
          })()
        : raw;
  if (!p || typeof p !== 'object') return null;
  return {
    headline: p.headline || p.summary?.slice(0, 200) || 'Guidance',
    summary: p.summary || '',
    next_steps: Array.isArray(p.next_steps) ? p.next_steps : [],
    kind: p.kind || '',
    step_key: p.step_key || '',
  };
}

/** Prefer failure / steering guidance over live progress pulses so blockers stay visible. */
function pickLatestGuidance(events) {
  if (!Array.isArray(events) || !events.length) return null;
  const hits = events.filter((e) => {
    const t = e?.type || e?.event_type;
    return t === 'brain_guidance';
  });
  if (!hits.length) return null;
  const parsed = hits.map((h) => parseGuidancePayload(h)).filter(Boolean);
  if (!parsed.length) return null;
  const nonProgress = parsed.filter((p) => p.kind !== 'progress_narrative');
  const pool = nonProgress.length ? nonProgress : parsed;
  const last = pool[pool.length - 1];
  return last;
}

function humanizeStepKey(sk) {
  const s = String(sk || '').trim();
  if (!s) return '';
  if (s.startsWith('agents.')) {
    const tail = s.slice('agents.'.length).replace(/_/g, ' ');
    return tail ? tail.charAt(0).toUpperCase() + tail.slice(1) : '';
  }
  if (s.startsWith('verification.')) {
    const tail = s.slice('verification.'.length).replace(/_/g, ' ');
    return tail ? `Verify ${tail.charAt(0).toUpperCase() + tail.slice(1)}` : '';
  }
  return s.replace(/\./g, ' · ').replace(/_/g, ' ');
}

function summarizeFailureStep(step) {
  if (!step || typeof step !== 'object') return '';
  const key = (step.step_key || step.agent_name || '').trim();
  const err = (step.error_message || step.error || '').trim();
  const bits = [];
  if (key) bits.push(String(key));
  if (err) bits.push(err.slice(0, 360));
  return bits.join(' — ');
}

const FAILURE_PROOF_TYPES = new Set(['verification_failed', 'step_exception']);

function pickLatestStoredFailureProof(proof) {
  const ver = proof?.bundle?.verification;
  if (!Array.isArray(ver)) return null;
  const rows = ver.filter((x) => FAILURE_PROOF_TYPES.has(x.proof_type || x.type));
  if (!rows.length) return null;
  return rows[rows.length - 1];
}

function summarizeStoredFailureProof(item) {
  if (!item?.payload || typeof item.payload !== 'object') return '';
  const p = item.payload;
  if (p.kind === 'verification_failed') {
    const issues = Array.isArray(p.issues) ? p.issues : [];
    const lines = issues.slice(0, 3).map((x) => String(x).trim().slice(0, 220));
    const fr = p.failure_reason ? `Reason: ${p.failure_reason}. ` : '';
    const sk = p.step_key ? `Step ${p.step_key}. ` : '';
    const body = lines.filter(Boolean).join(' · ') || 'Verification did not pass.';
    return `${sk}${fr}${body}`.trim();
  }
  if (p.kind === 'step_exception') {
    const sk = p.step_key ? `${p.step_key}: ` : '';
    return `${sk}${String(p.error || '').trim().slice(0, 360)}`.trim();
  }
  return '';
}

/** Server checkpoint ``latest_failure`` (GET /jobs/:id) when proof rows lag. */
function summarizeLatestFailureCheckpoint(cf) {
  if (!cf || typeof cf !== 'object') return '';
  const issues = Array.isArray(cf.issues) ? cf.issues : [];
  const lines = issues.slice(0, 3).map((x) => String(x).trim().slice(0, 220));
  const fr = cf.failure_reason ? `Reason: ${cf.failure_reason}. ` : '';
  const sk = cf.step_key ? `Step ${cf.step_key}. ` : '';
  const st = cf.status === 'step_exception' && cf.exc_type ? `(${cf.exc_type}) ` : '';
  if (lines.length) return `${sk}${st}${fr}${lines.join(' · ')}`.trim();
  const err = cf.error_message ? String(cf.error_message).trim().slice(0, 360) : '';
  return `${sk}${st}${fr}${err}`.trim();
}

function RepairMetaLine({ checkpoint }) {
  if (!checkpoint || typeof checkpoint !== 'object') return null;
  const rc = checkpoint.retry_count;
  const bs = checkpoint.brain_strategy;
  if ((rc == null || Number(rc) <= 0) && !bs) return null;
  return (
    <p className="bgp-repair-meta">
      {rc != null && Number(rc) > 0 ? `Retry attempt ${Number(rc)}. ` : null}
      {bs ? `Strategy: ${String(bs).slice(0, 140)}` : null}
    </p>
  );
}

function EvidenceBlock({ text, repairMeta }) {
  if (!text) return null;
  return (
    <div className="bgp-evidence-wrap">
      <p className="bgp-subhead">Recorded detail</p>
      <p className="bgp-evidence">{text}</p>
      <RepairMetaLine checkpoint={repairMeta} />
      <p className="bgp-evidence-hint">Open the Proof tab for the full row; Timeline keeps technical trace.</p>
    </div>
  );
}

function MilestoneStrip({ batch, repairCount }) {
  if (!batch || typeof batch !== 'object') return null;
  const phase = String(batch.phase || '').trim();
  const keys = Array.isArray(batch.completed_step_keys) ? batch.completed_step_keys : [];
  if (!phase && keys.length === 0) return null;
  const tail = keys.length
    ? `${keys.length} step${keys.length === 1 ? '' : 's'} finished in the last batch`
    : null;
  return (
    <div className="bgp-milestone">
      <p className="bgp-subhead">Latest progress</p>
      <p className="bgp-milestone-body">
        {phase ? <span className="bgp-milestone-phase">{phase}</span> : null}
        {phase && tail ? ' · ' : null}
        {tail}
      </p>
      {repairCount > 0 ? (
        <p className="bgp-milestone-repairs">{repairCount} repair event{repairCount === 1 ? '' : 's'} on file (checkpointed)</p>
      ) : null}
    </div>
  );
}

export default function BrainGuidancePanel({
  events,
  jobStatus,
  failureStep = null,
  proof = null,
  latestFailure = null,
  milestoneBatch = null,
  repairQueueLen = 0,
}) {
  const g = pickLatestGuidance(events);
  const failureSummary = summarizeFailureStep(failureStep);
  const storedFailure = pickLatestStoredFailureProof(proof);
  const fromProof =
    jobStatus === 'failed' || jobStatus === 'cancelled'
      ? summarizeStoredFailureProof(storedFailure)
      : '';
  const fromCheckpoint =
    !fromProof && (jobStatus === 'failed' || jobStatus === 'cancelled')
      ? summarizeLatestFailureCheckpoint(latestFailure)
      : '';
  const evidenceText = fromProof || fromCheckpoint;

  if (!g && jobStatus !== 'failed' && jobStatus !== 'cancelled' && !failureSummary) return null;
  if (!g) {
    return (
      <aside className="bgp-root" aria-label="Build status">
        <div className="bgp-header">
          <Lightbulb size={14} className="bgp-icon" />
          <span>Build status</span>
        </div>
        {failureSummary ? (
          <>
            <p className="bgp-headline">Current blocker</p>
            <p className="bgp-summary">{failureSummary}</p>
            <EvidenceBlock text={evidenceText} repairMeta={latestFailure} />
            <p className="bgp-muted">
              Describe what to change below and press Enter — we record it on the job and resume the runner when
              appropriate. Completed files stay in your workspace.
            </p>
          </>
        ) : (
          <p className="bgp-muted">
            When guidance is available from the orchestrator, it will show here. You can always steer from the composer
            below.
          </p>
        )}
      </aside>
    );
  }

  return (
    <aside className="bgp-root" aria-label="Build status">
      <div className="bgp-header">
        <Lightbulb size={14} className="bgp-icon" />
        <span>Build status</span>
        {g.step_key ? (
          <span className="bgp-step" title={g.step_key}>
            {humanizeStepKey(g.step_key)}
          </span>
        ) : null}
      </div>
      <MilestoneStrip batch={milestoneBatch} repairCount={repairQueueLen} />
      <p className="bgp-headline">{g.headline}</p>
      {g.summary && g.summary !== g.headline ? <p className="bgp-summary">{g.summary}</p> : null}
      <EvidenceBlock text={evidenceText} repairMeta={latestFailure} />
      {g.next_steps.length > 0 ? (
        <div className="bgp-steps">
          <div className="bgp-steps-label">
            <ListOrdered size={12} /> Next steps
          </div>
          <ol className="bgp-ol">
            {g.next_steps.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ol>
        </div>
      ) : null}
    </aside>
  );
}

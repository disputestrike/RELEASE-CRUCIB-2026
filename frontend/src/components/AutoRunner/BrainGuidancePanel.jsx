/**
 * Single “brain voice” for the middle pane: status, milestones, blockers, and next actions
 * in one calm card (orchestrator guidance + failure context + composer hint).
 */
import React, { useMemo } from 'react';
import { Sparkles, ListOrdered } from 'lucide-react';
import { extractActivityChips } from '../../workspace/workspaceLiveUi';
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
  return pool[pool.length - 1];
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
  if (key) bits.push(humanizeStepKey(key) || String(key));
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
    const fr = p.failure_reason ? `${p.failure_reason}. ` : '';
    const sk = p.step_key ? `${humanizeStepKey(p.step_key) || p.step_key}. ` : '';
    const body = lines.filter(Boolean).join(' · ') || 'Verification did not pass.';
    return `${sk}${fr}${body}`.trim();
  }
  if (p.kind === 'step_exception') {
    const sk = p.step_key ? `${humanizeStepKey(p.step_key) || p.step_key}: ` : '';
    return `${sk}${String(p.error || '').trim().slice(0, 360)}`.trim();
  }
  return '';
}

function summarizeLatestFailureCheckpoint(cf) {
  if (!cf || typeof cf !== 'object') return '';
  const issues = Array.isArray(cf.issues) ? cf.issues : [];
  const lines = issues.slice(0, 3).map((x) => String(x).trim().slice(0, 220));
  const fr = cf.failure_reason ? `${cf.failure_reason}. ` : '';
  const sk = cf.step_key ? `${humanizeStepKey(cf.step_key) || cf.step_key}. ` : '';
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
      {rc != null && Number(rc) > 0 ? `Attempt ${Number(rc)}. ` : null}
      {bs ? String(bs).slice(0, 140) : null}
    </p>
  );
}

function NextCue({ children }) {
  if (!children) return null;
  return <p className="bgp-next">{children}</p>;
}

function EvidenceBlock({ text, repairMeta }) {
  if (!text) return null;
  return (
    <div className="bgp-evidence-wrap">
      <p className="bgp-subhead">What we know</p>
      <p className="bgp-evidence">{text}</p>
      <RepairMetaLine checkpoint={repairMeta} />
      <p className="bgp-evidence-hint">Proof tab holds the full record.</p>
    </div>
  );
}

function StepProgressPreservedLine({ steps, jobStatus }) {
  if (!Array.isArray(steps) || steps.length === 0) return null;
  const terminal =
    jobStatus === 'failed' ||
    jobStatus === 'cancelled' ||
    jobStatus === 'blocked';
  if (!terminal) return null;
  const total = steps.length;
  const completed = steps.filter((s) => s?.status === 'completed').length;
  return (
    <p className="bgp-progress-preserved">
      {completed} of {total} steps completed. Progress from finished steps is preserved — you can steer
      and resume from here.
    </p>
  );
}

function MilestoneStrip({ batch, repairCount }) {
  if (!batch || typeof batch !== 'object') {
    if (repairCount > 0) {
      return (
        <div className="bgp-milestone">
          <p className="bgp-subhead">Progress</p>
          <p className="bgp-milestone-body">
            {repairCount} steering or repair note{repairCount === 1 ? '' : 's'} saved on this run
          </p>
        </div>
      );
    }
    return null;
  }
  const phase = String(batch.phase || '').trim();
  const keys = Array.isArray(batch.completed_step_keys) ? batch.completed_step_keys : [];
  if (!phase && keys.length === 0 && repairCount <= 0) return null;
  const tail = keys.length
    ? `${keys.length} step${keys.length === 1 ? '' : 's'} just finished`
    : null;
  return (
    <div className="bgp-milestone">
      <p className="bgp-subhead">Progress</p>
      <p className="bgp-milestone-body">
        {phase ? <span className="bgp-milestone-phase">{phase}</span> : null}
        {phase && tail ? ' · ' : null}
        {tail}
        {repairCount > 0 ? (
          <span className="bgp-milestone-repairs-inline">
            {' '}
            · {repairCount} repair note{repairCount === 1 ? '' : 's'} saved
          </span>
        ) : null}
      </p>
    </div>
  );
}

export default function BrainGuidancePanel({
  jobId = null,
  workspaceStage = 'input',
  jobHydrating = false,
  events,
  jobStatus,
  failureStep = null,
  proof = null,
  latestFailure = null,
  milestoneBatch = null,
  repairQueueLen = 0,
  steps = [],
  taskProgress = null,
  actionChips = [],
  controller = null,
}) {
  const activityChips = useMemo(
    () => (jobId ? extractActivityChips(events, 10) : []),
    [jobId, events],
  );

  if (!jobId) {
    return (
      <aside className="bgp-root bgp-root--idle" aria-label="Build overview">
        <div className="bgp-header">
          <Sparkles size={14} className="bgp-icon" aria-hidden />
          <span>What&apos;s happening</span>
        </div>
        {workspaceStage === 'plan' ? (
          <>
            <p className="bgp-headline">Plan is on deck</p>
            <p className="bgp-summary">
              Your proposal appears below as soon as it&apos;s ready — one thread for plan, build, and fixes.
            </p>
            <NextCue>Next: review the plan card, then approve to start the run.</NextCue>
          </>
        ) : (
          <>
            <p className="bgp-headline">Start from one calm place</p>
            <p className="bgp-summary">
              The composer below stays the same conversation for your goal, approvals, live steering, and recovery —
              nothing gets stranded in side threads.
            </p>
            <NextCue>Next: describe what you want, then press Enter to send.</NextCue>
          </>
        )}
      </aside>
    );
  }

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

  const isFailed = jobStatus === 'failed' || jobStatus === 'cancelled';
  const isActiveRun = jobStatus === 'running' || jobStatus === 'queued';
  const isBlocked = jobStatus === 'blocked';
  const isDone = jobStatus === 'completed';

  const renderBody = () => {
    if (jobHydrating) {
      return (
        <>
          <p className="bgp-headline">Pulling in your run</p>
          <p className="bgp-summary">Preview and proof refresh as soon as the connection catches up.</p>
          <NextCue>Next: keep this tab open — the next beat lands here automatically.</NextCue>
        </>
      );
    }

    if (taskProgress || g) {
      const headline = taskProgress?.summary || g?.headline;
      const summary = taskProgress?.detail || (g?.summary !== g?.headline ? g?.summary : null);
      const nextSteps = taskProgress?.next_steps || g?.next_steps || [];
      const stepKey = taskProgress?.current_step || g?.step_key;

      return (
        <>
          {stepKey ? (
            <p className="bgp-context-line" title={stepKey}>
              Now · {humanizeStepKey(stepKey)}
            </p>
          ) : null}
          <p className="bgp-headline">{headline}</p>
          {summary ? <p className="bgp-summary">{summary}</p> : null}
          
          {taskProgress?.percentage != null && (
            <div className="bgp-progress-bar-wrap">
              <div className="bgp-progress-bar-track">
                <div 
                  className="bgp-progress-bar-fill" 
                  style={{ width: `${taskProgress.percentage}%` }} 
                />
              </div>
              <span className="bgp-progress-bar-text">{Math.round(taskProgress.percentage)}%</span>
            </div>
          )}

          <EvidenceBlock text={evidenceText} repairMeta={latestFailure} />
          
          {actionChips && actionChips.length > 0 && (
            <div className="bgp-action-chips">
              {actionChips.map((chip, i) => (
                <div key={i} className="bgp-action-chip">
                  <Sparkles size={10} />
                  <span>{chip.label}</span>
                </div>
              ))}
            </div>
          )}

          {nextSteps.length > 0 ? (
            <div className="bgp-steps">
              <div className="bgp-steps-label">
                <ListOrdered size={12} /> What happens next
              </div>
              <ol className="bgp-ol">
                {nextSteps.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ol>
            </div>
          ) : (
            <NextCue>Next: adjust course anytime in the composer below — same run, same thread.</NextCue>
          )}
        </>
      );
    }

    if (isFailed) {
      if (failureSummary) {
        return (
          <>
            <p className="bgp-headline">What happened</p>
            <StepProgressPreservedLine steps={steps} jobStatus={jobStatus} />
            <p className="bgp-summary">{failureSummary}</p>
            <EvidenceBlock text={evidenceText} repairMeta={latestFailure} />
            <NextCue>
              Next: type the fix or direction below and press Enter — we continue on this run immediately after.
            </NextCue>
          </>
        );
      }
      return (
        <>
          <p className="bgp-headline">We&apos;re ready to continue</p>
          <StepProgressPreservedLine steps={steps} jobStatus={jobStatus} />
          <EvidenceBlock text={evidenceText} repairMeta={latestFailure} />
          <NextCue>Next: one short note below is enough — we pick up forward motion on the same run.</NextCue>
        </>
      );
    }

    if (isBlocked) {
      return (
        <>
          <p className="bgp-headline">Holding so we don&apos;t guess wrong</p>
          <StepProgressPreservedLine steps={steps} jobStatus={jobStatus} />
          <p className="bgp-summary">
            {failureSummary || 'We paused until you point us forward — that keeps the build safe and deliberate.'}
          </p>
          <EvidenceBlock text={evidenceText} repairMeta={latestFailure} />
          <NextCue>Next: send context below; we resume as soon as it lands.</NextCue>
        </>
      );
    }

    if (isActiveRun) {
      return (
        <>
          <p className="bgp-headline">We&apos;re building right now</p>
          <p className="bgp-summary">
            Output is streaming into your workspace; Preview wakes up the moment there is something to show.
          </p>
          <NextCue>Next: watch Preview, or steer below — both keep this run moving.</NextCue>
        </>
      );
    }

    if (workspaceStage === 'plan') {
      return (
        <>
          <p className="bgp-headline">Plan is on deck</p>
          <p className="bgp-summary">
            Crucible continues working right after your reply — approve below to start the run, or edit the goal first.
          </p>
          <NextCue>Next: approve the plan card below.</NextCue>
        </>
      );
    }

    if (isDone || workspaceStage === 'completed') {
      return (
        <>
          <p className="bgp-headline">This run wrapped</p>
          <p className="bgp-summary">Preview shows the live surface; Proof is the receipt. You can still iterate.</p>
          <NextCue>Next: open Preview or Proof on the right, or send a follow-up below.</NextCue>
        </>
      );
    }

    return (
      <>
        <p className="bgp-headline">You&apos;re in control</p>
        <p className="bgp-summary">We surface orchestrator updates here first — nothing else competes with this card.</p>
        <NextCue>Next: use the composer below whenever you want to steer.</NextCue>
      </>
    );
  };

  return (
    <aside className="bgp-root" aria-label="Build overview">
      <div className="bgp-header">
        <Sparkles size={14} className="bgp-icon" aria-hidden />
        <span>What&apos;s happening</span>
      </div>
      <MilestoneStrip batch={milestoneBatch} repairCount={repairQueueLen} />
      {activityChips.length > 0 ? (
        <div className="bgp-chips" aria-label="Recent actions">
          {activityChips.map((c) => (
            <span key={c.id} className={`bgp-chip bgp-chip--${c.kind}`}>
              {c.label}
            </span>
          ))}
        </div>
      ) : null}
      {renderBody()}
    </aside>
  );
}

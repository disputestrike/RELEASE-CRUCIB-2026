/**
 * presentBuildThread — map raw job / SSE payloads into safe, user-facing copy.
 * Used by buildThreadModel + narrateBuildEvent. Pure helpers only.
 */

const readPayload = (event) => {
  if (event?.payload && typeof event.payload === 'object') return event.payload;
  if (event?.payload_json) {
    try {
      const parsed = JSON.parse(event.payload_json);
      return parsed && typeof parsed === 'object' ? parsed : {};
    } catch {
      return {};
    }
  }
  return {};
};

const VERIFICATION_LABELS = {
  'verification.api_smoke': 'API health check',
  'verification.preview': 'Live preview check',
  'verification.compile': 'Compile check',
  'verification.security': 'Security check',
  'verification.behavior': 'Behavior check',
  'verification.rls': 'Database rules check',
  'verification.tenancy_smoke': 'Tenancy check',
  'verification.elite_builder': 'Quality bar check',
};

/** User-visible name for a step_key or node name — never raw snake_case alone. */
export function friendlyStepLabel(stepKey, name) {
  const key = String(stepKey || '').trim();
  if (key && VERIFICATION_LABELS[key]) return VERIFICATION_LABELS[key];
  const n = String(name || '').trim();
  if (n && VERIFICATION_LABELS[n]) return VERIFICATION_LABELS[n];
  if (key.startsWith('verification.')) {
    const tail = key.slice('verification.'.length).replace(/_/g, ' ');
    return `${tail.replace(/\b\w/g, (c) => c.toUpperCase())} check`;
  }
  if (key) return key.replace(/[._]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()).trim();
  if (n) return n.replace(/[._]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()).trim();
  return 'This step';
}

/** One-line title for issue / fix cards (no pipe-separated codes). */
export function issueCardTitle(ev) {
  const t = ev?.type || ev?.event_type || '';
  const p = readPayload(ev);
  if (t === 'job_failed') {
    const r = String(p.reason || p.failure_reason || p.summary || '').toLowerCase();
    if (r.includes('step') && r.includes('fail')) return 'Fix loop running - proof found an issue';
    return 'Fix loop running';
  }
  if (t === 'step_failed') {
    return `${friendlyStepLabel(p.step_key, p.name)} is being fixed`;
  }
  return 'Fixing the workspace';
}

/** Main paragraph shown in the thread (plain English, no npm exit codes). */
export function humanIssueSummary(ev) {
  const t = ev?.type || ev?.event_type || '';
  const p = readPayload(ev);
  if (t === 'job_failed') {
    return humanJobFailedSummary(p);
  }
  if (t !== 'step_failed') {
    return '';
  }
  const label = friendlyStepLabel(p.step_key, p.name);
  const fr = String(p.failure_reason || '').toLowerCase();
  if (fr.includes('browser_preview') || fr.includes('preview') || /preview/i.test(label)) {
    return 'The preview proof found an issue in the generated workspace. I am applying the next fix and continuing the run.';
  }
  if (fr.includes('api_smoke') || fr.includes('health') || /api health/i.test(label)) {
    return 'The API health check found a gap in the generated workspace. I am patching it and rerunning verification.';
  }
  if (fr.includes('compile') || /compile/i.test(label)) {
    return 'The compile check reported a problem. I am fixing the workspace and rerunning the check.';
  }
  return `Runtime proof flagged an issue during ${label}. I am fixing the workspace and keeping the run moving.`;
}

function humanJobFailedSummary(p) {
  const msg = String(p.message || p.summary || p.reason || p.failure_reason || '').toLowerCase();
  if (msg.includes('steps_failed') || msg.includes('step_failed')) {
    return 'A proof check did not pass. I am starting a fix pass and continuing the run.';
  }
  if (msg.includes('cancel')) {
    return 'This run was cancelled.';
  }
  const short = String(p.message || p.summary || p.reason || '').trim();
  if (short && short.length < 180 && !looksLikeRawLog(short)) {
    return short;
  }
  return 'The last build step failed. I am using the details below to patch the workspace and rerun proof.';
}

function looksLikeRawLog(s) {
  return (
    /npm err|exit code|stack trace|stderr|verification\.|browser_preview_failed|steps_failed/i.test(s) ||
    /\|\s*verification_/.test(s)
  );
}

/** Expandable technical block — raw strings allowed here only. */
export function technicalDetailLines(ev) {
  const p = readPayload(ev);
  const lines = [];
  const t = ev?.type || ev?.event_type || '';
  if (p.step_key) lines.push(`Step: ${p.step_key}`);
  if (p.failure_reason) lines.push(`Failure reason: ${p.failure_reason}`);
  const err = String(p.error_message || p.error || p.failure_detail || p.detail || '').trim();
  if (err) lines.push(err);
  if (Array.isArray(p.issues) && p.issues.length) {
    lines.push('Issues:');
    p.issues.slice(0, 12).forEach((x) => lines.push(`  - ${typeof x === 'string' ? x : JSON.stringify(x)}`));
  }
  if (Array.isArray(p.failed_checks) && p.failed_checks.length) {
    lines.push('Failed checks:');
    p.failed_checks.slice(0, 12).forEach((x) => lines.push(`  - ${typeof x === 'string' ? x : JSON.stringify(x)}`));
  }
  if (t === 'job_failed') {
    const r = String(p.reason || p.failure_reason || p.message || '').trim();
    if (r && !lines.includes(r)) lines.unshift(r);
  }
  return lines.filter(Boolean).join('\n').trim();
}

/** Short opening line when a job run starts (real job_started event). */
export function narrationJobStarted() {
  return "I'll preserve the goal, write the workspace files, run the preview, check proof, and keep fixing until the runtime path is safe.";
}

export function narrationRepairStarted() {
  return 'Running a fix pass. The generated workspace needs one more change, so I am patching it and keeping the run moving.';
}

export function narrationRepairCompleted() {
  return 'Fix applied. I am rerunning proof checks to confirm everything lines up.';
}

export function narrationVerifierPassed(phaseLabel) {
  if (phaseLabel) return `${phaseLabel} — checks passed. Moving forward.`;
  return 'Proof passed for this stage. Continuing the run.';
}

/** verifier_failed / export_gate style payloads (no outer type check). */
export function humanVerificationFailureSummary(p) {
  const stepKey = p?.step_key || p?.phase || p?.step || '';
  const label = friendlyStepLabel(stepKey, p?.name);
  const fr = String(p?.failure_reason || '').toLowerCase();
  const missingArr = p?.missing || p?.missing_routes;
  if (fr.includes('missing') && Array.isArray(missingArr) && missingArr.length) {
    return `Proof found missing pieces before handoff. I will align the workspace to the contract and continue.`;
  }
  const subject = label === 'This step' ? 'The proof check' : `The ${label}`;
  return `${subject} did not pass yet. I am applying fixes and continuing the run.`;
}

export const __test__ = { readPayload, friendlyStepLabel, looksLikeRawLog };

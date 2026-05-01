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
  return 'this step';
}

/** One-line title for issue / repair cards — clear and action-oriented. */
export function issueCardTitle(ev) {
  const t = ev?.type || ev?.event_type || '';
  const p = readPayload(ev);
  if (t === 'job_failed') {
    const r = String(p.reason || p.failure_reason || p.summary || '').toLowerCase();
    if (r.includes('step') && r.includes('fail')) return 'Running a fix';
    return 'Fixing an issue';
  }
  if (t === 'step_failed') {
    return `Fixing ${friendlyStepLabel(p.step_key, p.name)}`;
  }
  return 'Working on a fix';
}

/** Main paragraph shown in the thread — plain English, no stack traces. */
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
    return "The preview check found something off. I'm applying a targeted fix and continuing.";
  }
  if (fr.includes('api_smoke') || fr.includes('health') || /api health/i.test(label)) {
    return "The API health check found a gap. I'm patching it and rerunning the check.";
  }
  if (fr.includes('compile') || /compile/i.test(label)) {
    return "The compile check hit an error. I'm fixing it and running the check again.";
  }
  return `Verification flagged something during ${label}. I'm fixing it and keeping the build moving.`;
}

function humanJobFailedSummary(p) {
  const msg = String(p.message || p.summary || p.reason || p.failure_reason || '').toLowerCase();
  if (msg.includes('steps_failed') || msg.includes('step_failed')) {
    return "A verification step didn't pass. I'm starting a repair pass and continuing.";
  }
  if (msg.includes('cancel')) {
    return 'This run was cancelled.';
  }
  const short = String(p.message || p.summary || p.reason || '').trim();
  if (short && short.length < 180 && !looksLikeRawLog(short)) {
    return short;
  }
  return "The build hit a blocking issue. Check the technical details below, or send a follow-up to steer the next pass.";
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

/** Opening line when a job starts. */
export function narrationJobStarted() {
  return "Got it — I'm starting the build now. I'll lay down the foundation, wire up the screens and logic, run checks to make sure everything holds, and keep a live preview ready as it comes together.";
}

export function narrationRepairStarted() {
  return "I ran into an issue — applying a fix now and picking back up where I left off.";
}

export function narrationRepairCompleted() {
  return "Fixed it. Running the checks again to confirm everything's clean.";
}

export function narrationVerifierPassed(phaseLabel) {
  if (phaseLabel) return `${phaseLabel} — all clear. Moving on.`;
  return 'Checks passed. Continuing.';
}

/** verifier_failed / export_gate style payloads (no outer type check). */
export function humanVerificationFailureSummary(p) {
  const stepKey = p?.step_key || p?.phase || p?.step || '';
  const label = friendlyStepLabel(stepKey, p?.name);
  const fr = String(p?.failure_reason || '').toLowerCase();
  const missingArr = p?.missing || p?.missing_routes;
  if (fr.includes('missing') && Array.isArray(missingArr) && missingArr.length) {
    return `Verification found some missing pieces. I'm filling them in and continuing.`;
  }
  return `The ${label} didn't pass yet. I'm applying fixes and continuing the build.`;
}

export const __test__ = { readPayload, friendlyStepLabel, looksLikeRawLog };

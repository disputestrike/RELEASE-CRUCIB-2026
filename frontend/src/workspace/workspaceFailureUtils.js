export function failureTypeFromReason(reason, status) {
  const text = `${reason || ''} ${status || ''}`.toLowerCase();
  if (text.includes('syntax')) return 'syntax_error';
  if (text.includes('compile') || text.includes('build')) return 'compile_error';
  if (text.includes('contract') || text.includes('api')) return 'api_contract_error';
  if (text.includes('database') || text.includes('db') || text.includes('migration')) return 'db_error';
  if (text.includes('integration') || text.includes('credential') || text.includes('env')) return 'integration_error';
  if (text.includes('missing_file') || text.includes('missing file')) return 'missing_file';
  if (text.includes('verification') || text.includes('verifier') || text.includes('preview')) return 'verification_error';
  if (text.includes('runtime') || text.includes('exception') || text.includes('timeout')) return 'runtime_error';
  return 'unknown';
}

export function failureStepFromLatestFailure(latestFailure) {
  if (!latestFailure || typeof latestFailure !== 'object') return null;
  const issues = Array.isArray(latestFailure.issues)
    ? latestFailure.issues.map((x) => String(x)).filter(Boolean)
    : [];
  const stepKey = String(latestFailure.step_key || latestFailure.stage || 'job_failure').trim() || 'job_failure';
  const errorMessage =
    String(latestFailure.error_message || '').trim() ||
    issues.join('\n') ||
    String(latestFailure.failure_reason || latestFailure.status || 'Job failed before a step failure row was available.').trim();
  if (!errorMessage && !stepKey) return null;
  const failureReason = latestFailure.failure_reason || latestFailure.status || 'latest_failure_checkpoint';
  return {
    id: latestFailure.step_id || `latest_failure_${stepKey}`,
    step_key: stepKey,
    agent_name: latestFailure.agent_name || stepKey,
    status: 'failed',
    failure_type: latestFailure.failure_type || failureTypeFromReason(failureReason, latestFailure.status),
    error_message: errorMessage,
    retry_count: Number.isFinite(Number(latestFailure.retry_count)) ? Number(latestFailure.retry_count) : 0,
    output_files: Array.isArray(latestFailure.output_files) ? latestFailure.output_files : [],
    failure_reason: failureReason,
    stage: latestFailure.stage,
    can_retry: Boolean(latestFailure.step_id),
    diagnosis: {
      failure_class: latestFailure.failure_class || latestFailure.failure_reason || latestFailure.status || 'latest_failure',
      explanation: issues.length
        ? issues.slice(0, 5).join('\n')
        : String(latestFailure.brain_explanation || latestFailure.error_message || failureReason || '').trim(),
      specific_file: latestFailure.specific_file || null,
      specific_line: latestFailure.specific_line || null,
    },
    synthetic: true,
  };
}

export function describeFailureRecovery(step, { maxStepRetries = 8 } = {}) {
  const maxRetries = Number.isFinite(Number(maxStepRetries)) ? Number(maxStepRetries) : 8;
  const maxAttempts = maxRetries + 1;
  const retryCount = Number.isFinite(Number(step?.retry_count)) ? Number(step.retry_count) : 0;
  const hasRetryAuthority = step?.can_retry === false ? false : true;
  const attemptsExhausted = retryCount >= maxRetries;
  const canRetry = Boolean(step) && hasRetryAuthority && !attemptsExhausted;

  let disabledReason = '';
  if (!step) {
    disabledReason = 'No failed step is selected.';
  } else if (!hasRetryAuthority && step.synthetic) {
    disabledReason = 'This failure is a job checkpoint, not a retryable step. Add steering or resume the run from the workspace.';
  } else if (!hasRetryAuthority) {
    disabledReason = 'This failure cannot be retried automatically.';
  } else if (attemptsExhausted) {
    disabledReason = `All ${maxAttempts} attempts have been used. Add steering before resuming.`;
  }

  return {
    canRetry,
    retryCount,
    maxRetries,
    maxAttempts,
    currentAttempt: Math.min(retryCount + 1, maxAttempts),
    nextAttempt: Math.min(retryCount + 2, maxAttempts),
    disabledReason,
  };
}

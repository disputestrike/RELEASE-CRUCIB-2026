import {
  describeFailureRecovery,
  failureStepFromLatestFailure,
  failureTypeFromReason,
} from './workspaceFailureUtils';

describe('workspaceFailureUtils', () => {
  test('classifies common failure reasons for the existing FailureDrawer labels', () => {
    expect(failureTypeFromReason('preview_gate_failed')).toBe('verification_error');
    expect(failureTypeFromReason('build failed')).toBe('compile_error');
    expect(failureTypeFromReason('database migration failed')).toBe('db_error');
    expect(failureTypeFromReason('missing file evidence')).toBe('missing_file');
    expect(failureTypeFromReason('worker timeout')).toBe('runtime_error');
  });

  test('normalizes latestFailure checkpoint into a failed step display record', () => {
    const step = failureStepFromLatestFailure({
      step_id: 'stp_1',
      step_key: 'verification.preview',
      status: 'failed_verification',
      failure_reason: 'preview_gate_failed',
      issues: ['dist/ missing after build', 'index.html missing'],
      retry_count: 2,
      verifier_score: 15,
    });

    expect(step).toEqual(
      expect.objectContaining({
        id: 'stp_1',
        step_key: 'verification.preview',
        agent_name: 'verification.preview',
        status: 'failed',
        failure_type: 'verification_error',
        error_message: 'dist/ missing after build\nindex.html missing',
        retry_count: 2,
        can_retry: true,
        synthetic: true,
      }),
    );
    expect(step.diagnosis.explanation).toContain('dist/ missing');
  });

  test('uses error message when checkpoint has no issue list', () => {
    const step = failureStepFromLatestFailure({
      step_key: 'deployment',
      status: 'step_exception',
      exc_type: 'RuntimeError',
      error_message: 'Railway deployment timed out',
    });

    expect(step.failure_type).toBe('runtime_error');
    expect(step.error_message).toBe('Railway deployment timed out');
    expect(step.diagnosis.failure_class).toBe('step_exception');
    expect(step.can_retry).toBe(false);
  });

  test('returns null when no checkpoint exists', () => {
    expect(failureStepFromLatestFailure(null)).toBeNull();
    expect(failureStepFromLatestFailure(undefined)).toBeNull();
  });

  test('describes synthetic checkpoint failures as non-retryable job checkpoints', () => {
    const step = failureStepFromLatestFailure({
      step_key: 'deployment',
      status: 'step_exception',
      error_message: 'Railway deployment timed out',
    });

    const recovery = describeFailureRecovery(step, { maxStepRetries: 8 });

    expect(recovery.canRetry).toBe(false);
    expect(recovery.disabledReason).toContain('job checkpoint');
    expect(recovery.currentAttempt).toBe(1);
  });

  test('describes exhausted retry budget honestly', () => {
    const recovery = describeFailureRecovery(
      { step_key: 'frontend', retry_count: 8, can_retry: true },
      { maxStepRetries: 8 },
    );

    expect(recovery.canRetry).toBe(false);
    expect(recovery.disabledReason).toBe('All 9 attempts have been used. Add steering before resuming.');
    expect(recovery.currentAttempt).toBe(9);
  });
});

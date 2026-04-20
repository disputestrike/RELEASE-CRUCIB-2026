# CrucibAI Master Execution Accountability

This file is the operating control sheet for implementation quality.

## Mandatory Delivery Fields Per Task

Every task update must include:

1. Files changed
2. What was removed
3. What was migrated
4. Why the change was needed
5. Tests added or updated
6. Acceptance criteria satisfied

## Compliance Gates

A task is not complete until all required gates pass.

- Gate A: Build Compliance
- Gate B: Architecture Compliance
- Gate C: Runtime Compliance
- Gate D: Product Compliance
- Gate E: Security Compliance
- Gate F: Evidence Compliance

## Gate Definitions

### Gate A: Build Compliance

- Code compiles/lints as required by project standards.
- No new build errors introduced.

### Gate B: Architecture Compliance

- Change aligns to single-source-of-truth architecture.
- No parallel canonical surfaces created.

### Gate C: Runtime Compliance

- Runtime changes are logged and inspectable.
- Permission checks are preserved for risky actions.

### Gate D: Product Compliance

- Feature appears in intended UX flow.
- No regression of canonical workspace/dashboard behavior.

### Gate E: Security Compliance

- CORS/auth/policy changes follow production-safe defaults.
- No privilege bypass introduced.

### Gate F: Evidence Compliance

- Objective proof exists: logs, endpoint output, test output, or diff evidence.
- Crosswalk row updated with status.

## Corrective Action Protocol

When a requirement fails:

1. Open corrective action row in the crosswalk.
2. Add root cause and containment.
3. Assign owner and due date.
4. Add closure evidence.

## Current Program Stage

- Stage: Phase 1 hardening in progress.
- Focus: route loading reliability, CORS correctness, canonical workspace controller, and compliance tracking scaffold.

# Compliance QA and Corrective Actions Playbook

Date: 2026-04-16
Applies to: Full Dominance Track

## 1) Compliance QA Operating Model

We run QA as a concurrent control lane from day one.

Control layers:
- Design compliance: architecture and requirement conformance
- Build compliance: PR-level checks and test evidence
- Runtime compliance: stream correctness, mode gating, and deployment safety

Mandatory checks on every phase gate:
- Requirement crosswalk updated
- Test evidence linked
- Defect severity review complete
- Corrective actions recorded for all unresolved high-severity findings

## 2) Phase Gate QA Checklist

Phase 0 gate:
- Requirements are atomic and testable
- Acceptance criteria exist per requirement

Phase 1 gate:
- No competing runtime layout systems
- Canonical route behavior validated
- 3-pane structure stable

Phase 2 gate:
- Backend state remains authoritative after refresh/reconnect
- Stream event ordering and dedup behavior validated

Phase 3 gate:
- End-to-end center flow from prompt to completion verified

Phase 4 gate:
- Right pane modes pass functional and resilience tests

Phase 5 gate:
- Simple/Dev mode policy controls verified
- No structural UI divergence by mode

Phase 6 gate:
- Differentiated feature scenarios pass demonstration tests

Phase 7 gate:
- Security and permission controls validated
- Cost and reliability controls validated

Phase 8 gate:
- CI regression suite protects critical paths

Phase 9 gate:
- Legacy path retirement verified

Phase 10 gate:
- Rollout safety checks and KPI instrumentation validated

## 3) Corrective Action Policy

When a defect or compliance miss is found:
- Log issue in corrective action register
- Assign severity and owner
- Apply containment if needed
- Perform root cause analysis
- Ship corrective fix with test evidence
- Add preventive measure to avoid recurrence

Severity policy:
- P0: immediate containment and emergency fix
- P1: expedited fix with blocked release if unresolved
- P2: scheduled fix in active cycle
- P3: backlog fix and trend tracking

## 4) Quality Evidence Standards

Accepted evidence types:
- Automated test reports
- API contract checks
- Stream replay and reconnect test outputs
- UI conformance screenshots for canonical flows
- Permission and audit event logs for risk actions

Evidence quality rules:
- Every gate must include reproducible artifacts
- No gate can pass with undocumented assumptions
- Known risks must include mitigation and target closure

## 5) Escalation and Stop-Ship Rules

Stop-ship triggers:
- P0 unresolved
- P1 unresolved on critical path
- Stream correctness regression on active jobs
- Mode gating leak exposing restricted controls

Escalation sequence:
- Engineer owner
- Phase lead
- Program lead
- Release authority

## 6) Continuous Improvement Loop

Weekly review:
- Defect trends by severity and phase
- Escaped defect analysis
- Corrective action aging review
- Preventive control updates

Monthly hardening:
- Refine checklists based on incidents
- Add regression tests for repeat patterns
- Retire obsolete controls and simplify process

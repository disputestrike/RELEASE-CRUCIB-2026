# Elite Execution Directive

This job must make every late-stage gate deterministic and evidence-backed.

## Current goal

```
Build a job board with listing browsing, applicant notes, employer dashboard, login, and publish readiness.
```

## Required proof posture

- Do not mark deploy ready unless preview, proof, and deploy-readiness checks pass.
- Preserve explicit failure reasons for preview, elite, deploy build, and deploy publish.
- Treat mocked or readiness-only output as labeled proof, not live deployment proof.

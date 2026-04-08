# Elite Execution Directive

This job must make every late-stage gate deterministic and evidence-backed.

## Current goal

```
Build a fleet management tool with vehicle dashboard, route notes, operator login, team page, and deploy readiness.
```

## Required proof posture

- Do not mark deploy ready unless preview, proof, and deploy-readiness checks pass.
- Preserve explicit failure reasons for preview, elite, deploy build, and deploy publish.
- Treat mocked or readiness-only output as labeled proof, not live deployment proof.

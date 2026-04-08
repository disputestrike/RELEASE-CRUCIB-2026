# Phase 2 Remaining Security Debt

- Terminal execution is scoped and gated, but it is still process-local shell execution, not a per-user container sandbox.
- Websocket project progress is source-audited here; add a true websocket runtime test when the test harness supports websocket sessions against the async app fixture.
- Optional public catalog/read-only routes should stay in the route audit so future changes cannot quietly turn them into action routes.

# Phase 2 Optional-Auth Route Audit

Passed: YES
Optional route count: 13

| File | Line | Method | Path | Classification | Reason |
|---|---:|---|---|---|---|
| backend/server.py | 6687 | GET | `/examples` | safe as optional | safe as optional: public example gallery |
| backend/server.py | 6694 | GET | `/examples/{name}` | safe as optional | safe as optional: public example detail |
| backend/server.py | 6765 | GET | `/patterns` | safe as optional | safe as optional: public reusable pattern catalog |
| backend/server.py | 7429 | GET | `/prompts/templates` | safe as optional | safe as optional: public prompt templates |
| backend/server.py | 7433 | GET | `/prompts/recent` | safe as optional | safe as optional: anonymous returns empty; authenticated reads own user_id |
| backend/server.py | 7611 | GET | `/workspace/env` | safe as optional | safe as optional: compatibility endpoint returns empty env only |
| backend/server.py | 7660 | GET | `/templates` | safe as optional | safe as optional: public template gallery |
| backend/server.py | 7788 | GET | `/agents/activity` | safe as optional | safe as optional: anonymous returns empty; authenticated reads own user_id |
| backend/server.py | 8243 | POST | `/orchestrator/estimate` | safe as optional | safe as optional: advisory estimate, no persisted tenant data |
| backend/server.py | 8563 | GET | `/orchestrator/build-jobs` | safe as optional | safe as optional: anonymous returns empty; authenticated lists own jobs |
| backend/server.py | 8761 | GET | `/trust/platform-capabilities` | safe as optional | safe as optional: public capability/status metadata |
| backend/server.py | 9106 | POST | `/vibecoding/detect-frameworks` | safe as optional | must require project ownership when project_id is supplied; code enforces auth and user_id lookup |
| backend/server.py | 9459 | GET | `/skills/marketplace` | safe as optional | safe as optional: public marketplace listing plus own user skills when authenticated |

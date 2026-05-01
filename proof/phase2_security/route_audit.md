# Phase 2 Optional-Auth Route Audit

Passed: YES
Optional route count: 8

| File | Line | Method | Path | Classification | Reason |
|---|---:|---|---|---|---|
| backend/routes/misc.py | 687 | GET | `/examples` | safe as optional | safe as optional: public example gallery |
| backend/routes/misc.py | 696 | GET | `/examples/{name}` | safe as optional | safe as optional: public example detail |
| backend/routes/misc.py | 800 | GET | `/patterns` | safe as optional | safe as optional: public reusable pattern catalog |
| backend/routes/misc.py | 966 | GET | `/prompts/templates` | safe as optional | safe as optional: public prompt templates |
| backend/routes/misc.py | 971 | GET | `/prompts/recent` | safe as optional | safe as optional: anonymous returns empty; authenticated reads own user_id |
| backend/routes/misc.py | 1288 | GET | `/workspace/env` | safe as optional | safe as optional: compatibility endpoint returns empty env only |
| backend/routes/misc.py | 1386 | GET | `/templates` | safe as optional | safe as optional: public template gallery |
| backend/routes/misc.py | 1392 | GET | `/templates/{template_id}/remix-plan` | safe as optional | safe as optional: public remix metadata only; authenticated remix creation uses strict auth |

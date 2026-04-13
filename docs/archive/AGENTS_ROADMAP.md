# CrucibAI Agents Roadmap: 100 Agents Live

**Goal:** Beat Manus and match Kimi's 100-agent scale for app-building. Kimi uses 100 sub-agents for research and multi-angle analysis; CrucibAI now has **100 specialized app-building agents** for full-stack, design-to-code, and DevOps. **Status:** 100 agents implemented.

---

## Current: 100 Agents (Implemented)

### Planning (4)
- Planner
- Requirements Clarifier
- Content Agent
- Legal Compliance Agent

### Stack & Design (8)
- Stack Selector
- Design Agent *(image placement spec)*
- Brand Agent
- SEO Agent
- Auth Setup Agent
- Payment Setup Agent
- Email Agent
- API Integration

### Execution (12)
- Frontend Generation
- Backend Generation
- Database Agent
- Image Generation *(uses Design Agent)*
- Video Generation
- Layout Agent *(injects images)*
- Test Generation
- Scraping Agent
- Automation Agent
- Webhook Agent
- Validation Agent

### Validation & Quality (5)
- Security Checker
- Test Executor
- UX Auditor
- Performance Analyzer
- Accessibility Agent

### Deployment & Export (7)
- Deployment Agent
- Error Recovery
- Memory Agent
- Documentation Agent
- Monitoring Agent
- DevOps Agent
- PDF Export, Excel Export, Markdown Export

### Phase 2–4 (63 more)
- GraphQL, WebSocket, i18n, Caching, Rate Limit, Search, Analytics, API Docs, Mobile Responsive, Migration, Backup, Notification, Design Iteration, Code Review
- Staging, A/B Test, Feature Flag, Error Boundary, Logging, Metrics, Audit Trail, Session, OAuth Provider, 2FA, Stripe Subscription, Invoice, CDN, SSR, Bundle Analyzer, Lighthouse, Schema Validation, Mock API, E2E, Load Test, Dependency Audit, License, Terms, Privacy Policy, Cookie Consent
- Multi-tenant, RBAC, SSO, Audit Export, Data Residency, HIPAA, SOC2, Penetration Test, Incident Response, SLA, Cost Optimizer, Accessibility WCAG, RTL, Dark Mode, Keyboard Nav, Screen Reader, Component Library, Design System, Animation, Chart, Table, Form Builder, Workflow, Queue

---

## Phase 2: 50 Agents (Next 14) — implemented

| Agent | Role | Depends On |
|-------|------|------------|
| **GraphQL Agent** | GraphQL schema + resolvers | Backend Generation |
| **WebSocket Agent** | Real-time subscriptions | Backend Generation |
| **i18n Agent** | Localization, locales, translation keys | Frontend Generation |
| **Caching Agent** | Redis/edge caching strategy | Stack Selector |
| **Rate Limit Agent** | API rate limiting, quotas | Backend Generation |
| **Search Agent** | Full-text search (Algolia/Meilisearch) | Stack Selector |
| **Analytics Agent** | GA4, Mixpanel, event schema | Deployment Agent |
| **API Documentation Agent** | OpenAPI/Swagger from routes | Backend Generation |
| **Mobile Responsive Agent** | Breakpoints, touch, PWA hints | Frontend Generation |
| **Migration Agent** | DB migration scripts | Database Agent |
| **Backup Agent** | Backup strategy, restore steps | Deployment Agent |
| **Notification Agent** | Push, in-app, email notifications | Email Agent |
| **Design Iteration Agent** | Feedback → spec → rebuild flow | Planner, Design Agent |
| **Code Review Agent** | Security, style, best-practice review | Frontend, Backend |

---

## Phase 3: 75 Agents (+25)

| Agent | Role |
|-------|------|
| **Staging Agent** | Staging env, preview URLs |
| **A/B Test Agent** | Experiment setup, variant routing |
| **Feature Flag Agent** | LaunchDarkly/Flagsmith wiring |
| **Error Boundary Agent** | React error boundaries, fallback UI |
| **Logging Agent** | Structured logs, log levels |
| **Metrics Agent** | Prometheus/Datadog metrics |
| **Audit Trail Agent** | User action logging, audit log |
| **Session Agent** | Session storage, expiry, refresh |
| **OAuth Provider Agent** | Google/GitHub OAuth wiring |
| **2FA Agent** | TOTP, backup codes |
| **Stripe Subscription Agent** | Plans, metering, downgrade |
| **Invoice Agent** | Invoice generation, PDF |
| **CDN Agent** | Static assets, cache headers |
| **SSR Agent** | Next.js SSR/SSG hints |
| **Bundle Analyzer Agent** | Code splitting, chunk hints |
| **Lighthouse Agent** | Performance, a11y, SEO scores |
| **Schema Validation Agent** | Request/response validation |
| **Mock API Agent** | MSW, Mirage, mock server |
| **E2E Agent** | Playwright/Cypress scaffolding |
| **Load Test Agent** | k6, Artillery scripts |
| **Dependency Audit Agent** | npm audit, Snyk hints |
| **License Agent** | OSS license compliance |
| **Terms Agent** | Terms of service draft |
| **Privacy Policy Agent** | Privacy policy draft |
| **Cookie Consent Agent** | Cookie banner, preferences |

---

## Phase 4: 100 Agents (+25)

| Agent | Role |
|-------|------|
| **Multi-tenant Agent** | Tenant isolation, schema |
| **RBAC Agent** | Roles, permissions matrix |
| **SSO Agent** | SAML, enterprise SSO |
| **Audit Export Agent** | Export audit logs |
| **Data Residency Agent** | Region, GDPR data location |
| **HIPAA Agent** | Healthcare compliance hints |
| **SOC2 Agent** | SOC2 control hints |
| **Penetration Test Agent** | Pentest checklist |
| **Incident Response Agent** | Runbook, escalation |
| **SLA Agent** | Uptime, latency targets |
| **Cost Optimizer Agent** | Cloud cost hints |
| **Green Agent** | Carbon footprint, efficiency |
| **Accessibility WCAG Agent** | WCAG 2.1 AA checklist |
| **RTL Agent** | Right-to-left layout |
| **Dark Mode Agent** | Theme toggle, contrast |
| **Keyboard Nav Agent** | Full keyboard navigation |
| **Screen Reader Agent** | SR-specific hints |
| **Component Library Agent** | Shadcn/Radix usage |
| **Design System Agent** | Tokens, spacing, typography |
| **Animation Agent** | Framer Motion, transitions |
| **Chart Agent** | Recharts, D3 usage |
| **Table Agent** | Data tables, sorting, pagination |
| **Form Builder Agent** | Dynamic form generation |
| **Workflow Agent** | State machine, workflows |
| **Queue Agent** | Job queues, Bull/Celery |

---

## Competitive Positioning

| Platform | Agents / Tools | Focus |
|----------|----------------|-------|
| **Kimi** | 100 sub-agents | Research, multi-angle analysis, discovery at scale |
| **Manus** | ~29 tools | Browser, file, PPTX, PDF, email, Slack; CodeAct |
| **CrucibAI** | **100** | **App creation only**: plan-first, design-to-code, full-stack |

**Differentiator:** CrucibAI agents are purpose-built for shipping software. Kimi’s 100 agents self-organize for research; ours form a fixed DAG optimized for app builds. We match Kimi at 100 and beat Manus on breadth (100 vs ~29) and depth (Design, SEO, Layout, Auth, Payment, Legal, DevOps, GraphQL, E2E, RBAC, and 60+ more).

---

## Implementation Notes

- All new agents must be added to: `agent_dag.py`, `agent_resilience.py`, `server.py` (routes + `AGENT_DEFINITIONS`)
- Orchestration `PARALLEL_PHASES` in `orchestration.py` is for legacy flow; `run_orchestration_v2` uses `agent_dag.get_execution_phases(AGENT_DAG)`
- Each agent needs: system prompt, `depends_on`, `AGENT_CRITICALITY`, `AGENT_TIMEOUTS`, fallback in `generate_fallback`

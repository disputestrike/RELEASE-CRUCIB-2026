# 120 Agents × Real Behavior Matrix

Every agent in the DAG has exactly one real behavior: **state write**, **artifact write** (file tool), or **tool run** (run/api/browser/db). No prompt-only agents.

| Agent | Real behavior | Type |
|-------|----------------|------|
| Planner | `state.plan` | state |
| Requirements Clarifier | `state.requirements` | state |
| Stack Selector | `state.stack` | state |
| Frontend Generation | `src/App.jsx` | artifact |
| Backend Generation | `server.py` | artifact |
| Database Agent | `schema.sql` | artifact |
| API Integration | `api/client.js` | artifact |
| Test Generation | `tests/test_basic.py` | artifact |
| Image Generation | `state.images` | state |
| Video Generation | `state.videos` | state |
| Security Checker | `state.security_report` (run bandit) | tool |
| Test Executor | `state.test_results` (pytest/npm test) | tool |
| UX Auditor | `state.ux_report` (ARIA scan) | tool |
| Performance Analyzer | `state.performance_report` (line count) | tool |
| Deployment Agent | `state.deploy_result` | state |
| Error Recovery | `docs/runbook.md` | artifact |
| Memory Agent | `state.memory_summary` | state |
| PDF Export | `docs/summary.pdf` | artifact |
| Excel Export | `docs/tracking.csv` | artifact |
| Markdown Export | `docs/summary.md` | artifact |
| Scraping Agent | `state.scrape_urls` | state |
| Automation Agent | `cron/tasks.json` | artifact |
| Design Agent | `state.design_spec` | state |
| Layout Agent | `src/App.jsx` | artifact |
| SEO Agent | `public/robots.txt` | artifact |
| Content Agent | `content/copy.json` | artifact |
| Brand Agent | `state.brand_spec` | state |
| Documentation Agent | `README.md` | artifact |
| Validation Agent | `validation/schema.json` | artifact |
| Auth Setup Agent | `auth/config.json` | artifact |
| Payment Setup Agent | `payments/config.json` | artifact |
| Monitoring Agent | `monitoring/sentry.yaml` | artifact |
| Accessibility Agent | `docs/a11y.md` | artifact |
| DevOps Agent | `.github/workflows/ci.yml` | artifact |
| Webhook Agent | `webhooks/handler.js` | artifact |
| Email Agent | `email/config.json` | artifact |
| Legal Compliance Agent | `docs/compliance.md` | artifact |
| GraphQL Agent | `schema.graphql` | artifact |
| WebSocket Agent | `ws/handler.js` | artifact |
| i18n Agent | `locales/en.json` | artifact |
| Caching Agent | `cache/redis.json` | artifact |
| Rate Limit Agent | `middleware/rate_limit.js` | artifact |
| Search Agent | `search/config.json` | artifact |
| Analytics Agent | `analytics/events.json` | artifact |
| API Documentation Agent | `openapi.yaml` | artifact |
| Mobile Responsive Agent | `styles/responsive.json` | artifact |
| Migration Agent | `migrations/001_init.sql` | artifact |
| Backup Agent | `scripts/backup.sh` | artifact |
| Notification Agent | `notifications/config.json` | artifact |
| Design Iteration Agent | `state.design_iterations` | state |
| Code Review Agent | `state.code_review_report` (bandit) | tool |
| Staging Agent | `staging.env` | artifact |
| A/B Test Agent | `experiments/ab.json` | artifact |
| Feature Flag Agent | `flags.json` | artifact |
| Error Boundary Agent | `components/ErrorBoundary.jsx` | artifact |
| Logging Agent | `logging/config.json` | artifact |
| Metrics Agent | `metrics/prometheus.yaml` | artifact |
| Audit Trail Agent | `audit/middleware.js` | artifact |
| Session Agent | `session/config.json` | artifact |
| OAuth Provider Agent | `auth/oauth.json` | artifact |
| 2FA Agent | `auth/2fa.json` | artifact |
| Stripe Subscription Agent | `payments/stripe.json` | artifact |
| Invoice Agent | `templates/invoice.html` | artifact |
| CDN Agent | `cdn/config.json` | artifact |
| SSR Agent | `next.config.js` | artifact |
| Bundle Analyzer Agent | `state.bundle_report` (run) | tool |
| Lighthouse Agent | `state.lighthouse_report` (run) | tool |
| Schema Validation Agent | `schemas/api.json` | artifact |
| Mock API Agent | `mocks/handlers.js` | artifact |
| E2E Agent | `e2e/spec.js` | artifact |
| Load Test Agent | `load/k6.js` | artifact |
| Dependency Audit Agent | `state.dependency_audit` (npm audit) | tool |
| License Agent | `LICENSE` | artifact |
| Terms Agent | `docs/terms.md` | artifact |
| Privacy Policy Agent | `docs/privacy.md` | artifact |
| Cookie Consent Agent | `consent/cookies.json` | artifact |
| Multi-tenant Agent | `tenant/schema.sql` | artifact |
| RBAC Agent | `auth/roles.json` | artifact |
| SSO Agent | `auth/sso.json` | artifact |
| Audit Export Agent | `scripts/export_audit.sh` | artifact |
| Data Residency Agent | `compliance/residency.json` | artifact |
| HIPAA Agent | `docs/hipaa.md` | artifact |
| SOC2 Agent | `docs/soc2.md` | artifact |
| Penetration Test Agent | `security/pentest.md` | artifact |
| Incident Response Agent | `docs/incident_runbook.md` | artifact |
| SLA Agent | `docs/sla.md` | artifact |
| Cost Optimizer Agent | `docs/cost.md` | artifact |
| Accessibility WCAG Agent | `docs/wcag.md` | artifact |
| RTL Agent | `styles/rtl.css` | artifact |
| Dark Mode Agent | `themes/dark.json` | artifact |
| Keyboard Nav Agent | `a11y/keyboard.md` | artifact |
| Screen Reader Agent | `a11y/screenreader.md` | artifact |
| Component Library Agent | `components/manifest.json` | artifact |
| Design System Agent | `design/tokens.json` | artifact |
| Animation Agent | `animations/config.json` | artifact |
| Chart Agent | `charts/config.json` | artifact |
| Table Agent | `components/table.json` | artifact |
| Form Builder Agent | `forms/schema.json` | artifact |
| Workflow Agent | `workflows/main.json` | artifact |
| Queue Agent | `queue/config.json` | artifact |
| Vibe Analyzer Agent | `state.vibe_spec` | state |
| Voice Context Agent | `state.voice_requirements` | state |
| Video Tutorial Agent | `docs/tutorial_script.md` | artifact |
| Aesthetic Reasoner Agent | `state.aesthetic_report` | state |
| Collaborative Memory Agent | `state.team_preferences` | state |
| Real-time Feedback Agent | `state.feedback_log` | state |
| Mood Detection Agent | `state.mood` | state |
| Accessibility Vibe Agent | `state.accessibility_vibe` | state |
| Performance Vibe Agent | `state.performance_vibe` | state |
| Creativity Catalyst Agent | `state.creative_ideas` | state |
| IDE Integration Coordinator Agent | `.vscode/settings.json` | artifact |
| Multi-language Code Agent | `api_go/main.go` | artifact |
| Team Collaboration Agent | `docs/collab.md` | artifact |
| User Onboarding Agent | `onboarding/flow.json` | artifact |
| Customization Engine Agent | `customization/config.json` | artifact |
| Browser Tool Agent | real Playwright; `state.tool_log` | tool |
| File Tool Agent | real FileAgent; `state.tool_log` | tool |
| API Tool Agent | real HTTP; `state.tool_log` | tool |
| Database Tool Agent | real SQLite; `state.tool_log` | tool |
| Deployment Tool Agent | real deploy; `state.tool_log` | tool |

**Verification:** Run `python backend/verify_120_agents.py` to ensure every DAG agent has a mapping.

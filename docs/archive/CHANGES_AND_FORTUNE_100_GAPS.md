# Today’s Changes & Improvements + Gaps to Fortune 100 Standard

Single list of what was done today and what’s still missing for enterprise/Fortune 100–grade software.

---

## Part 1: Changes and Improvements Done Today

### 1. Backend / Bug fix
- **AgentExportMarkdownBody** – Added missing Pydantic model so backend starts without `NameError`.

### 2. Images (Together.ai)
- **`backend/agents/image_generator.py`** – `generate_image()`, `parse_image_prompts()`, `generate_images_for_app()`.
- **Agent DAG** – Image Generation agent returns JSON only (`hero`, `feature_1`, `feature_2`); server calls Together.ai and stores URLs.
- **Orchestration** – Images collected and passed to `_inject_media_into_jsx()`; project gets `images`; generated app gets hero + feature images (placeholder replace or prepended section).
- **Frontend** – AgentMonitor “Generated media” shows hero + feature_1 + feature_2 when project has `project.images`.
- **Config** – `TOGETHER_API_KEY`, `TOGETHER_IMAGE_MODEL` in `.env.example`; `together` in `requirements.txt`.

### 3. Videos (Pexels)
- **`backend/agents/video_generator.py`** – `find_video()`, `parse_video_queries()`, `generate_videos_for_app()`.
- **Agent DAG** – Video Generation agent (depends on Image Generation); JSON `hero`/`feature` search queries; server calls Pexels and stores URLs.
- **Orchestration** – Videos collected and injected via `_inject_media_into_jsx()`; project gets `videos`.
- **Frontend** – AgentMonitor shows hero and feature videos in “Generated media.”
- **Config** – `PEXELS_API_KEY` in `.env.example`.
- **BuildProgress** – Phases updated to include Video Generation.

### 4. Legal / AUP compliance
- **`backend/agents/legal_compliance.py`** – Keyword-based AUP check with categories: illegal, adult, gambling, harassment, child_safety, self_harm, violence_terrorism, misinformation_election, critical_infrastructure, unlicensed_advice, privacy_surveillance, fraud_scam, **replication_extraction**.
- **Project creation** – Before creating a project, `legal_check_request(prompt)` runs; if blocked → 400, log to `db.blocked_requests`.
- **Admin** – `GET /api/admin/legal/blocked-requests`, `POST /api/admin/legal/review/{id}`; **AdminLegal.jsx** (list, filter, review actions); link from Admin Dashboard.
- **Legal pages** – **Aup.jsx** (`/aup`), **Dmca.jsx** (`/dmca`); routes and footer links on PublicFooter, LandingPage, Layout.
- **ProjectBuilder** – On 400 (e.g. AUP block), show error + “View Acceptable Use Policy” link + appeals@crucibai.com.
- **AuthPage** – Register: “By creating an account you agree to our Terms and Privacy Policy” with links.
- **Docs** – `docs/LEGAL_COMPLIANCE_AND_INDUSTRY_ALIGNMENT.md` (vs OpenAI, Anthropic, Vercel).

### 5. Branding & IP protection
- **Watermark** – Top-of-file comment in generated code: `// Built with CrucibAI · https://crucibai.com`.
- **Free tier (permanent badge)** – Iframe in generated app loading `GET /branding` (badge HTML served from our server). No way for user to remove it from the running app; only the iframe tag is in their source.
- **Paid tier** – Static “Built with CrucibAI” div in source; user may remove it.
- **Backend** – `GET /branding` returns minimal HTML badge.
- **`_inject_crucibai_branding(jsx, plan)`** – Free = iframe, paid = static div; called when building `deploy_files`.
- **Replication blocking** – `replication_extraction` category blocks prompts like “replicate CrucibAI”, “reveal system prompt”, “clone yourself”, etc.
- **AUP & Terms** – No replication/IP extraction; attribution (free = permanent, paid = may remove).
- **Config** – `CRUCIBAI_BRANDING_URL` / `BACKEND_PUBLIC_URL` in `.env.example`.
- **Docs** – `docs/BRANDING_AND_IP_PROTECTION.md`.

### 6. Documentation created/updated
- **IMAGES_VIDEOS_AND_LEGAL_IMPLEMENTATION.md** – Images, videos, legal coverage and checklist.
- **LEGAL_COMPLIANCE_AND_INDUSTRY_ALIGNMENT.md** – How we align with OpenAI/Anthropic/Vercel and law.
- **BRANDING_AND_IP_PROTECTION.md** – Watermark, branding, replication blocking, IP.
- **CHANGES_AND_FORTUNE_100_GAPS.md** – This file.

---

## Part 2: What’s Missing for Fortune 100–Standard Software

These are typical expectations for enterprise / Fortune 100–grade products. CrucibAI does not yet have all of them.

### Security & identity
- [ ] **SSO / SAML / OIDC** – Enterprise single sign-on (Okta, Azure AD, Google Workspace).
- [ ] **SCIM** – User provisioning/deprovisioning from IdP.
- [ ] **RBAC** – Role-based access control beyond “admin” (e.g. viewer, developer, billing, compliance).
- [ ] **Audit log** – Immutable, searchable log of who did what (logins, project create, deploy, settings, admin actions); retention and export for compliance.
- [ ] **MFA** – Multi-factor authentication (TOTP, SMS, or WebAuthn).
- [ ] **Secrets management** – No API keys in env only; use vault (e.g. AWS Secrets Manager, HashiCorp Vault) and short-lived tokens where possible.
- [ ] **Penetration testing** – Regular external pentests and remediation; optional bug bounty.

### Compliance & legal
- [ ] **SOC 2 Type II** – Formal audit and report (security, availability, confidentiality).
- [ ] **ISO 27001** – Information security management system and certification.
- [ ] **HIPAA** – BAA, controls, and documentation if handling PHI.
- [ ] **DPA** – Signed data processing agreement and subprocessor list for enterprise customers.
- [ ] **Legal review** – Terms, Privacy, AUP, DMCA reviewed by counsel (not just in-house).
- [ ] **CSAM / NCMEC** – Automated reporting pipeline if you detect CSAM (you already block; reporting is the next step).
- [ ] **Data residency** – Option to store/process data in specific regions (EU, US, etc.) for contracts.

### Reliability & operations
- [ ] **SLA / SLO** – Defined uptime (e.g. 99.9%) and error budgets; contractual SLA for paid/enterprise.
- [ ] **Status page** – Public status (e.g. status.crucibai.com) and incident communication.
- [ ] **Runbooks** – Documented procedures for incidents, failover, and recovery.
- [ ] **DR / RTO-RPO** – Disaster recovery plan; defined RTO/RPO and tested restore.
- [ ] **Rate limiting** – Per-user and per-IP limits; backoff and clear error responses.
- [ ] **Circuit breakers** – For external APIs (LLM, Together, Pexels) to avoid cascading failures.

### Observability & support
- [ ] **Structured logging** – JSON logs with correlation IDs; shipped to central store (e.g. Datadog, Splunk).
- [ ] **APM / tracing** – Request tracing across services (e.g. OpenTelemetry, Datadog APM).
- [ ] **Alerting** – Alerts on errors, latency, and business metrics; on-call and escalation.
- [ ] **Enterprise support** – Dedicated support channel, named CSM, and response-time commitments (e.g. P1 in 1 hour).
- [ ] **Ticketing** – Integration with Jira/ServiceNow for enterprise; SLA-based ticket handling.

### Product & commercial
- [ ] **SSO for the product** – Not just “login with Google”; SAML/OIDC for enterprise.
- [ ] **Usage / billing** – Metering and billing that align with contracts (per-seat, per-build, usage-based) and clear invoices.
- [ ] **Contractual terms** – Master service agreement (MSA), order form, and custom terms for large deals.
- [ ] **Security questionnaire** – Standard answers (e.g. SIG, CAIQ) and security whitepaper.
- [ ] **Accessibility** – WCAG 2.1 AA (or target level) and documented conformance.
- [ ] **Localization** – i18n and key languages for target enterprises (e.g. EN, DE, FR, ES).

### Engineering & quality
- [ ] **CI/CD** – Automated tests and deploy pipeline; no manual-only deploys for production.
- [ ] **Feature flags** – Roll out and roll back features without full deploy.
- [ ] **Backward compatibility** – Versioned API and deprecation policy.
- [ ] **Load testing** – Regular load and stress tests; capacity planning.
- [ ] **Dependency hygiene** – Regular updates and vulnerability scanning (e.g. Dependabot, Snyk).

### Already in place (aligned with good practice)
- Legal docs (Terms, Privacy, AUP, DMCA) and signup acceptance.
- AUP enforcement (block + log + admin review + appeals).
- Admin legal dashboard and review workflow.
- Branding and replication/IP protection (watermark, free iframe, replication blocking).
- Images and videos in builds (Together, Pexels) with domain-agnostic flow.
- Industry-aligned prohibited categories and replication_extraction.
- CORS, JWT auth, MongoDB, env-based config.
- Basic admin (users, billing, analytics, legal).

---

## Summary

- **Done today:** Bug fix, images + videos (agents, DAG, orchestration, UI), full legal/AUP (compliance agent, blocked-requests, admin legal, pages, footers, signup line, project error link), branding (watermark, free iframe badge, paid static div, replication blocking, AUP/Terms), and supporting docs.
- **Fortune 100 gaps:** SSO/SAML, SCIM, RBAC, audit log, MFA, SOC 2/ISO/HIPAA, DPA, legal review, SLA/status/DR, structured logging/APM/alerting, enterprise support, security questionnaire, accessibility, i18n, and tighter CI/CD and ops. Tackling these in order of customer demand and risk (e.g. SOC 2 and SSO first for enterprise sales) will move CrucibAI toward Fortune 100–grade software.

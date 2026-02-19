# CrucibAI — Incident Response Plan

**Purpose:** Internal plan for security and availability incidents: who to contact, how to escalate, and when/how to notify users.

**Confidentiality:** Internal use only.

---

## 1. Definitions

- **Security incident:** Unauthorized access, data breach, abuse of credentials, or compromise of user/code data.
- **Availability incident:** Extended outage or severe degradation of the service (e.g. API or frontend down).
- **Severity:** **Critical** (active breach, major outage); **High** (suspected breach, partial outage); **Medium** (vulnerability found, degraded service); **Low** (minor issue, no user impact).

---

## 2. Ownership and contacts

| Role | Responsibility | Contact |
|------|----------------|--------|
| **Incident lead** | Triage, coordinate response, decide on user notification. | [Set: e.g. CTO or designated lead] |
| **Backend / infra** | Fix backend, DB, secrets, deploy. | [Set: dev/ops] |
| **Frontend** | Fix frontend, CORS, client-side issues. | [Set: frontend lead] |
| **Legal / compliance** | Advise on notification, GDPR/CCPA, regulatory. | [Set: if applicable] |

*Update the table above with real contacts (email or internal channel).*

---

## 3. Steps (what to do)

1. **Detect** — Alert from monitoring, user report, or internal finding.
2. **Triage** — Incident lead assigns severity (Critical / High / Medium / Low) and owner.
3. **Contain** — Stop the bleed: revoke tokens, disable affected feature, rollback, or patch. Preserve logs and evidence.
4. **Investigate** — Root cause; scope (which users, which data). Document in a private incident channel or doc.
5. **Remediate** — Deploy fix, rotate secrets if needed, harden.
6. **Notify (if required)** — For **security incidents affecting user data**, determine if user or regulator notification is required (e.g. GDPR Art. 33/34, CCPA). Legal/compliance should be involved. Use in-app message, email, or status page as appropriate.
7. **Post-incident** — Short write-up: what happened, root cause, what we fixed, what we’ll do to prevent recurrence. Share internally; do not expose sensitive detail in public postmortems without review.

---

## 4. When to notify users

- **Critical/High security incident** with impact on user data (e.g. unauthorized access, credential leak): **Notify affected users** and, where required by law, regulators. Timeline: per GDPR, notify supervisory authority within 72 hours where there is a risk to rights; notify data subjects without undue delay when there is high risk.
- **Major outage:** Update status page or in-app banner; post-incident summary when service is restored.
- **Medium/Low:** Internal follow-up; user notification only if we decide it’s necessary (e.g. a vulnerability that could have affected them).

---

## 5. Useful links and tools

- **Security audit (internal):** Run `cd backend && python -m security_audit` to generate SECURITY_AUDIT_REPORT.md.
- **Secrets:** Rotate JWT_SECRET, Stripe keys, DB URL, or other secrets only through a controlled process; ensure all instances and envs are updated.
- **Logs:** Preserve relevant logs (auth, errors, access) for the incident window; do not delete before investigation and any legal hold.

---

## 6. Checklist (incident in progress)

- [ ] Severity and owner assigned.
- [ ] Containment action taken (revoke, disable, rollback, patch).
- [ ] Logs and evidence preserved.
- [ ] Root cause and scope documented.
- [ ] Fix deployed and verified.
- [ ] Decision on user/regulator notification made (with legal if needed).
- [ ] If required, users and/or regulator notified.
- [ ] Post-incident write-up completed and shared internally.

---

*Last updated: February 2026. Review and update contacts and steps periodically.*

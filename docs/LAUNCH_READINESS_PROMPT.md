# CrucibAI — Launch Readiness Master Prompt (Fortune-500 Level)

**Purpose:** The single prompt and checklist to get CrucibAI ready for launch. Test everything, connect everything, align everything. No new features — verify what we have is wired, secure, and as good as any top-tier product.

**Use this when:** Preparing for launch. Run the prompt and the verification commands; fix any failures; then sign off.

---

## Copy-paste prompt (for any AI or engineer)

```
You are preparing CrucibAI for launch. Your job is to verify and harden — not to add new features.

1. TEST EVERYTHING — Run backend pytest, frontend tests, and security_audit. Every critical path must pass or be explicitly excluded with a reason. Fix any failing tests or fix the code they cover.

2. CONNECT EVERYTHING — Every frontend route must render; every frontend API call must hit a real backend route; every backend route must have correct auth (get_current_user / get_optional_user / Admin) and behavior. No dead buttons, no 404s on critical paths, no stub endpoints in user flow. Reference: docs/LAUNCH_SEQUENCE_AUDIT.md.

3. ALIGN EVERYTHING — Backend and frontend same shape (project, build_kind, deploy_files). Docs and UI copy match behavior ("120 agents," "web + mobile," "prompt-to-automation," "bring your code," "you run the ads; we built the stack"). Messaging: docs/MESSAGING_AND_BRAND_VOICE.md.

4. SECURITY — Auth on all protected routes; no secrets in client or logs; rate limits (global + auth/payment); CORS from env; HTTPS redirect when set; Security/trust page and incident response doc in place. No critical or high findings left unaddressed.

5. WIRE ONLY — Agents (user + swarm), import (paste/zip/git), deploy (ZIP/Vercel/Netlify), tokens/Stripe, admin, workspace files, security scan on project — all real, no fake steps in critical path. Reference: docs/CODEBASE_SOURCE_OF_TRUTH.md.

6. LAUNCH MEANS DONE — Do not add features. Fix breaks, fix wiring, fix tests. When all verification steps pass, CrucibAI is launch-ready at Fortune-500 level: as good as any other company's stack for what we promise.
```

---

## Launch readiness checklist (execute in order)

### Step 1: Backend tests

```bash
cd backend && pytest tests -v --tb=short
```

- **Pass:** All tests green. No skipped critical-path tests without a ticket.
- **Fail:** Fix the failing test or the code it tests; re-run until pass.

### Step 2: Frontend tests

```bash
cd frontend && npm test -- --watchAll=false
```

- **Pass:** All tests green.
- **Fail:** Fix the failing test or component; re-run until pass.

### Step 3: Security audit

```bash
cd backend && python -m security_audit
```

- **Pass:** No critical/high unaddressed; report generated (e.g. SECURITY_AUDIT_REPORT.md).
- **Fail:** Address critical/high findings; re-run.

### Step 4: Route and API audit (manual / doc check)

- Open **docs/LAUNCH_SEQUENCE_AUDIT.md**. Confirm:
  - All frontend routes in App.js have a component and protection as listed.
  - All frontend → backend API usages in the table have a matching backend route.
- If you find a missing route or broken link: add the route or fix the call; update the doc.

### Step 5: Alignment (docs vs UI)

- **Messaging:** docs/MESSAGING_AND_BRAND_VOICE.md — Monday→Friday, "You run the ads; we built the stack," one-liner. Used on landing/features where appropriate.
- **Ads gap:** Option A locked (docs/GAPS_AND_INTEGRATIONS_REVIEW.md). No native Meta/Google before launch.
- **Unique advantage:** docs/UNIQUE_COMPETITIVE_ADVANTAGE_AND_NEW_BIG_IDEA.md — one-liner and prompt-to-automation reflected in product and copy.

### Step 6: CI (optional but recommended)

- Push to main; confirm `.github/workflows/enterprise-tests.yml` runs: lint, security (npm audit, pip-audit, gitleaks, SecurityAudit), frontend unit, backend integration, E2E.
- If CI fails: fix the failing job; push again until green.

---

## Sign-off

When all steps above pass:

- [ ] Backend tests pass
- [ ] Frontend tests pass
- [ ] Security audit run; no critical/high open
- [ ] Route/API audit confirmed (LAUNCH_SEQUENCE_AUDIT)
- [ ] Docs and UI aligned (messaging, Option A, unique advantage)
- [ ] CI green (or explicitly waived with reason)

**Launch-ready:** CrucibAI is then verified at the level of full interconnection, security, and alignment — Fortune-500 grade for what we ship. No new features; we are ready to launch.

---

## References

- **Master build prompt (broader):** CRUCIBAI_MASTER_BUILD_PROMPT.md
- **Route/API audit:** docs/LAUNCH_SEQUENCE_AUDIT.md
- **Source of truth:** docs/CODEBASE_SOURCE_OF_TRUTH.md
- **Messaging:** docs/MESSAGING_AND_BRAND_VOICE.md
- **Gaps (Option A):** docs/GAPS_AND_INTEGRATIONS_REVIEW.md

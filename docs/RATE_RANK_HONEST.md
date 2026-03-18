# CrucibAI — Honest Rate, Rank & Compare

**Date:** March 2026  
**Scope:** All work done up to this point: full builds, build types (web/mobile/agent/automation), theme consistency, pricing (linear, no rollover), Contact/Get Help pages, Docker + migrations, Explorer/doc structure, sidebar/UX fixes, preview normalization, and the existing orchestration, auth, and test base.

**Intent:** Honest assessment. No bias, no skew. Strengths and gaps both called out.

---

## 1. What’s in place (evidence)

| Area | What’s actually there |
|------|------------------------|
| **Build types** | Backend infers and accepts: fullstack, landing, mobile, saas, bot, ai_agent, game, trading, any. Project Builder sends build_kind (website→landing, automation→ai_agent). Workspace sends build_kind to /build/plan for big builds. |
| **Full web bundle** | Orchestrated web builds get: src/App.jsx, src/index.js, src/styles.css, package.json, public/index.html, plus server/schema/tests when generated. Not minimal-only. |
| **Full mobile** | Mobile builds get full Expo: App.js, app.json, eas.json, package.json, babel.config.js, store-submission pack. |
| **Preview** | Sandpack gets root→src path normalization and injected src/index.js when missing. Backend injects index.js + styles.css into deploy_files when frontend code exists. |
| **Theme** | Light/dark via data-theme; CSS variables (--theme-*); sidebar, Layout, Workspace, TokenCenter, scrollbars aligned; public forms use form-input-public so no black-on-white on light pages. |
| **Pricing** | Linear $0.03/credit; no rollover in copy or logic; plan cards aligned; custom addon same rate. |
| **Contact / Get Help** | Contact page + GET /get-help; POST /api/contact; Enterprise form; footer links. |
| **Docs** | BUILD_TYPES_AND_DEPLOY, EXPLORER_WHAT_IS_WHAT, RAILWAY_AND_GIT_DEPLOY, RUN_LOCAL (with Docker), PROOF_SIDEBAR_AND_THEME. Single place to understand “what is what” and how builds/deploy work. |
| **Local run** | docker-compose (backend + Postgres); craco proxy to backend; CRUCIBAI_DEV for optional startup without full env. |
| **Migrations** | 001_full_schema.sql run on backend startup (run_migrations in db_pg). |
| **Orchestration** | DAG, 115+ agents, phases, Autonomous Domain, SpecializedAgent for game/ml/blockchain/etc., Critic + Truth post-build, fallback on critical agents. |
| **Auth & security** | JWT, Google OAuth, tool auth, SSRF/path safety, CORS. |
| **Credits** | Credit balance in sidebar; refresh on health recovery; display logic (credit_balance vs token_balance, “—” when backend down). |

---

## 2. Honest rating (1–10)

| Dimension | Score | Why |
|-----------|--------|-----|
| **Orchestration** | 9 | DAG, many agents, domain enrichment, specialized paths. Real strength. Some agents still “suggest” (e.g. plain text) rather than always emitting runnable artifacts. |
| **Build breadth** | 8.5 | Web, mobile, agent, landing, SaaS, bot, game, trading are recognized and routed. Full web/mobile bundles defined. Agent/automation output is more “guided” than a full no-code agent runner. |
| **Full-app output** | 8.5 | Full bundle (package.json, index.html, entry, styles) for web; full Expo for mobile. Export/deploy wired. Preview works when backend returns the bundle; Workspace-only (single-shot AI) can still get minimal file sets from the model. |
| **UX / polish** | 8.5 | Workspace, sidebar (Manus-style collapse, footer separation), theme consistency, Contact/Get Help, prompt preservation. Solid. Not at the level of a single-focus product (e.g. Cursor’s IDE). |
| **Pricing & credits** | 9 | Linear pricing, no rollover, clear plans, single source of truth. Credit display and backend dependency are documented. |
| **Documentation** | 9 | BUILD_TYPES, EXPLORER_WHAT_IS_WHAT, RUN_LOCAL, RAILWAY_AND_GIT_DEPLOY, and others. Onboarding and “where is what” are well covered. |
| **Operational readiness** | 7.5 | Docker Compose and migrations improve local and deploy. Some tests still assume DB/keys; OAuth in production has had issues; push to Git failed on permissions (remote = mandeepsinghgill/crucib, not disputestrike). |
| **Reliability** | 7.5 | Fallbacks and error recovery exist. “Backend not available” and preview depend on backend being up; Workspace dedupes repeated error messages. |
| **Security & auth** | 8.5 | Auth on tools, OAuth, validation, legal/AUP checks. Not independently audited. |
| **Observability** | 8.5 | OpenTelemetry, Prometheus /api/metrics, build events. Present and wired. |

**Overall (average of above): ~8.5/10.**

If we restrict to “product completeness and differentiation” (orchestration, build types, full bundle, docs, UX): **~8.7/10**.  
If we weight “runs reliably in production and all tests green” more: **~8.2/10**.

---

## 3. Honest rank vs competitors

**Where CrucibAI stands:**

- **Orchestration / multi-agent:** Top tier. Few products expose a DAG of 115+ agents, domain enrichment, and specialized (game/ml/blockchain) paths. **Rank: #1–2** (with Bolt/Manus-style platforms).
- **Full-app + multi-type:** Web (full bundle) and mobile (Expo) are first-class; agent/automation are guided. Comparable to Bolt, Replit, Lovable for “app from prompt”; ahead on orchestration depth. **Rank: top 3–5.**
- **UX / workspace:** Good workspace, theme, sidebar, Contact/Get Help. Cursor still leads for IDE integration; we’re strong for “prompt → plan → build” in one product. **Rank: top 5.**
- **Pricing transparency:** Linear pricing, no rollover, clear docs. **Rank: top 3.**
- **Documentation / discoverability:** EXPLORER_WHAT_IS_WHAT, BUILD_TYPES_AND_DEPLOY, RUN_LOCAL, etc. **Rank: top 3.**

**Rough overall ranking in a “build-from-prompt + orchestration” segment:**

| Rank | Tool | Note |
|------|------|------|
| 1–2 | **CrucibAI** / Bolt (or Manus) | We lead on orchestration depth, build types, and docs; they can lead on polish or distribution. |
| 3 | Cursor | Best for IDE + codebase; not a full “app from prompt” pipeline. |
| 4 | Replit / Lovable | Strong on “full app from description”; less agent depth. |
| 5 | v0, others | UI or narrower scope. |

So: **honest rank: #1–2 in our segment**, not a guaranteed “we are #1 in all of software.” In “AI coding tools” broadly, **top 5** is a fair claim; **top 3** is defensible when the comparison is “orchestration + multi-type build + docs.”

---

## 4. Compare (strengths vs gaps)

**Strengths**

- **Orchestration:** DAG, many agents, domain and specialized paths.
- **Build types:** Web, mobile, agent, automation, landing, SaaS, bot, game, trading — recognized and routed.
- **Full bundles:** Web and mobile outputs are full (not minimal-only) for the orchestration path.
- **Docs:** Clear “what is what,” how to build, how to run, how to deploy.
- **Theme and UX:** Consistent light/dark, sidebar, Contact/Get Help, pricing alignment.
- **Pricing:** Linear, no rollover, single source of truth.

**Gaps / risks**

- **Preview:** Depends on backend; single-shot Workspace flow can still get few files from the model.
- **Tests:** Some tests fail without DB/keys; not all green in every environment.
- **Production:** OAuth and “backend not available” have come up; need stable env and credentials.
- **Git push:** Current remote permissions prevented push; need correct remote (e.g. disputestrike/CrucibAI) or access.
- **Agent/automation:** “Build me an agent” is supported and routed; the output is more “spec + guidance” than a full no-code agent runner out of the box.

---

## 5. One-line summary

**Rate:** ~8.5/10 overall; ~8.7/10 on product completeness and differentiation.  
**Rank:** #1–2 in “orchestration + multi-type build from prompt”; top 5 in “AI coding tools” broadly.  
**Compare:** Strongest on orchestration, build-type coverage, full bundles, and docs; solid on UX and pricing; operational and reliability gaps (tests, OAuth, backend dependency, Git remote) keep it from 9+ without further hardening.

All of this is saved in the repo; the commit is done locally; push failed on permissions and would need the right remote or access.

# CrucibAI Master Build Prompt

**Use this prompt to build, audit, and harden CrucibAI at the highest level. No limits. 100% execution.**

---

## Copy-paste prompt (for any AI or engineer)

```
You are building CrucibAI to be the greatest AI app builder. Your job:

1. Remove all limits — CrucibAI must build web apps, mobile apps (Expo/React Native), landing pages, SaaS, bots, and just about everything. Real code, real wiring, real outcomes.

2. Build at 100% — Every critical path must work: auth, projects, orchestration (DAG, phases, agents), export (ZIP, GitHub, deploy), mobile (Expo + store pack), preview, events, tokens, security, self-heal. No "almost."

3. Test every line in spirit — For every critical path (auth, API, orchestration, export, SSE, websocket, tool execution): does it run? fail safely? connect to the UI? Audit security, data flow, user-facing behavior.

4. Security first — Auth on every protected route; no secrets in logs/client; input validation; injection resistance; env for keys; rate limiting; secure headers. Fix every gap.

5. Nothing placeholder, nothing broken — No TODOs that block core flows. No stubs that pretend to work in critical path. No silent "pass" in except blocks without logging. Replace or remove placeholders.

6. Connect everything — Every promised feature must be wired: API ↔ frontend, SSE ↔ timeline, export ↔ deploy_files, mobile ↔ build_kind and store pack. Agents must have real behavior (state, artifact, or tool), not prompt only.

7. Alignment — Backend and frontend same shape; docs and UI match behavior. "120 agents," "mobile + App Store / Play Store" must be accurate and implemented.

8. Implement 100% — When you find a gap (missing validation, broken link, unwired feature, security hole), fix it. Don't just list it.

9. Rate, rank, compare — When done, update competitive positioning: rate CrucibAI vs Devin, Cursor, Replit, Lovable, Manus, Kimi. Answer "who builds better, faster, more helpful?" clearly.

Lead with implementation and wiring, not just prompts. Build at CrucibAI level.
```

---

## The Prompt (expanded)

You are building CrucibAI to be the **greatest AI app builder**: the most exceptional, full-capacity, production-grade system for turning ideas into software. Your job is to:

1. **Remove all limits** on building ability. CrucibAI must be able to build web apps, mobile apps (Expo/React Native), landing pages, SaaS, bots, and “just about everything” — with real code, real wiring, and real outcomes. Nothing is “out of scope” for the product vision; only implementation priority and order of work.

2. **Build at 100%** — as good as CrucibAI is meant to be. Every critical path must work: auth, projects, orchestration (DAG, phases, agents), export (ZIP, GitHub, deploy), mobile (Expo + store pack), preview, events, tokens, security checks, and self-heal. No “almost” or “mostly.” If it’s in the product, it must be wired and testable.

3. **Test every line of code** in spirit: treat the codebase as production. For every critical path (auth, API, orchestration, file write, export, SSE, websocket, tool execution), ask: does this run? does it fail safely? is it connected to the UI or caller? Audit line by line where it matters — security, data flow, and user-facing behavior.

4. **Security first.** Check: authentication and authorization on every protected route; no secrets in logs or client; input validation and sanitization; SQL/NoSQL and command injection resistance; env-based config (no hardcoded keys); rate limiting and abuse protection; secure headers and CORS. Fix every gap.

5. **Nothing placeholder, nothing broken.** No TODOs that block core flows. No stubs that pretend to work (e.g. “fraud flags stub” must either be implemented or removed from critical path). No dead code that looks like a feature. No “pass” in an except block that swallows real failures without logging or handling. Replace placeholders with real behavior or remove them from critical paths.

6. **Connect everything.** Every feature that the UI or docs promise must be wired: API ↔ frontend, SSE ↔ event timeline, websocket ↔ progress, export ↔ deploy_files, mobile ↔ build_kind and store pack. Agents must have real behavior (state, artifact, or tool) — not “prompt only.” Wiring means: the code path exists, is called, and produces the expected outcome.

7. **Alignment and completeness.** Backend and frontend must align: same project shape, same build_kind, same deploy_files structure. Docs and UI copy must match behavior. If we say “120 agents,” the DAG and orchestration must reflect that. If we say “mobile + App Store / Play Store,” the export must include the store pack and the UI must show it.

8. **Modern and functional.** Use current best practices: async where appropriate, structured logging, clear errors, env-based config, and dependency management. No deprecated patterns that compromise security or reliability.

9. **Implement 100%.** When you find a gap — missing validation, missing error handling, broken link, unwired feature, or security hole — you fix it. You don’t just list it; you implement the fix and verify the wiring.

10. **Rate, rank, and compare.** When the build and audit are done, update the competitive positioning: rate CrucibAI honestly against the criteria (orchestration, quality, visibility, mobile, store path, security, speed). Rank it vs. Devin, Cursor, Replit, Lovable, Manus, Kimi. Compare in the docs so the answer to “who builds better, faster, and more helpful?” is clear and defensible.

---

## Execution Checklist (for the AI or engineer)

- [ ] **Security:** Auth on all protected routes; no secrets in client/logs; validation and injection-safe paths; env for keys; rate limit and CORS.
- [ ] **Orchestration:** DAG runs; all agents in DAG have real behavior or explicit skip; build_kind (web/mobile) flows through; deploy_files built for both web and mobile; autonomy loop runs after phases.
- [ ] **Export:** ZIP, GitHub, Deploy endpoints use deploy_files; mobile projects include store-submission/; no broken blob or missing files.
- [ ] **Frontend:** Project load, build progress, events, export, and mobile badge use the right API and state; no dead buttons or broken links.
- [ ] **Placeholders & stubs:** Replace or remove any stub that blocks a critical path; ensure fallbacks are safe and logged.
- [ ] **Errors:** No silent `pass` in except blocks; log and return or re-raise appropriately.
- [ ] **Docs & UI:** Copy matches behavior; “web + mobile,” “store pack,” “120 agents” are accurate.
- [ ] **Rate/rank:** Update RATE_RANK_TOP50 (or equivalent) and comparison docs so CrucibAI is positioned clearly vs. competitors.

---

## One-Line Summary

**Build CrucibAI at full capacity: no limits, 100% execution, test every critical line, security first, nothing placeholder or broken, everything wired and connected, then rate and rank it against the best.**

Use this prompt to drive the audit and implementation. When done, CrucibAI should be the greatest version of itself — ready to build software, mobile apps, landing pages, and just about everything, with nothing missing or broken that would prevent it from being the best.

---

## Execution summary (audit applied)

- **Security:** Auth on protected routes (get_current_user / get_optional_user); JWT and MFA; no secrets in client; capabilities endpoint logs when Docker check fails; admin fraud endpoint documented as extensible.
- **Orchestration:** DAG with Native Config + Store Prep; build_kind (web/mobile) flows through; deploy_files built for web and mobile (Expo + store-submission/); autonomy loop runs after phases.
- **Export:** Project deploy ZIP (GET /projects/:id/deploy/zip) uses deploy_files from DB (includes store-submission/ for mobile); POST /export/zip and /export/deploy accept any files dict (Workspace editor state).
- **Placeholders:** Admin fraud_flags returns empty list with clear message; fallbacks in agent_resilience are safe; no silent failure in capabilities (log added).
- **Rate/rank:** RATE_RANK_TOP50 and comparison docs updated to reflect web + mobile and App Store / Play Store path.

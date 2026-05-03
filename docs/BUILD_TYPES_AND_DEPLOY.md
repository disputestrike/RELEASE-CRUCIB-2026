# Build Types, Full Builds, and Deploy

This doc answers: **How does â€œbuild me a mobile / agent / softwareâ€ work?** and **How do we define the full-build contract and deploy path?**

---

## Confirmation (TL;DR)

- **Full app / full mobile:** Yes. When you build from **Project Builder** (or orchestration runs with the right `build_kind`), you get a **full** output: web = `src/App.jsx`, `src/index.js`, `src/styles.css`, `package.json`, `public/index.html` + backend/DB/tests when applicable; mobile = full Expo app (App.js, app.json, eas.json, package.json, store submission). No minimal-only path for orchestrated projects.
- **What is what in the repo:** All the folders you see in Cursor (backend, frontend, docs, scripts, agents, routers, pages, etc.) are created and saved in the repo. To know **what each folder is and where things live**, use **docs/EXPLORER_WHAT_IS_WHAT.md**.

---

## 1. How the system recognizes what youâ€™re building

### From the **Project Builder** (explicit type)

When you create a project from **New Project** and choose a type, we send that as `build_kind` in `requirements`:

| You choose       | Backend `build_kind` | What gets built |
|------------------|----------------------|------------------|
| Full-Stack App    | `fullstack`          | Web app: React + backend + DB + tests, full bundle (see below) |
| Website          | `landing`            | Landing/marketing page, hero + features + CTA |
| Mobile App       | `mobile`             | Expo (React Native) app + app.json, eas.json, store submission pack |
| SaaS             | `saas`               | Multi-tenant, billing, auth, dashboard |
| Bot              | `bot`                | Slack/Discord/Telegram/webhook bot |
| AI Agent         | `ai_agent`           | Agent with tools, prompts, optional API/runner |
| Game             | `game`               | Browser/mobile game, loop, UI, levels |
| Trading / Fintech| `trading`            | Orders, positions, P&L, charts |
| Anything         | `any`                | No restriction; stack chosen from prompt |
| API Backend      | `fullstack`          | Backend-focused web project |
| Automation       | `ai_agent`           | Automation/agent-style project |

So: **â€œBuild me a mobileâ€** = choose **Mobile App** in Project Builder â†’ `build_kind: "mobile"` â†’ orchestration produces an Expo bundle.  
**â€œBuild me an agentâ€** = choose **AI Agent** (or **Automation**) â†’ `build_kind: "ai_agent"` â†’ plan and agents target agent/automation outputs.

### From the **Dashboard / Workspace** (inferred from prompt)

If you type in the Dashboard (e.g. â€œBuild me a todo appâ€) and go straight to the **Workspace** (no project created yet), the **backend** infers `build_kind` from the prompt when a **project is later created** (e.g. from Project Builder or save flow). The inference rules (in `_infer_build_kind`) include:

- **Mobile**: â€œmobile appâ€, â€œreact nativeâ€, â€œflutterâ€, â€œios appâ€, â€œandroid appâ€, â€œbuild me a mobileâ€, etc.
- **Agent / automation**: â€œbuild me an agentâ€, â€œautomationâ€, â€œscheduled taskâ€, â€œcronâ€, â€œwebhook agentâ€, â€œbuild agentâ€, etc.
- **Website**: â€œwebsiteâ€, â€œbuild me a websiteâ€, â€œbuild me a webâ€.
- **Landing**: â€œlanding pageâ€, â€œone-pageâ€, â€œmarketing pageâ€.
- **SaaS, bot, game, trading**: same keywords as in the table above.

So when someone says **â€œBuild me an agentâ€** or **â€œBuild me a mobileâ€**, the system either uses the type they picked (Project Builder) or infers it from the prompt when running **orchestration** (e.g. after creating a project).

---

## 2. Two ways to â€œbuildâ€

### A. **Project flow (full orchestration, full bundle)**

1. User goes to **Project Builder**, enters name/description, selects type (e.g. Mobile, AI Agent, Website).
2. Frontend sends `POST /api/projects` with `requirements: { prompt, build_kind }`.
3. Backend creates the project and starts **orchestration** (`run_orchestration_v2`).
4. DAG runs many agents (Planner, Stack Selector, Frontend Generation, Backend Generation, Database Agent, etc.) and produces **deploy_files**.
5. **Web (`fullstack` / `landing`)**: We always emit a **full** bundle, not minimal:
   - `src/App.jsx` (or generated frontend)
   - `src/index.js` (entry)
   - `src/styles.css` (Tailwind CDN)
   - `package.json` (React, react-scripts)
   - `public/index.html`
   - Backend: `server.py`, `schema.sql`, `tests/test_basic.py` when applicable.
6. **Mobile**: Expo app with `App.js`, `app.json`, `eas.json`, `package.json`, `babel.config.js`, store-submission guide and metadata.
7. **Agent / automation**: Uses the same DAG; agents are steered by `[Build kind: ai_agent]` in the prompt; outputs (e.g. scripts, API, runner) are stored in the project.

Preview and deploy use these **deploy_files**, so the project is **complete** for export (ZIP, GitHub, Vercel, Netlify, Railway).

### B. **Workspace-only flow (no project, single-shot AI)**

1. User types on the **Dashboard** (e.g. â€œBuild me a flower websiteâ€) â†’ intent **build** â†’ navigate to **Workspace** with `initialPrompt` + `autoStart`.
2. **No project is created.** Workspace calls `/ai/chat` or `/ai/chat/stream` with a long prompt that asks for multiple files (App.js, Navbar, Footer, pages/Home.js, etc.).
3. Response is parsed; root-level files are normalized to `/src/` and a default `src/index.js` is injected if missing so **Sandpack preview** works.
4. User can later **export** (ZIP) or **deploy** from the Workspace UI; that uses the in-memory files. To get the **full orchestration bundle** (with backend, DB, tests, package.json, index.html), they need to **create a project** from Project Builder with the same intent and run the full build there.

So: **â€œBuild me a softwareâ€** in the Dashboard â†’ Workspace gives a **single-shot** full-stack-style app (multi-file when the model complies). **â€œBuild me a softwareâ€** in **Project Builder** with type Full-Stack â†’ **full build** with backend, DB, tests, and full web bundle.

---

## 3. Full build contract (no â€œminimalâ€ only)

- **Web (orchestration path)**  
  Every web project from orchestration gets:
  - `src/App.jsx`, `src/index.js`, `src/styles.css`
  - `package.json`, `public/index.html`
  - Backend and DB when generated: `server.py`, `schema.sql`, `tests/test_basic.py`  
  So export/deploy is a **full** runnable project, not a minimal snippet.

- **Preview**  
  - Sandpack expects `/src/` and an entry. We normalize root-level files to `/src/` and inject `src/index.js` if missing (frontend Workspace logic).
  - Backend always adds `src/index.js` and `src/styles.css` to `deploy_files` when it has frontend code, so after orchestration the project has a runnable bundle for preview and deploy.

- **Mobile**  
  Full Expo project: entry, config, store submission docs, so you can build and submit.

- **Agent / automation**  
  Orchestration runs with `build_kind: "ai_agent"`; agents are instructed to produce agent/automation artifacts (tools, prompts, API, runner). Output is stored in the project and can be exported/deployed like any other type.

---

## 4. Deploy

- **From a project (orchestration)**  
  Use **Deploy** in the Workspace when viewing that project. Backend serves `GET /api/projects/:id/deploy/files`. Frontend can:
  - **Export as ZIP** (all `deploy_files`).
  - **Deploy to GitHub / Vercel / Netlify / Railway** using the same file set.

- **From Workspace without a project**  
  Export and deploy use the **in-memory** files (from the single-shot AI run). No orchestration bundle unless the user creates a project and runs a full build.

So: **full build** = create a project with the right type (or inferred `build_kind`) and run orchestration; then preview and deploy both use the full bundle.

---

## 5. Summary

| Question | Answer |
|----------|--------|
| How does â€œbuild me a mobileâ€ work? | Choose **Mobile App** in Project Builder (or prompt implies mobile) â†’ `build_kind: "mobile"` â†’ orchestration produces full Expo app. |
| How does â€œbuild me an agentâ€ work? | Choose **AI Agent** or **Automation** (or prompt implies agent/automation) â†’ `build_kind: "ai_agent"` â†’ orchestration produces agent/automation outputs. |
| How does â€œbuild me a softwareâ€ work? | Full-Stack or inferred `fullstack` â†’ full web bundle + backend + DB + tests; single-shot in Workspace = multi-file React app when the model complies. |
| How does the agent recognize what to build? | **Project Builder**: you pick the type â†’ `build_kind`. **Orchestration**: `build_kind` from requirements or `_infer_build_kind(prompt)`. |
| Full build contract? | Web: always `src/App.jsx`, `src/index.js`, `src/styles.css`, `package.json`, `public/index.html` + backend/DB/tests when applicable. Mobile: full Expo. No â€œminimal-onlyâ€ for orchestrated projects. |
| Deploy? | From project: use Deploy in Workspace (ZIP / GitHub / Vercel / Netlify / Railway) from `deploy_files`. From Workspace-only: export/deploy from in-memory files. |

This is the single source of truth for build types, full builds, and deploy behavior.


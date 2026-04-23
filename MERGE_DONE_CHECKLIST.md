# Merge Done Checklist — CrucibAI (disputestrike/CrucibAI)

**Date:** March 2026  
**Merge:** Crucib (dashboard/layout/workspace/export) into this repo. Keep this repo's landing, integrations, token/pricing.

---

## What Was Done

### 1. Copied from crucib (this folder = target)

- **Components:** `Layout.jsx`, `Layout.css`, `Sidebar.jsx`, `Sidebar.css`, `Layout3Column.jsx`, `Layout3Column.css`, `RightPanel.jsx`, `RightPanel.css`, `OnboardingTour.jsx`, `OnboardingTour.css`, `Logo.jsx`, `VoiceWaveform.jsx`, `VoiceWaveform.css`, `SandpackErrorBoundary.jsx`, `SandpackErrorBoundary.css`, `CrucibAIComputer.jsx`, `InlineAgentMonitor.jsx`, `InlineAgentMonitor.css`, `ManusComputer.jsx`, `AdvancedIDEUX.jsx`, `VibeCoding.jsx`, `DeployButton.jsx`
- **Pages:** `Dashboard.jsx`, `Dashboard.css`, `Workspace.jsx`, `Workspace.css`, `ExportCenter.jsx`
- **Stores:** `useLayoutStore.js`, `useTaskStore.js`

### 2. Kept from this repo (not overwritten)

- **Landing:** `LandingPage.jsx` (route `/`)
- **Token & pricing:** `TokenCenter.jsx`, `Pricing.jsx`
- **App & routes:** `App.js` (unchanged; `/` = LandingPage, `/app` = Layout + Dashboard/Workspace/Export)
- **Integrations:** All backend and integration code unchanged
- **Public:** `PublicNav`, `PublicFooter`, `OurProjectsPage`, etc.

### 3. Fixes applied after copy

- **Layout.jsx:** Added `logApiError` import and usage in `checkBackend` and `fetchSidebarData` for consistency with this repo.
- **ExportCenter.jsx:** Added `logApiError` import and used in `fetchData` catch.
- **Sidebar.jsx:** Already had nullish coalescing fix (parens for `??`/`||`) from crucib.

---

## How to Run (100%)

1. **Backend:** From repo root, start backend (e.g. `uvicorn` or `python -m backend.main` per this repo's README).
2. **Frontend:** `cd frontend && npm install && npm run dev` (or `yarn dev`). Open app at `http://localhost:3000`.
3. **Verify:**  
   - `/` shows **this repo's landing page**.  
   - Log in → `/app` shows **crucib's dashboard**.  
   - Navigate to Workspace, Export, Tokens, Pricing — all work with this repo's API and token/pricing.

---

## Reaching 10/10 (Post-Merge)

- Merged product uses **this repo's** landing, integrations, token/pricing and **crucib's** dashboard, layout, workspace, export.
- Error handling aligned with this repo (`logApiError`).
- One codebase, one app: landing → auth → dashboard → workspace → export, with token/pricing from this repo.

For the **rate/rank/compare** at 10/10, see `docs/POST_MERGE_RATE_RANK_COMPARE.md` in the crucib repo (or below).

---

## Launch GTM

See **`docs/LAUNCH_GTM.md`** for the post-launch strategy (founder vs builder, execution as weapon, mobile app build as unique card) and what the app must support for launch.

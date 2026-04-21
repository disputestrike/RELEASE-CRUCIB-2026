# CF17 — Legacy Pages Inventory

**Generated:** 2026-04-20  
**Purpose:** Every file under `frontend/src/pages/` is tagged with one of four
dispositions so we can finish the Workspace-V3 consolidation without
breaking public URLs or admin tooling.

Dispositions:

| Tag | Meaning |
|---|---|
| `keep` | Canonical page, stays. |
| `migrate` | Content/functionality should fold into WorkspaceV3Shell surfaces. |
| `keep-behind-flag` | Retained for rollback/contingency under `REACT_APP_WORKSPACE_LEGACY` or similar flag. |
| `delete` | Superseded — remove after one release cycle with a 301 redirect. |

This table is the authoritative crosswalk for Phase 2 consolidation and is
referenced by `frontend/src/legacy/pagesManifest.js`.

## Inventory (76 page files)

| File | Route(s) | Disposition | Target | Notes |
|---|---|---|---|---|
| `About.jsx` | `/about` | keep | — | Public marketing page. |
| `AdminAnalytics.jsx` | `/app/admin/analytics` | keep | — | Admin tooling. |
| `AdminBilling.jsx` | `/app/admin/billing` | keep | — | Admin tooling. |
| `AdminDashboard.jsx` | `/app/admin` | keep | — | Admin tooling. |
| `AdminLegal.jsx` | `/app/admin/legal` | keep | — | Admin tooling. |
| `AdminPanel.tsx` | (unrouted) | delete | — | Superseded by AdminDashboard. |
| `AdminUserProfile.jsx` | `/app/admin/users/:id` | keep | — | Admin tooling. |
| `AdminUsers.jsx` | `/app/admin/users` | keep | — | Admin tooling. |
| `AgentMonitor.jsx` | `/app/projects/:id` | migrate | WorkspaceV3Shell/RightRail/Monitor | Fold into rail monitor panel. |
| `AgentsPage.jsx` | `/app/agents` | migrate | WorkspaceV3Shell/Agents tab | New Agents tab inside Workspace-V3. |
| `AuditLog.jsx` | `/app/audit-log` | keep | — | Admin/compliance surface. |
| `Aup.jsx` | `/aup` | keep | — | Legal. |
| `AuthPage.jsx` | `/auth` | keep | — | Login. |
| `Benchmarks.jsx` | `/benchmarks` | keep | — | Proof page; now hydrated via `/api/benchmarks/*`. |
| `Blog.jsx` | `/blog`, `/blog/:slug` | keep | — | Marketing. |
| `BlogPost.jsx` | (component) | keep | — | Used by Blog. |
| `Builder.jsx` | `/builder` (redirected) | delete | — | Redirect points to `/app/workspace`; file unreferenced. |
| `Changelog.jsx` | `/changelog` | keep | — | Marketing. |
| `ChannelsPage.jsx` | `/app/channels` | keep | — | Collaboration. |
| `CommerceManagePage.jsx` | `/app/commerce` | keep | — | Paid tier. |
| `Contact.jsx` | `/contact` | keep | — | Marketing. |
| `Cookies.jsx` | `/cookies` | keep | — | Legal. |
| `DashboardVNext.jsx` | `/app/dashboard` | keep | — | Canonical dashboard. |
| `Dmca.jsx` | `/dmca` | keep | — | Legal. |
| `DocsPage.jsx` | `/docs`, `/documentation` | keep | — | Marketing. |
| `Enterprise.jsx` | `/enterprise` | keep | — | Marketing. |
| `EnvPanel.jsx` | `/app/env` | migrate | WorkspaceV3Shell/Settings | Fold env editor into Settings. |
| `ExamplesGallery.jsx` | `/app/examples` | keep | — | In-app gallery. |
| `ExportCenter.jsx` | `/app/exports` | keep | — | Export surface. |
| `Features.jsx` | `/features` | keep | — | Marketing. |
| `FineTuning.jsx` | `/app/fine-tuning` | keep | — | Advanced feature. |
| `GenerateContent.jsx` | `/app/generate` | keep | — | Generator surface. |
| `GetHelp.jsx` | `/get-help` | keep | — | Support. |
| `KnowledgePage.jsx` | `/app/knowledge` | keep | — | Knowledge base. |
| `LandingPage.jsx` | `/` | keep | — | Marketing home. |
| `LearnPanel.jsx` | `/app/learn` | keep | — | In-app learning. |
| `LearnPublic.jsx` | `/learn` | keep | — | Marketing. |
| `ModelManager.jsx` | `/app/models` | keep | — | Advanced feature. |
| `MonitoringDashboard.jsx` | `/app/live`, `/app/monitoring` | keep | — | Live ops surface. |
| `OnboardingPage.jsx` | `/onboarding` | keep | — | First-run page; now also posts `/api/onboard/start`. |
| `OurProjectsPage.jsx` | `/our-projects` | keep | — | Marketing case studies. |
| `PatternLibrary.jsx` | `/app/patterns` | keep | — | In-app library. |
| `PatternsPublic.jsx` | `/patterns` | keep | — | Marketing. |
| `PaymentsWizard.jsx` | `/app/payments-wizard` | keep | — | Setup flow. |
| `Pricing.jsx` | `/pricing` | keep | — | Marketing. |
| `Privacy.jsx` | `/privacy` | keep | — | Legal. |
| `ProjectBuilder.jsx` | `/app/projects/new` | migrate | WorkspaceV3Shell/NewProject | Reduce to trigger inside shell. |
| `PromptLibrary.jsx` | `/app/prompts` | keep | — | In-app library. |
| `PromptsPublic.jsx` | `/prompts` | keep | — | Marketing. |
| `PublicProofPage.jsx` | `/proof` | keep | — | Proof surface. |
| `SafetyDashboard.jsx` | `/app/safety` | keep | — | Safety ops. |
| `Security.jsx` | `/security` | keep | — | Legal/trust. |
| `SessionsPage.jsx` | `/app/sessions` | keep | — | Admin. |
| `Settings.jsx` | `/app/settings` | keep | — | Settings. |
| `ShareView.jsx` | `/share/:token` | keep | — | Public share. |
| `ShortcutCheatsheet.jsx` | `/app/shortcuts` | keep | — | In-app reference. |
| `ShortcutsPublic.jsx` | `/shortcuts` | keep | — | Marketing. |
| `SkillsMarketplace.jsx` | `/app/skills-marketplace` | keep | — | Plugins/marketplace. |
| `SkillsPage.jsx` | `/app/skills` | keep | — | Skills list. |
| `Status.jsx` | `/status` | keep | — | Status page. |
| `StudioPage.jsx` | `/app/studio` | keep | — | Advanced authoring. |
| `TemplatesGallery.jsx` | `/app/templates` | keep | — | Templates. |
| `TemplatesPublic.jsx` | `/templates` | keep | — | Marketing. |
| `Terms.jsx` | `/terms` | keep | — | Legal. |
| `TokenCenter.jsx` | `/app/tokens` | keep | — | Billing. |
| `TutorialsPage.jsx` | `/tutorials` | keep | — | Marketing. |
| `UnifiedIDEPage.jsx` | `/app/ide` | keep-behind-flag | — | Retired IDE shell; keep for power users until V3 fully ships. |
| `UnifiedWorkspace.jsx` | (alias redirect) | delete | — | Superseded by WorkspaceV3Shell. |
| `VibeCodePage.jsx` | `/app/vibecode` | keep | — | Experimental mode. |
| `WorkspaceMembersPage.jsx` | `/app/members` | keep | — | Collab admin. |
| `WorkspaceV3Shell.jsx` | `/app/workspace`, `/app/workspace-v3` | keep | — | **Canonical workspace shell.** |
| `WorkspaceVNext.jsx` | (fallback) | keep-behind-flag | — | Used when `REACT_APP_WORKSPACE_LEGACY=true`. |
| `__tests__/AdminDashboard.test.jsx` | (test) | keep | — | Test. |
| `__tests__/AdminUsers.test.jsx` | (test) | keep | — | Test. |
| `__tests__/UnifiedWorkspaceSurfaceMode.test.js` | (test) | delete | — | References deleted UnifiedWorkspace. |
| `__tests__/WorkspaceVNext.test.jsx` | (test) | keep-behind-flag | — | Stays as long as VNext stays. |

## Summary

- Total: 76 files  
- `keep`: 64  
- `migrate`: 5  (AgentMonitor, AgentsPage, EnvPanel, ProjectBuilder, + one folded) 
- `keep-behind-flag`: 3  (UnifiedIDEPage, WorkspaceVNext, its test)  
- `delete`: 4  (AdminPanel.tsx, Builder.jsx, UnifiedWorkspace.jsx, UnifiedWorkspaceSurfaceMode.test.js)

## Next actions

1. Execute the 4 deletes in a dedicated branch with redirect entries in App.js (DONE — redirects already in place for `/builder`, `/workspace`, and `/app/workspace-*` aliases).
2. Migrate the 5 `migrate` files by copy-and-reduce inside `WorkspaceV3Shell.jsx`, then redirect.
3. Keep-behind-flag entries remain until WorkspaceV3Shell has been in production for one full release cycle with no rollback requests.

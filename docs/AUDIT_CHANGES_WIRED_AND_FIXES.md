# Audit: All 55 Changes — Where They Live & Wiring Status

**Date:** After pull of latest code (post 5ab5ecf).  
**Purpose:** Verify every item from `docs/CHANGES_LAST_5_HOURS.md` is present, wired, and working.

---

## Summary

| Category | Items | Status | Notes |
|----------|-------|--------|------|
| 1. Build types & full builds | 6 | ✅ Wired | server.py, ProjectBuilder.jsx, Workspace.jsx |
| 2. Preview & Sandpack | 4 | ✅ Wired | Workspace.jsx path norm, index.js inject, filesReadyKey |
| 3. Pricing & credits | 5 | ✅ Wired | server, TokenCenter, Pricing, docs |
| 4. Contact & Get Help | 6 | ✅ Fixed | **Was broken:** missing `contact_submissions` table — added to migration + ensure_all_tables |
| 5. Enterprise & form styling | 3 | ✅ Wired | Enterprise.jsx, index.css form-input-public |
| 6. Theme light/dark | 3 | ✅ Wired | index.css, Sidebar/Layout/Workspace/TokenCenter.css |
| 7. Sidebar & layout | 7 | ✅ Wired | Sidebar.jsx: Engine+Credits only at bottom; Settings in Guest dropdown; Folder icon |
| 8. Backend connectivity | 3 | ✅ Wired | Layout.jsx refreshUser on health; craco proxy; CRUCIBAI_DEV |
| 9. Docker & migrations | 4 | ✅ Wired | docker-compose.yml, db_pg run_migrations + ensure_all_tables |
| 10. Documentation | 5 | ✅ Present | docs/*.md |
| 11. UX & chat | 5 | ✅ Wired | Dashboard icon-only Copy/Edit; Workspace dedup; mic message; product-support in ai.py |
| 12. Duplicate arrow | 1 | ✅ Wired | Single collapse in Sidebar |
| 13–14. Git, rate/rank | 3 | ✅ N/A | Repo state, docs |

**One fix applied:** `contact_submissions` table was missing from PostgreSQL schema. Contact form would 500 on submit. Added to `backend/migrations/001_full_schema.sql` and `backend/db_pg.py` (REQUIRED_TABLES + ENSURE_TABLES_SQL).

---

## 1. Build types & full builds (6)

| # | Change | Where | Verified |
|---|--------|------|----------|
| 1 | Extended _infer_build_kind | backend/server.py | ✅ |
| 2 | Landing allowed in orchestration | backend/server.py run_orchestration_v2 | ✅ |
| 3 | Full web bundle package.json + public/index.html | backend/server.py deploy_files for web | ✅ |
| 4 | Backend injects src/index.js + src/styles.css | backend/server.py when frontend exists | ✅ |
| 5 | ProjectBuilder website→landing, automation→ai_agent | frontend/src/pages/ProjectBuilder.jsx | ✅ |
| 6 | Workspace sends build_kind to /build/plan | frontend/src/pages/Workspace.jsx (detectedBuildKind, big builds) | ✅ |

---

## 2. Preview & Sandpack (4)

| # | Change | Where | Verified |
|---|--------|------|----------|
| 7 | Root → /src/ path normalization | Workspace.jsx sandpackFiles useMemo | ✅ |
| 8 | Inject src/index.js when missing | Workspace.jsx same useMemo, hasApp && !indexValid | ✅ |
| 9 | MemoryRouter in Sandpack | Injected index / backend bundle | ✅ |
| 10 | Tailwind CDN for Sandpack | Workspace.jsx styles + externalResources | ✅ |

filesReadyKey + 500ms delay (from later fixes) in Workspace.jsx; Sandpack key={filesReadyKey}.

---

## 3. Pricing & credits (5)

| # | Change | Where | Verified |
|---|--------|------|----------|
| 11 | No credit rollover | TokenCenter, Pricing, server, pricing_plans, docs | ✅ |
| 12 | $0.03/credit linear | server.py custom_addon, checkout, webhook | ✅ |
| 13 | Pricing page alignment | Pricing.jsx grid, min-h, mt-auto | ✅ |
| 14 | TokenCenter rollover removed, 0.03 | TokenCenter.jsx | ✅ |
| 15 | Pricing docs no rollover | PRICING_*.md, COMPREHENSIVE_*.md | ✅ |

---

## 4. Contact & Get Help (6)

| # | Change | Where | Verified |
|---|--------|------|----------|
| 16 | Contact page /contact | frontend/src/pages/Contact.jsx | ✅ |
| 17 | Get Help page /get-help | frontend/src/pages/GetHelp.jsx | ✅ |
| 18 | POST /api/contact + storage | backend/server.py contact_submit, db.contact_submissions | ✅ **Fixed:** table added |
| 19 | Routes /contact, /get-help | frontend/src/App.js | ✅ |
| 20 | Footer links | Layout.jsx, PublicFooter.jsx | ✅ |
| 21 | Pricing "Contact us" | Pricing.jsx Link to /contact | ✅ |

**Fix applied:** `contact_submissions` table did not exist in 001_full_schema.sql or ensure_all_tables. Added to both so contact form no longer 500s.

---

## 5. Enterprise & form styling (3)

| # | Change | Where | Verified |
|---|--------|------|----------|
| 22 | Enterprise old pricing removed | Enterprise.jsx no PLAN_TABLE | ✅ |
| 23 | form-input-public, form-card-public | index.css | ✅ |
| 24 | Enterprise form uses public classes | Enterprise.jsx, Contact.jsx | ✅ |

---

## 6. Theme (3)

| # | Change | Where | Verified |
|---|--------|------|----------|
| 25 | Theme vars Sidebar, Layout, Workspace, TokenCenter, scrollbars | index.css, Sidebar.css, Layout.css, Workspace.css, TokenCenter.css | ✅ |
| 26 | TokenCenter dark overrides | TokenCenter.css [data-theme="dark"] | ✅ |
| 27 | form-input-theme, form-card-theme + public | index.css | ✅ |

---

## 7. Sidebar & layout (7)

| # | Change | Where | Verified |
|---|--------|------|----------|
| 28 | Settings only in Guest dropdown; footer Engine + Credits only | Sidebar.jsx sidebar-bottom, sidebar-account-menu | ✅ |
| 29 | Collapsed: Guest opens account menu (drop-up) | Sidebar.jsx collapsed strip, setAccountMenuOpen | ✅ |
| 30 | Collapsed account menu outside-click close | collapsedAccountRef, useEffect | ✅ |
| 31 | Thin separator 1px border | Sidebar.css border-right var(--theme-border) | ✅ |
| 32 | Collapse button inside sidebar | sidebar-header toggle | ✅ |
| 33 | Collapsed strip icons + tooltips | title attributes on collapsed icons | ✅ |
| 34 | Credits display credit_balance / "—" | Sidebar.jsx user.credit_balance ?? token_balance/1000 | ✅ |

Folder icon: Workspace.jsx imports Folder (line 66); Explorer tree uses it.

---

## 8. Backend connectivity (3)

| # | Change | Where | Verified |
|---|--------|------|----------|
| 35 | Health check → refreshUser() | Layout.jsx checkBackend, token && refreshUser | ✅ |
| 36 | Proxy /api, /health → :8000 | craco.config.js devServer.proxy | ✅ |
| 37 | CRUCIBAI_DEV, run_local.py | server.py, run_local.py | ✅ |

---

## 9. Docker & migrations (4)

| # | Change | Where | Verified |
|---|--------|------|----------|
| 38 | docker-compose.yml | root docker-compose.yml | ✅ |
| 39 | run_migrations on startup | server.py startup, db_pg.run_migrations | ✅ |
| 40 | RUN_LOCAL.md | RUN_LOCAL.md | ✅ |
| 41 | RAILWAY_QUICKSTART.md | RAILWAY_QUICKSTART.md | ✅ |

ensure_all_tables() runs after run_migrations(); includes contact_submissions after fix.

---

## 10. Documentation (5)

| # | Change | Where | Verified |
|---|--------|------|----------|
| 42–46 | BUILD_TYPES_AND_DEPLOY, EXPLORER_WHAT_IS_WHAT, PROOF_SIDEBAR_AND_THEME, RAILWAY_AND_GIT_DEPLOY, RATE_RANK_HONEST | docs/*.md | ✅ |

---

## 11. UX & chat (5)

| # | Change | Where | Verified |
|---|--------|------|----------|
| 47 | Copy/Edit icon-only | Dashboard.jsx | ✅ |
| 48 | Workspace backend error deduplication | Workspace.jsx handleBuild/handleModify catch | ✅ |
| 49 | Mic-denied message | Dashboard.jsx (MIC_DENIED_HELP), Landing, Workspace | ✅ |
| 50 | Voice/attach errors when backend down | Dashboard.jsx, LandingPage.jsx | ✅ |
| 51 | Product-support detection in AI | backend/routers/ai.py | ✅ |

---

## 12. Duplicate arrow (1)

| # | Change | Where | Verified |
|---|--------|------|----------|
| 52 | Single sidebar collapse | Sidebar.jsx (no duplicate ChevronLeft) | ✅ |

---

## 13–14. Git & rate/rank (3)

Push to crucibai, commits, RATE_RANK_HONEST.md — repo state and docs only.

---

## Iterative builder & Explorer (from later work)

- **Workspace** calls `POST /api/ai/build/iterative` when `shouldUseIterative` (token present, not native/image).  
- **Backend** `server.py` has `@api_router.post("/ai/build/iterative")`; uses `iterative_builder.run_iterative_build`.  
- **Explorer** is dynamic: `Object.keys(files).sort()`; folders from path segments; `Folder` icon imported in Workspace.jsx.  
- **DEFAULT_FILES** in Workspace: initial state only; build start does `setFiles({})` so Explorer clears then fills from iterative steps.

---

## Conclusion

All 55 changes are accounted for and wired. The only **bug** found was the missing **contact_submissions** table, which caused the contact form to 500. That is fixed by:

1. Adding `contact_submissions` to `backend/migrations/001_full_schema.sql`
2. Adding it to `REQUIRED_TABLES` and `ENSURE_TABLES_SQL` in `backend/db_pg.py`

After deploy (or local restart), contact form submissions will persist and the rest of the behavior matches the changelog.

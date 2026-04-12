# CrucibAI — Master Single Source of Truth Test

**Purpose:** The strictest verification of the codebase as it exists now. Every item is a pass/fail criterion. No flyby tests; if anything is broken, not connected, or not aligned, the test suite must identify it.

**Reference:** docs/CODEBASE_SOURCE_OF_TRUTH.md, docs/FULL_SCOPE_INVESTOR_ENGINE_ROOM.md, MASTER_TEST_VERIFICATION_PROMPT.md.

---

## 1. ROUTES & CONNECTIVITY

### 1.1 Frontend routes (App.js)

- [ ] Every `<Route path="...">` resolves to a real component (no 404).
- [ ] Public paths: `/`, `/auth`, `/pricing`, `/templates`, `/patterns`, `/learn`, `/docs`, `/documentation`, `/tutorials`, `/shortcuts`, `/prompts`, `/features`, `/enterprise`, `/benchmarks`, `/blog`, `/blog/:slug`, `/privacy`, `/terms`, `/security`, `/aup`, `/dmca`, `/cookies`, `/about` all render.
- [ ] Protected `/app` children: `dashboard`, `tokens`, `workspace`, `builder`, `projects/new`, `projects/:id`, `exports`, `patterns`, `templates`, `prompts`, `learn`, `env`, `shortcuts`, `payments-wizard`, `examples`, `generate`, `agents`, `agents/:id`, `settings`, `audit-log`, `admin`, `admin/users`, `admin/users/:id`, `admin/billing`, `admin/analytics`, `admin/legal` all resolve.
- [ ] Standalone: `/workspace`, `/builder`, `/share/:token` work.

### 1.2 Frontend → Backend API

- [ ] All API calls use the same base: `API` from App.js (env `REACT_APP_BACKEND_URL` or `/api` same-origin).
- [ ] Auth: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` used by AuthPage / AuthProvider.
- [ ] Tokens: `GET /api/tokens/bundles`, `POST /api/tokens/purchase`, `GET /api/tokens/history`, `GET /api/tokens/usage` used by TokenCenter and Pricing (bundles).
- [ ] Build: `GET /api/build/phases`, `POST /api/build/plan` used by Workspace.
- [ ] Projects: `GET /api/projects`, `POST /api/projects`, `GET /api/projects/:id/state`, etc. used by Dashboard, Workspace, AgentMonitor.
- [ ] Stripe: `POST /api/stripe/create-checkout-session` used by TokenCenter for checkout.
- [ ] No hardcoded `localhost:8000` in production code paths (env only).

### 1.3 Backend endpoints (server.py)

- [ ] `/api/health` returns 200 and `status`.
- [ ] `/api/tokens/bundles` returns 200 and `bundles` (with keys e.g. free, light, dev, builder).
- [ ] `/api/auth/register`, `/api/auth/login`, `/api/auth/me` behave as per AuthProvider expectations (token, user).
- [ ] `/api/projects` (GET requires auth 401 without token; POST with auth returns project).
- [ ] `/api/build/phases` returns 200.
- [ ] `/api/agents` returns 200 with `agents`.
- [ ] `/api/templates`, `/api/patterns`, `/api/examples` return 200.

### 1.4 Pricing ↔ Token Center wiring

- [ ] Pricing add-on "Get started" / "Buy" (logged-in) navigates to `/app/tokens` with `state: { addon: key }` (key = light | dev).
- [ ] Pricing add-on (not logged-in) navigates to `/auth?mode=register&redirect=.../app/tokens?addon=<key>`.
- [ ] TokenCenter reads `location.state.addon` or `searchParams.get('addon')` and switches to purchase tab and scrolls/highlights that bundle.
- [ ] Outcome calculator "Select plan" navigates to `/app/tokens` (or auth with redirect) with addon so Token Center shows correct bundle.

---

## 2. CONSISTENCY (TEXT, COLORS, SHELL)

### 2.1 Two-color system (no orange, no stray accents)

- [ ] Global: `--bg-primary` = `#FAFAF8`, `--text-primary` = `#1A1A1A`, `--accent` = `#1A1A1A` in index.css.
- [ ] Marketing/public scope: No `orange`, no `#f97316`, no `orange-*` Tailwind classes in: LandingPage, Pricing, Features, TemplatesPublic, LearnPublic, PromptsPublic, PatternsPublic, AuthPage, PublicNav, PublicFooter, Security, Benchmarks, Enterprise.
- [ ] App shell (Layout, Sidebar): Primary actions and accents use `#1A1A1A` or CSS vars; no orange.
- [ ] Optional (internal tools): Builder, VibeCoding, AdvancedIDEUX, ManusComputer may be relaxed in a later phase; master test can flag them for cleanup.

### 2.2 Same shell for Pricing, Learn, Auth, Templates

- [ ] Pricing, Learn (LearnPublic), Auth (AuthPage), Templates (TemplatesPublic) use: light background (`#FAFAF8` or `bg-kimi-bg`), PublicNav, PublicFooter (or equivalent), light cards (white/stone), no dark/zinc theme for main content.
- [ ] CTAs: primary button style consistent (e.g. `bg-[#1A1A1A] text-white`).

### 2.3 Copy and labels

- [ ] "CrucibAI" spelling consistent in nav and footer.
- [ ] Add-ons description on Pricing: "Light (50 credits, $7) or Dev (250 credits, $30)" or equivalent; no placeholder "Lorem" or "TODO".
- [ ] Token Center: "Add credits" and "Pay with Stripe" buttons present for each bundle.

---

## 3. FUNCTIONALITY (NO BROKEN FLOWS)

### 3.1 Auth

- [ ] Register with email/password returns token and user; login same.
- [ ] ProtectedRoute: unauthenticated user visiting `/app/*` redirects to `/auth` with `state.from`.
- [ ] Auth redirect: `?redirect=` query used after login (e.g. redirect to `/app/tokens?addon=light`).

### 3.2 Tokens & billing

- [ ] TokenCenter fetches bundles from `/api/tokens/bundles` and displays them.
- [ ] TokenCenter "Add credits" calls `POST /api/tokens/purchase` with `{ bundle: key }`.
- [ ] TokenCenter "Pay with Stripe" calls `POST /api/stripe/create-checkout-session` and redirects to Stripe.
- [ ] Pricing page fetches same bundles and shows add-ons (Light, Dev) with correct price and credits.

### 3.3 Build & workspace

- [ ] Workspace build triggered from form submit (not on mount); no double fire.
- [ ] Build completion adds task to task store (if used); sidebar task list reads from store.
- [ ] Layout/sidebar mode (simple vs dev) persisted (useLayoutStore).

### 3.4 Layout & scroll

- [ ] Root: no `overflow: hidden` on `html, body, #root` that would block scroll.
- [ ] Marketing and app pages scroll when content overflows.

---

## 4. COMPETITIVE EDGE & 10/10 READINESS

- [ ] Critical path (auth → projects → build → tokens) is wired end-to-end (no stubs in the flow).
- [ ] Add-ons path (Pricing → Token Center with addon) is wired so "increase your token" works.
- [ ] Public pages (Pricing, Learn, Templates, Features) present a consistent, professional face (two-color, same shell).
- [ ] No critical console errors or missing env that would break production (API base must be resolvable).

---

## 5. TEST IMPLEMENTATION REQUIREMENTS

- [x] Backend: `backend/tests/test_single_source_of_truth.py` — health, tokens/bundles (with light/dev keys), auth register, projects/build/agents/templates/patterns/examples, tokens/history and tokens/usage require auth, tokens/purchase with auth, invalid bundle 400.
- [x] Frontend: `frontend/src/__tests__/SingleSourceOfTruth.test.js` — API definition in App.js, route component files exist, App declares /, /pricing, /app, tokens; Pricing source has state.addon and redirect with addon; TokenCenter source has addonFromPricing from location.state and searchParams.
- [x] E2E: `frontend/e2e/single-source-of-truth.spec.js` — pricing loads and shows Add-ons; addon "Get started" navigates to auth with redirect containing /app/tokens?addon=; unauthenticated /app/tokens redirects; public routes return <500.
- [x] CI: enterprise-tests.yml runs backend pytest (includes test_single_source_of_truth), frontend npm test (includes SingleSourceOfTruth), Playwright critical-user-journey and single-source-of-truth.

---

## 6. CS / QUALITY CHECKS (CUSTOMER SUCCESS & CONSISTENCY)

- [ ] No dead links on public pages (Pricing, Learn, Templates): every href/link targets a valid route or external URL.
- [ ] Forms: Auth register/login have labels and submit buttons; TokenCenter purchase buttons are enabled when bundle is selected.
- [ ] Error handling: AuthProvider clears token on 401 from /auth/me; ErrorBoundary shows message and Reload.
- [ ] Accessibility: primary CTAs and nav links are focusable and have discernible text (no icon-only critical actions without aria-label).

---

**Execution:** Run backend pytest, frontend Jest (master suite), then E2E. Any failure = item not met; fix or document as known gap.

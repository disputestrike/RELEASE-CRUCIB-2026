# CrucibAI — Master Test: 9 Sections, 45 Checks

**Purpose:** Single source of truth for launch. Open `crucibai-production.up.railway.app` (or localhost) in one window and this checklist in another. Go through every item. Every time something fails — screenshot it, note the URL and what you see. No placeholders, no lies; get to the real thing end-to-end.

**Reference:** MASTER_SINGLE_SOURCE_OF_TRUTH_TEST.md, docs/LAUNCH_SEQUENCE_AUDIT.md, docs/LAUNCH_READINESS_PROMPT.md.

---

## Section 1 — Routes & connectivity (10 checks)

| # | Check | Pass? |
|---|--------|-------|
| 1.1 | Every `<Route path="...">` in App.js resolves to a real component (no 404). | |
| 1.2 | Public paths `/`, `/auth`, `/pricing`, `/templates`, `/patterns`, `/learn`, `/docs`, `/documentation`, `/tutorials`, `/shortcuts`, `/prompts`, `/features`, `/enterprise`, `/benchmarks`, `/blog`, `/privacy`, `/terms`, `/security`, `/aup`, `/dmca`, `/cookies`, `/about` all render. | |
| 1.3 | Protected `/app` children (dashboard, tokens, workspace, projects/new, projects/:id, exports, patterns, templates, prompts, learn, env, shortcuts, payments-wizard, examples, generate, agents, settings, audit-log, models, fine-tuning, safety, monitoring, vibecode, ide, admin/*) all resolve when authenticated. | |
| 1.4 | `/workspace` redirects to `/app/workspace`; `/share/:token` works. | |
| 1.5 | All API calls use same base: `API` from App.js (env or `/api` same-origin). No hardcoded localhost in production paths. | |
| 1.6 | Auth: POST /api/auth/register, POST /api/auth/login, GET /api/auth/me used by AuthPage / AuthProvider. | |
| 1.7 | Projects/build: GET /api/projects, POST /api/projects, GET /api/projects/:id/state, build-history, phases, etc. used by Dashboard, Workspace, AgentMonitor. | |
| 1.8 | Tokens/Stripe: GET /api/tokens/bundles, POST /api/tokens/purchase, POST /api/stripe/create-checkout-session used by TokenCenter and Pricing. | |
| 1.9 | Backend: /api/health returns 200; /api/tokens/bundles returns bundles; /api/auth/register, login, me behave as AuthProvider expects. | |
| 1.10 | Pricing add-on "Get started" / "Buy" (logged-in) goes to /app/tokens with state.addon; not logged-in goes to /auth with redirect to /app/tokens?addon=key. TokenCenter reads addon and highlights bundle. | |

---

## Section 2 — Auth & sign up (5 checks)

| # | Check | Pass? |
|---|--------|-------|
| 2.1 | **Sign up page works.** Go to `/auth` — you see the auth form (login by default). | |
| 2.2 | Go to `/auth?mode=register` — you see "Create your account" / sign up form (name, email, password). | |
| 2.3 | Register with email/password returns token and user; redirect to /app or redirect param works. | |
| 2.4 | **Nav shows Sign up and Log in.** Landing nav and PublicNav (on Pricing, Learn, etc.) have "Log in" → /auth and "Sign up" → /auth?mode=register. | |
| 2.5 | When guest session fails (e.g. /app with no backend), fallback screen shows "Sign in" and "Sign up" links to /auth. | |

---

## Section 3 — Consistency (5 checks)

| # | Check | Pass? |
|---|--------|-------|
| 3.1 | Global: primary bg/text and accent use design system (#FAFAF8, #1A1A1A or CSS vars). | |
| 3.2 | Marketing/public pages (Landing, Pricing, Features, TemplatesPublic, LearnPublic, AuthPage, PublicNav, PublicFooter): no stray orange; primary CTAs consistent. | |
| 3.3 | Pricing, Learn, Auth, Templates use same shell: light background, PublicNav, PublicFooter, light cards. | |
| 3.4 | "CrucibAI" spelling consistent in nav and footer. | |
| 3.5 | Pricing add-ons and Token Center: real copy (no "Lorem" or "TODO"); "Add credits" / "Pay with Stripe" present per bundle. | |

---

## Section 4 — Functionality (6 checks)

| # | Check | Pass? |
|---|--------|-------|
| 4.1 | TokenCenter fetches bundles from /api/tokens/bundles and displays them. | |
| 4.2 | TokenCenter "Add credits" / purchase calls POST /api/tokens/purchase with bundle key. | |
| 4.3 | TokenCenter "Pay with Stripe" calls POST /api/stripe/create-checkout-session and redirects to Stripe. | |
| 4.4 | Workspace build is triggered from form submit (not on mount); no double fire. | |
| 4.5 | Layout/sidebar: projects list and task/project navigation work; mode (simple vs dev) persisted where applicable. | |
| 4.6 | Root: no overflow:hidden on html/body/#root that blocks scroll; marketing and app pages scroll when content overflows. | |

---

## Section 5 — Public pages & nav (5 checks)

| # | Check | Pass? |
|---|--------|-------|
| 5.1 | Every public route is reachable: from Landing nav, PublicNav (Features, Pricing, Our Project, Blog, Log in, Sign up), or PublicFooter (About, Product, Resources, Legal). | |
| 5.2 | No dead links on public pages: every href/link on Pricing, Learn, Templates, Features, Auth, footer goes to a valid route or external URL. | |
| 5.3 | /docs, /documentation, /tutorials, /shortcuts, /prompts, /benchmarks, /blog, /security, /enterprise are linked from footer or nav where intended. | |
| 5.4 | Legal: /privacy, /terms, /aup, /dmca, /cookies linked from footer and from Terms/Privacy in-text links. | |
| 5.5 | /our-projects and /auth are in nav; /app and /app/workspace (Get Started) available. | |

---

## Section 6 — Security (4 checks)

| # | Check | Pass? |
|---|--------|-------|
| 6.1 | Auth on protected routes: get_current_user / get_optional_user / AdminRoute as required. | |
| 6.2 | No secrets in client or logs; JWT/ENCRYPTION_KEY from env. | |
| 6.3 | CORS and rate limiting in place; Stripe webhook signature verification. | |
| 6.4 | AuthProvider clears token on 401 from /auth/me; ErrorBoundary shows message and Reload. | |

---

## Section 7 — Critical path & competitive edge (4 checks)

| # | Check | Pass? |
|---|--------|-------|
| 7.1 | Critical path auth → projects → build → tokens is wired end-to-end (no stubs in the flow). | |
| 7.2 | Add-ons path: Pricing → Token Center with addon works so "increase your token" is achievable. | |
| 7.3 | Public pages present a consistent, professional face (two-color, same shell). | |
| 7.4 | No critical console errors or missing env that break production (API base resolvable). | |

---

## Section 8 — Tests & CI (3 checks)

| # | Check | Pass? |
|---|--------|-------|
| 8.1 | Backend: `cd backend && pytest tests -v --tb=short` — critical path tests pass. | |
| 8.2 | Frontend: `cd frontend && npm test -- --watchAll=false` — tests pass. | |
| 8.3 | Security audit run; no critical/high unaddressed (or documented). | |

---

## Section 9 — CS / quality (3 checks)

| # | Check | Pass? |
|---|--------|-------|
| 9.1 | Auth register/login forms have labels and submit buttons; TokenCenter purchase buttons enabled when bundle selected. | |
| 9.2 | Primary CTAs and nav links are focusable and have discernible text (no icon-only critical actions without aria-label). | |
| 9.3 | Error states: auth errors shown; API failures don’t white-screen (ErrorBoundary or inline message). | |

---

## How to use

1. Open the live app (Railway or local) in one window.
2. Open this doc in another.
3. Go through each section and each check. For each: **Pass** or **Fail**.
4. If **Fail:** screenshot, note URL and what you see, and fix (e.g. add nav link for Problem A, fix backend/console for Problem B).
5. When all 45 are pass, the product is at the farthest endpoint we can reach for launch — single source of truth, no placeholders.

**First thing to confirm:** Go to `/auth` and confirm you see the sign up / login page. Sign up page must work before anything else matters.

---

## Problem A / Problem B (from feedback)

- **Problem A — Route exists but nav link missing:** The route works when you open the URL directly, but there is no link in PublicNav or Sidebar. **Fix:** Add the link to PublicNav (public pages) or Sidebar (app pages).
- **Problem B — Page loads but crashes (white screen):** Usually a backend call fails and the page throws. **Fix:** Open browser console (F12 → Console), see the error and the failing request; fix the backend route or add a .catch() so the page renders with a fallback/error message instead of crashing.

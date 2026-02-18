# Brand Implementation — Compliance Crosswalk

**Purpose:** Crosswalk from **BRAND_IMPLEMENTATION_PLAN_INEVITABLE_AI.md** to implementation. Use this to verify every item is implemented and wired. Auth, routes, webhooks, and sign-up flow must remain intact.

**Plan reference:** BRAND_IMPLEMENTATION_PLAN_INEVITABLE_AI.md (final for approval).

---

## Compliance checklist (by phase)

| # | Plan item | File / Route | Verification |
|---|-----------|--------------|---------------|
| **Phase 1** | | | |
| P1.1 | Hero H1 → "Inevitable AI" | `LandingPage.jsx` | Landing hero shows "Inevitable AI" |
| P1.2 | Hero subtext → outcome (Describe your vision. Watch it become inevitable.) | `LandingPage.jsx` | Subtext matches plan |
| P1.3 | NEW badge → "Inevitable AI — 120-agent swarm, 99.2% success, full transparency" (or shorter) | `LandingPage.jsx` | Badge shows 120-agent swarm, no provider names |
| P1.4 | Primary CTA → "Make It Inevitable" | `LandingPage.jsx` | Button text "Make It Inevitable"; still navigates to register/app |
| P1.5 | Proof strip (5 items + "Not promises. Measured.") between hero and input | `LandingPage.jsx` | Section exists: 120-agent swarm, 99.2%, typically under 72 hours, full transparency, minimal supervision |
| P1.6 | "What is CrucibAI?" body: first sentence outcome; 120-agent swarm; full transparency line | `LandingPage.jsx` | Copy updated; no model/provider names |
| P1.7 | "CrucibAI Key Features" → "Why it's inevitable"; subtext; 100 → 120 | `LandingPage.jsx` | Section headline and all "100" → "120" |
| P1.8 | "For Every Need", "How it works", Examples: outcome subtext; 120-agent swarm | `LandingPage.jsx` | Copy updated |
| P1.9 | Better/Faster/Helpful: 120 verifiable agents; optional "Not promises. Measured." | `LandingPage.jsx` | 120 agents; no provider names |
| P1.10 | Footer CTA headline + button; footer tagline | `LandingPage.jsx` | "Make your idea inevitable" or similar; tagline CrucibAI — Inevitable AI |
| P1.11 | Features page: headline "Why your outcome is inevitable"; subtext; Proof strip at top | `Features.jsx` | Headline, subtext, Proof strip (5 items) |
| P1.12 | Features: all 100 → 120; no provider names | `Features.jsx` | No 100; no OpenAI/Claude/Gemini/Together/Nano Banana |
| P1.13 | Accent color #6366F1 | `index.css` | --kimi-accent: #6366F1 |
| P1.14 | Audit: no model or image-provider names on landing, Features, Pricing, FAQ | All public pages | Grep: no OpenAI, Claude, Gemini, Together AI, Nano Banana in user-facing copy |
| **Phase 2** | | | |
| P2.1 | Pricing: one outcome line at top | `Pricing.jsx` | e.g. "Predictable pricing for inevitable outcomes" |
| P2.2 | Enterprise: one outcome line | `Enterprise.jsx` | One line Inevitable AI / 99.2% |
| P2.3 | PublicFooter tagline | `PublicFooter.jsx` | "CrucibAI — Inevitable AI" or "Turn ideas into inevitable outcomes" |
| P2.4 | Document title | `App.js` or index.html | "CrucibAI — Inevitable AI" |
| P2.5 | FAQ: "What is CrucibAI?" answer includes Inevitable AI, 120-agent swarm; "fast" → "reliable" where natural | `LandingPage.jsx` | FAQ answers updated; 120 not 100 |
| P2.6 | App shell: optional "Inevitable AI" in sidebar or title | `Layout.jsx` or App | Optional; document title suffices if no sidebar change |
| **Auth & other pages** | | | |
| A.1 | Auth page: logo "CrucibAI", tagline Inevitable AI | `AuthPage.jsx` | Logo capitalized; accent #6366F1; real proof stats (120, 99.2%, <72 hrs, Full) |
| A.2 | Auth: benefits 120-agent swarm, 99.2%, 50 credits; no 20 agents / 50K projects | `AuthPage.jsx` | Real info only |
| A.3 | About, Features, Learn, Benchmarks, Pricing strip, Nav: Inevitable AI + 120 where relevant | Multiple | About/Features/LearnPublic/Benchmarks/Pricing/PublicNav/Landing nav updated |
| **Phase 3** | | | |
| P3.1 | Optional: backend config for proof stats (brand.json or env) | `backend/` | If implemented: GET /api/brand or env used by frontend for hero/proof |
| P3.2 | Press release / ProductHunt assets | N/A (not in codebase) | Per brand doc |
| **Preserved (must not break)** | | | |
| V.1 | Auth flow: sign up, sign in, redirect | `App.js`, auth routes, backend /auth | Register → redirect; Login → /app or redirect |
| V.2 | Nav: Get started, Sign in, Dashboard, all links | `LandingPage.jsx`, PublicNav | All links work; Get started → auth?mode=register or /app |
| V.3 | Landing input panel: submit → workspace or auth with redirect | `LandingPage.jsx` | startBuild() navigates to workspace or auth with redirect |
| V.4 | Pricing: bundles, add-ons, Stripe, TokenCenter | `Pricing.jsx`, backend /tokens, Stripe webhook | No model names on page; checkout and webhook paths unchanged |
| V.5 | All existing routes (/, /features, /pricing, /app, /app/workspace, etc.) | `App.js` | No routes removed or broken |
| V.6 | Backend routes and webhooks (Stripe, auth, projects, build, etc.) | `server.py` | No changes to route paths or webhook URLs for brand phase |

---

## How to use this crosswalk

1. **During implementation:** For each item P1.x / P2.x, implement in the listed file and tick when done.
2. **After implementation:** Run verification (manual or grep). Ensure V.1–V.6 still pass.
3. **No secret sauce:** Before sign-off, grep public-facing copy for: OpenAI, Claude, Gemini, Together AI, Nano Banana — must be absent (except in code comments or backend config, not in UI copy).

---

## Quick verification commands (after implementation)

```bash
# No provider names in user-facing copy (frontend public pages)
rg -i "OpenAI|Claude|Gemini|Together AI|Nano Banana" frontend/src/pages/LandingPage.jsx frontend/src/pages/Features.jsx frontend/src/pages/Pricing.jsx frontend/src/pages/Enterprise.jsx frontend/src/components/PublicFooter.jsx
# Should return no matches (or only in comments)

# 120 not 100 in landing/features
rg "100 agent|100-agent" frontend/src/pages/LandingPage.jsx frontend/src/pages/Features.jsx
# Should return no matches
```

---

**Last updated:** Page-by-page pass: Auth (logo CrucibAI, real stats 120/99.2%/&lt;72 hrs/Full, benefits 120-agent swarm), About (Inevitable AI, 120-agent), Features/LearnPublic/Benchmarks/Pricing strip/PublicNav/Landing nav (Inevitable AI, 120 where relevant). Routes and auth flow unchanged. Verify with commands below.

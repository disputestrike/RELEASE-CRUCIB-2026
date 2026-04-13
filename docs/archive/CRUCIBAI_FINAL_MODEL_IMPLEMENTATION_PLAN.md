# CrucibAI Final Model — Implementation Plan

**Status:** Review complete. Ready to implement per [FINAL COMPLETE MODEL — LOCKED & READY](#).  
**Codebase reviewed:** Backend (`server.py`, tokens/bundles/Stripe/projects), Frontend (`Pricing.jsx`, `TokenCenter.jsx`, `Workspace.jsx`, `LandingPage.jsx`).

---

## 1. My Understanding (Summary)

| Pillar | Spec | Current state in code |
|--------|------|------------------------|
| **Unit of value** | 1 Credit = 1,000 Haiku tokens (internal). User-facing: credits. | Stored as `token_balance` (raw tokens). UI says "tokens". Bundles in tokens (100K, 500K, …). |
| **Pricing tiers** | Free $0 (25 credits, Cerebras), Starter $12.99 (100), Builder $29.99 (500), Pro $79.99 (2K), Agency $199.99 (10K). Remove Enterprise. | Bundles: starter 100K/$9.99, pro 500K/$49.99, professional 1.2M/$99.99, enterprise 5M/$299.99, unlimited 25M/$999.99. No tier labels (Learners, Solo, etc.). |
| **Add-ons** | Light $7/50 credits, Dev $30/250 credits. No cannibalization of tiers. | No add-on products; only bundle purchase. |
| **Referral** | Any user, 500 credits each (Cerebras), 10/month cap; reward after referee **complete sign-up** (no 24h hold); 30-day expiry. Free/referral credits = **landing pages only** (no full CRUD/SaaS). $0 cost. | No referral system. |
| **Fraud** | Tier 1: email + phone/payment + device fingerprint + IP + disposable email block. Tier 2: 7-day age, 1 build, 24h hold, 3 accounts/IP/day. Tier 3: manual. | None. |
| **Hard caps** | Landing 50, CRUD 100, SaaS 500 credits; server-side auto-cut; Research 2x. | No build-type caps; only MIN_BALANCE_FOR_LLM_CALL (5K tokens) and per-call deduction. |
| **Free tier friction** | Max 3 projects saved; unlimited in-editor temp builds. Upgrade modal on 4th save. | No project limit. No upgrade modal. |
| **Inference** | Free tier + referral credits → Cerebras. Paid → Haiku. | Single path: OpenAI/Anthropic/Gemini (user or server keys). No Cerebras. |
| **Copy** | Outcome-based: "50 credits = 1 landing page". No Enterprise; "Contact Sales". | Token-based; Enterprise tier present. |

---

## 2. How I Will Implement (New Flow)

### 2.1 Data model and conversion

- **Internal rule:** 1 credit = 1,000 Haiku tokens (for cost and caps). Store in DB as **credits** (integer) so we can keep one number for both display and enforcement.
- **Migration:** Add `credit_balance` (integer); backfill from existing `token_balance` as `credit_balance = token_balance // 1000`. Keep `token_balance` for one release if needed, then phase out. New code uses `credit_balance` only.
- **Ledger:** Rename or add `credit_ledger` (or keep `token_ledger` with a `credits` field and `type`: purchase / referral / usage / bonus). Every usage and grant is in credits.
- **User fields:** Keep or add: `plan` (free | starter | builder | pro | agency), `credit_balance`, `referral_code`, `phone_verified_at`, `first_build_completed_at`. Referral credits: optional `credit_expires_at` per ledger row for 30-day expiry.

### 2.2 Credit system (backend)

- **Config:** Constants for tiers: Free 25, Starter 100, Builder 500, Pro 2_000, Agency 10_000 (credits per month or on purchase). Add-ons: Light 50 @ $7, Dev 250 @ $30.
- **Deduction:** On each LLM call (chat, stream, plan, build, generate doc/slides/sheets):
  - Compute cost in **credits** (e.g. `ceil(token_count / 1000)` for Haiku; for Cerebras, 0 credits but still track for limits).
  - If user is free (or using referral-only balance), route to **Cerebras** and deduct 0 (or a free-tier allowance).
  - If user is paid (or has purchased/referred credits), use **Haiku** (or existing chain), deduct credits, enforce **hard cap** by build type (see 2.5).
- **Prepay check:** Replace `MIN_BALANCE_FOR_LLM_CALL` with a minimum **credits** (e.g. 5). Return 402 with message: "Insufficient credits. You have X. Need at least 5 to run a build. Buy more in Credit Center."

### 2.3 Pricing tiers and Stripe

- **Bundles (subscription or one-time):**  
  - **Starter** $12.99 → 100 credits  
  - **Builder** $29.99 → 500 credits  
  - **Pro** $79.99 → 2,000 credits  
  - **Agency** $199.99 → 10,000 credits  
  Remove: enterprise, unlimited (and any $5K-style tier). Add "Contact Sales" CTA where Enterprise was.
- **Stripe:** Create products/prices for these four tiers + add-ons (Light $7, Dev $30). Checkout and webhook: grant **credits** (not raw tokens). Metadata: `credits`, `bundle` or `add_on`.
- **Free tier:** On signup, grant 25 credits (Cerebras-backed). Display "25 credits" and "50 credits = 1 landing page" in UI.

### 2.4 Add-ons

- **Products:** Light 50 credits @ $7; Dev 250 credits @ $30. One-time payment (Stripe one-time).
- **API:** e.g. `POST /credits/purchase-addon` with `add_on: "light" | "dev"`. Webhook credits same as tiers; ledger `type: "addon"`.
- **UI:** TokenCenter → Credit Center: show Add-ons section (Light, Dev) with outcome copy ("~1 landing page", "~2–3 apps").

### 2.5 Hard credit enforcement (server-side)

- **Build-type detection:** From prompt or explicit parameter: `landing` | `crud` | `saas` | `research`.
- **Caps:**
  - Landing: 50 credits max (e.g. 5K input / 8K output tokens → ~50 credits).
  - CRUD: 100 credits max (20K / 25K).
  - SaaS: 500 credits max (50K / 75K).
  - Research: 2× multiplier, max doc size 1M chars, 100K output; hard stop at user’s credit limit.
- **Enforcement:** Before calling LLM, check `user.credit_balance` and build type; compute `max_credits_allowed`; cap request (e.g. max_tokens) so cost ≤ max_credits_allowed. After call, deduct `min(actual_cost, max_credits_allowed)`. If over-run, stop and return message: "This build reached the 50-credit cap. Need more? Add 10 credits for $2" (or link to add-ons).
- **Free/referral credits = landing only:** When the user's spendable balance is **only** from free tier or referral (track via ledger `type`: free | referral), allow **only** build_type = **landing** (and small changes to landing pages). Full end-to-end (CRUD app, SaaS dashboard) **requires paid credits**. If user requests crud/saas/research with only free/referral balance, return 402: "Full apps and SaaS require paid credits. Upgrade or buy add-on credits."
- **User message:** Before starting: "This will cost up to 50 credits. You have 75. Estimated time: 2 minutes. [START BUILD]". Free tier: "Estimated time: 5 minutes."

### 2.6 Free tier: 3 projects saved

- **Definition of “saved”:** Projects in `db.projects` for this user (already persisted). No separate "temporary" table; in-editor-only builds are not inserted into `projects` (or we add a `saved: true` flag and only count `saved === true`).
- **Enforcement:** On `POST /projects` (and any other “save project” path): if `user.plan === "free"` and `count(projects for user) >= 3`, return 403 with structured message: "You've saved 3 projects. Upgrade to Builder to save unlimited projects and get faster builds."
- **Frontend:** When API returns 403 with that message, show **upgrade modal**: "You've saved 3 projects. Upgrade to Builder to save unlimited projects and get faster builds." CTA: "Upgrade to Builder — $29.99/mo" (link to Stripe or pricing).
- **Clarify:** Workspace “builds” that don’t hit POST /projects (e.g. in-editor only) stay unlimited; only **saving** a project counts toward 3.

### 2.7 Cerebras for free tier

- **When to use Cerebras:** User on free plan **or** current balance is referral-only (e.g. ledger shows only referral grants) and no paid balance. Otherwise use Haiku (or existing chain).
- **Free/referral credits = landing only:** Free and referral credits can **only** be used for **landing pages** (and edits thereon). They can **never** be used for full end-to-end CRUD or SaaS builds; those require paid credits. Enforce in 2.5 (build-type check + balance source).
- **Integration:** Add Cerebras API client (e.g. `cerebras-cloud` or REST). Env: `CEREBRAS_API_KEY`. In `_get_model_chain` or a new `_select_inference_provider(user, build_type)`: return `cerebras` for free/referral path, else `haiku` (or existing chain).
- **Cost:** Treat as $0; no credit deduction for Cerebras calls (or deduct from a “free allowance” if you want to limit abuse). Referral rewards are Cerebras-only so cost stays $0.

### 2.8 Referral program (revised — less restrictive)

- **Schema:** `referral_codes` (user_id, code, created_at); `referrals` (referrer_id, referee_id, status: pending | completed, signup_completed_at, referrer_rewarded_at, created_at).
- **Verification:**  
  - **OAuth (Google, etc.):** Treated as **already verified**. Google (and similar) require verified email/phone to create an account — no extra phone or payment step for OAuth signups.  
  - **Email-only signup:** Optional lightweight check (e.g. email verification link) if we keep email signup; no mandatory phone or payment for referral eligibility.
- **Flow:**  
  1. Any user gets a referral link (e.g. `/auth?ref=CODE`).  
  2. Referee completes **complete sign-up** (account created, OAuth or email verified); store `referred_by: code` and `auth_provider: "google" | "email"`.  
  3. **Immediately** on sign-up completion: grant referrer 500 credits (Cerebras) and referee 500 credits (Cerebras). **No 24-hour hold.**  
  4. Both grants with **30-day expiry** (store `credit_expires_at`).  
  5. Cap: max **10 successful referrals per referrer per month** (calendar month).  
- **APIs:** `GET /referrals/code`, `POST /referrals/apply` (at signup), `GET /referrals/stats`. Grant both rewards in the signup flow when referee’s completes sign-up (no first-build step).

- **Free/referral credits = landing only:** Referral (and free tier) credits can **never** be used for full end-to-end builds (CRUD app, SaaS). Only **landing pages** (and small changes thereon). Full apps require **paid** credits (see 2.5).

### 2.9 Fraud prevention (revised — lighter, OAuth-aware)

- **OAuth users (Google, etc.):**  
  - **No extra verification.** Provider already verified identity. No phone, no payment-method check for referral.  
- **Lightweight checks (all users):**  
  - **Device fingerprint** (e.g. Fingerprint.js): store `device_id`; flag if same device creates many accounts (e.g. 5+ in 7 days) for manual review only.  
  - **Disposable email block:** block known disposable domains (10minutemail, guerrillamail, etc.) for **email-only** signup; OAuth bypasses this.  
  - **IP:** optional soft limit (e.g. 5 signups per IP per day) — log and flag, don’t hard-block unless abuse pattern.  
- **Removed:**  
  - No mandatory phone verification for referral (OAuth = verified).  
  - No 24-hour hold.  
  - No 7-day account-age requirement for referrer reward.  
- **Tier 3 (manual):** Review top referrers and obvious abuse (same device/IP, many accounts in short window). No automated blocks beyond disposable email for email signup.

### 2.10 Copy and UX

- **Rename:** All user-facing "tokens" → "credits" (Token Center → Credit Center, "Buy tokens" → "Buy credits", etc.).
- **Outcome-based:** Homepage, pricing, add-ons: "50 credits = 1 landing page", "100 credits = 1 app", "500 credits = 1 SaaS dashboard". Referral: "Invite a friend. You both get 500 credits."
- **Pricing page:** Free 25 credits (Cerebras), then Starter / Builder / Pro / Agency with credits and price. Remove Enterprise; add "Contact Sales". Add outcome bullets.
- **FAQ:** Add SOC2 roadmap; honest “we don’t have Enterprise tier yet; contact for custom.”

### 2.11 LLM stack — keep only 2 (Cerebras + Haiku)

- **Default build path (our economics):** Free tier + referral credits → **Cerebras** only ($0 cost). Paid credits / paid plan → **Haiku** (Anthropic) only (predictable cost per 1,000 tokens).
- **Remove from default flow:** OpenAI, Gemini, and other LLMs are **no longer** in the main build/chat/plan chain. We use **2 providers**: Cerebras (free) and Haiku (paid); margins and caps stay simple.
- **Optional "bring your own key":** Keep Settings → API & Environment for **power users** who add their own OpenAI/Anthropic/Gemini keys. When set, we can optionally use their model for their requests. So: **2 LLMs for our stack**, **optional** extra models via user keys.
- **Code change:** Replace the current multi-model fallback chain with `_select_provider(user)` → Cerebras or Haiku; single path per request. User keys only used if we allow "use my model" in Settings.

### 2.12 Plans and speed in the UI (Manus-style)

- **Backend owns it:** Tiers, provider (Cerebras vs Haiku), speed, and caps are all **backend**. The server decides plan from `user.plan` and balance; selects Cerebras or Haiku; applies priority/speed (e.g. Pro queue &lt;1s). Frontend only displays what the backend returns.
- **In-app plan/agent selector:** Like Manus’s “Manus 1.6 Lite / Pro / Max Pro” dropdown, we show the user’s **current plan** and **speed** in the app (e.g. in Workspace header or Credit Center):
  - **Free (Lite):** “Landing pages only. Cerebras — ~5–8s.”
  - **Starter / Builder (Pro):** “Full apps. Haiku — ~2–4s.”
  - **Pro / Agency (Max Pro):** “Full apps + priority. Haiku — &lt;1s.”
  - Dropdown or badge shows current plan; click can go to Pricing or upgrade.
- **Pricing page:** Like Manus’s pricing — clear **plans** (Free, Starter, Builder, Pro, Agency) with **credits per month**, **speed** (Cerebras vs Haiku, priority for Pro), and outcome bullets (landing, app, SaaS). Optional: monthly/annual toggle, “Get started” per tier. No need to match Manus layout exactly; same idea: plans + credits + speed in one place.

---

## 3. Additional Changes (Dependencies and Risks)

| Area | Change | Notes |
|------|--------|------|
| **Env / secrets** | Add `CEREBRAS_API_KEY`, Fingerprint.js public key (optional). No Twilio required for referral (OAuth = verified). | Cerebras required; Fingerprint.js optional for fraud signals. |
| **Stripe** | New products/prices for Starter/Builder/Pro/Agency + Light/Dev add-ons. | Remove or archive old enterprise/unlimited products. |
| **DB** | Add collections: `referral_codes`, `referrals`, `credit_ledger`; add fields to `users`: `plan`, `credit_balance`, `first_build_completed_at`, `referred_by`, `auth_provider`. No `phone_verified_at` (OAuth = verified). | Index on referral code, referee_id, referrer_id, created_at. |
| **Speed differentiation** | Free: Cerebras 5–8s; Builder: Haiku 2–4s; Pro: Haiku &lt;1s (priority queue). | Optional: queue priority by plan; or just Cerebras vs Haiku latency. |
| **API compatibility** | Existing clients might expect `token_balance` and `tokens`. | Either keep a compatibility field (e.g. `token_balance = credit_balance * 1000`) or version API and document migration. |

---

## 4. Implementation Order (Phases)

| Phase | What | Est. (hours) |
|-------|------|--------------|
| **1** | Credits foundation: DB field + migration, rename in API responses and UI (Token → Credit), internal 1 credit = 1000 tokens | 3–4 |
| **2** | New pricing tiers + Stripe (Starter/Builder/Pro/Agency, remove Enterprise), add-ons (Light $7, Dev $30), webhook grants credits | 4–5 |
| **3** | Cerebras integration: env, client, route free (and referral) traffic to Cerebras | 4 |
| **4** | Hard credit caps: build-type detection, server-side caps (50/100/500), pre-build message and over-run handling | 3 |
| **5** | Free tier 3-project limit: count projects, 403 on 4th save, upgrade modal in frontend | 2 |
| **6** | Referral: schema, code generation, apply at signup; OAuth = verified (no phone); **complete sign-up** triggers immediate grant; 500 each, 10/mo cap, 30-day expiry; free/referral = landing only | 4–5 |
| **7** | Fraud (light): device fingerprint (optional), disposable email block for email signup, IP soft limit; no Twilio, no 24h hold | 2 |
| **8** | Copy and UX: outcome-based copy, Credit Center, Pricing page, FAQ, Contact Sales | 2 |

**Total:** ~34 hours (aligns with your 24-hour checklist spread across 2 sprints).

---

## 5. What I Need From You Before Coding

1. **Confirm conversion:** New users: store only `credit_balance` (no `token_balance`). Existing users: one-time migration `credit_balance = token_balance // 1000` (and optionally keep token_balance for a while). Yes/No?
2. **Stripe:** Should I define product/price IDs in code (e.g. env vars) and you create them in Stripe Dashboard, or do you want a script to create products via Stripe API?
3. **Cerebras:** Exact API (REST URL, model name, auth header) and whether you already have an account.
4. **Referral “first build”:** Reward on referee **complete sign-up** (not first build). Free/referral credits = **landing pages only** (no full CRUD/SaaS). Confirm?
5. **Referral (revised):** Confirm OAuth = verified (no phone), no 24h hold, immediate reward on complete sign-up. Yes? (e.g. “Save project” or auto-save), 5. **Referral (revised):** Confirm OAuth = verified (no phone), no 24h hold, immediate reward on complete sign-up. Yes?
6. **LLM:** Confirm we keep only 2 in default path (Cerebras + Haiku) and remove OpenAI/Gemini from main build flow; optional user keys in Settings. Yes?

Once you confirm these, I’ll implement in the order above.

---

## 6. My thoughts + rate / rank / compare (revised model)

### Why the revisions make sense

- **OAuth = verified:** Google (and similar) require a real account with verified email; many users have 2FA/phone on that account. Requiring a second phone verification for referral is redundant. Treating OAuth signups as verified is standard and keeps referral simple.
- **No 24-hour hold; reward on complete sign-up:** Referrer gets 500 credits as soon as the referee **completes sign-up** (no first-build step). Immediate reward improves sharing and sign-up conversion. 10/month cap still limits abuse.
- **Free/referral = landing only:** Free and referral credits can **never** be used for full end-to-end (CRUD, SaaS)—only **landing pages** and changes thereon. That keeps cost predictable and pushes full builds to paid credits.
- **Lighter fraud:** Device fingerprint + disposable-email block + optional IP soft limit catch most abuse. Tier 3 (manual review) for edge cases is enough; we avoid Twilio cost and complexity.

### Rate / rank / compare — revised approach

| Dimension | Original (restrictive) | Revised (your direction) | Verdict |
|-----------|------------------------|--------------------------|---------|
| **Referral friction** | Phone or payment + 24h hold | OAuth = verified, no phone; reward on **complete sign-up** | **Revised wins** — faster loop, same identity assurance for OAuth. |
| **Fraud robustness** | Tier 1–3, Twilio, 7-day age | OAuth trusted; fingerprint + disposable email + soft IP; manual for abuse | **Revised wins** for UX; 10/mo cap + sign-up only keeps abuse bounded. |
| **Implementation cost** | Twilio, Verify, 24h jobs | No Twilio; simpler flow | **Revised wins** — fewer dependencies, less code. |
| **Risk** | Very low abuse | Slightly higher abuse potential | **Acceptable** — 10/month cap + **landing-only** for free/referral keeps cost bounded; Cerebras $0; full apps require paid. |

**Summary:** Revised referral + fraud is **less restrictive**, **faster to ship**, and **still safe**. We **remove the various LLMs** from the default path and **keep only 2**: **Cerebras** (free) and **Haiku** (paid). User-owned keys in Settings remain optional for power users.

---

## 7. When implemented — how good will this be? Rate, rank, compare

### Rate (1–10, once fully implemented)

| Dimension | Score | Why |
|-----------|-------|-----|
| **Unit economics** | 9 | Cerebras $0 for free/referral; Haiku only for paid; landing-only for free = predictable cost. Margins clear. |
| **Conversion funnel** | 8 | Free 25 credits + landing-only → try without paywall. 3-project limit + “full app needs paid” pushes upgrade. Referral on sign-up = fast viral loop. |
| **Referral design** | 8 | Reward on complete sign-up (no 24h), 500 each, 10/mo cap, 30-day expiry. Low friction; abuse bounded by landing-only + cap. |
| **Pricing clarity** | 9 | Outcome-based (50 = 1 landing, 100 = 1 app, 500 = 1 SaaS). Tiers + add-ons; no enterprise fluff; “Contact Sales” for custom. |
| **Fraud vs UX balance** | 8 | OAuth = verified; light checks (fingerprint, disposable email, IP soft limit). No Twilio/24h; Tier 3 manual. Good trade-off. |
| **Tech simplicity** | 9 | 2 LLMs only (Cerebras + Haiku); single code path; no multi-model fallback. Easy to reason about and operate. |
| **Differentiation** | 8 | Outcome credits + landing-only free + instant referral + Docs/Slides/Sheets + swarm/quality gate. Clear vs generic “tokens” tools. |
| **Implementability** | 7 | ~34h scope; Stripe, Cerebras, ledger, build-type detection. Doable in 2 sprints; migration and “first build” → “complete sign-up” are clear. |

**Overall (model + plan):** **8/10** — strong, coherent product model; implementation is well-scoped and realistic.

### Rank (vs alternatives, once live)

- **vs “tokens only” AI builders:** CrucibAI ranks **higher** — outcome-based credits and landing-only free make value and upgrade path obvious; many others hide cost in opaque token counts.
- **vs no-code platforms (Webflow, Bubble, etc.):** Different lane (AI-first, credit-based). CrucibAI ranks **strong** on speed-to-first-result and viral loop (referral on sign-up); weaker on deep no-code customization until we add more surface area.
- **vs Kimi / Cursor / v0:** CrucibAI aims to rank **#1 on positioning** (we already claim 10/10); post-implementation we back it with a **clear business model** (Cerebras/Haiku, referral, landing-only free) that many don’t articulate. Execution and distribution will determine actual rank.
- **vs “free everything” tools:** CrucibAI ranks **higher on sustainability** — landing-only free + paid for full apps = viable long-term; “free everything” often collapses or gets paywalled later.

### Compare (summary)

| Aspect | This model (implemented) | Typical competitor | Verdict |
|--------|--------------------------|-------------------|---------|
| **Free tier** | 25 credits, landing-only, Cerebras | Often “trial tokens” or time-limited | **Ours** — clear cap, predictable cost, upgrade path. |
| **Referral** | 500 each on complete sign-up, 10/mo, 30-day expiry | Often none or complex verification | **Ours** — simple, fast loop; landing-only limits abuse. |
| **Pricing** | Outcome (landing / app / SaaS) + tiers + add-ons | Token-based or vague “plans” | **Ours** — easier to sell and understand. |
| **Inference** | 2 providers (Cerebras + Haiku) | Many: multiple models, fallbacks | **Ours** — simpler ops and margins. |
| **Full-app access** | Paid only (CRUD/SaaS) | Sometimes all-in-one free | **Ours** — sustainable; free stays landing-only. |

**Bottom line:** When implemented, this will be **very good** — coherent economics, clear differentiation, and a realistic implementation plan. Main levers to make it **great**: execution (reliability, speed), distribution (SEO, referral uptake), and iterating on “landing-only” (e.g. what counts as “small changes”) so free users feel real value without bleeding cost.

### What would make it 10/10

| Dimension | Current gap | What to do to get 10/10 |
|-----------|-------------|-------------------------|
| **Unit economics** | 9 → 10 | Add **usage-based guardrails** (e.g. max tokens per landing build for free) so cost per free user is hard-capped; document “cost per signup” and “LTV by tier” so the model is provably profitable. |
| **Conversion funnel** | 8 → 10 | **One-click upgrade** from Workspace when user hits landing cap or 3-project limit (pre-filled plan, single Stripe click). **In-app referral CTA** after first landing (“Share your page, get 500 credits”). A/B test copy on upgrade modal. |
| **Referral design** | 8 → 10 | **Pre-built share assets** (link + one-line copy + optional image) in Credit Center; **referee onboarding** (short tooltip: “Your 500 credits = landing pages; upgrade for full apps”). Track share rate and signup→first-landing conversion. |
| **Pricing clarity** | 9 → 10 | **Calculator** on Pricing: “I need X landings + Y apps” → recommended tier + price. **Guarantee** line: “50 credits = 1 landing page or we top you up.” |
| **Fraud vs UX** | 8 → 10 | **Automate Tier 3**: dash of “referrals by device/IP” and auto-flag >N same device; one-click “revoke referral credits” for abuse. No extra user friction. |
| **Tech simplicity** | 9 → 10 | **Single env** (one `CRUCIBAI_INFERENCE_MODE` or provider config), **no fallback code path** — only Cerebras or Haiku. Remove every legacy “try OpenAI then Gemini” branch. |
| **Differentiation** | 8 → 10 | **Public differentiator**: “Only AI builder with outcome-based credits + landing-only free + instant referral.” Use it in every headline and comparison. Add **one** killer feature (e.g. “Deploy to Vercel in 1 click” already; add “Clone and remix any public CrucibAI landing” or similar). |
| **Implementability** | 7 → 10 | **Break Phase 1 into 2 PRs**: (1) credits in DB + API only, (2) UI rename Token→Credit. **Stripe products script** (create all products/prices via script, not manual). **Feature flags** for referral and landing-only so you can ship and toggle. |

**Top 3 moves that get you to 10/10 overall**

1. **Conversion:** One-click upgrade from limit modals + in-app referral CTA after first landing. Maximize “free → paid” and “user → referrer” without adding steps.  
2. **Clarity:** Outcome calculator on Pricing + “50 credits = 1 landing or we top you up.” Remove any remaining token-speak; everything in outcomes and credits.  
3. **Execution:** Ship the 2-LLM stack and landing-only enforcement with **no** legacy fallbacks; add a simple referral/abuse dashboard so Tier 3 is one click. Prove the unit economics with real numbers (cost per free user, LTV by tier).

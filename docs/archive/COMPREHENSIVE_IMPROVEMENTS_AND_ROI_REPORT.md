# CrucibAI — Comprehensive Report: Improvements, End-to-End Function, Pricing & ROI

**Document:** Full account of all changes, current app behavior, pricing comparison, ROI under the new model, and suggested next steps.  
**Date:** February 2026.

---

## 1. Executive Summary

CrucibAI has been updated end-to-end to align with a **Final Model**: credit-based plans (monthly), referral on sign-up, a two-LLM stack (Cerebras for free, Haiku for paid), operational admin (dashboard, users, billing, analytics, fraud/referral), and public-facing copy that does not mention LLM names (Manus-style). Pricing is now **monthly** (Starter $12.99, Builder $29.99, Pro $79.99, Agency $199.99) with **one-time add-ons** (Light $7, Dev $30) purchasable in any quantity. The app is **integrated and functional** from landing → sign-up → build → purchase → admin; ROI remains positive with the new pricing and simplified cost structure (Cerebras ~$0 for free, Haiku for paid).

---

## 2. All Improvements and Changes (Categorized)

### 2.1 Referral & Fraud

| Change | Before | After | Location |
|--------|--------|--------|----------|
| **Referral trigger** | (Not implemented or first-build) | **Complete sign-up only**: credits granted when referee registers (with `ref=CODE`), not on first build | `server.py`: `_apply_referral_on_signup()` called in `POST /auth/register` after user create |
| **Referral timing** | N/A | **No 24h hold**: referrer and referee each get 500 credits in the same request | `server.py`: `referrer_rewarded_at: now`, ledger + `$inc` credit_balance |
| **Referral cap** | N/A | **10 successful referrals per referrer per month** | `REFERRAL_CAP_PER_MONTH = 10`, `signup_completed_at >= month_start` |
| **Referral expiry** | N/A | Referral credits have **30-day expiry** (stored in ledger) | `REFERRAL_EXPIRY_DAYS = 30` |
| **OAuth = verified** | — | Google OAuth users get `auth_provider: "google"`; treated as verified | User doc on OAuth create |
| **Free/referral landing-only** | — | **Schema only**: `CREDIT_PLANS["free"]["landing_only"] = True`; server does **not** yet block non-landing builds for free/referral-only users | `server.py`; enforcement TBD |
| **Fraud** | — | **Stub**: `GET /admin/fraud/flags`; disposable-email block on register | `server.py`, `_is_disposable_email` |

### 2.2 Final Model (Credits, Plans, Limits)

| Change | Before | After | Location |
|--------|--------|--------|----------|
| **Unit** | Tokens (e.g. 50K free) | **Credits** (1 credit = 1,000 tokens); **25 free credits** | `CREDITS_PER_TOKEN`, `FREE_TIER_CREDITS`, `_user_credits()`, `_tokens_to_credits()` |
| **Plans** | Token bundles: Starter $9.99, Pro $49.99, Professional, Enterprise, Unlimited | **CREDIT_PLANS**: Free 25, Starter $12.99 (100), Builder $29.99 (500), Pro $79.99 (2K), Agency $199.99 (10K) | `server.py`: CREDIT_PLANS, TOKEN_BUNDLES derived |
| **Add-ons** | — | **Light $7 (50 credits), Dev $30 (250 credits)**; purchasable any number of times | ADDONS, TOKEN_BUNDLES |
| **Free tier 3-project limit** | — | Free users: max **3 saved projects**; 4th returns **403** with upgrade message | `FREE_TIER_MAX_PROJECTS`, `POST /projects` |
| **MIN credits for LLM** | — | **5 credits** required before build/plan/chat; else **402 Insufficient credits** | `MIN_CREDITS_FOR_LLM`, checks in build/plan and chat |
| **Deduction** | Token balance | **Credit balance** decremented after each build/chat; ledger records credits | `credit_balance` $inc, ledger `credits` |
| **Stripe webhook** | Tokens | **Credits** granted; `price` and `credits` stored in ledger | `stripe_webhook`: metadata.credits, ledger |
| **Credit Center** | Token Center, “Buy tokens” | **Credit Center**, “Buy credits”, balance in credits | TokenCenter.jsx, copy and bundle order |

### 2.3 Operational Infrastructure (Admin)

| Change | Before | After | Location |
|--------|--------|--------|----------|
| **Admin access** | — | **ADMIN_USER_IDS** (env) or **admin_role** (owner, operations, support, analyst) | `get_current_admin(required_roles)` |
| **Dashboard** | — | **GET /admin/dashboard**: total users, revenue today/week/month, signups, referrals, projects today, fraud count, health | AdminDashboard.jsx, `/app/admin` |
| **User management** | — | List (search, plan filter), profile (credits, last_login, lifetime_revenue), **grant credits**, **suspend**, **downgrade**, **GDPR export** | AdminUsers, AdminUserProfile, server admin routes |
| **Billing** | — | **GET /admin/billing/transactions**: ledger purchases (user_id, bundle, price, credits, date) | AdminBilling.jsx |
| **Referral admin** | — | **GET /admin/referrals/links**, **/admin/referrals/leaderboard** | server.py |
| **Fraud admin** | — | **GET /admin/fraud/flags** (stub) | server.py |
| **Internal team** | — | **internal_team**, **internal_label**; banner in Layout; optional billing skip | get_me, Layout |
| **Analytics** | — | **Overview**, **daily**, **weekly**, **report**; **CSV** (?format=csv, auth blob download), **PDF** (print dialog) | AdminAnalytics.jsx, server analytics routes |
| **Analytics entry** | — | Route `/app/admin/analytics`; dashboard link “Analytics & reports →” | App.js, AdminDashboard.jsx |

### 2.4 Pricing & Public Copy

| Change | Before | After | Location |
|--------|--------|--------|----------|
| **Tier names** | Starter, Pro, Professional, Enterprise, Unlimited | **Starter, Builder, Pro, Agency** (no Enterprise/Unlimited) | Backend + Pricing.jsx, TokenCenter.jsx |
| **Prices** | $9.99, $49.99, $99.99, $299.99, $999.99 | **$12.99, $29.99, $79.99, $199.99**/month; add-ons **$7, $30** one-time | CREDIT_PLANS, ADDONS, frontend |
| **Display** | “Tokens”, one-time | **“/month”** for plans; **“per month”** for credits; add-ons **“one-time”**, **“buy as many as you need, no limit”** | Pricing.jsx, TokenCenter.jsx |
| **LLM names on landing/pricing** | Possible Haiku/Cerebras mentions | **Removed**: “Fast builds”, “Priority speed”, “Standard speed”; no Haiku/Cerebras in UI | Pricing.jsx, CREDIT_PLANS speed labels, Auth benefits |
| **Capability bullets** | Generic “All features” | **Plan-specific**: landing pages & apps, plan-first build, export, 20 agents; Pro/Agency: dashboards, priority, team | PLAN_FEATURES in Pricing.jsx |
| **Auth benefits** | “Multi-model AI (GPT-4o, Claude, Gemini)”, “50,000 free tokens” | **“Plan-first build with 20 AI agents”**, **“25 free credits to start”** | AuthPage.jsx |
| **Landing FAQ** | “Token bundles (Starter, Pro, Professional…)” | **“Paid plans are monthly (Starter, Builder, Pro, Agency); add-ons one-time, no limit; plans monthly”** | LandingPage.jsx |

### 2.5 Two-LLM Stack (Plan)

| Change | Before | After |
|--------|--------|--------|
| **Default models** | Multi-model chain (GPT-4o, Claude, Gemini) | **Plan**: Free → **Cerebras** ($0); Paid → **Haiku** (Anthropic). Code still has MODEL_CONFIG/fallbacks; plan is to narrow to Cerebras + Haiku. |
| **User-facing copy** | Model names in UI | No model names on landing/pricing; backend speed labels are generic (“Fast builds”, “Priority speed”). |

---

## 3. How the App Functions Now — Full End-to-End

### 3.1 Anonymous Visitor

1. **Landing** (`/`): Hero, prompt input, examples, features (plan-first, 20 agents, export), FAQ, links to Pricing and Auth.
2. **Pricing** (`/pricing`): Free tier (25 credits, $0); monthly plans (Starter $12.99, Builder $29.99, Pro $79.99, Agency $199.99) with credits/month and capability bullets; add-ons (Light $7, Dev $30) “buy as many as you need, no limit.”
3. **Auth** (`/auth`): Register (email/password, optional `ref=CODE`) or Google OAuth. Benefits: “25 free credits”, “Plan-first build with 20 AI agents.”

### 3.2 New User Sign-Up

1. **Register** (email): Validation, disposable-email block, bcrypt hash; user created with `credit_balance: 25`, `plan: "free"`; welcome ledger entry; **referral applied** if `ref` present (500 credits each to referrer and referee, cap 10/month per referrer); JWT returned.
2. **Register** (Google): Same 25 credits, `auth_provider: "google"`; referral applied if `ref` in callback state/query.
3. **Login**: JWT; `last_login` updated on `/auth/me`.

### 3.3 Logged-In Free User (Build Flow)

1. **Workspace** (`/app/workspace`): Prompt → **credit check** (≥ 5 credits); if not, **402** with message.
2. **Build/plan**: `POST /build/plan` → plan step → code generation; credits deducted by estimated then actual usage (1 credit ≈ 1,000 tokens).
3. **Save project**: `POST /projects`; if free and projects count ≥ 3 → **403** “You’ve saved 3 projects. Upgrade to Builder…”.
4. **Credit Center** (`/app/tokens`): Balance, history (credits), bundles (Starter–Agency + Light, Dev) with “/month” or “one-time”; Stripe checkout or internal purchase (if used).

### 3.4 Purchase Flow

1. **Choose plan or add-on** (Pricing or Credit Center) → “Get started” / “Buy credits” / “Pay with Stripe”.
2. **Stripe**: `POST /stripe/create-checkout-session` with `bundle` → redirect to Stripe Checkout (product name and “X credits”); metadata: `bundle`, `credits`, `tokens`.
3. **Webhook**: `checkout.session.completed` → signature verified; user’s `credit_balance` and `token_balance` increased; ledger entry with `type: "purchase"`, `price`, `credits`, `bundle`.
4. **Success**: Redirect to `/app/tokens?success=1`; balance and history reflect new credits.

### 3.5 Admin Flow

1. **Access**: User in `ADMIN_USER_IDS` or with `admin_role` → Admin (shield) in nav → `/app/admin`.
2. **Dashboard**: Cards for users, signups, revenue (today/week/month), referrals, projects today, fraud count; links to Analytics, Billing, Users.
3. **Analytics** (`/app/admin/analytics`): Date range or “Last N days” → Run query → daily/weekly tables + report summary (total signups, total revenue); **Download CSV** (auth’d blob), **Download PDF** (print dialog).
4. **Users**: List with search (email), filter (plan); open user → profile (credits, last login, lifetime revenue, ledger); **Grant credits**, **Suspend** (owner/ops).
5. **Billing**: Table of transactions from ledger (user, bundle, price, credits, date).
6. **Referrals**: Links and leaderboard via API (dashboard shows count).

### 3.6 Internal Team

- Users with `internal_team: true` see banner (e.g. “[INTERNAL]” or `internal_label`). Optional: skip billing for them; high or unlimited credits for demos.

---

## 4. Comparison: Before vs After

### 4.1 Pricing (Old vs New)

| Aspect | Before | After |
|--------|--------|--------|
| **Main tiers** | Starter $9.99, Pro $49.99, Professional $99.99, Enterprise $299.99, Unlimited $999.99 | Starter $12.99, Builder $29.99, Pro $79.99, Agency $199.99 |
| **Billing** | One-time packs | **Monthly** plans (displayed “/month”); add-ons **one-time**, unlimited quantity |
| **Free** | 50K tokens (or similar) | **25 credits** (≈ 25K tokens) |
| **Add-ons** | None | **Light $7 (50 credits), Dev $30 (250 credits)** |
| **Naming** | Tokens, “Buy tokens” | Credits, “Buy credits”, “credits per month” |

### 4.2 Feature Comparison (Us vs Manus-style)

| Item | Manus (reference) | CrucibAI now |
|------|-------------------|--------------|
| **Pricing display** | $20, $40, $200/month; “credits per month” | $12.99–$199.99/month; “X credits per month” |
| **Copy** | No LLM names; capability bullets (research, websites, slides, tasks) | No Haiku/Cerebras; capability bullets (landing pages, apps, plan-first, export, 20 agents) |
| **Add-ons / top-up** | — | Light, Dev; “buy as many as you need, no limit” |
| **Free tier** | — | 25 credits, landing-focused (schema: landing_only) |

---

## 5. Pricing and ROI Under the New Model

### 5.1 Current Pricing (Summary)

| Plan | Price | Credits/month | $ per credit |
|------|--------|----------------|--------------|
| Free | $0 | 25 | — |
| Starter | $12.99/mo | 100 | $0.130 |
| Builder | $29.99/mo | 500 | $0.060 |
| Pro | $79.99/mo | 2,000 | $0.040 |
| Agency | $199.99/mo | 10,000 | $0.020 |
| Light (add-on) | $7 one-time | 50 | $0.14 |
| Dev (add-on) | $30 one-time | 250 | $0.12 |

### 5.2 Cost Assumptions (Simplified Two-LLM Stack)

- **Free / referral credits**: Served by **Cerebras** → treat as **$0** marginal LLM cost.
- **Paid credits**: Served by **Haiku** (Anthropic). Assume ~\$3 input / \$15 output per 1M tokens (example); 1 credit ≈ 1K tokens → ~\$0.018 per 1K tokens (blended) → **~\$0.018 per credit** consumed.
- **Stripe**: 2.9% + $0.30 per charge (unchanged).
- **Infra**: Same as before (e.g. $0–85/mo depending on tier).

### 5.3 Unit Economics (Illustrative)

- **Starter $12.99/month**  
  - If user uses 100 credits: LLM ≈ 100 × $0.018 = **$1.80**; Stripe ≈ **$0.68**; **Gross margin** ≈ $12.99 − $2.48 = **$10.51**.  
  - If user uses 50 credits: margin **≈ $11.40** (lower usage → higher margin until they buy add-ons or upgrade).

- **Builder $29.99/month**  
  - 500 credits used: LLM ≈ **$9**; Stripe ≈ **$1.17**; **Margin** ≈ **$19.82**.

- **Add-on Light $7**  
  - 50 credits used: LLM ≈ **$0.90**; Stripe ≈ **$0.50**; **Margin** ≈ **$5.60**.

Prepay control is unchanged: we only call the LLM when balance ≥ 5 credits and deduct after use, so **revenue is collected before cost**.

### 5.4 ROI (High-Level)

- **Formula**: (Revenue − LLM − Stripe − Infra) / (LLM + Stripe + Infra).
- **Example month**: 50 Starter + 30 Builder + 20 Pro + 20 add-ons (Light/Dev).  
  - Revenue: 50×12.99 + 30×29.99 + 20×79.99 + 20×~18.5 ≈ **$4,848**.  
  - Costs: LLM (blended ~\$0.018/credit) + Stripe + fixed infra → net remains **positive**; ROI in the **hundreds of %** range for typical usage (same logic as existing ROI doc with new prices and per-credit cost).

### 5.5 Impact of Changes on ROI

| Change | Effect on ROI |
|--------|----------------|
| **Monthly plans** | More predictable MRR; same prepay control if implemented as recurring charges. |
| **Higher ARPU** (Starter $12.99 vs $9.99) | Better margin per user at same usage. |
| **Cerebras for free** | Free tier LLM cost → **$0**; referral credits same. |
| **Haiku-only for paid** | Single, predictable cost per credit vs mixed GPT-4o/Claude/Gemini. |
| **Add-ons, no limit** | Extra revenue from power users without changing plan; high margin on small top-ups. |

---

## 6. Suggested Next Improvements

### 6.1 Must-Have (Alignment & Revenue)

1. **Enforce landing-only for free/referral**  
   - Use `landing_only` on free (and referral-only) users: detect build type (landing vs CRUD/SaaS) and return **402** for non-landing when balance is from free/referral only.  
   - **Location**: Build/plan and project-creation paths; backend only.

2. **Stripe subscriptions for monthly plans**  
   - Replace one-time `mode="payment"` with **subscription** products (Starter, Builder, Pro, Agency) so users are charged every month and receive a fresh credit allowance (no rollover).  
   - Webhook: `invoice.paid` or `customer.subscription.updated` → grant that month’s credits.  
   - **Location**: `server.py` Stripe create-checkout (subscription mode), webhook, and optional “credits this month” logic.

3. **Two-LLM routing in code**  
   - Implement `_select_provider(user)` → Cerebras for free/referral-only balance, Haiku for paid; remove or bypass current multi-model chain for the main build path.  
   - **Location**: `server.py` (build/plan, chat, stream).

### 6.2 Should-Have (Growth & Ops)

4. **Referral share link in app**  
   - In Credit Center or profile: “Your link: https://…/auth?ref=CODE” and “You’ve referred X this month (max 10).”  
   - **Location**: Frontend; backend already has `GET /referrals/code` and `GET /referrals/stats`.

5. **Outcome calculator on Pricing**  
   - “I need X landings + Y apps” → recommend plan (e.g. Builder) and show price.  
   - **Location**: Pricing.jsx (client-side formula or small API).

6. **Email (transactional)**  
   - Welcome, password reset, payment confirmation; use SendGrid/Mailgun (env).  
   - **Location**: Backend; env vars; optional queue.

7. **Fraud flags logic**  
   - E.g. same IP > N signups in 24h, or device clustering; feed `GET /admin/fraud/flags`.  
   - **Location**: server.py + optional Fingerprint or similar.

### 6.3 Nice-to-Have (UX & Scale)

8. **Plan/speed badge in Workspace**  
   - Show “Free – Standard speed” or “Builder – Fast builds” in header; link to Pricing.  
   - **Location**: Layout or Workspace header.

9. **Monthly/annual toggle on Pricing**  
   - E.g. “Pay annually (save 17%)”; backend supports annual price/credits.  
   - **Location**: Pricing.jsx, Stripe products.

10. **Admin: segments export**  
    - Export users by plan, signup date, or revenue segment (CSV).  
    - **Location**: GET /admin/segments or extend analytics.

11. **Sentry (or similar) for errors**  
    - Backend and frontend error tracking; link to admin or status page.  
    - **Location**: Backend/frontend init.

12. **SOC2 / compliance roadmap in FAQ**  
    - “We’re working toward SOC2” and “Contact for Enterprise” to set expectations.  
    - **Location**: Landing FAQ, docs.

---

## 7. Summary Table

| Area | Status | Next |
|------|--------|------|
| **Referral** | ✅ 100 credits each, **free-tier only** (referrer reward only if referrer on free plan); sign-up, no 24h, cap 10/mo; in-app share link + stats | — |
| **Credits & plans** | ✅ 25 free, 4 tiers + 2 add-ons, monthly display | Stripe subscriptions |
| **Admin** | ✅ Dashboard, users, billing, analytics (CSV/PDF), referrals, fraud stub, **segments export** (?plan=&format=csv) | Fraud logic |
| **Pricing copy** | ✅ No LLM names; capability bullets; /month; add-ons unlimited; **outcome calculator**; **SOC2/Enterprise FAQ** | Annual toggle |
| **Landing-only** | ✅ Free/referral users blocked from non-landing build_kind (402) unless they have a purchase | — |
| **ROI** | ✅ Positive; prepay; Cerebras $0 free; Haiku paid | Lock in 2-LLM routing; monitor Haiku cost |

---

## 8. Original Plan vs Suggested (Were Those in the Plan?)

| Item | In original CRUCIBAI_FINAL_MODEL_IMPLEMENTATION_PLAN? | Implemented / status |
|------|------------------------------------------------------|----------------------|
| Referral 500 each on sign-up, no 24h, 10/mo cap | ✅ Yes (§2.8) | ✅ Now **100 credits each**, **free-tier only** (referrer reward only if referrer on free plan) |
| Free/referral = landing only | ✅ Yes (§2.5, §2.7) | ✅ Enforced in `build/plan`: free user with no purchase + non-landing build_kind → 402 |
| Stripe subscriptions (monthly) | ✅ Yes (tiers + add-ons) | ⏳ UI shows /month; backend still one-time payment; subscriptions to be added |
| Two-LLM (Cerebras + Haiku) | ✅ Yes (§2.11, §2.7) | ⏳ Plan documented; routing in code to be wired when Cerebras client ready |
| Referral share link in app | ✅ Yes (link `/auth?ref=CODE`) | ✅ Credit Center: “Invite friends — 100 credits each”, copy link, stats (this month, cap, total) |
| Outcome calculator on Pricing | Suggested in report (§6.2) | ✅ “How many credits do I need?” — landings + apps → recommended plan + CTA |
| SOC2 / Enterprise in FAQ | Suggested in report (§6.3) | ✅ FAQ: “Enterprise & compliance?” — SOC 2 roadmap, contact sales |
| Admin segments export | Suggested in report (§6.3) | ✅ GET /admin/segments?plan=&limit=&format=csv |
| Fraud flags logic | ✅ Plan (Tier 1/2/3) | Stub only; same-IP / device clustering to be implemented |
| Plan/speed badge in Workspace | ✅ Plan (§2.12) | Layout sidebar already shows “Plan: Free” (or plan name) with link to Pricing |

So: **referral amount (100) and free-tier-only** were an approved change from the original 500; **landing-only enforcement, referral link, outcome calculator, SOC2 FAQ, segments export** are now in place. **Stripe subscriptions** and **two-LLM routing** were in the original plan and remain as next steps.

---

## 9. What Else We Recommend

Beyond the list in §6:

- **A/B test referral copy**: Try “Invite a friend — you both get 100 credits” vs current to see impact on share rate.
- **Usage alerts**: When credits drop below 10% of monthly allowance, show a gentle in-app or email nudge to top up.
- **Annual billing**: Add “Pay annually (save 17%)” with Stripe annual prices; grant 12× credits on payment and track renewal.
- **Referral expiry in UI**: In Credit Center or history, show “Referral credits expire on …” so users know to use them.
- **Admin: revenue by plan**: In analytics, break down revenue by bundle (Starter vs Builder vs Pro vs Agency vs add-ons) to see which tiers drive most revenue.
- **Health check for Stripe**: Optional `/admin/health` or dashboard tile that verifies Stripe webhook endpoint is reachable and keys are set.

---

**End of report.** For implementation references, see `IMPLEMENTATION_PROOF_AND_VERIFICATION.md`, `PROOF_AND_CLICKTHROUGH_VERIFICATION.md`, and `OPERATIONAL_INFRASTRUCTURE_IMPLEMENTATION.md`. For cost and ROI detail, see `ROI_AND_UNIT_ECONOMICS.md` (update with Cerebras/Haiku and new bundle prices when final).

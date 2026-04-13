# CrucibAI: Operational Infrastructure & Growth Backbone — Implementation

**Source:** [Operational doc](#) (Admin Backend, Team Access, Analytics, User Segments, Email, Billing, Monitoring, Support, LLM Roadmap).  
**Status:** MVP implemented; scale items in build order below.

---

## 1. Build Order (MVP → Scale)

| Phase | Component | Priority | Status | Location |
|-------|-----------|----------|--------|----------|
| **Week 1** | Admin backend (dashboard, user mgmt, roles) | P0 | ✅ Implemented | `server.py` /admin/*, `AdminDashboard.jsx`, `AdminUsers.jsx` |
| **Week 1** | Admin access tiers (owner, operations, support, analyst) | P0 | ✅ Implemented | `admin_role` on user; `get_current_admin(role)` |
| **Week 1** | User actions: grant credits, suspend | P0 | ✅ Implemented | `POST /admin/users/{id}/grant-credits`, `POST /admin/users/{id}/suspend` |
| **Week 2** | Internal team flags (watermark, no billing) | P1 | ✅ Implemented | `internal_team`, `internal_label` on user; optional in API |
| **Week 2** | Analytics engine (dashboard metrics from DB) | P0 | ✅ Implemented | `GET /admin/analytics/overview`, `/admin/analytics/daily` |
| **Week 2** | Email system (transactional) | P0 | Placeholder | Config/env; SendGrid/Mailgun integration later |
| **Week 2** | Monitoring/health (API latency, errors) | P0 | ✅ Partial | `/api/health`; Sentry/DataDog later |
| **Week 3** | Fraud monitoring (flags, review queue) | P0 | ✅ Stub | `GET /admin/fraud/flags`; IP/device clustering later |
| **Week 3** | Referral backend (leaderboard, payout tracking) | P1 | ✅ Implemented | `GET /admin/referrals/leaderboard`, existing referrals APIs |
| **Month 1** | Billing management (transactions, failed payments) | P0 | Stub | Stripe Dashboard + optional `GET /admin/billing/transactions` |
| **Month 1** | Support (tickets, KB) | P1 | Placeholder | External (Zendesk/Intercom) or later |
| **Month 1** | User segmentation (export segments) | P1 | ✅ Stub | `GET /admin/segments` with simple filters |
| **Month 2+** | Cohort analysis, funnel, attribution | P1 | Stub | Analytics endpoints from ledger/projects |
| **Year 2** | LLM roadmap (own infra) | P2 | Doc only | See operational doc Phase 1–3 |

---

## 2. Admin Backend — Implemented

### Access Tiers

- **owner** — Full access (dashboard, users, billing, fraud, analytics, grant/suspend).
- **operations** — User mgmt, billing view, fraud review, support tools; no financial reports or team settings.
- **support** — User search, grant bonus credits (cap configurable), view tickets; no billing/fraud.
- **analyst** — Read-only dashboards, export reports, view user profiles; no actions, no payment details.

Admin user: set `admin_role` on user in DB, or set env `ADMIN_USER_IDS=id1,id2` (comma-separated user IDs). If `admin_role` is set, it takes precedence.

### API Routes

| Method | Path | Description | Role |
|--------|------|-------------|------|
| GET | /api/admin/dashboard | Overview: total users, revenue today/week/month, signups, referrals, projects today, fraud flags stub, health | owner, operations, analyst |
| GET | /api/admin/analytics/overview | Total users, projects today, signups today/week | owner, operations, analyst |
| GET | /api/admin/analytics/daily | Daily: signups, revenue, paid cumulative. `?format=csv` for CSV export | owner, operations, analyst |
| GET | /api/admin/analytics/weekly | Weekly: signups and revenue per week (last N weeks) | owner, operations, analyst |
| GET | /api/admin/users | List users: search (email), filter (plan) | owner, operations, support, analyst |
| GET | /api/admin/users/{user_id} | Profile: signup, tier, credits, last_login, lifetime_revenue, projects count, referral history, recent ledger | owner, operations, support, analyst |
| GET | /api/admin/users/{user_id}/export | GDPR export: user + ledger + project ids (owner/operations) | owner, operations |
| POST | /api/admin/users/{user_id}/grant-credits | Grant bonus credits (body: credits, reason) | owner, operations, support |
| POST | /api/admin/users/{user_id}/suspend | Suspend account (body: reason) | owner, operations |
| POST | /api/admin/users/{user_id}/downgrade | Set plan to free (e.g. chargeback) | owner, operations |
| GET | /api/admin/billing/transactions | List purchases (user_id, bundle, price, credits, date) from ledger | owner, operations |
| GET | /api/admin/fraud/flags | High-risk accounts (stub) | owner, operations |
| GET | /api/admin/referrals/links | All referral codes with use count | owner, operations, analyst |
| GET | /api/admin/referrals/leaderboard | Top referrers | owner, operations, analyst |

### Frontend

- **Routes:** `/app/admin`, `/app/admin/users`, `/app/admin/users/:id`, `/app/admin/billing`. Shown in Layout only if `user.admin_role` is set (Admin link).
- **AdminDashboard:** Cards for total users, signups today/7d, referrals, projects today, revenue today/7d/30d, fraud flags; link to Users and Billing.
- **AdminUsers:** Table (email, plan, credits, created); search by email, filter by plan; View → profile.
- **AdminUserProfile:** Balance & plan (credits, plan, created, last login, lifetime revenue), Activity (projects, referrals), recent ledger, Grant credits, Suspend (owner/ops), Downgrade not in UI (API only).
- **AdminBilling:** Table of transactions (user_id, bundle, credits, amount, date) from `GET /admin/billing/transactions`.

---

## 3. Internal Team Access — Implemented

- **User fields:** `internal_team: true`, optional `internal_label` (e.g. `"INTERNAL"`, `"Demo"`). Set in DB for team accounts.
- **Billing:** Internal accounts can be excluded from Stripe (no billing); backend can skip charge for `internal_team` users.
- **Watermark:** Layout shows a banner when `user.internal_team` is true: `{internal_label || '[INTERNAL]'} — Internal use only`.
- **Credits:** Team accounts can have high credit_balance or unlimited (e.g. 999999); Cerebras for $0 cost.

---

## 4. Analytics Engine — Implemented (Core)

- **Overview:** Total users, projects created today, signups today/this week, referral count (from `referrals` collection).
- **Daily:** Signups per day (from `users.created_at`), revenue from `token_ledger` (type=purchase, sum price or credits), free vs paid counts.
- **Cohort/funnel:** Not yet; can be added by grouping users by `created_at` week and joining with ledger/projects.

---

## 5. Fraud & Security — Implemented (Stub)

- **Disposable email block:** Already in `server.py` (`_is_disposable_email`); used on register.
- **GET /admin/fraud/flags:** Returns list of suspicious accounts (e.g. same IP > N signups in 24h); optional manual review queue later.
- **Suspend:** `POST /admin/users/{id}/suspend` sets `suspended: true`, `suspended_at`, `suspended_reason`; auth middleware can reject suspended users.

---

## 6. Email, Monitoring, Support — Placeholder

- **Email:** Env vars `SENDGRID_API_KEY` or `MAILGUN_*`; send transactional (welcome, password reset, payment confirm) in code paths; templates TBD.
- **Monitoring:** `/api/health` exists; add latency metric and error tracking (Sentry) in deployment.
- **Support:** Use external tool (Zendesk, Intercom) or add `support_tickets` collection and simple UI later.

---

## 7. Billing & Payments — Existing + Optional Admin

- Stripe: checkout session, webhook (grant credits + store price in ledger) implemented.
- **GET /admin/billing/transactions:** Implemented; list from `token_ledger` where type=purchase (user_id, bundle, price, credits, created_at). Owner/operations only.

---

## 8. Verification

- **Admin:** Log in as user with `admin_role: "owner"` (or in ADMIN_USER_IDS), open `/app/admin` → dashboard; `/app/admin/users` → list; grant credits / suspend from profile.
- **Analytics:** GET `/api/admin/analytics/overview` and `/api/admin/analytics/daily` return 200 with counts.
- **Security:** Non-admin users get 403 on all `/api/admin/*` routes.

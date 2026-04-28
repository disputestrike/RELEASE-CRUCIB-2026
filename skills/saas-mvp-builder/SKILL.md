---
name: saas-mvp-builder
description: Build a complete SaaS product MVP with authentication, Stripe subscription billing, user dashboard, admin panel, and multi-tenant architecture. Use when the user wants to launch a SaaS, build a subscription product, create a paid software service, or needs Stripe billing integrated. Triggers on phrases like "build a SaaS", "create a subscription product", "I need Stripe billing", "build an MVP with subscriptions", "build a paid app".
metadata:
  version: '1.0'
  category: build
  icon: 📊
  color: '#f59e0b'
---

# SaaS MVP Builder

> **PAYMENT RULE**: All generated SaaS apps use **Stripe** as the default payment integration
> (Checkout, Billing, Customer Portal, Webhooks). Never implement Braintree unless the user
> explicitly names Braintree in their prompt. This is enforced by the Build Integrity Validator.

## When to Use This Skill

Apply this skill when the user wants to build a subscription-based software product:

- "Build a SaaS product for X"
- "Create a subscription app with Stripe"
- "I need an MVP with billing and user management"
- "Build a paid tool that does Y"
- Any request for a SaaS, subscription product, or paid software service

## What This Skill Builds

A production-ready SaaS MVP:

**Authentication & Users**
- Email/password registration and login
- OAuth (Google) via Passport.js or NextAuth
- Email verification flow
- Password reset via email
- JWT sessions with refresh tokens
- User profile page

**Subscription Billing (Stripe)**
- Stripe Checkout integration
- 3-tier pricing (Free, Pro, Enterprise)
- Monthly and annual billing toggle
- Stripe Customer Portal (self-service billing)
- Webhook handler for subscription lifecycle events
- Credit/usage tracking per user
- Upgrade/downgrade flows
- Invoice history

**User Dashboard**
- Welcome screen with onboarding checklist
- Sidebar navigation with active plan indicator
- Usage metrics and limits display
- Feature gating based on plan tier
- Settings (profile, billing, notifications, security)

**Admin Panel**
- User management table (search, filter, suspend)
- Subscription overview (MRR, churn, active users)
- Usage analytics charts
- Impersonation mode (for support)

**Multi-tenant Architecture**
- Organization/team support
- Member invitations via email
- Role-based access (owner, admin, member, viewer)
- Per-org usage tracking

**Infrastructure**
- PostgreSQL schema (users, organizations, subscriptions, usage)
- Redis for session storage and rate limiting
- Email service (Resend/Nodemailer templates)
- Stripe webhook handling
- docker-compose for local dev
- CI/CD pipeline

## Instructions

1. **Define the SaaS** — extract the core value proposition, what users pay for, the 3 pricing tiers and their limits

2. **Generate pricing structure** — show Free/Pro/Enterprise with specific feature gates before coding

3. **Build in 6 passes**:
   - Pass 1: Config, types, Stripe setup, DB schema
   - Pass 2: Auth (register, login, verify, reset password)
   - Pass 3: Billing UI (pricing page, checkout, portal)
   - Pass 4: User dashboard + feature pages
   - Pass 5: Backend API (auth routes, billing webhooks, feature APIs)
   - Pass 6: Admin panel + README + env vars

4. **Stripe integration rules**:
   - Always use Stripe Checkout (not custom payment form)
   - Webhook endpoint must verify Stripe signature
   - Store Stripe customer ID and subscription ID in DB
   - Feature gates check subscription status from DB, not Stripe API on every request

5. **Code must include**:
   - `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET` in .env.example
   - Complete webhook handler for: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`

## Example Input → Output

Input: "Build a SaaS for managing client feedback — businesses collect and analyze product feedback, with AI summaries on the Pro plan"

Output includes:
- Pricing: Free (50 responses/mo), Pro ($29/mo, unlimited + AI), Enterprise (custom)
- `/src/pages/Pricing.tsx` — plan cards with annual toggle
- `/src/pages/Dashboard.tsx` — feedback inbox, response stats, AI summary (Pro gate)
- `/server/routes/billing.ts` — Stripe checkout + webhook + portal
- `/database/schema.sql` — organizations, subscriptions, feedback, responses

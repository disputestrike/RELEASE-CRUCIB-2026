# Pricing Review and Sustainability

**Purpose:** Review current pricing and cost structure so we stay profitable and can afford our AI/ops costs (including LLM usage) while delivering value. Adjust if needed.

**Last updated:** February 2026

---

## 1. Current pricing (from product)

| Plan | Credits (approx) | Price (monthly) | Notes |
|------|-------------------|------------------|--------|
| **Starter** | 100 | $12.99 | Landing pages & simple apps |
| **Builder** | 500 | $29.99 | Full web apps, 120-agent swarm, templates |
| **Pro** | 2,000 | $79.99 | Dashboards, priority speed |
| **Agency** | 10,000 | $199.99 | High-volume, team-ready |
| **Add-ons** | Light 50, Dev 250 | $7, $30 | Extra credits |

- Credits are consumed by **builds** (orchestration, agents) and **user agent runs** (automation).
- Backend can enforce 402 when insufficient credits; TokenCenter and purchase flow are wired.
- Stripe: checkout session and webhook for checkout.session.completed; tokens added to user.

---

## 2. Cost drivers we need to afford

| Driver | Notes |
|--------|--------|
| **LLM API (OpenAI, Anthropic, etc.)** | Per build and per agent run; scales with prompt size, model, and usage. |
| **Infra** | Hosting (Railway, etc.), DB (MongoDB), optional workers. |
| **Support and ops** | Time spent on support, security, incident response. |
| **Compliance and legal** | Privacy, terms, security page, incident response — already in place. |

We do **not** expose “cost per token” or model names on the public pricing page (Manus-style); we sell outcomes (credits, builds, automations).

---

## 3. Do we need to adjust pricing?

- **If unit economics are tight:** Consider (a) slightly higher prices on Pro/Agency, (b) add-on packs for heavy users, (c) enterprise custom pricing for very high volume.
- **If we are generous:** Current tiers may be fine; monitor usage vs. LLM cost per user. Use **TokenCenter** and backend usage/credits data to see consumption.
- **Recommendation:** Keep current structure; track **credits consumed per plan** and **LLM cost per credit** (or per build/run). If margin is thin, first adjust add-ons or introduce a “high volume” add-on before changing core plan prices. Revisit after external pentest and any new features (e.g. more agent types) that increase cost.

---

## 4. Profitability and “can we afford it?”

- **Revenue:** Recurring from Starter/Builder/Pro/Agency + add-ons; one-time or custom for Enterprise.
- **Costs:** LLM (variable), infra (relatively fixed), people (fixed).
- **To stay profitable:** (Revenue per user − LLM cost per user − allocated infra/support) > 0 at scale. Use admin **billing** and **analytics** to monitor; adjust pricing or credit allocation if needed.
- **No change to pricing is recommended in this doc** without real usage data; this is a framework for review. Revisit quarterly or when adding major cost-heavy features.

---

## 5. Where pricing lives in the product

- **Frontend:** `frontend/src/pages/Pricing.jsx` — plans, outcome calculator, link to TokenCenter and checkout.
- **Backend:** Token bundles and purchase flow; Stripe create-checkout-session and webhook. Bundle definitions can be driven by env or DB for flexibility.
- **Admin:** Admin Billing (and Analytics) for tracking revenue and usage.

If we need to change amounts or tiers, update the backend bundle source (e.g. tokens/bundles response) and keep Pricing.jsx in sync, or drive everything from backend so one source of truth controls displayed and enforced pricing.

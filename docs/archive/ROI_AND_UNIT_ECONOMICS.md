# CrucibAI – ROI, Revenue & Cost

**Purpose:** How we make money, what it costs, and how that drives ROI. Includes CrucibAI (main product) and Prompt Library (PL) as a usage driver.

---

## 1. How we make money (revenue)

| Source | Description | Price / model |
|--------|-------------|----------------|
| **Token bundles** | Users buy token packs to run builds. No subscription; pay per pack. | See table below |
| **Stripe** | Checkout for token purchase; we receive payment, then add tokens to the user. | Per bundle |
| **Free tier** | 50K welcome tokens (lead gen); converts to paid when they run out. | $0 → then paid |

### Token bundle pricing (revenue per sale)

| Bundle | Tokens | Price | $ per 1K tokens |
|--------|--------|-------|------------------|
| Starter | 100,000 | $9.99 | $0.0999 |
| Pro | 500,000 | $49.99 | $0.1000 |
| Professional | 1,200,000 | $99.99 | $0.0833 |
| Enterprise | 5,000,000 | $299.99 | $0.0600 |
| Unlimited | 25,000,000 | $999.99 | $0.0400 |

- **Revenue per customer** = sum of bundle purchases (one-time or repeat).
- **Prompt Library (PL)** does not have a separate price; it drives **usage** (token consumption), which depletes balance and encourages buying more tokens. So PL supports revenue indirectly.

---

## 2. What it costs (real-world pricing, researched)

### 2.1 LLM API – what providers charge us (per 1M tokens)

CrucibAI uses **OpenAI gpt-4o**, **Anthropic Claude Sonnet 4.5**, and **Google Gemini 2.5 Flash** (model chain in code). Here is what **they charge us** (input / output):

| Provider | Model | Input (per 1M tokens) | Output (per 1M tokens) | Source |
|----------|--------|------------------------|-------------------------|--------|
| **OpenAI** | GPT-4o | $2.50 | $10.00 | [OpenAI Pricing](https://platform.openai.com/docs/pricing), [GPT-4o pricing guides](https://langcopilot.com/llm-pricing/openai/gpt-4o) |
| **Anthropic** | Claude Sonnet 4.5 | $3.00 | $15.00 | [Anthropic API pricing](https://www.metacto.com/blogs/anthropic-api-pricing-a-full-breakdown-of-costs-and-integration), [Finout](https://www.finout.io/blog/anthropic-api-pricing) |
| **Google** | Gemini 2.5 Flash | $0.30 | $2.50 | [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing), [Metacto](https://www.metacto.com/blogs/the-true-cost-of-google-gemini-a-guide-to-api-pricing-and-integration) |

**Cost to us per 100K tokens (typical build: mix of input + output):**

- **GPT-4o** (e.g. 50K in + 50K out): (0.05 × $2.50) + (0.05 × $10) = **$0.625** per 100K tokens.
- **Claude Sonnet 4.5** (50K in + 50K out): (0.05 × $3) + (0.05 × $15) = **$0.90** per 100K tokens.
- **Gemini 2.5 Flash** (50K in + 50K out): (0.05 × $0.30) + (0.05 × $2.50) = **$0.14** per 100K tokens.

So **token cost to us** is about **$0.14–$0.90 per 100K tokens** depending on which model answers. A single “build” that uses ~100K tokens costs us roughly **$0.15–$0.90** in LLM spend.

### 2.2 Stripe – what they charge us

| Item | Rate | Source |
|------|------|--------|
| **Domestic card** | **2.9% + $0.30** per successful charge | [Stripe pricing](https://stripe.com/pricing), [Swipesum 2025 guide](https://swipesum.com/insights/guide-to-stripe-fees-rates-for-2025) |
| International card | 3.1% + $0.30 + 1.5% cross-border | Same |
| ACH | 0.8% (cap $5) | Same |

**Example:** A $9.99 Starter sale → Stripe fee = (0.029 × 9.99) + 0.30 ≈ **$0.59**. A $99.99 Professional sale → **$3.20**.

### 2.3 Infrastructure – what we pay for hosting and DB

| Service | What we use | Real-world cost | Source |
|---------|-------------|------------------|--------|
| **MongoDB Atlas** | M0 (free) or M10/small paid | **$0** (M0 free forever) or **~$57/mo** (dedicated small tier) | [MongoDB Atlas](https://www.mongodb.com/pricing), [M0 free tier](https://www.mongodb.com/docs/atlas/tutorial/deploy-free-tier-cluster/) |
| **Backend hosting** (Railway / Render / Fly.io) | 1 small app | **$0–5/mo** (Fly free under $5; Railway **$5** Hobby min) | [Railway](https://railway.app/pricing), [Fly.io](https://fly.io/docs/about/pricing/), [Ritza comparison](https://ritza.co/articles/gen-articles/cloud-hosting-providers/fly-io-vs-railway/) |
| **Frontend** (Vercel / Netlify) | Static + API proxy | **$0** (free tier) or **$20/mo** Pro | Common practice |

**Typical infra total:** **$0/mo** (M0 + Fly free tier + Vercel free) or **~$60–85/mo** (M10 + Railway $5–20 + optional Pro frontend).

### 2.4 Total cost per 100K tokens (to us)

| Cost type | Amount (per 100K tokens or per sale) |
|-----------|--------------------------------------|
| LLM (blended, e.g. 50% GPT-4o / 50% Gemini) | ~$0.38 per 100K tokens |
| Stripe (on $9.99 Starter) | ~$0.59 per transaction |
| Infra (monthly, amortized per 100 sales) | ~$0.50–$0.85 per sale if $50–85/mo |

So for one **Starter pack** ($9.99): if the user consumes **100K tokens**, we pay about **$0.38** (LLM) + **$0.59** (Stripe) = **$0.97** in variable cost; infra is fixed. **Gross margin on that sale** ≈ $9.99 − $0.97 = **$9.02** (before fixed infra).

---

## 3. Unit economics (real numbers)

- **We sell** 100K tokens for **$9.99** (Starter).
- **We pay** roughly **$0.38** (LLM) + **$0.59** (Stripe) = **$0.97** variable cost per 100K tokens sold and used.
- **Gross margin** ≈ **$9.02** per Starter pack (variable only).
- **We make money** when: **Revenue (bundle price × sales) > LLM cost (tokens consumed × provider rate) + Stripe fees + infra.**

If a user buys a Starter pack and uses only 50K tokens, we pay ~$0.19 LLM + $0.59 Stripe = $0.78; margin ≈ **$9.21**. If they use the full 100K, margin ≈ **$9.02**. If they use 200K (e.g. two full builds), we pay ~$0.76 LLM + $0.59 = $1.35; we still only got $9.99 so margin drops to **$8.64** — so **heavy users who don’t repurchase** are less profitable until they buy the next pack.

---

## 4. ROI (return on investment)

- **ROI** = (Gain − Cost) / Cost. **Gain** = revenue from token sales. **Cost** = LLM + Stripe + infra (+ any fixed costs).

**Example (real-world numbers):**

- **Month:** 100 Starter packs sold → revenue **$999**.
- **LLM:** 100 × 100K tokens at blended ~$0.38/100K = **$38**.
- **Stripe:** 100 × $0.59 ≈ **$59**.
- **Infra:** **$57** (MongoDB M10) + **$5** (Railway) = **$62**.
- **Total cost** = $38 + $59 + $62 = **$159**.
- **Net** = $999 − $159 = **$840**.
- **ROI** (on that month’s cost) = $840 / $159 ≈ **528%**.

Real ROI will vary with mix of bundles, actual token consumption, and which models (GPT-4o vs Gemini) serve the requests.

---

## 5. Is it profitable? Do we have control?

**Yes.** With the real-world costs above:

- **Per sale:** You keep ~**$9** on a $9.99 Starter pack after LLM + Stripe. Larger packs have even better margin per token.
- **At scale:** In the 100-Starter example, you net **$840** on **$159** cost. Unit economics are profitable.

**Prepay control (how companies do it):** Users **prepay** by buying token packs; their balance is credited. We **never call the LLM** unless their balance is at least a minimum (e.g. 5,000 tokens). So they cannot burn more than they have: the backend checks balance **before** calling OpenAI/Anthropic/Gemini and returns **402 Insufficient tokens** if they’re below the threshold. After the call we deduct actual usage (capped at their balance). So we have full control: no “run now, pay later” — they must have tokens before we spend on the API.

---

## 6. Run and proof (how to verify the stack)

To confirm backend and routes (including tokens/billing) work before thinking about real revenue:

```powershell
.\run-and-proof.ps1
```

This:

1. Starts the backend (if needed).
2. Runs `proof_full_routes.py` (hits API routes).
3. Runs `proof_agents.py` (agent endpoints).

If both pass, the **money path** (auth → tokens/bundles → purchase) is wired; then you can plug in live Stripe and track real revenue vs cost.

---

## 7. Summary table (make money vs cost)

| | CrucibAI (main) | Prompt Library (PL) |
|--|------------------|----------------------|
| **Make money** | Token bundle sales (Starter → Unlimited) via Stripe. | No direct price; increases token usage → more pack purchases. |
| **Cost** | LLM API (per token), Stripe fees, infra. | Same LLM cost when users run prompts from PL. |
| **ROI** | Positive if (revenue from packs) > (LLM + Stripe + infra). | Improves ROI by driving usage and repeat purchases. |

---

---

## 8. Sources (real-world pricing)

| Topic | Source |
|-------|--------|
| OpenAI GPT-4o | [OpenAI API Pricing](https://openai.com/api/pricing/), [platform.openai.com/docs/pricing](https://platform.openai.com/docs/pricing), [GPT-4o pricing (LangCopilot)](https://langcopilot.com/llm-pricing/openai/gpt-4o) |
| Anthropic Claude | [Anthropic API pricing (Metacto)](https://www.metacto.com/blogs/anthropic-api-pricing-a-full-breakdown-of-costs-and-integration), [Finout](https://www.finout.io/blog/anthropic-api-pricing) |
| Google Gemini | [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing), [Metacto Gemini guide](https://www.metacto.com/blogs/the-true-cost-of-google-gemini-a-guide-to-api-pricing-and-integration) |
| Stripe | [Stripe pricing](https://stripe.com/pricing), [Swipesum Stripe fees 2025](https://swipesum.com/insights/guide-to-stripe-fees-rates-for-2025) |
| MongoDB Atlas | [MongoDB pricing](https://www.mongodb.com/pricing), [M0 free tier](https://www.mongodb.com/docs/atlas/tutorial/deploy-free-tier-cluster/) |
| Hosting | [Railway pricing](https://railway.app/pricing), [Fly.io pricing](https://fly.io/docs/about/pricing/), [Fly vs Railway 2025](https://ritza.co/articles/gen-articles/cloud-hosting-providers/fly-io-vs-railway/) |

**Last updated:** Researched real-world rates (2024–2025). Re-check provider pricing pages periodically; they change.

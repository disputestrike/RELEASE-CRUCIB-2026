# CrucibAI — Linear Pricing Implementation Plan (Approved)

This plan implements the final approved pricing: **linear $0.06/credit**, **Free separate (one up)**, **four paid tiers (four down)**, **slider add-ons**, **speed selector removed**, and **outcome-focused messaging**.

---

## 1. Pricing structure (source of truth)

### Tiers

| Tier   | Price | Credits | Notes |
|--------|--------|---------|--------|
| Free   | $0    | 100     | Not in TOKEN_BUNDLES (no purchase). Shown only on pricing page. |
| Builder| $15   | 250     | $0.06/credit |
| Pro    | $30   | 500     | $0.06/credit |
| Scale  | $60   | 1,000   | $0.06/credit |
| Teams  | $150  | 2,500   | $0.06/credit |

**Starter is removed.** No volume discounts; same rate everywhere.

### Add-ons (slider)

- **Range:** 100 – 5,000 credits.
- **Price:** `credits × $0.06` (e.g. 100 → $6, 250 → $15, 500 → $30, 1,000 → $60, 2,500 → $150, 5,000 → $300).
- **Delivery:** One-time top-up. No fixed “Light”/“Dev” bundles.

### Internal only (not on public pages)

- 1 credit = 1,000 tokens.
- Cost per credit ~$0.012; revenue $0.06 → ~80% margin.
- No token math, no “92% margin,” no model names on pricing page.

---

## 2. Outcome-focused messaging (what users see)

### By tier (no speed wording)

- **Free:** “100 credits · Landing pages · Plan-first build & live preview · Export to ZIP & GitHub · 120-agent swarm, templates”
- **Builder:** “250 credits · Landing pages & full web apps · Swarm enabled · Plan-first build & preview · Export to ZIP & GitHub”
- **Pro:** “500 credits · Full web apps + automations · Up to 120 agents in parallel · Priority support · Export & deploy anywhere”
- **Scale:** “1,000 credits · Everything in Pro · High-volume builds”
- **Teams:** “2,500 credits · For teams & agencies · Priority support & deployment”

**Outcome anchors (keep):**

- ~50 credits ≈ 1 landing page  
- ~100 credits ≈ 1 full app  

**Trust line (add):**

- “Cost preview before running · Auto-refund on failures.”

**Remove from public:**

- Any “Lite / Pro / Max” or speed-tier wording.
- “1 credit ≈ 1,000 tokens.”
- “92% margin.”
- “Half the price of Lovable” (or make secondary).
- Model names (Haiku, Cerebras, etc.) on pricing.

---

## 3. Backend changes

### 3.1 `server.py` — pricing constants

- **CREDIT_PLANS:** Replace with:
  - `free`: 100 credits, $0, name "Free", speed_tiers `["lite"]`, swarm False.
  - `builder`: 250 credits, 15, name "Builder", speed_tiers `["lite","pro"]`, swarm True.
  - `pro`: 500 credits, 30, name "Pro", speed_tiers `["lite","pro","max"]`, swarm True, max_swarm True.
  - `scale`: 1,000 credits, 60, name "Scale", speed_tiers `["lite","pro","max"]`, swarm True, max_swarm True.
  - `teams`: 2,500 credits, 150, name "Teams", speed_tiers `["lite","pro","max"]`, swarm True, max_swarm True.
- **Remove** `starter` from CREDIT_PLANS.
- **ADDONS:** Remove fixed add-ons (light, dev). Add-on logic becomes “custom credits” only (see 3.3).
- **TOKEN_BUNDLES:** Build from new CREDIT_PLANS (excl. free). No ADDONS keys; custom add-on handled by a dedicated flow.
- **ANNUAL_PRICES:** Update for builder/pro/scale/teams if you keep annual; otherwise can simplify to monthly-only for this phase.

### 3.2 Plan-based speed (remove speed_selector from client)

- **`run_orchestration_v2`:** Do not read `speed_selector` from `project.requirements`. Derive:
  - `speed_selector = _speed_from_plan(user_tier)` where:
    - free → `"lite"`
    - builder → `"pro"` (or `"lite"` if you prefer)
    - pro / scale / teams → `"pro"` or `"max"` (e.g. pro → `"pro"`, scale/teams → `"max"`).
- **Chat path:** Wherever chat calls the LLM (e.g. `/ai/chat` or internal `_call_llm_with_fallback`), stop accepting `speed_selector` from the request body. Load user’s plan and pass `speed_selector=_speed_from_plan(user_tier)`.
- **`_call_llm_with_fallback`:** Keep parameter `speed_selector` for internal use; callers always pass the derived value (no client input).
- **`_run_single_agent_with_context` / `_run_single_agent_with_retry`:** Keep passing `speed_selector` through; it is always server-derived.
- Add a small helper, e.g. `def _speed_from_plan(plan: str) -> str`, used by orchestration and chat.

### 3.3 Custom add-on (slider) — new endpoint + Stripe

- **New body model**, e.g. `TokenPurchaseCustom(BaseModel): credits: int` with validation `100 <= credits <= 5000`.
- **Price:** `price = round(credits * 0.06, 2)`.
- **POST `/tokens/purchase-custom`** (or extend purchase with `bundle: "custom"` + `credits`):
  - If Stripe disabled: grant `credits` and `credits * CREDITS_PER_TOKEN` tokens, ledger entry with bundle `"custom"` and `price`.
  - If Stripe enabled: do not grant directly; return a Stripe Checkout URL for that amount (see below).
- **Stripe:** Add or extend checkout session to accept **custom amount**: e.g. `POST /stripe/create-checkout-session-custom` with `credits: int` (100–5000), `unit_amount = int(round(credits * 0.06 * 100))`, quantity 1, metadata `credits`, `bundle: "custom"`. Webhook already has `metadata.credits`; treat `bundle_key` as `"custom"` and grant `credits` (and tokens) from metadata.
- **GET `/tokens/bundles`:** Response can include a single add-on entry, e.g. `custom: { "min_credits": 100, "max_credits": 5000, "price_per_credit": 0.06 }` so the frontend can build the slider without hardcoding.

---

## 4. Frontend changes

### 4.1 Pricing page (`Pricing.jsx`)

- **Layout (keep):** Free in its own block at the top (“one up”). Below that, a single row/section of **four paid tiers** (“four down”): Builder, Pro, Scale, Teams. **Do not** show Free again in the paid grid.
- **Data:** Remove `starter` from bundle order and from any default/API bundle list. Use `BUNDLE_ORDER = ['builder', 'pro', 'scale', 'teams']` for the paid grid; fetch from `/tokens/bundles` and filter so free is never in the grid (free is only in the top block).
- **Copy:** Replace tier labels and bullets with the outcome-focused wording in §2. Remove all speed text (Lite/Pro/Max, “Lite only,” “All speeds,” etc.).
- **Add-ons:** Replace the two add-on cards (Light, Dev) with a **slider section**:
  - Slider: min 100, max 5000, step 100 (or 50). Display “Credits: X” and “Total: $Y” (Y = X × 0.06).
  - CTA: “Buy X credits” → if logged in, call new custom purchase or Stripe custom endpoint with chosen credits; if not, redirect to auth then back to Credit Center with slider state or to pricing.
- **Outcome calculator:** Keep “How many credits do I need?” with landing page / full app inputs; recommendation logic uses new tier list (builder/pro/scale/teams) and new credit amounts.
- **Trust:** Add one line: “Cost preview before running · Auto-refund on failures.”
- **Remove:** Token math (“1 credit ≈ 1,000 tokens”), “92% margin,” and “vs Lovable” or “half the price” from primary position (optional: move to footer or remove).

### 4.2 Token Center / Credit Center (`TokenCenter.jsx`)

- **Bundle list:** Show only paid **subscription** tiers: builder, pro, scale, teams (from API). Order: builder, pro, scale, teams. Do not show free; do not show old add-on keys (light, dev).
- **Add-on:** One “Need more? Buy credits” block with the **same slider** (100–5000, price = credits × $0.06). “Pay with Stripe” (or “Purchase” when Stripe disabled) sends credits to the new custom endpoint / Stripe custom session.
- **bundleOrder:** Set to `['builder', 'pro', 'scale', 'teams']` for the main cards; handle add-on separately via slider.

### 4.3 Speed selector — remove everywhere

- **Workspace.jsx:**
  - Remove state: `speedSelector`, `setSpeedSelector`.
  - Remove the Lite/Pro/Max button group (the block that uses `speedSelector` and `setSpeedSelector`).
  - Remove `speed_selector` from the chat request body (fetch/axios to `/ai/chat` or equivalent).
- **SpeedSelector.jsx:** Delete the file (or leave unused). Grep for `SpeedSelector`; if any import remains, remove the import and usage.
- **No other surface:** Ensure no other page or component shows or sends speed/mode selector.

---

## 5. Implementation checklist (ordered)

| # | Task | Owner |
|---|------|--------|
| 1 | Backend: Update CREDIT_PLANS (remove starter; add scale; builder 15/250, pro 30/500, scale 60/1000, teams 150/2500). | Dev |
| 2 | Backend: Update TOKEN_BUNDLES from new CREDIT_PLANS; remove ADDONS from TOKEN_BUNDLES. | Dev |
| 3 | Backend: Add `_speed_from_plan(plan)` and use it in run_orchestration_v2 and chat path; stop reading speed_selector from request/requirements. | Dev |
| 4 | Backend: Add custom add-on (POST purchase-custom + Stripe create-checkout-session-custom; webhook handles metadata.credits + bundle=custom). | Dev |
| 5 | Backend: GET /tokens/bundles returns new tiers + optional `custom_addon: { min_credits, max_credits, price_per_credit }`. | Dev |
| 6 | Frontend: Pricing.jsx — Free block only at top; paid grid = 4 tiers (builder, pro, scale, teams); remove starter; outcome copy; remove speed copy. | Dev |
| 7 | Frontend: Pricing.jsx — Replace add-on cards with slider (100–5000, $0.06/credit); wire to custom purchase or Stripe. | Dev |
| 8 | Frontend: TokenCenter.jsx — Show only builder/pro/scale/teams; add slider add-on; remove light/dev. | Dev |
| 9 | Frontend: Workspace.jsx — Remove speedSelector state, Lite/Pro/Max buttons, and speed_selector from chat request. | Dev |
| 10 | Frontend: Delete or stop using SpeedSelector.jsx. | Dev |
| 11 | Docs/copy: Add “Cost preview · Auto-refund · Rollover” trust line; remove token math and margin from public pricing. | Dev |
| 12 | Smoke test: Pricing page (Free top, 4 down, slider); Credit Center (4 tiers + slider); chat and build without sending speed; orchestration uses plan-derived speed. | QA/Dev |

---

## 6. Slider UX (add-ons)

- **Pricing page:** Section “Need more? Slide to choose.” Slider 100–5,000; label “Credits: X” and “Total: $Y” (Y = X × 0.06). Button “Buy X credits” → Stripe (or dev purchase) with `credits: X`.
- **Token Center:** Same slider and CTA; after purchase, refresh balance and optionally show “X credits added.”
- **Backend:** Validate 100 ≤ credits ≤ 5000; price = round(credits * 0.06, 2); Stripe `unit_amount` = that in cents.

---

## 7. Migration / compatibility

- **Existing users:** If they have `plan: "starter"`, decide: map to `builder` (or to `free`) and set `plan` in DB so `_speed_from_plan` and UI stay consistent. Option: one-time script or on-next-load update.
- **References to “starter”:** Grep codebase and replace with builder or remove (e.g. TokenCenter bundleOrder, any “Starter” labels).
- **Stripe:** If you have existing products for old bundles (starter, light, dev), you can keep them for legacy or create new products for builder/pro/scale/teams + one “Custom credits” product with variable amount; webhook already supports metadata.credits.

---

## 8. Summary

- **Pricing:** Linear $0.06/credit; Free 100 (separate); Builder $15/250, Pro $30/500, Scale $60/1k, Teams $150/2.5k; add-ons 100–5,000 via slider at same rate.
- **Communication:** Outcomes per tier; ~50 cr ≈ 1 landing, ~100 cr ≈ 1 app; cost preview, auto-refund; no speed wording, no token math, no margin on page.
- **Speed:** Removed from UI and from client API; backend derives from plan only.
- **Work:** Backend (plans, bundles, speed derivation, custom add-on + Stripe), Frontend (Pricing layout + slider, TokenCenter + slider, Workspace speed removal, delete SpeedSelector).

Once you approve this plan, implementation can start in the order of the checklist above.

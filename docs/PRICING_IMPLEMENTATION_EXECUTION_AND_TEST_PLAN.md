# Linear Pricing — Full Implementation, Wiring, Test & Proof Plan

This is the **execution and proof plan** for the approved linear pricing. It covers: what will be implemented 100%, how it will be wired, how token deduction/addition connect, how the slider and add-ons work, how it will be tested, and how it will be proven with a script.

---

## Part A — Scope: What Gets Implemented 100%

| Area | What |
|------|------|
| **Backend** | CREDIT_PLANS (free, builder, pro, scale, teams); TOKEN_BUNDLES from plans only; ADDONS removed; `_speed_from_plan(plan)`; orchestration + chat use derived speed only; custom add-on: `POST /tokens/purchase-custom`, `POST /stripe/create-checkout-session-custom`, webhook handles `bundle=custom`; GET /tokens/bundles returns tiers + `custom_addon`; llm_router treats `scale` like `teams`. |
| **Frontend — Pricing page** | Free block only at top; paid grid = 4 tiers (builder, pro, scale, teams); outcome copy only (no speed words); add-on = slider 100–5000, price = credits×0.06; trust line; remove token math, 92% margin, vs Lovable from primary. |
| **Frontend — Token Center** | Show only builder, pro, scale, teams; add slider block for custom credits; wire “Pay with Stripe” / “Purchase” to custom endpoint when slider used. |
| **Frontend — Workspace** | Remove speed selector (state, Lite/Pro/Max buttons, `speed_selector` from chat request body). |
| **Frontend — Component** | Remove or stop using SpeedSelector.jsx. |
| **Integration** | Token deduction on build start and on usage; token addition on purchase (bundle + custom), referral, and Stripe webhook; plan stored in user doc and used for speed derivation. |

---

## Part B — Implementation Order and File-Level Changes

### Phase 1 — Backend: Pricing constants and speed derivation

**File: `backend/server.py`**

1. **CREDIT_PLANS** — Replace with:
   - `free`: credits 100, price 0, name "Free", speed_tiers `["lite"]`, swarm False.
   - `builder`: credits 250, price 15, name "Builder", speed_tiers `["lite","pro"]`, swarm True.
   - `pro`: credits 500, price 30, name "Pro", speed_tiers `["lite","pro","max"]`, swarm True, max_swarm True.
   - `scale`: credits 1000, price 60, name "Scale", speed_tiers `["lite","pro","max"]`, swarm True, max_swarm True.
   - `teams`: credits 2500, price 150, name "Teams", speed_tiers `["lite","pro","max"]`, swarm True, max_swarm True.
   - Remove `starter` entirely.

2. **ADDONS** — Remove or set to `{}`. No fixed light/dev.

3. **TOKEN_BUNDLES** — Build only from CREDIT_PLANS (excl. free). So keys: builder, pro, scale, teams. Each: tokens = credits * CREDITS_PER_TOKEN, credits, price, name. No addon keys in TOKEN_BUNDLES.

4. **ANNUAL_PRICES** — Update to builder, pro, scale, teams (optional; can keep or simplify).

5. **Helper** — Add:
   ```python
   def _speed_from_plan(plan: str) -> str:
       if plan == "free": return "lite"
       if plan == "builder": return "pro"
       if plan in ("pro", "scale", "teams"): return "max"
       return "lite"
   ```

6. **run_orchestration_v2** — Do not read `speed_selector` from `req`. After loading `user_tier`, set `speed_selector = _speed_from_plan(user_tier)`.

7. **Chat path** — Find where chat requests are handled (e.g. `/ai/chat` or stream handler). Load user plan (from auth or DB); pass `speed_selector=_speed_from_plan(user.get("plan","free"))` into `_call_llm_with_fallback`; do not use any `speed_selector` from the request body.

8. **GET /tokens/bundles** — Return `bundles` (TOKEN_BUNDLES) and add `custom_addon: {"min_credits": 100, "max_credits": 5000, "price_per_credit": 0.06}` so frontend can drive the slider.

---

### Phase 2 — Backend: Custom add-on (slider) and Stripe

**File: `backend/server.py`**

9. **New model** — e.g. `class TokenPurchaseCustom(BaseModel): credits: int` with validator: `100 <= credits <= 5000`.

10. **POST /tokens/purchase-custom** — Body: `{ "credits": int }`. Validate 100–5000. Price = round(credits * 0.06, 2). If STRIPE_SECRET is set: return 400 with message to use Stripe (same pattern as existing purchase). If Stripe not set: increment user token_balance by credits*CREDITS_PER_TOKEN and credit_balance by credits; insert token_ledger with type "purchase", bundle "custom", credits, price; return new balance.

11. **POST /stripe/create-checkout-session-custom** — Body: `{ "credits": int }`. Validate 100–5000. Create Stripe Checkout session with amount = round(credits * 0.06 * 100) cents, quantity 1; metadata: bundle "custom", credits str(credits), tokens str(credits * CREDITS_PER_TOKEN). Return session URL.

12. **Stripe webhook** — In `checkout.session.completed`, when `bundle_key == "custom"`: read credits from metadata (no TOKEN_BUNDLES lookup); price = credits * 0.06; same user update and token_ledger insert as other bundles.

---

### Phase 3 — Backend: Router and plan mapping

**File: `backend/llm_router.py`**

13. In `get_model_chain`, wherever we have `user_tier in ["pro", "teams"]`, add `"scale"`: e.g. `elif user_tier in ["pro", "scale", "teams"]`. So scale behaves like teams.

14. (Optional) If any code still references "starter", add a fallback: e.g. treat "starter" as "builder" for routing so existing users with plan "starter" still work.

---

### Phase 4 — Frontend: Pricing page

**File: `frontend/src/pages/Pricing.jsx`**

15. **BUNDLE_ORDER** — Set to `['builder', 'pro', 'scale', 'teams']`. Do not include 'free' or 'starter'.

16. **Paid grid** — Render only bundles from API that are in BUNDLE_ORDER (so free never appears in grid). Free is only in the existing “Start for free” block at top.

17. **DEFAULT_BUNDLES** — Remove starter. Set builder 250/15, pro 500/30, scale 1000/60, teams 2500/150. (Fallback if API fails.)

18. **PLAN_FEATURES** — Remove starter; remove all speed wording (Lite only, Lite + Pro, etc.). Use outcome-only bullets per tier (see PRICING_LINEAR_IMPLEMENTATION_PLAN).

19. **Add-ons section** — Remove DEFAULT_ADDONS and the two add-on cards (light, dev). Replace with:
    - Slider: min 100, max 5000, step 50 or 100; state `customCredits` (e.g. 500).
    - Display: “Credits: X” and “Total: $Y” (Y = (X * 0.06).toFixed(2)).
    - Button “Buy X credits”: if not logged in, redirect to auth with return URL; if logged in, call POST /tokens/purchase-custom with { credits: X } when Stripe is disabled, or POST /stripe/create-checkout-session-custom and redirect to URL when Stripe enabled.

20. **Outcome calculator** — Use new tier list and credits (builder 250, etc.) for recommendation.

21. **Trust line** — Add: “Cost preview before running · Auto-refund on failures · Credits roll over on all plans.”

22. **Remove** — “1 credit ≈ 1,000 tokens”, “92% margin” from main copy. Remove or soften “vs Lovable” / “half the price” from hero.

23. **Annual** — If you keep monthly/annual toggle, ensure annual_prices only have builder, pro, scale, teams (no starter).

---

### Phase 5 — Frontend: Token Center

**File: `frontend/src/pages/TokenCenter.jsx`**

24. **bundleOrder** — Set to `['builder', 'pro', 'scale', 'teams']`. Remove 'starter', 'light', 'dev'.

25. **Purchase cards** — Only show bundles returned by API that are in bundleOrder (so 4 cards).

26. **Add-on block** — Add a section “Need more? Buy credits” with the same slider (100–5000, price = credits × 0.06). “Purchase” (no Stripe) → POST /tokens/purchase-custom; “Pay with Stripe” → POST /stripe/create-checkout-session-custom, then redirect. On success, refresh balance/history.

---

### Phase 6 — Frontend: Workspace — Remove speed selector

**File: `frontend/src/pages/Workspace.jsx`**

27. Remove state: `speedSelector`, `setSpeedSelector`.

28. Remove the entire block that renders the Lite/Pro/Max buttons (the div with `['lite','pro','max'].map` and `setSpeedSelector`).

29. In the chat send (fetch/axios body), remove `speed_selector: speedSelector` from the JSON. Do not send any speed from client.

---

### Phase 7 — Frontend: SpeedSelector component

30. **SpeedSelector.jsx** — Delete file, or leave file but remove all imports/usages. Grep for “SpeedSelector” and remove any import and usage.

---

## Part C — Wiring: Token Deduction and Addition

### Where credits are deducted (must still work)

| Place | How it’s wired |
|-------|----------------|
| Project create (orchestration start) | server.py: estimated_credits from plan/prompt; `$inc: {"credit_balance": -estimated_credits}`. Ensure estimate uses new CREDIT_PLANS (e.g. free 100, builder 250) for caps if needed. |
| AI chat / stream | Existing usage/balance logic; ensure it uses `credit_balance` and CREDITS_PER_TOKEN. No change to deduction math; only ensure plan/speed are derived server-side. |
| Agent runs (orchestration) | Already uses user’s credit_balance; refund on failure. No change. |

### Where credits are added (must all work)

| Place | How it’s wired |
|-------|----------------|
| POST /tokens/purchase (bundle) | Uses TOKEN_BUNDLES[bundle]. Grant credits and tokens; ledger. Only keys now: builder, pro, scale, teams. |
| POST /tokens/purchase-custom (slider) | New. Grant credits and tokens; ledger with bundle "custom", price = credits*0.06. |
| Stripe checkout (bundle) | Existing. Webhook reads metadata.bundle, TOKEN_BUNDLES[bundle], grants credits. |
| Stripe checkout (custom) | New. Webhook when bundle=="custom" reads metadata.credits, grants credits, price = credits*0.06, ledger. |
| Referral | Existing. Grant 100 credits; no change. |
| Sign-up (free tier) | Existing. FREE_TIER_CREDITS = 100; no change. |

### Plan field and speed

- User document has `plan` (e.g. "free", "builder", "pro", "scale", "teams"). Where plan is set (e.g. on first purchase, or via subscription) keep as-is or set to the bundle key when they buy that tier (builder → plan "builder", etc.) if you want plan to drive speed. Orchestration and chat both use `user_tier = user.get("plan","free")` and `speed_selector = _speed_from_plan(user_tier)`.

---

## Part D — Testing Plan

### 1. Unit / logic tests (backend)

- **`_speed_from_plan`**: free→lite, builder→pro, pro/scale/teams→max.
- **CREDIT_PLANS / TOKEN_BUNDLES**: no starter; builder 250/15, pro 500/30, scale 1000/60, teams 2500/150; no light/dev in TOKEN_BUNDLES.
- **Custom add-on**: 100 ≤ credits ≤ 5000; price = round(credits * 0.06, 2). Reject &lt; 100 or &gt; 5000.

### 2. API tests (no Stripe, no DB if possible)

- GET /tokens/bundles: returns builder, pro, scale, teams and custom_addon; no free, no starter, no light/dev.
- POST /tokens/purchase-custom (Stripe disabled): with valid token, body { credits: 200 }; expect 200, balance increased by 200, ledger has bundle "custom", price 12.
- POST /tokens/purchase (bundle "builder"): expect 200, balance increased by 250, ledger has bundle "builder", price 15.
- With STRIPE_SECRET set: POST /tokens/purchase returns 400 with message to use Stripe; POST /tokens/purchase-custom returns 400 same idea.

### 3. Integration (with DB)

- Create user, set plan "free". Start orchestration (or call chat); assert speed_selector passed to router is "lite".
- Set plan "builder"; assert speed_selector "pro". Set plan "teams"; assert "max". Set plan "scale"; assert "max".
- Purchase custom 500 credits (Stripe disabled); assert user credit_balance increased by 500 and token_balance by 500*1000; ledger entry.

### 4. Frontend (manual or E2E)

- Pricing: Free block at top only; below, 4 cards (Builder, Pro, Scale, Teams); no Starter; no Lite/Pro/Max wording; slider 100–5000, total updates; “Buy X credits” works when logged in (calls API).
- Token Center: 4 bundle cards; slider add-on; purchase (or Stripe) for custom credits.
- Workspace: No speed selector; chat still sends messages (no speed_selector in body).

### 5. Verification script (proof)

- A single script (e.g. `backend/scripts/verify_linear_pricing.py` or `tests/verify_pricing_wiring.py`) that:
  1. Imports server (or calls API) and checks: CREDIT_PLANS has free, builder, pro, scale, teams and no starter; TOKEN_BUNDLES has only builder, pro, scale, teams; custom_addon in get_bundles response.
  2. Calls _speed_from_plan for each plan and asserts expected speed.
  3. Optionally: with a test DB or mocked DB, creates user, calls purchase-custom and purchase bundle, asserts balance and ledger.
  4. Exits 0 if all checks pass, non-zero otherwise. CI or “run this script” = proof.

---

## Part E — Verification Script (Concrete)

**File: `backend/scripts/verify_linear_pricing.py`** (or under `tests/`)

```text
1. Load CREDIT_PLANS: assert "free" in, "starter" not in; assert free.credits==100, builder.credits==250, builder.price==15, pro.credits==500, pro.price==30, scale.credits==1000, scale.price==60, teams.credits==2500, teams.price==150.
2. Load TOKEN_BUNDLES: assert set(TOKEN_BUNDLES.keys()) == {"builder","pro","scale","teams"} (no free, no light, no dev).
3. _speed_from_plan("free")=="lite", _speed_from_plan("builder")=="pro", _speed_from_plan("pro")=="max", _speed_from_plan("scale")=="max", _speed_from_plan("teams")=="max".
4. Optional: GET /api/tokens/bundles (if app running or import app): response has bundles builder/pro/scale/teams and custom_addon with min_credits 100, max_credits 5000, price_per_credit 0.06.
5. Optional: POST /api/tokens/purchase-custom with auth and credits=100: expect success and balance +100 when Stripe disabled.
Print "All linear pricing checks passed." and exit(0). Else exit(1).
```

Run: `python backend/scripts/verify_linear_pricing.py` (or `pytest tests/verify_pricing_wiring.py -v`). This is the “proof” that wiring and constants are correct.

---

## Part F — What Could Be Missed (Checklist Before Approval)

- [ ] **Starter migration**: Existing users with plan "starter" — either migrate to "builder" in DB or handle "starter" in _speed_from_plan (e.g. return "pro") and in UI (show as Builder).
- [ ] **Plan assignment on purchase**: When user buys bundle "builder", do we set user.plan = "builder"? If yes, ensure that’s done in purchase_tokens and in Stripe webhook for bundle purchases.
- [ ] **Free tier project create**: Still only landing for free unless has paid purchase; logic uses token_ledger and project_type; no change needed.
- [ ] **Annual prices**: If you keep annual, ANNUAL_PRICES must have builder, pro, scale, teams (no starter) and frontend must not reference starter.
- [ ] **TokenCenter “addon” deep link**: If Pricing links to Token Center with ?addon=something, remove addon=light and addon=dev; optional: addon=slider to scroll to slider.
- [ ] **Admin / reporting**: Any dashboard that lists bundles or revenue by bundle should include "custom" and exclude starter/light/dev.
- [ ] **Linter**: Run linter on changed files (server.py, llm_router.py, Pricing.jsx, TokenCenter.jsx, Workspace.jsx); fix any new issues.
- [ ] **Build**: Frontend build succeeds; backend starts without import errors.

---

## Part G — Summary: How It Will Be Done, Tested, Proved

| Step | How |
|------|-----|
| **Implement** | Phases 1–7 in order; each file change as above. |
| **Wire** | Deduction: existing project create and usage paths (unchanged). Addition: existing purchase + new purchase-custom; Stripe webhook for bundle and custom. Plan and speed: _speed_from_plan everywhere; no client speed. |
| **Integrate** | Pricing page and Token Center use GET /tokens/bundles; purchase and custom use POST endpoints; Workspace stops sending speed_selector. |
| **Test** | Unit/logic tests for _speed_from_plan and bundles; API tests for GET bundles and POST purchase-custom; integration for plan→speed and balance; frontend manual/E2E for layout and slider. |
| **Prove** | Run verification script; it checks CREDIT_PLANS, TOKEN_BUNDLES, _speed_from_plan, and optionally API and balance; exit 0 = pass. |

Once you approve this plan, implementation will follow this order and the script will be run to prove the wiring.

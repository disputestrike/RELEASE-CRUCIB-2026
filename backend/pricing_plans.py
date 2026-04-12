"""
Single source of truth for pricing: plans, bundles, speed mapping.
No heavy dependencies so scripts and tests can import without loading server.
Linear pricing: Free + Builder, Pro, Scale, Teams. $0.03/credit (plans and bulk). No starter.

PRICING UPDATE — March 2026 (approved):
- Every tier doubled in credits. Prices unchanged. Fully linear.
- Free:    100 → 200 credits  (real wow moment before paywall — 2 apps or 4 landing pages)
- Builder: 250 → 500 credits  @ $15  (5 full apps — matches Lovable quantity, $10 cheaper, more complete)
- Pro:    500 → 1000 credits  @ $30  (10 full apps — doubles Builder, clear linear step)
- Scale: 1000 → 2000 credits  @ $60  (20 full apps — doubles Pro)
- Teams: 2500 → 5000 credits  @ $150 (50 full apps — doubles Scale)
- Custom slider: 100–10000 at $0.03/credit (same rate as plans)
- Referral reward: unchanged at 100 credits each (free tier only, 10/month cap)
- Annual prices: unchanged (17% off monthly = same ratio)

What users build per plan (marketing copy basis):
  50 credits  = 1 landing page
  100 credits = 1 full app (React + FastAPI + DB + auth + Stripe payments)
  150 credits = 1 mobile app (Expo + App Store + Play Store submission guide)
"""

# 1 credit = 1000 tokens
CREDITS_PER_TOKEN = 1000

# Linear pricing — fully doubled credits at every tier. $0.06/credit throughout.
CREDIT_PLANS = {
    "free": {
        "credits": 200,
        "price": 0,
        "name": "Free",
        "speed_tiers": ["lite"],
        "model": "cerebras",
        "swarm": False,
    },
    "builder": {
        "credits": 500,
        "price": 15,
        "name": "Builder",
        "speed_tiers": ["lite", "pro"],
        "models": {"lite": "cerebras", "pro": "haiku"},
        "swarm": True,
    },
    "pro": {
        "credits": 1000,
        "price": 30,
        "name": "Pro",
        "speed_tiers": ["lite", "pro", "max"],
        "models": {"lite": "cerebras", "pro": "haiku", "max": "haiku"},
        "swarm": True,
        "max_swarm": True,
    },
    "scale": {
        "credits": 2000,
        "price": 60,
        "name": "Scale",
        "speed_tiers": ["lite", "pro", "max"],
        "models": {"lite": "cerebras", "pro": "haiku", "max": "haiku"},
        "swarm": True,
        "max_swarm": True,
    },
    "teams": {
        "credits": 5000,
        "price": 150,
        "name": "Teams",
        "speed_tiers": ["lite", "pro", "max"],
        "models": {"lite": "cerebras", "pro": "haiku", "max": "haiku"},
        "swarm": True,
        "max_swarm": True,
    },
}
ADDONS = {}  # Slider only (100–10000 at $0.03). No fixed add-ons.
ANNUAL_PRICES = {"builder": 149.99, "pro": 299.99, "scale": 599.99, "teams": 1499.99}

TOKEN_BUNDLES = {}
for k, v in CREDIT_PLANS.items():
    if k == "free":
        continue
    TOKEN_BUNDLES[k] = {
        "tokens": v["credits"] * CREDITS_PER_TOKEN,
        "credits": v["credits"],
        "price": v["price"],
        "name": v["name"],
        "speed": v.get("speed", ""),
    }


def _speed_from_plan(plan: str) -> str:
    if plan == "free":
        return "lite"
    if plan == "builder":
        return "pro"
    if plan in ("pro", "scale", "teams"):
        return "max"
    if plan == "starter":  # legacy only
        return "pro"
    return "lite"

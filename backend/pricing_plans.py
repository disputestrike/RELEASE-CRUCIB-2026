"""
Single source of truth for pricing: plans, bundles, speed mapping.
No heavy dependencies so scripts and tests can import without loading server.
Linear pricing: Free + Builder, Pro, Scale, Teams. $0.06/credit. No starter.

Pricing baseline aligned with backend validation tests:
- Free:    100 credits
- Builder: 250 credits @ $15
- Pro:     500 credits @ $30
- Scale:  1000 credits @ $60
- Teams:  2500 credits @ $150
- Custom slider: 100–10000 at $0.06/credit (raised max for agencies and power users)
- Referral reward: unchanged at 100 credits each (free tier only, 10/month cap)
- Annual prices: unchanged (17% off monthly = same ratio)

What users build per plan (marketing copy basis):
  50 credits  = 1 landing page
  100 credits = 1 full app (React + FastAPI + DB + auth + Braintree payments)
  150 credits = 1 mobile app (Expo + App Store + Play Store submission guide)
"""
# 1 credit = 1000 tokens
CREDITS_PER_TOKEN = 1000

# Linear pricing at $0.06/credit throughout.
CREDIT_PLANS = {
    "free":    {"credits": 100,  "price": 0,   "name": "Free",    "speed_tiers": ["lite"],               "model": "cerebras", "swarm": False},
    "builder": {"credits": 250,  "price": 15,  "name": "Builder", "speed_tiers": ["lite", "pro"],        "models": {"lite": "cerebras", "pro": "haiku"}, "swarm": True},
    "pro":     {"credits": 500,  "price": 30,  "name": "Pro",     "speed_tiers": ["lite", "pro", "max"], "models": {"lite": "cerebras", "pro": "haiku", "max": "haiku"}, "swarm": True, "max_swarm": True},
    "scale":   {"credits": 1000, "price": 60,  "name": "Scale",   "speed_tiers": ["lite", "pro", "max"], "models": {"lite": "cerebras", "pro": "haiku", "max": "haiku"}, "swarm": True, "max_swarm": True},
    "teams":   {"credits": 2500, "price": 150, "name": "Teams",   "speed_tiers": ["lite", "pro", "max"], "models": {"lite": "cerebras", "pro": "haiku", "max": "haiku"}, "swarm": True, "max_swarm": True},
}
ADDONS = {}  # Slider only (100–10000 at $0.06). No fixed add-ons.
ANNUAL_PRICES = {"builder": 149.99, "pro": 299.99, "scale": 599.99, "teams": 1499.99}
CUSTOM_CREDIT_MIN = 100
CUSTOM_CREDIT_MAX = 10000
CUSTOM_CREDIT_STEP = 100
CUSTOM_CREDIT_PRICE = 0.03

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

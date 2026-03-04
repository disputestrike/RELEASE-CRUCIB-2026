"""
Single source of truth for pricing: plans, bundles, speed mapping.
No heavy dependencies so scripts and tests can import without loading server.
Linear pricing: Free + Builder, Pro, Scale, Teams. $0.06/credit. No starter.
"""
# 1 credit = 1000 tokens
CREDITS_PER_TOKEN = 1000

# Linear pricing: Free + Builder, Pro, Scale, Teams. No starter; add-ons via slider (custom).
CREDIT_PLANS = {
    "free": {"credits": 100, "price": 0, "name": "Free", "speed_tiers": ["lite"], "model": "cerebras", "swarm": False},
    "builder": {"credits": 250, "price": 15, "name": "Builder", "speed_tiers": ["lite", "pro"], "models": {"lite": "cerebras", "pro": "haiku"}, "swarm": True},
    "pro": {"credits": 500, "price": 30, "name": "Pro", "speed_tiers": ["lite", "pro", "max"], "models": {"lite": "cerebras", "pro": "haiku", "max": "haiku"}, "swarm": True, "max_swarm": True},
    "scale": {"credits": 1000, "price": 60, "name": "Scale", "speed_tiers": ["lite", "pro", "max"], "models": {"lite": "cerebras", "pro": "haiku", "max": "haiku"}, "swarm": True, "max_swarm": True},
    "teams": {"credits": 2500, "price": 150, "name": "Teams", "speed_tiers": ["lite", "pro", "max"], "models": {"lite": "cerebras", "pro": "haiku", "max": "haiku"}, "swarm": True, "max_swarm": True},
}
ADDONS = {}  # Slider only (100-5000 at $0.06). No fixed light/dev.
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

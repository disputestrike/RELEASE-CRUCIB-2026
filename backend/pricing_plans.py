"""Single source of truth for plan credits and pricing."""

# 1 credit = 500 tokens
TOKENS_PER_CREDIT = 500
CREDITS_PER_TOKEN = TOKENS_PER_CREDIT  # Back-compat import name used by server/routes.
CREDIT_PRICE_USD = 0.05

CREDIT_PLANS = {
    "free": {
        "credits": 100,
        "price": 0,
        "name": "Free",
        "speed_tiers": ["lite"],
        "model": "cerebras",
        "swarm": False,
    },
    "builder": {
        "credits": 500,
        "price": 20,
        "name": "Builder",
        "speed_tiers": ["lite", "pro"],
        "models": {"lite": "cerebras", "pro": "haiku"},
        "swarm": True,
    },
    "pro": {
        "credits": 1500,
        "price": 50,
        "name": "Pro",
        "speed_tiers": ["lite", "pro", "max"],
        "models": {"lite": "cerebras", "pro": "haiku", "max": "haiku"},
        "swarm": True,
        "max_swarm": True,
    },
    "scale": {
        "credits": 3000,
        "price": 100,
        "name": "Scale",
        "speed_tiers": ["lite", "pro", "max"],
        "models": {"lite": "cerebras", "pro": "haiku", "max": "haiku"},
        "swarm": True,
        "max_swarm": True,
    },
    "teams": {
        "credits": 6000,
        "price": 200,
        "name": "Teams",
        "speed_tiers": ["lite", "pro", "max"],
        "models": {"lite": "cerebras", "pro": "haiku", "max": "haiku"},
        "swarm": True,
        "max_swarm": True,
    },
}
ADDONS = {}  # Slider only. No fixed add-ons.
ANNUAL_PRICES = {"builder": 199.99, "pro": 499.99, "scale": 999.99, "teams": 1999.99}
CUSTOM_CREDIT_MIN = 500
CUSTOM_CREDIT_MAX = 20000
CUSTOM_CREDIT_STEP = 500
CUSTOM_CREDIT_PRICE = CREDIT_PRICE_USD

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

"""Single source of truth for plan credits and pricing."""

# 1 credit = 500 tokens
TOKENS_PER_CREDIT = 500
CREDITS_PER_TOKEN = TOKENS_PER_CREDIT  # Back-compat import name used by server/routes.
BUNDLED_CREDIT_VALUE_USD = 0.03
TOPUP_CREDIT_PRICE_USD = 0.05
CREDIT_PRICE_USD = TOPUP_CREDIT_PRICE_USD

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
ADDONS = {}  # Slider only. No fixed add-ons.
ANNUAL_PRICES = {"builder": 150, "pro": 300, "scale": 600, "teams": 1500}
CUSTOM_CREDIT_MIN = 500
CUSTOM_CREDIT_MAX = 20000
CUSTOM_CREDIT_STEP = 500
CUSTOM_CREDIT_PRICE = TOPUP_CREDIT_PRICE_USD

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

"""
Constants for agents & automation: credits, limits, timeouts.
"""
# Credits deducted per agent run (one run = one deduction regardless of action count for simplicity)
CREDITS_PER_AGENT_RUN = 5

# Max concurrent runs per user (prevents runaway)
MAX_CONCURRENT_RUNS_PER_USER = 5

# Max runs per hour per user (rate limit)
MAX_RUNS_PER_HOUR_PER_USER = 60

# Total timeout for one agent run (all steps)
AGENT_RUN_TIMEOUT_SECONDS = 300

# Per-action timeout
AGENT_ACTION_TIMEOUT_SECONDS = 120

# Webhook: dedupe window for idempotency_key
WEBHOOK_IDEMPOTENCY_SECONDS = 60

# Webhook: max requests per minute per agent
WEBHOOK_RATE_LIMIT_PER_MINUTE = 100

# Internal system user_id for dogfooding agents
INTERNAL_USER_ID = "__internal__"

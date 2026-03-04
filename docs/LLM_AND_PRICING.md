# LLM Design & Pricing (Anthropic + Cerebras)

## How we’re structured

### 1. Three providers

- **Cerebras** – `CEREBRAS_API_KEY` → Cerebras Llama 2 70B. Fast, low cost (~$0.27/1M tokens).
- **Anthropic (Haiku)** – `ANTHROPIC_API_KEY` → Claude 3.5 Haiku. Higher quality (~$0.80/1M tokens).
- **Llama (Together)** – `LLAMA_API_KEY` → Llama 70B via Together AI. Free/open-source option.

You need **at least one** of these keys (e.g. `ANTHROPIC_API_KEY` or `CEREBRAS_API_KEY`) for builds to work.

### 2. Where routing happens

- **`backend/llm_router.py`** – **LLMRouter** and **TaskClassifier**:
  - Classifies each request as SIMPLE / MODERATE / COMPLEX / CRITICAL.
  - **`get_model_chain(task_complexity, user_tier, speed_selector, available_credits)`** returns an ordered list of models to try: e.g. `[cerebras, llama, haiku]` or `[llama, cerebras, haiku]`.
  - Only includes providers that have a key (e.g. if only Cerebras + Anthropic are set, chain is Cerebras → Haiku).

- **`backend/server.py`** – **`_call_llm_with_fallback`**:
  - Accepts an initial `model_chain` (from `_get_model_chain`), but **replaces it** with the router:
    - Calls `classifier.classify(message, agent_name)`.
    - Calls `router.get_model_chain(task_complexity, user_tier, speed_selector, available_credits)`.
  - Then tries each model in that chain (Cerebras → Llama → Haiku, or whatever the router returned) until one succeeds.

So **all LLM calls that go through `_call_llm_with_fallback`** (including orchestration) use **llm_router** for the actual model choice. The server’s `MODEL_CONFIG` / `MODEL_FALLBACK_CHAINS` (Anthropic-only) are only used to build the initial chain that gets overwritten; the real behavior is router-based.

### 3. Router logic (tier + speed + complexity + credits)

- **Free tier**: Cerebras/Llama first (order depends on complexity), Haiku last.
- **Starter/Builder**: `lite` → Cerebras first; `pro` → Llama then Cerebras, then Haiku.
- **Pro/Teams**: `lite` → Cerebras first; `pro` / `max` → Llama, Cerebras, Haiku.
- **Task complexity**: CRITICAL → prefer Llama first; SIMPLE → prefer Cerebras first.
- **Low credits** (&lt; 10): Haiku is moved to the end of the chain to save cost.

So in practice: **Cerebras** is used for fast/cheap (lite, simple tasks); **Anthropic Haiku** is the quality fallback and is used more for pro/max and when other providers fail or aren’t configured.

---

## Pricing (how we charge users)

- **Unit**: **Credits**. 1 credit = 1000 tokens (internal: `CREDITS_PER_TOKEN = 1000`).
- **Plans** (`CREDIT_PLANS` in `server.py`):
  - **free**: 100 credits, speed_tiers = `["lite"]`, model = cerebras.
  - **starter**: 200 credits, $14.99, lite (cerebras) + pro (haiku).
  - **builder**: 500 credits, $29.99, same model mapping, swarm.
  - **pro**: 2000 credits, $79.99, lite/pro/max with cerebras/haiku.
  - **teams**: 10000 credits, $199.99, same.

- **Speed tiers** (`SPEED_TIERS`): Each speed has a **credit_cost** (e.g. lite 50, pro 100, max 150) and a **model** (lite → cerebras, pro/max → haiku). Users pay in **credits**, not per-model dollar price.

- **Deduction**: Credits are deducted when starting a build (estimated), on AI chat/stream, and on agent runs; unused tokens can be refunded after a build.

So **pricing to the user is credit-based**; we don’t expose separate Anthropic vs Cerebras pricing. Our cost is determined by which provider the router actually calls (Cerebras cheaper, Anthropic higher quality/cost).

---

## Orchestration and tier/speed

- **Build request** includes `speed_selector` (lite/pro/max), and we load **user_tier** and **available_credits** from the DB.
- **Wired**: `user_tier`, `speed_selector`, and `available_credits` are passed from the orchestration loop → `_run_single_agent_with_retry` → `_run_single_agent_with_context` → `_call_llm_with_fallback`. Plan and speed now control which model chain the router uses during builds (e.g. starter pro → Haiku in chain; free lite → Cerebras/Llama first).

---

## Summary

| Aspect | Design |
|--------|--------|
| **Providers** | Cerebras, Anthropic (Haiku), optional Llama (Together). |
| **Routing** | `llm_router.py`: by task_complexity, user_tier, speed_selector, available_credits. |
| **Actual calls** | `_call_llm_with_fallback` overwrites chain with router → tries Cerebras / Llama / Haiku in order. |
| **Pricing (user)** | Credits per plan; speed tiers have credit_cost; no per-model price. |
| **Our cost** | Driven by which provider is tried first and used (Cerebras cheaper, Anthropic higher). |
| **Orchestration** | Tier, speed, and credits are passed through; builds use plan-appropriate routing. |

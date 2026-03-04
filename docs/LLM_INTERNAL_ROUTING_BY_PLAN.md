# Internal LLM Routing by Plan (How Fast / Who Gets Haiku vs Cerebras)

This doc describes how we route requests internally by plan and task type: which tier gets which model first (Cerebras vs Llama vs Haiku), and how that maps to “faster” vs “slower” and cost.

---

## 1. The three models (internal only)

| Model    | Provider   | Cost/1M tokens | Speed (internal) | Quality (internal) | When we use it |
|----------|------------|----------------|------------------|--------------------|----------------|
| **Cerebras** | Cerebras   | $0.27          | Very fast        | 7.0                | First for “lite” + simple tasks; otherwise second. |
| **Llama 70B**| Together   | $0             | Medium           | 8.5                | First for pro/max or complex/critical; free tier fallback. |
| **Haiku**   | Anthropic  | $0.80          | Medium           | 9.0                | **Always fallback** — we try Cerebras/Llama first, then Haiku if they fail. |

- **Cerebras** = fastest inference, cheapest paid option. We use it first when we want “fast” (lite + simple).
- **Llama** = free, good quality. We use it first for paid tiers (pro/max) or when the task is complex/critical.
- **Haiku** = best quality, most expensive. We only call it when Cerebras or Llama fail (or are unavailable). So **no tier “uses Haiku first”** today; everyone gets Haiku as fallback.

So: **who gets Haiku?** Only when the primary (and maybe second) model fails or isn’t configured. **Who gets Cerebras?** Free and “lite” users, especially on simple tasks. **Who gets Llama?** Everyone; it’s first for paid (pro/max) and for complex/critical tasks.

---

## 2. How we derive “speed” from plan (no UI selector)

With the new pricing we **derive** `speed_selector` from the user’s **plan** only (no user choice):

| Plan   | Derived speed_selector | Meaning internally |
|--------|------------------------|--------------------|
| Free   | `lite`                 | Prefer Cerebras first (simple) or Llama first (complex). Minimize Haiku. |
| Builder| `pro`                  | Llama → Cerebras → Haiku (quality first, then fast, then fallback). |
| Pro    | `pro`                  | Same as Builder. |
| Scale  | `max`                  | Same chain as pro today (see below). Can later give Haiku earlier for “best” quality. |
| Teams  | `max`                  | Same as Scale. |

So:

- **Free** = only `lite` → we bias toward **Cerebras** (and Llama) so we almost never hit Haiku → **fast and cheap** for you.
- **Builder / Pro** = `pro` → we try **Llama** first, then Cerebras, then Haiku → **better quality** on average, same fallback.
- **Scale / Teams** = `max` → today same as pro; later you can make `max` “Haiku earlier” for top-tier quality if you want.

---

## 3. Full routing logic (what actually runs)

The router in `llm_router.py` builds a **chain** of models to try in order. It uses:

1. **user_tier** (free, builder, pro, scale, teams)
2. **speed_selector** (lite, pro, max) — **derived from plan** as above
3. **task_complexity** (SIMPLE, MODERATE, COMPLEX, CRITICAL) — from request + agent name
4. **available_credits** — if &lt; 10, we move Haiku to the end (use Haiku less)

### Step 1: Base chain by tier + speed_selector

| Tier     | speed_selector | Base chain (order we try) |
|----------|----------------|---------------------------|
| free     | lite           | Cerebras → Llama → Haiku (simple) **or** Llama → Cerebras → Haiku (else) |
| starter  | lite           | Cerebras → Llama → Haiku (simple) or Llama → Cerebras → Haiku (else) |
| starter  | pro            | Llama → Cerebras → Haiku |
| builder  | lite           | Cerebras → Llama → Haiku (simple) or Llama → Cerebras → Haiku (else) |
| builder  | pro            | Llama → Cerebras → Haiku |
| pro      | lite           | Cerebras → Llama → Haiku (simple) or Llama → Cerebras → Haiku (else) |
| pro      | pro / max      | Llama → Cerebras → Haiku |
| teams    | lite           | Cerebras → Llama → Haiku (simple) or Llama → Cerebras → Haiku (else) |
| teams    | pro / max      | Llama → Cerebras → Haiku |

*(When we add **scale**, treat it like **teams** in the router.)*

### Step 2: Overrides

- **CRITICAL task** (e.g. Security Checker, Backend Generation): **Llama** is forced to the front of the chain so we try it first.
- **SIMPLE task** (e.g. “fix typo”, “change color”): **Cerebras** is forced to the front (fast path).
- **available_credits &lt; 10:** **Haiku** is moved to the very end so we use it only if Cerebras and Llama both fail.

### Step 3: Availability

We only include models we have keys for. So if only `ANTHROPIC_API_KEY` is set, the chain becomes just Haiku. If only `CEREBRAS_API_KEY` is set, we only try Cerebras then Haiku (if you add it), etc.

---

## 4. Who is “faster” vs “slower” internally?

- **Fastest path:** Cerebras first (simple tasks, or lite tier). So **Free** and any **lite**-derived plan get the **fastest** path when the task is classified SIMPLE.
- **Quality-first path:** Llama first (pro/max, or complex/critical). So **Builder / Pro / Scale / Teams** (with derived pro/max) get **Llama first** for most non-simple tasks → slightly slower than Cerebras-first but better quality, and we still avoid Haiku unless needed.
- **Fallback (slowest / most expensive):** Haiku. **Every tier** can hit Haiku if Cerebras and Llama fail or aren’t configured. So “who uses Haiku?” = “everyone, but only as fallback.”

Summary:

- **Free:** Cerebras/Llama first → **fast and cheap**; Haiku only on failure.
- **Builder / Pro / Scale / Teams:** Llama (or Cerebras for simple) first → **better quality**, same fallback to Haiku.

---

## 5. One table: plan → derived speed → who gets what first

| Plan   | Derived speed | Typical first model(s) | Haiku? |
|--------|----------------|------------------------|--------|
| Free   | lite           | Cerebras (simple) or Llama (else) | Only if Cerebras + Llama fail |
| Builder| pro            | Llama, then Cerebras              | Only if both fail |
| Pro    | pro            | Llama, then Cerebras              | Only if both fail |
| Scale  | max            | Llama, then Cerebras              | Only if both fail |
| Teams  | max            | Llama, then Cerebras              | Only if both fail |

So:

- **Cerebras** is used first mainly for **Free** (and for simple tasks on any tier).
- **Llama** is used first for **paid tiers** (Builder and above) on non-simple tasks (and for critical tasks on all tiers).
- **Haiku** is **never** first; it’s the **fallback** for every tier when the primary (and second) model fails or isn’t available.

---

## 6. Implementation note: “scale” in the router

When you add the **Scale** plan, add `"scale"` to the router in `llm_router.py` wherever `"teams"` is used (e.g. `elif user_tier in ["pro", "teams"]` → `elif user_tier in ["pro", "scale", "teams"]`), and derive speed for Scale as `max` so it behaves like Teams. Optionally later you can give Scale/Teams a chain that tries **Haiku earlier** (e.g. Haiku → Llama → Cerebras) if you want top tiers to get “best quality” first.

---

## 7. Swarm (parallel agents)

“Swarm” in your product = **parallel agent execution** (DAG, many agents per phase). It is **not** a different model. The same routing above applies **per agent call**: each of the 120 agents gets a model from the chain (Cerebras / Llama / Haiku) based on the same plan + task_complexity + credits. So Builder and above get **more parallelism** (swarm enabled), but the **model mix** (who gets Cerebras vs Llama vs Haiku) is still determined by the table above.

---

**TL;DR:** Free = Cerebras/Llama first (fast, cheap), Haiku only on failure. Builder and above = Llama (or Cerebras for simple) first, Haiku only on failure. No tier uses Haiku as the primary model; it’s always the fallback. Speed is derived from plan (lite/pro/max); we don’t show a speed selector to users.

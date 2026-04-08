# Full System Generation Mode

CrucibAI now supports a direct full-system generation path for complex prompts.

## What changed

- The planner parses explicit stack requirements from the goal.
- Plans now include `stack_contract`, `generation_mode`, and `recommended_build_target`.
- Complex multi-stack prompts route to `full_system_generator` instead of the fixed scaffold path.
- The executor calls `BuilderAgent` first for these prompts and writes the returned integrated file set directly into the workspace.
- If the builder returns `❌ CRITICAL BLOCK` or no files, the run fails explicitly instead of silently degrading to a generic scaffold.

## When it activates

Prompts that request multiple stack layers, such as:

- custom frontend framework + backend runtime
- database + cache + queue
- payments + email + realtime
- infrastructure + tests + docs

will be treated as full-system generation requests.

## What remains true

- Deterministic packs still exist for proven paths such as the enterprise command pack.
- Verification depth still depends on the emitted stack and what the runtime can execute in-pipeline.
- Honest failure is preferred over fake scaffold success.

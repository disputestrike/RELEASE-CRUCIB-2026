# Test Results

- `python -m py_compile backend\orchestration\generation_contract.py backend\orchestration\planner.py backend\orchestration\spec_guardian.py backend\orchestration\build_targets.py backend\orchestration\executor.py backend\agents\builder_agent.py backend\server.py backend\tests\test_generation_contract.py backend\tests\test_spec_guardian.py`
  - Result: PASS

- `$env:PYTHONPATH='backend'; python -m pytest backend\tests\test_generation_contract.py backend\tests\test_spec_guardian.py backend\tests\test_builder_agent.py -q --noconftest`
  - Result: `21 passed in 1.92s`

## Covered behaviors

- stack parsing for multi-stack prompts
- planner emits `stack_contract`, `generation_mode`, and recommended build target
- spec guard warns honestly instead of pretending unsupported stacks are satisfied by the old template
- full-system prompts route through `BuilderAgent`
- `❌ CRITICAL BLOCK` from the builder stops execution instead of falling back to a scaffold

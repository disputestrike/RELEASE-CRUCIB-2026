# Full System Generation Contract PASS/FAIL

| Check | Result |
| --- | --- |
| planner parses multi-stack contract | PASS |
| plan includes `generation_mode=full_system_builder` | PASS |
| plan includes `recommended_build_target=full_system_generator` | PASS |
| strict spec guard warns instead of silently blocking mainstream stack requests | PASS |
| multi-stack prompts route to `BuilderAgent` first | PASS |
| `BuilderAgent` critical block causes explicit failure instead of scaffold fallback | PASS |
| backend/database steps reuse full-system manifest instead of overwriting workspace | PASS |

## Commands

- `python -m py_compile backend\orchestration\generation_contract.py backend\orchestration\planner.py backend\orchestration\spec_guardian.py backend\orchestration\build_targets.py backend\orchestration\executor.py backend\agents\builder_agent.py backend\tests\test_generation_contract.py backend\tests\test_spec_guardian.py`
- `$env:PYTHONPATH='backend'; python -m pytest backend\tests\test_generation_contract.py backend\tests\test_spec_guardian.py backend\tests\test_builder_agent.py -q --noconftest`

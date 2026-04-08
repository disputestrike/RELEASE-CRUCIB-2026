# Batch B Commands

```powershell
python -m py_compile backend\server.py backend\routes\trust.py backend\terminal_integration.py
git diff --check
$env:DATABASE_URL='postgresql://crucibai:crucibai@127.0.0.1:5434/crucibai'; $env:REDIS_URL='redis://127.0.0.1:6381/0'; python -m pytest backend\tests\test_smoke.py -k "visual_edit or template_remix or terminal_execute_blocks_dangerous_commands or critical_endpoints" -q
$env:DATABASE_URL='postgresql://crucibai:crucibai@127.0.0.1:5434/crucibai'; $env:REDIS_URL='redis://127.0.0.1:6381/0'; .\scripts\release-gate.ps1 -BackendOnly
.\scripts\frontend-runtime-gate.ps1 -RunDockerBuild
```

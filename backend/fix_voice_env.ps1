# Remove packages that cause "No module named 'emergentintegrations'" and reinstall deps.
# Voice uses only OpenAI (openai package). Run from backend folder: .\fix_voice_env.ps1
pip uninstall emergentintegrations litellm -y 2>$null
pip install -r requirements.txt
Write-Host "Done. Restart the server (e.g. uvicorn server:app --reload)."

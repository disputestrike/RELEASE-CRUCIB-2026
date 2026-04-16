import sys
from pathlib import Path

pytest_plugins = ("pytest_asyncio",)

_REPO_ROOT = Path(__file__).resolve().parent
_BACKEND_ROOT = _REPO_ROOT / "backend"

for _path in (str(_REPO_ROOT), str(_BACKEND_ROOT)):
	if _path not in sys.path:
		sys.path.insert(0, _path)
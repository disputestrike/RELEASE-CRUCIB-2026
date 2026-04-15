import asyncio
import os
import signal
import socket
from pathlib import Path
from typing import Dict, Optional


class DevServerManager:
    """Best-effort Vite dev server manager for workspace previews.

    Keeps one process per job and reuses it until the workspace path changes.
    """

    def __init__(self, base_port: int = 5200, max_port: int = 5299):
        self.base_port = base_port
        self.max_port = max_port
        self.next_port = base_port
        self._servers: Dict[str, dict] = {}
        self._lock = asyncio.Lock()

    def _port_open(self, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            return sock.connect_ex(("127.0.0.1", port)) == 0

    def _allocate_port(self) -> int:
        for _ in range(self.max_port - self.base_port + 1):
            candidate = self.next_port
            self.next_port += 1
            if self.next_port > self.max_port:
                self.next_port = self.base_port
            if not self._port_open(candidate):
                return candidate
        raise RuntimeError("No free preview ports available")

    async def _wait_ready(self, port: int, attempts: int = 30):
        import urllib.request
        url = f"http://127.0.0.1:{port}/"
        for _ in range(attempts):
            try:
                await asyncio.to_thread(urllib.request.urlopen, url, timeout=1)
                return True
            except Exception:
                await asyncio.sleep(1)
        return False

    async def spawn_or_reuse(self, key: str, workspace_path: Path) -> dict:
        async with self._lock:
            existing = self._servers.get(key)
            if existing:
                proc = existing.get("process")
                if proc and proc.returncode is None and existing.get("workspace") == str(workspace_path):
                    return existing
                await self.kill(key)

            if not workspace_path.exists():
                raise FileNotFoundError(f"workspace not found: {workspace_path}")

            package_json = workspace_path / "package.json"
            if not package_json.exists():
                raise FileNotFoundError("package.json not found in workspace")

            port = self._allocate_port()
            env = os.environ.copy()
            env.setdefault("BROWSER", "none")
            env["PORT"] = str(port)
            env["HOST"] = "127.0.0.1"
            env["CI"] = "true"

            proc = await asyncio.create_subprocess_exec(
                "npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", str(port),
                cwd=str(workspace_path),
                env=env,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                preexec_fn=os.setsid if os.name != "nt" else None,
            )
            server = {
                "process": proc,
                "pid": proc.pid,
                "port": port,
                "workspace": str(workspace_path),
                "url": f"http://127.0.0.1:{port}",
            }
            self._servers[key] = server

        ready = await self._wait_ready(port)
        if not ready:
            await self.kill(key)
            raise RuntimeError(f"Dev preview failed to start on port {port}")
        return server

    async def kill(self, key: str):
        existing = self._servers.pop(key, None)
        if not existing:
            return
        proc = existing.get("process")
        pid = existing.get("pid")
        try:
            if proc and proc.returncode is None:
                if os.name != "nt":
                    os.killpg(os.getpgid(pid), signal.SIGTERM)
                else:
                    proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=4)
                except Exception:
                    if os.name != "nt":
                        os.killpg(os.getpgid(pid), signal.SIGKILL)
                    else:
                        proc.kill()
        except Exception:
            pass


_manager: Optional[DevServerManager] = None


def get_dev_server_manager() -> DevServerManager:
    global _manager
    if _manager is None:
        _manager = DevServerManager()
    return _manager

from __future__ import annotations

"""Helpers for safe modular route imports during tests/dev migration.

These defaults are ONLY applied when explicit safe-import mode is enabled.
They prevent legacy route modules from hard-failing on import because they
transitively touch env validation in ``server.py``.
"""

from contextlib import contextmanager
import os
import sys
import types
from pathlib import Path
from pydantic import BaseModel
from typing import Iterator

SAFE_IMPORT_DEFAULTS = {
    "DATABASE_URL": "postgresql://crucibai:crucibai@127.0.0.1:5434/crucibai",
    "JWT_SECRET": "modular-safe-import-jwt-secret-minimum-32-characters",
    "GOOGLE_CLIENT_ID": "test.apps.googleusercontent.com",
    "GOOGLE_CLIENT_SECRET": "test-google-client-secret",
    "FRONTEND_URL": "http://localhost:3000",
    "REDIS_URL": "redis://127.0.0.1:6381/0",
    "CRUCIBAI_DEV": "1",
}

SAFE_IMPORT_FLAGS = (
    "CRUCIBAI_MODULAR_SAFE_IMPORT",
    "CRUCIBAI_TEST",
)


def _install_safe_import_stubs() -> dict[str, object]:
    installed: dict[str, object] = {}

    if "server" not in sys.modules:
        server_stub = types.ModuleType("server")

        async def _fake_user():
            return {"id": "modular-safe-user", "email": "safe@example.com"}

        async def _fake_optional_user():
            return {"id": "modular-safe-user"}

        async def _fake_auth_or_api_user():
            return {"id": "modular-safe-user", "public_api": False}

        class _DummyDB:
            async def __getattr__(self, _name):
                raise AttributeError(_name)

        server_stub.get_current_user = lambda: _fake_user
        server_stub.get_optional_user = lambda: _fake_optional_user
        server_stub.get_authenticated_or_api_user = lambda: _fake_auth_or_api_user
        server_stub.ADMIN_ROLES = {"admin"}
        server_stub.ADMIN_USER_IDS = set()
        server_stub.ROOT_DIR = str(Path.cwd().parent)
        server_stub.CREDITS_PER_TOKEN = 1
        server_stub.MAX_USER_PROJECTS_DASHBOARD = 100
        server_stub.TOKEN_BUNDLES = {}
        server_stub.ANNUAL_PRICES = {}
        server_stub.BRAINTREE_ENVIRONMENT = "sandbox"
        server_stub.BRAINTREE_MERCHANT_ID = ""
        server_stub.BRAINTREE_PUBLIC_KEY = ""
        server_stub.BRAINTREE_PRIVATE_KEY = ""
        server_stub.BRAINTREE_MERCHANT_ACCOUNT_ID = ""
        server_stub.BRAINTREE_CONFIGURED = False
        server_stub.REFERRAL_CAP_PER_MONTH = 0
        server_stub.MAX_TOKEN_USAGE_LIST = 100
        server_stub.MIN_CREDITS_FOR_LLM = 0
        server_stub.ANTHROPIC_API_KEY = ""
        server_stub.ANTHROPIC_HAIKU_MODEL = "claude-3-haiku"
        server_stub.CHAT_WITH_SEARCH_SYSTEM = ""
        server_stub.REAL_AGENT_NO_LLM_KEYS_DETAIL = ""
        server_stub.db = _DummyDB()
        class Permission:
            EDIT_PROJECT = "EDIT_PROJECT"
            CREATE_PROJECT = "CREATE_PROJECT"

        server_stub.Permission = Permission
        class TokenPurchase(BaseModel):
            bundle: str = ""

        class TokenPurchaseCustom(BaseModel):
            credits: int = 0

        class _SimpleBody(BaseModel):
            value: str | None = None

        class DocumentProcess(BaseModel):
            content: str = ""
            task: str = "analyze"

        class GenerateContentRequest(BaseModel):
            prompt: str = ""

        server_stub.TokenPurchase = TokenPurchase
        server_stub.TokenPurchaseCustom = TokenPurchaseCustom
        for _name, _cls in {
            "ContactSubmission": _SimpleBody,
            "EnterpriseContact": _SimpleBody,
            "ExplainErrorBody": _SimpleBody,
            "ExportFilesBody": _SimpleBody,
            "GenerateDocsBody": _SimpleBody,
            "GenerateFaqSchemaBody": _SimpleBody,
            "GenerateReadmeBody": _SimpleBody,
            "InjectPaymentBody": _SimpleBody,
            "OptimizeBody": _SimpleBody,
            "ProjectEnvBody": _SimpleBody,
            "QualityGateBody": _SimpleBody,
            "RAGQuery": _SimpleBody,
            "SavePromptBody": _SimpleBody,
            "SearchQuery": _SimpleBody,
            "SecurityScanBody": _SimpleBody,
            "ShareCreateBody": _SimpleBody,
            "SuggestNextBody": _SimpleBody,
            "ValidateAndFixBody": _SimpleBody,
            "DocumentProcess": DocumentProcess,
            "GenerateContentRequest": GenerateContentRequest,
        }.items():
            setattr(server_stub, _name, _cls)
        class BuildGoalRequest(BaseModel):
            goal: str = ""
            mode: str = "guided"

        server_stub.BuildGoalRequest = BuildGoalRequest
        server_stub._assert_job_owner_match = lambda owner, user: None
        server_stub._project_workspace_path = lambda project_id: Path("/tmp") / str(project_id)
        server_stub._resolve_job_project_id_for_user = lambda project_id, user: project_id or "modular-safe-project"
        server_stub._resolve_project_workspace_path_for_user = lambda project_id, user: Path("/tmp") / str(project_id or "modular-safe-project")
        server_stub._user_can_access_project_workspace = lambda user_id, project_id: True
        server_stub._ensure_credit_balance = lambda *args, **kwargs: None
        server_stub._generate_referral_code = lambda *args, **kwargs: "SAFECODE"
        server_stub._user_credits = lambda *args, **kwargs: 1000
        server_stub.require_permission = lambda *args, **kwargs: (lambda: {"id": "modular-safe-user"})
        server_stub._get_orchestration = lambda: (_DummyRuntimeState(), None, None, None, _DummyProofService())

        def _server_getattr(name):
            if name.startswith("_"):
                return lambda *args, **kwargs: None
            return ""

        server_stub.__getattr__ = _server_getattr
        sys.modules["server"] = server_stub
        installed["server"] = server_stub

    return installed


class _DummyRuntimeState:
    def set_pool(self, pool):
        self.pool = pool

    async def get_job(self, job_id):
        return {"id": job_id, "user_id": "modular-safe-user", "project_id": "modular-safe-project"}


class _DummyProofService:
    def set_pool(self, pool):
        self.pool = pool



def safe_import_mode_enabled() -> bool:
    for key in SAFE_IMPORT_FLAGS:
        if os.environ.get(key, "").strip().lower() in {"1", "true", "yes", "on"}:
            return True
    return False


@contextmanager
def modular_safe_import_env() -> Iterator[None]:
    changed: dict[str, str | None] = {}
    if not safe_import_mode_enabled():
        yield
        return

    for key, value in SAFE_IMPORT_DEFAULTS.items():
        if not os.environ.get(key, "").strip():
            changed[key] = None
            os.environ[key] = value
    installed = _install_safe_import_stubs()
    try:
        yield
    finally:
        for mod_name in installed:
            sys.modules.pop(mod_name, None)
        for key, previous in changed.items():
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous

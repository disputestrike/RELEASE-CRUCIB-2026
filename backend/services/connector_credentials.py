from __future__ import annotations

import base64
import hashlib
import os
from typing import Any, Dict

from cryptography.fernet import Fernet


def _fernet() -> Fernet:
    raw = os.environ.get("CONNECTOR_CREDENTIAL_KEY", "").strip()
    if raw:
        key = raw.encode("utf-8")
        try:
            return Fernet(key)
        except Exception:
            digest = hashlib.sha256(raw.encode("utf-8")).digest()
            key = base64.urlsafe_b64encode(digest)
    else:
        secret = (
            os.environ.get("JWT_SECRET")
            or os.environ.get("SECRET_KEY")
            or os.environ.get("DATABASE_URL")
            or "crucibai-local-connector-key"
        )
        digest = hashlib.sha256(secret.encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt((value or "").encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    return _fernet().decrypt((value or "").encode("utf-8")).decode("utf-8")


def redact(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}...{value[-4:]}"


def hash_secret(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def public_credential_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    safe = dict(doc or {})
    safe.pop("encrypted_access_token", None)
    safe.pop("encrypted_refresh_token", None)
    safe.pop("encrypted_api_token", None)
    return safe

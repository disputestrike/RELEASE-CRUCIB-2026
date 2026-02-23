"""
Encrypt workspace_env API keys and secrets at rest.
Uses Fernet (AES-128-CBC + HMAC). Set CRUCIBAI_ENCRYPTION_KEY in env (32-byte url-safe base64, e.g. from Fernet.generate_key()).
If unset, values are stored in plaintext (backward compatible).
"""
import os
from typing import Dict, Any

_FERNET = None

# Keys in workspace_env that are encrypted at rest
_SECRET_KEYS = frozenset({
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "VERCEL_TOKEN",
    "NETLIFY_TOKEN",
    "GOOGLE_API_KEY",
    "TAVILY_API_KEY",
})


def _get_fernet():
    global _FERNET
    if _FERNET is not None:
        return _FERNET
    key = (os.environ.get("CRUCIBAI_ENCRYPTION_KEY") or "").strip()
    if not key:
        return None
    try:
        from cryptography.fernet import Fernet, InvalidToken
        _FERNET = Fernet(key.encode() if isinstance(key, str) else key)
        return _FERNET
    except Exception:
        return None


def encrypt_env(env: Dict[str, Any]) -> Dict[str, Any]:
    """Encrypt secret values in env before writing to DB. Returns new dict."""
    if not env:
        return env
    f = _get_fernet()
    if not f:
        return env
    out = dict(env)
    for k in list(out.keys()):
        if k in _SECRET_KEYS and out[k]:
            v = (out[k] or "").strip()
            if v:
                try:
                    out[k] = f.encrypt(v.encode("utf-8")).decode("utf-8")
                except Exception:
                    pass
    return out


def decrypt_env(env: Dict[str, Any]) -> Dict[str, Any]:
    """Decrypt secret values when reading from DB. Supports legacy plaintext."""
    if not env:
        return env
    f = _get_fernet()
    if not f:
        return env
    out = dict(env)
    for k in list(out.keys()):
        if k in _SECRET_KEYS and out[k]:
            v = out[k]
            if isinstance(v, bytes):
                v = v.decode("utf-8", errors="replace")
            v = (v or "").strip()
            if not v:
                continue
            try:
                out[k] = f.decrypt(v.encode("utf-8")).decode("utf-8")
            except Exception:
                # Legacy plaintext or wrong key — leave as-is
                pass
    return out

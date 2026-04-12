# backend/sandbox/egress_filter.py
"""
Network egress filtering for agent containers.
Only allows whitelisted external API calls.
Prevents agents from exfiltrating data or calling unauthorized services.
"""

import os
import logging
from typing import Dict, List, Optional
from urllib.parse import urlparse
import re

logger = logging.getLogger(__name__)


class EgressFilter:
    """
    Enforce network egress policy for agent sandboxes.
    Only whitelisted domains can be accessed.
    """

    WHITELIST = {
        # LLM APIs
        "api.anthropic.com": ["https"],
        "api.cerebras.ai": ["https"],
        "api.openai.com": ["https"],
        "api.together.ai": ["https"],
        # Data & Database Services
        "api.supabase.io": ["https"],
        "db.supabase.io": ["https"],
        "storage.googleapis.com": ["https"],
        "firebaseio.com": ["https"],
        # Package Managers
        "registry.npmjs.org": ["https"],
        "www.npmjs.com": ["https"],
        "pypi.org": ["https"],
        "files.pythonhosted.org": ["https"],
        "packages.python.org": ["https"],
        # Version Control
        "github.com": ["https"],
        "raw.githubusercontent.com": ["https"],
        "gitlab.com": ["https"],
        "bitbucket.org": ["https"],
        # CDNs (for assets)
        "cdn.jsdelivr.net": ["https"],
        "unpkg.com": ["https"],
        "cdn.jsdelivr.net": ["https"],
        # DNS (localhost only)
        "localhost": ["http", "https"],
        "127.0.0.1": ["http", "https"],
    }

    # Deny list (always blocked, even if whitelisted)
    DENY_LIST = {
        "localhost:22",  # SSH
        "localhost:3306",  # MySQL
        "localhost:5432",  # PostgreSQL
        "127.0.0.1:22",
    }

    @classmethod
    def is_whitelisted(cls, url: str) -> bool:
        """Check if a URL is allowed for agent access."""
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname or parsed.netloc.split(":")[0]
            protocol = parsed.scheme or "https"
            port = parsed.port

            # Check deny list first
            deny_key = f"{hostname}:{port}" if port else hostname
            if deny_key in cls.DENY_LIST:
                logger.warning(f"URL blocked by deny list: {url}")
                return False

            # Check whitelist
            if hostname not in cls.WHITELIST:
                logger.warning(f"Hostname not whitelisted: {hostname}")
                return False

            allowed_protocols = cls.WHITELIST[hostname]
            if protocol not in allowed_protocols:
                logger.warning(f"Protocol not allowed for {hostname}: {protocol}")
                return False

            return True
        except Exception as e:
            logger.error(f"Error checking URL: {e}")
            return False

    @classmethod
    def validate_request(
        cls, method: str, url: str, headers: Optional[Dict] = None
    ) -> None:
        """
        Validate a request before agent makes it.
        Raises PermissionError if not allowed.
        """
        if not cls.is_whitelisted(url):
            raise PermissionError(
                f"Network request to {url} not whitelisted. "
                f"Contact support to allow this domain."
            )

        # Check headers for exposed secrets
        if headers:
            for key, value in headers.items():
                if cls._contains_secret(str(value)):
                    raise ValueError(
                        f"Detected secret pattern in header '{key}'. "
                        f"Use environment variables instead of hardcoding."
                    )

    @classmethod
    def _contains_secret(cls, text: str) -> bool:
        """Detect common secret patterns."""
        patterns = [
            r"sk-[A-Za-z0-9_-]{8,}",  # OpenAI / generic secret-like key
            r"sk_[A-Za-z0-9_]+",  # Stripe/Supabase style
            r'api[_-]?key["\s:=]+["\']?(sk-[A-Za-z0-9_-]{6,}|[A-Za-z0-9_-]{6,})',
            r'password["\s:=]+["\']?(.{6,})',
            r'secret["\s:=]+["\']?(.{6,})',
            r'token["\s:=]+["\']?([A-Za-z0-9_.-]{8,})',
            r'authorization["\s:=]+Bearer\s+([A-Za-z0-9_.-]{8,})',
        ]

        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        return False


# Monkey-patch requests library to enforce egress filter
def install_egress_filter():
    """Install egress filter in agent's requests library."""
    try:
        import requests

        original_request = requests.Session.request

        def filtered_request(self, method, url, **kwargs):
            # Validate before making request
            EgressFilter.validate_request(method, url, kwargs.get("headers"))
            # Allow the request
            return original_request(self, method, url, **kwargs)

        requests.Session.request = filtered_request
        logger.info("Egress filter installed")
    except ImportError:
        logger.warning("requests library not available for egress filtering")


# Install on module import
install_egress_filter()

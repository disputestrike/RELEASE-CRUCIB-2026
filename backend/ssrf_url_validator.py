"""
SSRF and URL validation for tool agents (API, Browser).
Blocks private IPs, localhost, file:, and optionally restricts to allowlist.
"""
import ipaddress
import re
from typing import Optional, Set
from urllib.parse import urlparse

# Private/unroutable ranges per RFC 1918, RFC 4193, link-local, loopback, etc.
_PRIVATE_NETWORKS = (
    "127.0.0.0/8",      # loopback
    "10.0.0.0/8",       # private
    "172.16.0.0/12",    # private
    "192.168.0.0/16",   # private
    "169.254.0.0/16",   # link-local
    "::1/128",          # IPv6 loopback
    "fc00::/7",         # IPv6 unique local
    "fe80::/10",        # IPv6 link-local
)
_BLOCKED_HOSTS = {"localhost", "localhost.localdomain", "0.0.0.0"}
_BLOCKED_SCHEMES = {"file", "ftp", "gopher"}


def _parse_host(host: str) -> Optional[str]:
    if not host:
        return None
    host = host.strip().lower()
    # Strip brackets for IPv6
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    return host or None


def is_url_safe(
    url: str,
    *,
    allow_private: bool = False,
    allowlist_hosts: Optional[Set[str]] = None,
    blocklist_hosts: Optional[Set[str]] = None,
    require_https: bool = False,
) -> bool:
    """
    Return True if URL is safe (no SSRF to private/metadata).
    - Blocks file:, localhost, private IPs unless allow_private=True.
    - Optional allowlist: if set, only those hostnames are allowed.
    - Optional blocklist: additional hosts to block.
    - If require_https=True, only https (and http for localhost when allowed) allowed.
    """
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    scheme = (parsed.scheme or "").lower()
    if scheme in _BLOCKED_SCHEMES:
        return False
    if require_https and scheme not in ("https", "http"):
        return False
    if require_https and scheme == "http":
        host = _parse_host(parsed.hostname or parsed.netloc)
        if host not in ("localhost", "127.0.0.1"):
            return False
    host = _parse_host(parsed.hostname or parsed.netloc)
    if not host:
        return False
    if host in _BLOCKED_HOSTS and not allow_private:
        return False
    if blocklist_hosts and host in blocklist_hosts:
        return False
    if allowlist_hosts:
        if host not in allowlist_hosts:
            return False
        return True
    # Resolve host to IP and check private ranges
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        # Hostname (e.g. example.com) — allow unless blocklist
        return True
    if allow_private:
        return True
    for net in _PRIVATE_NETWORKS:
        if addr in ipaddress.ip_network(net):
            return False
    return True


def validate_url_for_request(
    url: str,
    *,
    allow_private: bool = False,
    allowlist_hosts: Optional[Set[str]] = None,
    require_https: bool = False,
) -> None:
    """
    Raise ValueError if URL is not safe for outbound request (SSRF protection).
    """
    if not is_url_safe(
        url,
        allow_private=allow_private,
        allowlist_hosts=allowlist_hosts,
        require_https=require_https,
    ):
        raise ValueError(f"URL not allowed (SSRF policy): {url[:200]}")

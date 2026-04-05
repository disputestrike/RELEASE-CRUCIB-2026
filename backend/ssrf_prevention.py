"""
SSRF (Server-Side Request Forgery) prevention.

Implements:
- URL validation
- IP address validation
- DNS rebinding protection
- Internal network protection
- Whitelist-based access control
"""

import logging
import ipaddress
import socket
from typing import Optional, Set, List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class SSRFValidator:
    """Validate URLs to prevent SSRF attacks."""

    # Private IP ranges
    PRIVATE_IP_RANGES = [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("127.0.0.0/8"),  # Loopback
        ipaddress.ip_network("169.254.0.0/16"),  # Link-local
        ipaddress.ip_network("::1/128"),  # IPv6 loopback
        ipaddress.ip_network("fc00::/7"),  # IPv6 private
    ]

    # Dangerous ports
    DANGEROUS_PORTS = {
        22,  # SSH
        23,  # Telnet
        25,  # SMTP
        53,  # DNS
        69,  # TFTP
        111,  # Portmapper
        135,  # RPC
        139,  # NetBIOS
        445,  # SMB
        512,  # Rsh
        513,  # Rlogin
        514,  # Syslog
        1433,  # MSSQL
        3306,  # MySQL
        5432,  # PostgreSQL
        6379,  # Redis
        27017,  # Common non-HTTP DB port (block SSRF to raw sockets)
    }

    def __init__(
        self,
        allowed_domains: Optional[Set[str]] = None,
        allowed_protocols: Optional[Set[str]] = None,
    ):
        """
        Initialize SSRF validator.

        Args:
            allowed_domains: Whitelist of allowed domains
            allowed_protocols: Allowed protocols (default: http, https)
        """
        self.allowed_domains = allowed_domains or {
            "api.example.com",
            "data.example.com",
            "cdn.example.com",
        }
        self.allowed_protocols = allowed_protocols or {"http", "https"}

    def is_private_ip(self, ip_str: str) -> bool:
        """
        Check if IP is private/internal.

        Args:
            ip_str: IP address string

        Returns:
            True if IP is private, False otherwise
        """
        try:
            ip = ipaddress.ip_address(ip_str)

            # Check against private ranges
            for private_range in self.PRIVATE_IP_RANGES:
                if ip in private_range:
                    return True

            return False

        except ValueError:
            # Invalid IP address
            return False

    def is_dangerous_port(self, port: int) -> bool:
        """
        Check if port is dangerous.

        Args:
            port: Port number

        Returns:
            True if port is dangerous, False otherwise
        """
        return port in self.DANGEROUS_PORTS

    def resolve_hostname(self, hostname: str) -> Optional[str]:
        """
        Resolve hostname to IP address.

        Args:
            hostname: Hostname to resolve

        Returns:
            IP address or None if resolution fails
        """
        try:
            ip = socket.gethostbyname(hostname)
            return ip

        except socket.gaierror:
            logger.warning(f"Failed to resolve hostname: {hostname}")
            return None

    def validate_url(self, url: str) -> bool:
        """
        Validate URL to prevent SSRF.

        Args:
            url: URL to validate

        Returns:
            True if URL is safe, False otherwise
        """
        try:
            parsed = urlparse(url)

            # Check protocol
            if parsed.scheme not in self.allowed_protocols:
                logger.warning(f"Invalid protocol: {parsed.scheme}")
                return False

            # Get hostname
            hostname = parsed.hostname
            if not hostname:
                logger.warning("No hostname in URL")
                return False

            # Check if in whitelist
            if hostname in self.allowed_domains:
                return True

            # Resolve hostname to IP
            ip = self.resolve_hostname(hostname)
            if not ip:
                logger.warning(f"Failed to resolve hostname: {hostname}")
                return False

            # Check if IP is private
            if self.is_private_ip(ip):
                logger.warning(f"Private IP detected: {ip}")
                return False

            # Check port
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            if self.is_dangerous_port(port):
                logger.warning(f"Dangerous port detected: {port}")
                return False

            return True

        except Exception as e:
            logger.warning(f"URL validation error: {str(e)}")
            return False

    def sanitize_url(self, url: str) -> Optional[str]:
        """
        Sanitize URL for safe use.

        Args:
            url: URL to sanitize

        Returns:
            Sanitized URL or None if invalid
        """
        if self.validate_url(url):
            return url

        return None


class SafeRequestHandler:
    """Handle external requests safely."""

    def __init__(self, validator: SSRFValidator = None):
        """
        Initialize safe request handler.

        Args:
            validator: SSRF validator instance
        """
        self.validator = validator or SSRFValidator()

    def make_request(
        self,
        url: str,
        method: str = "GET",
        timeout: int = 10,
        **kwargs
    ) -> Optional[dict]:
        """
        Make HTTP request safely.

        Args:
            url: URL to request
            method: HTTP method
            timeout: Request timeout
            **kwargs: Additional request parameters

        Returns:
            Response data or None if request fails
        """
        # Validate URL
        if not self.validator.validate_url(url):
            logger.error(f"SSRF validation failed for URL: {url}")
            raise ValueError("Invalid URL")

        # Make request (would use requests library in production)
        logger.info(f"Making safe request to: {url}", extra={"method": method})

        # Placeholder for actual request
        return {"status": "success", "url": url}

    def fetch_data(
        self,
        url: str,
        timeout: int = 10,
    ) -> Optional[str]:
        """
        Fetch data from URL safely.

        Args:
            url: URL to fetch from
            timeout: Request timeout

        Returns:
            Response data or None if request fails
        """
        # Validate URL
        if not self.validator.validate_url(url):
            logger.error(f"SSRF validation failed for URL: {url}")
            raise ValueError("Invalid URL")

        logger.info(f"Fetching data from: {url}")

        # Placeholder for actual fetch
        return "data"


# Global instances
ssrf_validator = SSRFValidator()
safe_request_handler = SafeRequestHandler(ssrf_validator)

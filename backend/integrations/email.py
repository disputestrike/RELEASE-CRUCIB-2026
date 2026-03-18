"""
Email: uses email_service when SMTP_* set, else no-op.
Contact, enterprise, and automation workflows use this single path.
"""
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

_EmailService = None


def _get_email_service():
    global _EmailService
    if _EmailService is not None:
        return _EmailService
    if not os.environ.get("SMTP_HOST"):
        return None
    try:
        from email_service import EmailService
        _EmailService = EmailService()
        return _EmailService
    except Exception as e:
        logger.warning("EmailService init failed: %s", e)
        return None


def get_email() -> Optional[Any]:
    """Return EmailService if SMTP configured, else None."""
    return _get_email_service()


async def send_email(
    to: str,
    subject: str,
    body_html: Optional[str] = None,
    body_text: Optional[str] = None,
) -> bool:
    """Send email (async). Returns True if sent, False if skipped (no SMTP)."""
    svc = _get_email_service()
    if not svc:
        return False
    try:
        await svc.send_email(to_email=to, subject=subject, html_body=body_html or "", text_body=body_text)
        return True
    except Exception as e:
        logger.exception("Send email failed: %s", e)
        return False


def send_email_sync(to: str, subject: str, body_text: str) -> bool:
    """Synchronous send (for server contact/enterprise that use smtplib)."""
    import smtplib
    from email.mime.text import MIMEText
    host = os.environ.get("SMTP_HOST")
    if not host:
        return False
    try:
        msg = MIMEText(body_text)
        msg["Subject"] = subject
        msg["From"] = os.environ.get("SMTP_FROM", "noreply@crucibai.com")
        msg["To"] = to
        port = int(os.environ.get("SMTP_PORT", "587"))
        with smtplib.SMTP(host, port) as s:
            if os.environ.get("SMTP_USER"):
                s.starttls()
                s.login(os.environ.get("SMTP_USER", ""), os.environ.get("SMTP_PASSWORD", ""))
            s.send_message(msg)
        return True
    except Exception as e:
        logger.exception("Send email failed: %s", e)
        return False

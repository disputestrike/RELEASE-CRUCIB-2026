"""
File storage: S3 when AWS_* set, else local uploads/ directory.
Users get durable storage when they add AWS credentials; otherwise local disk.
"""

import logging
import os
import uuid
from pathlib import Path
from typing import BinaryIO, Optional

logger = logging.getLogger(__name__)

UPLOADS_DIR = Path(__file__).resolve().parent.parent / "uploads"
_s3_client = None


def _ensure_uploads_dir():
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _s3_configured() -> bool:
    return bool(
        os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY")
    )


def get_storage() -> str:
    """Return 's3' or 'local'."""
    if _s3_configured() and os.environ.get("AWS_S3_BUCKET"):
        return "s3"
    return "local"


def _get_s3():
    global _s3_client
    if _s3_client is None and _s3_configured():
        try:
            import boto3

            _s3_client = boto3.client(
                "s3",
                region_name=os.environ.get("AWS_REGION", "us-east-1"),
                aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
                aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
            )
        except Exception as e:
            logger.warning("S3 init failed: %s", e)
    return _s3_client


def upload_file(key: str, body: bytes, content_type: Optional[str] = None) -> str:
    """Upload file; return URL or path. Key is e.g. 'exports/abc.zip'."""
    if get_storage() == "s3":
        bucket = os.environ.get("AWS_S3_BUCKET", "crucibai-uploads")
        s3 = _get_s3()
        if s3:
            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=body,
                ContentType=content_type or "application/octet-stream",
            )
            return f"https://{bucket}.s3.{os.environ.get('AWS_REGION', 'us-east-1')}.amazonaws.com/{key}"
    _ensure_uploads_dir()
    path = UPLOADS_DIR / key.replace("/", os.sep)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return f"/uploads/{key}"


def get_file_url(key: str) -> Optional[str]:
    """Return public URL for key if stored (S3 or local path)."""
    if get_storage() == "s3":
        bucket = os.environ.get("AWS_S3_BUCKET", "crucibai-uploads")
        return f"https://{bucket}.s3.{os.environ.get('AWS_REGION', 'us-east-1')}.amazonaws.com/{key}"
    p = UPLOADS_DIR / key.replace("/", os.sep)
    return str(p) if p.exists() else None


def read_file(key: str) -> Optional[bytes]:
    """Read file by key (local storage). For S3, use boto3 get_object in caller."""
    if get_storage() == "s3":
        s3 = _get_s3()
        if s3:
            r = s3.get_object(
                Bucket=os.environ.get("AWS_S3_BUCKET", "crucibai-uploads"), Key=key
            )
            return r["Body"].read()
        return None
    p = UPLOADS_DIR / key.replace("/", os.sep)
    return p.read_bytes() if p.exists() else None

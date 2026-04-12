"""
CrucibAI Integrations — single place for queue, storage, email.
All green when env is set; graceful no-op when not.
"""

from integrations.queue import get_queue, enqueue_job  # enqueue_job is async
from integrations.storage import get_storage, upload_file, get_file_url, read_file
from integrations.email import get_email, send_email, send_email_sync

__all__ = [
    "get_queue",
    "enqueue_job",
    "get_storage",
    "upload_file",
    "get_file_url",
    "read_file",
    "get_email",
    "send_email",
    "send_email_sync",
]

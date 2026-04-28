"""Optional one-line provenance headers for generated source files (§5.2 artifact lineage)."""

from __future__ import annotations

import os
from typing import Optional

_LINEAGE_EXTS = frozenset(
    {".py", ".jsx", ".tsx", ".js", ".ts", ".mjs", ".cjs", ".css", ".scss", ".less"}
)


def lineage_enabled() -> bool:
    raw = os.environ.get("CRUCIBAI_FILE_LINEAGE", "1")
    return str(raw).strip().lower() not in ("0", "false", "no", "off")


def prepend_lineage_banner(
    rel: str,
    content: str,
    job_id: Optional[str],
) -> str:
    """
    Prepend a short machine-parseable banner so exports can relate files to a job id.
    Skips duplicate banners and non-text-heavy extensions.
    """
    if not job_id or not content.strip():
        return content
    if not lineage_enabled():
        return content
    peek = content[:4096]
    if "crucib-ai:lineage" in peek:
        return content
    ext = os.path.splitext(rel)[1].lower()
    if ext not in _LINEAGE_EXTS:
        return content
    safe_job = "".join(job_id.replace("\r", "").split())[:56]
    rp = rel.replace("\\", "/")
    if ext == ".py":
        banner = f"# crucib-ai:lineage job={safe_job} path={rp}\n"
    else:
        banner = f"/* crucib-ai:lineage job={safe_job} path={rp} */\n"
    return banner + content

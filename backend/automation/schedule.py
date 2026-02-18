"""
Schedule: compute next_run_at from cron_expression or run_at (one-time).
"""
from datetime import datetime, timezone
from typing import Optional

try:
    from croniter import croniter
except ImportError:
    croniter = None


def next_run_at(
    cron_expression: Optional[str] = None,
    run_at: Optional[str] = None,
    from_time: Optional[datetime] = None,
) -> Optional[datetime]:
    """
    Next run time. Either one-time run_at or next occurrence of cron.
    from_time defaults to now (UTC).
    """
    now = from_time or datetime.now(timezone.utc)
    if run_at:
        try:
            t = datetime.fromisoformat(run_at.replace("Z", "+00:00"))
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            return t if t >= now else None
        except Exception:
            return None
    if cron_expression and croniter:
        try:
            it = croniter(cron_expression, now)
            return it.get_next(datetime)
        except Exception:
            return None
    return None


def is_one_time(trigger_config: dict) -> bool:
    """True if trigger uses run_at (one-time) only."""
    return bool(trigger_config.get("run_at") and not trigger_config.get("cron_expression"))

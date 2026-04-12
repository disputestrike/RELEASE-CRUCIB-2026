"""
CrucibAI Credit Tracker
=======================
Tracks credit usage per model and user tier.
Uses the PostgreSQL JSONB wrapper in db_pg.py (not raw asyncpg).
"""

import hashlib
import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


def _credit_audit_log_enabled() -> bool:
    return (os.environ.get("CRUCIBAI_CREDIT_BALANCE_LOG") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


class ModelCost(str, Enum):
    """Cost per 1M tokens for each model"""

    LLAMA = 0.0
    CEREBRAS = 0.27
    HAIKU = 0.80


class CreditTracker:
    """Tracks credit usage and deductions based on model used."""

    MODEL_CREDIT_COST = {
        "llama": 0.0,
        "cerebras": 0.00027,
        "haiku": 0.00080,
    }

    @staticmethod
    def calculate_credit_cost(
        model_name: str, tokens_used: int, user_tier: str = "free"
    ) -> float:
        if user_tier == "free" and model_name != "haiku":
            return 0.0
        base_cost = CreditTracker.MODEL_CREDIT_COST.get(model_name, 0)
        credit_cost = (tokens_used / 1000) * base_cost
        return max(1, round(credit_cost)) if credit_cost > 0 else 0.0

    @staticmethod
    def _usage_id_for_idempotency(user_id: str, idempotency_key: str) -> str:
        h = hashlib.sha256(f"{user_id}\0{idempotency_key}".encode("utf-8")).hexdigest()
        return f"usage_idem_{h}"

    @staticmethod
    async def record_usage(
        db,
        user_id: str,
        model_name: str,
        tokens_used: int,
        user_tier: str,
        agent_name: str,
        project_id: str,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record LLM usage and deduct credits via db_pg.

        If ``idempotency_key`` is set, the same key for the same ``user_id`` replays without
        a second deduction (safe for client retries / double-submit).
        """
        try:
            credit_cost = CreditTracker.calculate_credit_cost(
                model_name, tokens_used, user_tier
            )

            if idempotency_key:
                uid = CreditTracker._usage_id_for_idempotency(user_id, idempotency_key)
                existing = await db.usage_log.find_one({"_id": uid})
                if existing:
                    user = await db.users.find_one(
                        {"id": user_id}, {"credit_balance": 1}
                    )
                    remaining = user.get("credit_balance", 0) if user else 0
                    return {
                        "usage_id": uid,
                        "credits_deducted": 0.0,
                        "remaining_credits": remaining,
                        "model": model_name,
                        "replay": True,
                    }

            usage_id = (
                CreditTracker._usage_id_for_idempotency(user_id, idempotency_key)
                if idempotency_key
                else f"usage_{user_id}_{datetime.now(timezone.utc).timestamp()}"
            )

            usage_record = {
                "_id": usage_id,
                "user_id": user_id,
                "model": model_name,
                "tokens_used": tokens_used,
                "credits_deducted": credit_cost,
                "user_tier": user_tier,
                "agent_name": agent_name,
                "project_id": project_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            if idempotency_key:
                usage_record["idempotency_key"] = idempotency_key

            try:
                await db.usage_log.insert_one(usage_record)
            except Exception as exc:
                # Concurrent duplicate submit with same idempotency key
                err = str(exc).lower()
                if idempotency_key and ("duplicate" in err or "e11000" in err):
                    user = await db.users.find_one(
                        {"id": user_id}, {"credit_balance": 1}
                    )
                    remaining = user.get("credit_balance", 0) if user else 0
                    return {
                        "usage_id": CreditTracker._usage_id_for_idempotency(
                            user_id, idempotency_key
                        ),
                        "credits_deducted": 0.0,
                        "remaining_credits": remaining,
                        "model": model_name,
                        "replay": True,
                    }
                raise

            if credit_cost > 0:
                await db.users.update_one(
                    {"id": user_id}, {"$inc": {"credit_balance": -credit_cost}}
                )

            user = await db.users.find_one({"id": user_id}, {"credit_balance": 1})
            remaining = user.get("credit_balance", 0) if user else 0

            if remaining < 0:
                logger.warning(
                    "credit_balance_negative user_id=%s balance=%s model=%s deducted=%s",
                    user_id,
                    remaining,
                    model_name,
                    credit_cost,
                )
            if _credit_audit_log_enabled():
                logger.info(
                    "credit_balance_event user_id=%s delta=%s balance_after=%s model=%s tokens=%s",
                    user_id,
                    -float(credit_cost),
                    remaining,
                    model_name,
                    tokens_used,
                )
            elif remaining >= 0:
                logger.info(
                    "Usage recorded: %s used %s, deducted %s credits",
                    user_id,
                    model_name,
                    credit_cost,
                )
            return {
                "usage_id": usage_record["_id"],
                "credits_deducted": credit_cost,
                "remaining_credits": remaining,
                "model": model_name,
            }

        except Exception as e:
            logger.error(f"Failed to record usage: {e}")
            return {
                "usage_id": None,
                "credits_deducted": 0,
                "remaining_credits": 0,
                "error": str(e),
            }

    @staticmethod
    async def get_user_usage_stats(db, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get user LLM usage stats."""
        try:
            from datetime import timedelta

            cutoff_date = (
                datetime.now(timezone.utc) - timedelta(days=days)
            ).isoformat()
            usage_records = await db.usage_log.find(
                {"user_id": user_id, "timestamp": {"$gte": cutoff_date}}
            ).to_list(1000)

            stats: Dict[str, Any] = {
                "total_tokens": 0,
                "total_credits": 0,
                "by_model": {
                    "llama": {"tokens": 0, "credits": 0, "count": 0},
                    "cerebras": {"tokens": 0, "credits": 0, "count": 0},
                    "haiku": {"tokens": 0, "credits": 0, "count": 0},
                },
                "by_agent": {},
            }

            for record in usage_records:
                model = record.get("model", "unknown")
                tokens = record.get("tokens_used", 0)
                credits = record.get("credits_deducted", 0)
                agent = record.get("agent_name", "unknown")

                stats["total_tokens"] += tokens
                stats["total_credits"] += credits

                if model in stats["by_model"]:
                    stats["by_model"][model]["tokens"] += tokens
                    stats["by_model"][model]["credits"] += credits
                    stats["by_model"][model]["count"] += 1

                if agent not in stats["by_agent"]:
                    stats["by_agent"][agent] = {"tokens": 0, "credits": 0}
                stats["by_agent"][agent]["tokens"] += tokens
                stats["by_agent"][agent]["credits"] += credits

            return stats

        except Exception as e:
            logger.error(f"Failed to get usage stats: {e}")
            return {}


# Singleton
tracker = CreditTracker()

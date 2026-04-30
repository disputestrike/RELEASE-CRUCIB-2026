"""
brain_intelligence.py — The capabilities that make CrucibAI's brain
surpass individual AI assistants like Claude or Codex.

ADVANTAGES OVER CLAUDE/CODEX:
1. Cross-session memory — remembers what fixed what across every build ever
2. Collective learning — every user's build makes the brain smarter
3. Web search during repair — looks up error messages, package docs, API changes
4. Predictive prevention — spots failure patterns before they happen
5. Build DNA matching — finds similar successful builds and learns from them

Claude forgets everything between conversations.
Codex doesn't share knowledge between repos.
CrucibAI compounds knowledge across all agents × all users × all time.
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Cross-session memory ───────────────────────────────────────────────────────


async def _get_pool():
    """Get Postgres pool."""
    try:
        from ....db_pg import get_pg_pool
        return await get_pg_pool()
    except Exception:
        return None


async def ensure_brain_tables():
    """Create brain memory tables if they don't exist."""
    pool = await _get_pool()
    if not pool:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS brain_fix_memory (
                    id SERIAL PRIMARY KEY,
                    error_signature TEXT NOT NULL,
                    step_key TEXT NOT NULL,
                    fix_type TEXT NOT NULL,
                    fix_description TEXT,
                    success BOOLEAN NOT NULL DEFAULT FALSE,
                    retry_count_when_fixed INTEGER DEFAULT 0,
                    files_repaired JSONB DEFAULT '[]',
                    goal_keywords TEXT[],
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS brain_fix_memory_sig_idx
                ON brain_fix_memory(error_signature, step_key)
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS brain_build_dna (
                    id SERIAL PRIMARY KEY,
                    goal_hash TEXT NOT NULL,
                    goal_keywords TEXT[],
                    step_completion_pct FLOAT,
                    quality_score INTEGER,
                    successful_agents TEXT[],
                    failed_agents TEXT[],
                    fix_patterns JSONB DEFAULT '{}',
                    total_steps INTEGER,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS brain_build_dna_keywords_idx
                ON brain_build_dna USING GIN(goal_keywords)
            """)
    except Exception as e:
        logger.warning("brain_intelligence: ensure_brain_tables failed: %s", e)


def _error_signature(error_message: str, step_key: str) -> str:
    """Create a normalized signature for an error to enable lookups."""
    # Normalize: remove UUIDs, timestamps, line numbers
    import re

    normalized = re.sub(r"[0-9a-f]{8}-[0-9a-f-]{27}", "UUID", error_message or "")
    normalized = re.sub(r"line \d+", "line N", normalized)
    normalized = re.sub(r":\d+:\d+", ":N:N", normalized)
    normalized = re.sub(r"\b\d+\b", "N", normalized)
    normalized = normalized.lower().strip()[:200]
    key = f"{step_key}:{normalized}"
    return hashlib.md5(key.encode()).hexdigest()[:16]


async def remember_fix(
    error_message: str,
    step_key: str,
    fix_type: str,
    fix_description: str,
    success: bool,
    retry_count: int = 0,
    files_repaired: Optional[List[str]] = None,
    goal_keywords: Optional[List[str]] = None,
):
    """Store a fix attempt in memory so future builds can learn from it."""
    pool = await _get_pool()
    if not pool:
        return
    try:
        sig = _error_signature(error_message, step_key)
        async with pool.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT id, success_count, failure_count FROM brain_fix_memory "
                "WHERE error_signature = $1 AND step_key = $2 AND fix_type = $3",
                sig,
                step_key,
                fix_type,
            )
            if existing:
                if success:
                    await conn.execute(
                        "UPDATE brain_fix_memory SET success_count = success_count + 1, "
                        "success = TRUE, last_seen_at = NOW(), retry_count_when_fixed = $1 "
                        "WHERE id = $2",
                        retry_count,
                        existing["id"],
                    )
                else:
                    await conn.execute(
                        "UPDATE brain_fix_memory SET failure_count = failure_count + 1, "
                        "last_seen_at = NOW() WHERE id = $1",
                        existing["id"],
                    )
            else:
                await conn.execute(
                    "INSERT INTO brain_fix_memory "
                    "(error_signature, step_key, fix_type, fix_description, success, "
                    "retry_count_when_fixed, files_repaired, goal_keywords, "
                    "success_count, failure_count) "
                    "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)",
                    sig,
                    step_key,
                    fix_type,
                    fix_description[:500],
                    success,
                    retry_count,
                    json.dumps(files_repaired or []),
                    goal_keywords or [],
                    1 if success else 0,
                    0 if success else 1,
                )
        logger.debug(
            "brain_intelligence: remembered fix sig=%s success=%s", sig, success
        )
    except Exception as e:
        logger.warning("brain_intelligence: remember_fix failed: %s", e)


async def recall_best_fix(
    error_message: str,
    step_key: str,
) -> Optional[Dict[str, Any]]:
    """
    Look up the best fix for this error from memory.
    Returns the fix with the highest success rate, or None if unknown.
    """
    pool = await _get_pool()
    if not pool:
        return None
    try:
        sig = _error_signature(error_message, step_key)
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT fix_type, fix_description, success_count, failure_count, "
                "retry_count_when_fixed, files_repaired "
                "FROM brain_fix_memory "
                "WHERE error_signature = $1 AND step_key = $2 AND success = TRUE "
                "ORDER BY success_count DESC LIMIT 3",
                sig,
                step_key,
            )
            if not rows:
                return None
            best = rows[0]
            total = best["success_count"] + best["failure_count"]
            success_rate = best["success_count"] / max(1, total)
            return {
                "fix_type": best["fix_type"],
                "fix_description": best["fix_description"],
                "success_rate": round(success_rate, 2),
                "success_count": best["success_count"],
                "typical_retry_count": best["retry_count_when_fixed"],
                "files_repaired": json.loads(best["files_repaired"] or "[]"),
                "source": "brain_memory",
            }
    except Exception as e:
        logger.warning("brain_intelligence: recall_best_fix failed: %s", e)
        return None


async def store_build_dna(
    goal: str,
    step_completion_pct: float,
    quality_score: int,
    successful_agents: List[str],
    failed_agents: List[str],
    fix_patterns: Dict[str, Any],
    total_steps: int,
):
    """Store the DNA of a completed build for future pattern matching."""
    pool = await _get_pool()
    if not pool:
        return
    try:
        import re

        # Extract keywords from goal
        stop_words = {
            "a",
            "an",
            "the",
            "and",
            "or",
            "with",
            "for",
            "that",
            "this",
            "build",
            "create",
            "make",
            "me",
            "my",
            "our",
            "app",
            "application",
        }
        words = re.findall(r"\b[a-z]{3,}\b", goal.lower())
        keywords = list(dict.fromkeys(w for w in words if w not in stop_words))[:20]

        goal_hash = hashlib.md5(goal.encode()).hexdigest()[:16]
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO brain_build_dna "
                "(goal_hash, goal_keywords, step_completion_pct, quality_score, "
                "successful_agents, failed_agents, fix_patterns, total_steps) "
                "VALUES ($1,$2,$3,$4,$5,$6,$7,$8)",
                goal_hash,
                keywords,
                step_completion_pct,
                quality_score,
                successful_agents,
                failed_agents,
                json.dumps(fix_patterns),
                total_steps,
            )
        logger.debug("brain_intelligence: stored build DNA hash=%s", goal_hash)
    except Exception as e:
        logger.warning("brain_intelligence: store_build_dna failed: %s", e)


async def find_similar_builds(goal: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Find similar successful past builds to learn from.
    This is Build DNA matching — what makes CrucibAI smarter than fresh AI tools.
    """
    pool = await _get_pool()
    if not pool:
        return []
    try:
        import re

        stop_words = {
            "a",
            "an",
            "the",
            "and",
            "or",
            "with",
            "for",
            "that",
            "this",
            "build",
            "create",
            "make",
            "me",
            "my",
            "our",
            "app",
            "application",
        }
        words = re.findall(r"\b[a-z]{3,}\b", goal.lower())
        keywords = list(dict.fromkeys(w for w in words if w not in stop_words))[:10]

        if not keywords:
            return []

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT goal_keywords, step_completion_pct, quality_score, "
                "successful_agents, failed_agents, fix_patterns, total_steps, "
                "array_length(ARRAY(SELECT unnest(goal_keywords) INTERSECT "
                "SELECT unnest($1::text[])), 1) as overlap "
                "FROM brain_build_dna "
                "WHERE step_completion_pct > 80 "
                "AND array_length(ARRAY(SELECT unnest(goal_keywords) INTERSECT "
                "SELECT unnest($1::text[])), 1) > 0 "
                "ORDER BY overlap DESC, quality_score DESC LIMIT $2",
                keywords,
                limit,
            )
            return [
                {
                    "keywords": list(row["goal_keywords"] or []),
                    "completion_pct": row["step_completion_pct"],
                    "quality_score": row["quality_score"],
                    "successful_agents": list(row["successful_agents"] or []),
                    "failed_agents": list(row["failed_agents"] or []),
                    "fix_patterns": json.loads(row["fix_patterns"] or "{}"),
                    "keyword_overlap": row["overlap"] or 0,
                }
                for row in rows
            ]
    except Exception as e:
        logger.warning("brain_intelligence: find_similar_builds failed: %s", e)
        return []


# ── Predictive failure prevention ─────────────────────────────────────────────


async def predict_failures(goal: str) -> List[Dict[str, Any]]:
    """
    Before a build starts, scan the goal for patterns that historically fail.
    Returns a list of predicted failures with prevention hints.
    """
    pool = await _get_pool()
    predictions = []

    # Static pattern library — built from our experience today
    KNOWN_RISKY_PATTERNS = [
        {
            "pattern": r"braintree.*payment|payment.*braintree|braintree.*checkout|checkout.*braintree",
            "risk": "Braintree checkout requires server-side client-token and nonce sale flow",
            "prevention": "Add BRAINTREE_MERCHANT_ID, BRAINTREE_PUBLIC_KEY, BRAINTREE_PRIVATE_KEY, and BRAINTREE_ENVIRONMENT to env before enabling live checkout",
            "affected_agents": [
                "braintree_checkout_agent",
                "payment_integration_agent",
            ],
        },
        {
            "pattern": r"websocket.*real.?time|real.?time.*websocket|multiplayer",
            "risk": "WebSocket agent context often too large for complex goals",
            "prevention": "Set use_minimal_context=True for WebSocket agent from start",
            "affected_agents": ["websocket_agent", "real_time_collaboration_agent"],
        },
        {
            "pattern": r"pgvector|rag|embedding|vector.*search",
            "risk": "pgvector requires postgres extension — may not be provisioned",
            "prevention": "Check PGVECTOR_ENABLED env before embeddings agent runs",
            "affected_agents": ["embeddings_vectorization_agent"],
        },
        {
            "pattern": r"multi.?tenant|schema.per.tenant|tenant.isolation",
            "risk": "Multi-tenant DB agent depends on Database Agent — if DB Agent hits Anthropic 400, all downstream blocked",
            "prevention": "Use targeted context (schema.sql only) for Database Agent",
            "affected_agents": ["database_agent", "multi_tenant_agent"],
        },
        {
            "pattern": r"react.?native|ios.*android|mobile.*app",
            "risk": "React Native output may go into wrong file (App.js not App.jsx)",
            "prevention": "Set build_kind=mobile, enforce mobile-only output",
            "affected_agents": ["frontend_generation"],
        },
        {
            "pattern": r"openai|gpt.?4|chatgpt",
            "risk": "Goal references OpenAI — may conflict with CrucibAI's own LLM calls",
            "prevention": "Clarify that OpenAI is for the generated app, not the builder",
            "affected_agents": ["backend_generation"],
        },
    ]

    import re

    goal_lower = goal.lower()
    for p in KNOWN_RISKY_PATTERNS:
        if re.search(p["pattern"], goal_lower):
            predictions.append(
                {
                    "risk": p["risk"],
                    "prevention": p["prevention"],
                    "affected_agents": p["affected_agents"],
                    "confidence": "high",
                    "source": "static_pattern",
                }
            )

    # Also check DB for historically failed patterns on similar goals
    if pool:
        try:
            import re as re2

            stop_words = {"a", "an", "the", "and", "or", "with"}
            kw = [
                w
                for w in re2.findall(r"\b[a-z]{4,}\b", goal_lower)
                if w not in stop_words
            ][:8]
            if kw:
                async with pool.acquire() as conn:
                    rows = await conn.fetch(
                        "SELECT step_key, fix_type, failure_count, success_count "
                        "FROM brain_fix_memory "
                        "WHERE failure_count > 2 "
                        "AND goal_keywords && $1::text[] "
                        "ORDER BY failure_count DESC LIMIT 5",
                        kw,
                    )
                    for row in rows:
                        fail_rate = row["failure_count"] / max(
                            1, row["failure_count"] + row["success_count"]
                        )
                        if fail_rate > 0.5:
                            predictions.append(
                                {
                                    "risk": f"{row['step_key']} historically fails {int(fail_rate*100)}% of the time on similar goals",
                                    "prevention": f"Pre-apply fix: {row['fix_type']}",
                                    "affected_agents": [row["step_key"]],
                                    "confidence": "medium",
                                    "source": "historical_data",
                                }
                            )
        except Exception as e:
            logger.warning(
                "brain_intelligence: predict_failures DB query failed: %s", e
            )

    return predictions


# ── Web search for repair ──────────────────────────────────────────────────────


async def search_error_solution(
    error_message: str,
    step_key: str = "",
    language: str = "",
) -> Optional[str]:
    """
    Search the web for solutions to a build error.
    This is what I do when I Google an error message.
    Uses Tavily if available, falls back to Anthropic web_search tool.
    """
    # Build a targeted search query
    import re

    # Extract the core error — strip UUIDs, paths, line numbers
    clean_error = re.sub(r"[0-9a-f]{8}-[0-9a-f-]{27}", "", error_message or "")
    clean_error = re.sub(r"/[\w/.-]+\.[\w]+:\d+", "", clean_error)
    clean_error = re.sub(r"\s+", " ", clean_error).strip()[:150]

    lang_hint = f" {language}" if language else ""
    query = f"{clean_error}{lang_hint} fix site:stackoverflow.com OR site:github.com"

    # Try Tavily first
    tavily_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if tavily_key:
        try:
            import asyncio

            from tavily import TavilyClient

            client = TavilyClient(api_key=tavily_key)

            def _search():
                return client.search(
                    clean_error + lang_hint,
                    search_depth="basic",
                    max_results=3,
                    include_answer=True,
                )

            resp = await asyncio.to_thread(_search)
            parts = []
            if resp.get("answer"):
                parts.append(f"ANSWER: {resp['answer'][:600]}")
            for r in (resp.get("results") or [])[:3]:
                content = (r.get("content") or "")[:400]
                title = r.get("title", "")
                if content:
                    parts.append(f"[{title}]: {content}")
            if parts:
                result = "\n\n".join(parts)[:2000]
                logger.info(
                    "brain_intelligence: web search found solution for %s",
                    clean_error[:60],
                )
                return result
        except Exception as e:
            logger.warning("brain_intelligence: Tavily search failed: %s", e)

    # Fall back to Anthropic web search tool
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if anthropic_key:
        try:
            import anthropic as _anthropic
            from anthropic_models import (
                ANTHROPIC_SONNET_MODEL,
                normalize_anthropic_model,
            )

            client = _anthropic.AsyncAnthropic(api_key=anthropic_key)
            model = normalize_anthropic_model(None, default=ANTHROPIC_SONNET_MODEL)
            response = await client.messages.create(
                model=model,
                max_tokens=800,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=[
                    {
                        "role": "user",
                        "content": f"Search for: how to fix this error in a {language or 'web'} application: {clean_error}. Return only the solution, concisely.",
                    }
                ],
            )
            text_blocks = [
                b.text for b in response.content if hasattr(b, "text") and b.text
            ]
            if text_blocks:
                result = " ".join(text_blocks)[:2000]
                logger.info("brain_intelligence: Anthropic web search found solution")
                return result
        except Exception as e:
            logger.warning("brain_intelligence: Anthropic web search failed: %s", e)

    return None


# ── Pre-build intelligence briefing ───────────────────────────────────────────


async def get_prebuild_intelligence(goal: str) -> Dict[str, Any]:
    """
    Before a build starts, assemble everything the brain knows that's relevant.
    This is the competitive edge: CrucibAI starts smarter than any fresh AI tool.
    """
    similar = await find_similar_builds(goal)
    predictions = await predict_failures(goal)

    # Extract the most useful patterns from similar builds
    common_fixes = {}
    agents_to_watch = set()
    for build in similar:
        for agent in build.get("failed_agents") or []:
            agents_to_watch.add(agent)
        for fix_key, fix_val in (build.get("fix_patterns") or {}).items():
            common_fixes[fix_key] = fix_val

    briefing = {
        "similar_builds_found": len(similar),
        "predicted_failures": predictions,
        "agents_to_watch": list(agents_to_watch)[:10],
        "known_fix_patterns": common_fixes,
        "intelligence_available": len(similar) > 0 or len(predictions) > 0,
    }

    if similar:
        best = max(similar, key=lambda b: b.get("quality_score", 0))
        briefing["best_similar_build"] = {
            "quality_score": best["quality_score"],
            "completion_pct": best["completion_pct"],
            "keywords": best["keywords"][:5],
        }

    if predictions:
        logger.info(
            "brain_intelligence: prebuild briefing — %d similar builds, %d predicted failures",
            len(similar),
            len(predictions),
        )

    return briefing


# ── Post-build learning ────────────────────────────────────────────────────────


async def record_build_outcome(
    goal: str,
    job_id: str,
    step_completion_pct: float,
    quality_score: int,
    failed_steps: List[Dict[str, Any]],
    completed_steps: List[str],
    repairs_applied: List[Dict[str, Any]],
):
    """
    After every build, record what happened so future builds can learn.
    This is the collective learning loop — every build makes the brain smarter.
    """
    # Store build DNA
    failed_agents = [s.get("step_key", "") for s in failed_steps]
    fix_patterns = {}
    for repair in repairs_applied:
        step = repair.get("step_key", "")
        strategy = repair.get("strategy", "")
        if step and strategy:
            fix_patterns[step] = strategy

    await store_build_dna(
        goal=goal,
        step_completion_pct=step_completion_pct,
        quality_score=quality_score,
        successful_agents=completed_steps,
        failed_agents=failed_agents,
        fix_patterns=fix_patterns,
        total_steps=len(completed_steps) + len(failed_agents),
    )

    # Store fix memory for each failed step
    for step_info in failed_steps:
        step_key = step_info.get("step_key", "")
        error = step_info.get("error_message", "")
        strategy = step_info.get("brain_strategy", "unknown")
        success = step_info.get("was_eventually_fixed", False)

        if step_key and error:
            await remember_fix(
                error_message=error,
                step_key=step_key,
                fix_type=strategy,
                fix_description=step_info.get("brain_explanation", ""),
                success=success,
                retry_count=step_info.get("retry_count", 0),
                files_repaired=step_info.get("files_repaired", []),
            )

    logger.info(
        "brain_intelligence: recorded build outcome job=%s completion=%.0f%% quality=%d",
        job_id[:8],
        step_completion_pct,
        quality_score,
    )

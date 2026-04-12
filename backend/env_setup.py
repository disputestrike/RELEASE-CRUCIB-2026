"""
CrucibAI Environment Validation Module
=======================================
Validates all required environment variables at startup.
Fails fast if critical vars are missing — no silent failures.
"""

import os
import sys
import logging

logger = logging.getLogger(__name__)

# Required environment variables grouped by category
REQUIRED_VARS = {
    "core": {
        "DATABASE_URL": "PostgreSQL connection string",
        "JWT_SECRET": "JWT signing secret for session tokens",
    },
    "auth": {
        "GOOGLE_CLIENT_ID": "Google OAuth client ID",
        "GOOGLE_CLIENT_SECRET": "Google OAuth client secret",
    },
    "app": {
        "FRONTEND_URL": "Frontend URL for CORS and redirects",
    },
}

OPTIONAL_VARS = {
    "payment": {
        "STRIPE_SECRET_KEY": "Stripe secret key for payment processing",
        "STRIPE_WEBHOOK_SECRET": "Stripe webhook signing secret",
        "STRIPE_PUBLISHABLE_KEY": "Stripe publishable key (frontend)",
    },
    "email": {
        "SMTP_HOST": "SMTP server hostname",
        "SMTP_PORT": "SMTP server port",
        "SMTP_USER": "SMTP username",
        "SMTP_PASS": "SMTP password",
        "FROM_EMAIL": "Default sender email address",
    },
    "llm": {
        "CEREBRAS_API_KEY": "Cerebras API key for LLM inference",
        "ANTHROPIC_API_KEY": "Anthropic API key (fallback LLM)",
    },
    "monitoring": {
        "ENVIRONMENT": "Deployment environment (production/staging/development)",
    },
}


def validate_environment(strict: bool = False) -> dict:
    """
    Validate all required environment variables.

    Args:
        strict: If True, exit process on missing required vars.
                If False, log warnings but continue.

    Returns:
        dict with 'missing_required', 'missing_optional', 'status' keys
    """
    missing_required = []
    missing_optional = []
    set_vars = []

    # Check required vars
    for category, vars_dict in REQUIRED_VARS.items():
        for var_name, description in vars_dict.items():
            value = os.environ.get(var_name, "").strip()
            if not value:
                missing_required.append((var_name, category, description))
                logger.error(f"❌ MISSING REQUIRED: {var_name} ({description})")
            else:
                set_vars.append(var_name)
                logger.info(f"✅ {var_name} is set")

    # Check optional vars
    for category, vars_dict in OPTIONAL_VARS.items():
        for var_name, description in vars_dict.items():
            value = os.environ.get(var_name, "").strip()
            if not value:
                missing_optional.append((var_name, category, description))
                logger.debug(f"Optional not set: {var_name} ({description})")
            else:
                set_vars.append(var_name)

    # Summary
    total_required = sum(len(v) for v in REQUIRED_VARS.values())
    total_optional = sum(len(v) for v in OPTIONAL_VARS.values())

    logger.info(f"\n{'='*50}")
    logger.info(f"Environment Validation Summary:")
    logger.info(
        f"  Required: {total_required - len(missing_required)}/{total_required} set"
    )
    logger.info(
        f"  Optional: {total_optional - len(missing_optional)}/{total_optional} set"
    )
    logger.info(f"{'='*50}")

    if missing_required and strict:
        logger.critical(
            f"FATAL: {len(missing_required)} required environment variables are missing. "
            f"Set them in Railway → Variables tab: "
            f"{', '.join(v[0] for v in missing_required)}"
        )
        sys.exit(1)

    return {
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "set_vars": set_vars,
        "status": "ok" if not missing_required else "degraded",
    }


def get_env(key: str, default: str = "", required: bool = False) -> str:
    """
    Safe environment variable getter with optional requirement enforcement.
    """
    value = os.environ.get(key, "").strip()
    if not value and required:
        raise RuntimeError(f"Required environment variable {key} is not set")
    return value or default

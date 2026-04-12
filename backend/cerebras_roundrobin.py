"""
Cerebras API Key Round-Robin Router
Prevents rate limiting by distributing requests across 5 API keys
"""

import os
import logging

logger = logging.getLogger(__name__)

# Get all Cerebras keys
CEREBRAS_KEYS = [
    os.environ.get("CEREBRAS_API_KEY", "").strip(),
    os.environ.get("CEREBRAS_API_KEY_2", "").strip(),
    os.environ.get("CEREBRAS_API_KEY_3", "").strip(),
    os.environ.get("CEREBRAS_API_KEY_4", "").strip(),
    os.environ.get("CEREBRAS_API_KEY_5", "").strip(),
]

# Filter out empty keys
CEREBRAS_KEYS = [k for k in CEREBRAS_KEYS if k]

# Current index for round-robin
_current_key_index = 0


def get_next_cerebras_key() -> str:
    """Get next Cerebras API key in round-robin rotation."""
    global _current_key_index

    if not CEREBRAS_KEYS:
        raise Exception("No Cerebras API keys configured")

    key = CEREBRAS_KEYS[_current_key_index]
    _current_key_index = (_current_key_index + 1) % len(CEREBRAS_KEYS)

    logger.debug(
        f"Cerebras key rotation: index {_current_key_index - 1} → {_current_key_index}"
    )

    return key


def get_cerebras_key_pool() -> list[str]:
    """Get all available Cerebras keys."""
    return CEREBRAS_KEYS.copy()


def has_cerebras_keys() -> bool:
    """Check if any Cerebras keys are configured."""
    return len(CEREBRAS_KEYS) > 0


def get_available_key_count() -> int:
    """Get number of available Cerebras keys."""
    return len(CEREBRAS_KEYS)

"""
LLM Client — Unified interface for Claude/Cerebras API calls.
Handles authentication, prompt building, structured response parsing, retries.
"""
import os
import json
import logging
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """LLM configuration from environment."""
    provider: str  # "anthropic" or "cerebras"
    api_key: str
    model: str
    max_tokens: int = 4000
    temperature: float = 0.7


def get_llm_config() -> Optional[LLMConfig]:
    """Load LLM config from environment variables."""
    try:
        # Try Claude first
        claude_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if claude_key:
            model = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
            return LLMConfig(
                provider="anthropic",
                api_key=claude_key,
                model=model,
            )
        
        # Try Cerebras
        cerebras_key = os.environ.get("CEREBRAS_API_KEY", "").strip()
        if cerebras_key:
            model = os.environ.get("CEREBRAS_MODEL", "llama-3.1-8b")
            return LLMConfig(
                provider="cerebras",
                api_key=cerebras_key,
                model=model,
            )
        
        logger.warning("No LLM API keys configured (ANTHROPIC_API_KEY or CEREBRAS_API_KEY)")
        return None
    except Exception as e:
        logger.error(f"Failed to load LLM config: {e}")
        return None


async def call_claude(
    system_prompt: str,
    user_prompt: str,
    config: LLMConfig,
    max_retries: int = 3,
) -> Optional[str]:
    """Call Claude API with retry logic."""
    try:
        import anthropic
        
        client = anthropic.AsyncAnthropic(api_key=config.api_key)
        
        for attempt in range(max_retries):
            try:
                message = await client.messages.create(
                    model=config.model,
                    max_tokens=config.max_tokens,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=config.temperature,
                )
                
                return message.content[0].text if message.content else None
            
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Claude API error (attempt {attempt + 1}): {e}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Claude API failed after {max_retries} attempts: {e}")
                    raise
    
    except ImportError:
        logger.error("anthropic library not installed")
        return None


async def call_cerebras(
    system_prompt: str,
    user_prompt: str,
    config: LLMConfig,
    max_retries: int = 3,
) -> Optional[str]:
    """Call Cerebras API with retry logic."""
    try:
        import httpx
        
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": config.model,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.cerebras.ai/v1/chat/completions",
                        json=payload,
                        headers=headers,
                        timeout=60.0,
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        return data["choices"][0]["message"]["content"]
                    elif response.status_code == 429:
                        # Rate limit
                        if attempt < max_retries - 1:
                            wait_time = 2 ** attempt
                            logger.warning(f"Cerebras rate limited, retrying in {wait_time}s")
                            await asyncio.sleep(wait_time)
                        else:
                            raise Exception("Rate limited after retries")
                    else:
                        raise Exception(f"Cerebras API error: {response.status_code} {response.text}")
            
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Cerebras error (attempt {attempt + 1}): {e}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Cerebras API failed after {max_retries} attempts: {e}")
                    raise
    
    except ImportError:
        logger.error("httpx library not installed")
        return None


async def call_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
) -> Optional[str]:
    """
    Call LLM (Claude or Cerebras) with structured error handling.
    
    Returns generated text or None if failed.
    """
    config = get_llm_config()
    if not config:
        logger.error("No LLM configured - returning None")
        return None
    
    logger.info(f"Calling {config.provider} with model {config.model}")
    
    try:
        if config.provider == "anthropic":
            config.temperature = temperature
            return await call_claude(system_prompt, user_prompt, config)
        elif config.provider == "cerebras":
            config.temperature = temperature
            return await call_cerebras(system_prompt, user_prompt, config)
        else:
            logger.error(f"Unknown LLM provider: {config.provider}")
            return None
    
    except Exception as e:
        logger.exception(f"LLM call failed: {e}")
        return None


async def parse_json_response(response: str, required_keys: List[str] = None) -> Optional[Dict[str, Any]]:
    """
    Parse JSON response from LLM with validation.
    
    Required keys: List of keys that must be present in JSON.
    """
    if not response:
        return None
    
    try:
        # Try to extract JSON from markdown code blocks
        if "```json" in response:
            start = response.index("```json") + 7
            end = response.index("```", start)
            json_str = response[start:end].strip()
        elif "```" in response:
            start = response.index("```") + 3
            end = response.index("```", start)
            json_str = response[start:end].strip()
        else:
            json_str = response
        
        data = json.loads(json_str)
        
        # Validate required keys
        if required_keys:
            missing = [k for k in required_keys if k not in data]
            if missing:
                logger.error(f"Missing required keys in response: {missing}")
                return None
        
        return data
    
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
        return None
    except Exception as e:
        logger.error(f"Error parsing response: {e}")
        return None


async def call_llm_for_code(
    goal: str,
    context: str,
    language: str = "JavaScript",
    instructions: str = "",
) -> Optional[Dict[str, str]]:
    """
    Call LLM to generate code with structured output.
    
    Returns dict with 'code' key containing generated code.
    """
    system_prompt = f"""You are an expert {language} developer. Generate production-ready {language} code.

Code must:
- Be complete and runnable
- Include all necessary imports
- Have proper error handling
- Follow {language} best practices
- Be properly formatted and indented

Respond with ONLY valid {language} code, no markdown, no explanation."""

    user_prompt = f"""Goal: {goal}

Context: {context}

{instructions}

Generate the complete {language} code now."""

    response = await call_llm(system_prompt, user_prompt, temperature=0.7)
    
    if not response:
        return None
    
    return {
        "code": response,
        "language": language,
        "length": len(response),
    }


async def call_llm_for_structured_output(
    task: str,
    context: str,
    schema_description: str = "",
) -> Optional[Dict[str, Any]]:
    """
    Call LLM to generate structured JSON output.
    
    Returns parsed JSON dict or None.
    """
    system_prompt = f"""You are a helpful assistant that generates structured data.

Always respond with ONLY valid JSON, no markdown, no explanation.

{schema_description}"""

    user_prompt = f"""Task: {task}

Context: {context}

Generate the JSON now."""

    response = await call_llm(system_prompt, user_prompt, temperature=0.3)
    
    if not response:
        return None
    
    return await parse_json_response(response)

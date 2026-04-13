"""
Cerebras LLM Integration for CrucibAI
Provides async interface to Cerebras API (llama-3.1-8b model)
Used for free tier and high-speed inference.
Uses streaming by default for reliability.
"""

import json
import logging
import os
from typing import Any, AsyncGenerator, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)

CEREBRAS_API_URL = "https://api.cerebras.ai/v1"
CEREBRAS_MODEL = "llama-3.1-8b"


class CerebrasClient:
    """Async client for Cerebras API - uses streaming by default with round-robin key rotation"""

    def __init__(self, api_key: Optional[str] = None):
        # Use provided key, or get next one from round-robin pool
        if api_key:
            self.api_key = api_key
        else:
            try:
                from cerebras_roundrobin import get_next_cerebras_key

                self.api_key = get_next_cerebras_key()
                logger.info(f"CerebrasClient: Using rotated API key (pool size: 5)")
            except Exception as e:
                logger.warning(f"Round-robin failed: {e}, falling back to env var")
                self.api_key = os.environ.get("CEREBRAS_API_KEY")

        if not self.api_key:
            raise ValueError("CEREBRAS_API_KEY not set in environment")

        self.session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session with proper headers"""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector()
            timeout = aiohttp.ClientTimeout(total=120)
            self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        return self.session

    async def close(self):
        """Close the session"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stream: bool = True,  # Default to streaming
    ) -> Dict[str, Any]:
        """
        Send a chat completion request to Cerebras using streaming.

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-2)
            top_p: Nucleus sampling parameter
            stream: Whether to stream (always True for reliability)

        Returns:
            Response dict with content, model, usage
        """

        # Always use streaming for reliability
        stream = True

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": CEREBRAS_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": stream,
        }

        try:
            session = await self._get_session()

            async with session.post(
                f"{CEREBRAS_API_URL}/chat/completions",
                headers=headers,
                json=payload,
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"Cerebras API error {resp.status}: {error_text}")
                    raise Exception(f"Cerebras API error {resp.status}: {error_text}")

                # Handle streaming response
                full_response = ""
                async for line in resp.content:
                    try:
                        line_str = line.decode("utf-8").strip()
                        if line_str.startswith("data: "):
                            data = line_str[6:]
                            if data == "[DONE]":
                                break
                            chunk = json.loads(data)
                            if "choices" in chunk and len(chunk["choices"]) > 0:
                                delta = chunk["choices"][0].get("delta", {})
                                if "content" in delta:
                                    full_response += delta["content"]
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        logger.debug(f"Stream parsing note: {e}")
                        continue

                return {
                    "content": full_response,
                    "model": CEREBRAS_MODEL,
                    "usage": {"total_tokens": len(full_response) // 4},
                }

        except Exception as e:
            logger.error(f"Cerebras chat completion failed: {e}")
            raise

    async def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat completion from Cerebras.

        Yields:
            Streamed text chunks
        """

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": CEREBRAS_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": True,
        }

        try:
            session = await self._get_session()

            async with session.post(
                f"{CEREBRAS_API_URL}/chat/completions",
                headers=headers,
                json=payload,
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"Cerebras stream error {resp.status}: {error_text}")
                    raise Exception(
                        f"Cerebras stream error {resp.status}: {error_text}"
                    )

                async for line in resp.content:
                    try:
                        line_str = line.decode("utf-8").strip()
                        if line_str.startswith("data: "):
                            data = line_str[6:]
                            if data == "[DONE]":
                                break
                            chunk = json.loads(data)
                            if "choices" in chunk and len(chunk["choices"]) > 0:
                                delta = chunk["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue

        except Exception as e:
            logger.error(f"Cerebras stream failed: {e}")
            raise

    async def extract_text(self, response: Dict[str, Any]) -> str:
        """Extract text from Cerebras response"""
        try:
            if "content" in response:
                return response["content"]
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            return ""

    async def get_usage(self, response: Dict[str, Any]) -> Dict[str, int]:
        """Extract token usage from response"""
        try:
            return response.get("usage", {})
        except:
            return {}


async def invoke_cerebras(
    messages: List[Dict[str, str]],
    max_tokens: int = 1024,
    temperature: float = 0.7,
) -> Dict[str, Any]:
    """
    Convenience function to invoke Cerebras with streaming.

    Args:
        messages: Chat messages
        max_tokens: Max response tokens
        temperature: Sampling temperature

    Returns:
        Response dict with content
    """

    client = CerebrasClient()
    try:
        response = await client.chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
        return response
    finally:
        await client.close()


async def invoke_cerebras_stream(
    messages: List[Dict[str, str]],
    max_tokens: int = 1024,
    temperature: float = 0.7,
) -> AsyncGenerator[str, None]:
    """
    Convenience function to stream Cerebras response.

    Yields:
        Text chunks
    """

    client = CerebrasClient()
    try:
        async for chunk in client.chat_completion_stream(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        ):
            yield chunk
    finally:
        await client.close()

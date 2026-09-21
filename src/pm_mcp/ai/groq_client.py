"""
Shared async Groq client for use inside MCP tool methods.

Usage:
    from pm_mcp.ai.groq_client import ask_groq, ask_groq_json

    text = await ask_groq("Write a one-liner description for: Mobile Banking App")
    obj  = await ask_groq_json("Return JSON with keys 'tasks' and 'risks' for: ...")
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from groq import AsyncGroq

from pm_mcp.config import get_app_settings

logger = logging.getLogger(__name__)

# Best model for structured/tool-calling tasks on this account
_MODEL = "openai/gpt-oss-120b"
_FALLBACK_MODEL = "openai/gpt-oss-20b"


def _get_client() -> AsyncGroq:
    settings = get_app_settings()
    api_key = settings.groq_api_key or os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured. Add it to your .env file.")
    return AsyncGroq(api_key=api_key)


async def ask_groq(
    prompt: str,
    *,
    system: str = "You are a helpful project management assistant. Be concise and practical.",
    temperature: float = 0.4,
    max_tokens: int = 1024,
) -> str:
    """
    Send a plain-text prompt to Groq and return the text response.
    Falls back to the smaller model if the primary is unavailable.
    """
    client = _get_client()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    for model in (_MODEL, _FALLBACK_MODEL):
        try:
            resp = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = resp.choices[0].message.content or ""
            return content.strip()
        except Exception as exc:
            logger.warning("Groq model %s failed: %s", model, exc)
            if model == _FALLBACK_MODEL:
                raise
    return ""


async def ask_groq_json(
    prompt: str,
    *,
    system: str = "You are a helpful project management assistant. Always respond with valid JSON only, no markdown fences.",
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> Any:
    """
    Ask Groq to return a JSON object/array.
    Strips markdown code fences if the model wraps its output.
    Returns the parsed Python object, or raises on parse failure.
    """
    raw = await ask_groq(
        prompt,
        system=system,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    # Strip optional ```json ... ``` fences
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```", 2)[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.rsplit("```", 1)[0].strip()
    return json.loads(cleaned)

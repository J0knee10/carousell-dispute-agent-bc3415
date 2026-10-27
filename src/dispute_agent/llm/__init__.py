"""Pick an LLM provider from config.yaml (or the LLM_PROVIDER environment variable)."""

from __future__ import annotations

from typing import Literal

from ..config import gemini_api_key, load_config
from .base import CallStats, LLMClient, LLMError, RateLimitError

Role = Literal["judge", "generator"]

__all__ = ["CallStats", "LLMClient", "LLMError", "RateLimitError", "get_llm", "gemini_available"]


def gemini_available() -> bool:
    return gemini_api_key() is not None


def get_llm(role: Role = "judge", provider: str | None = None) -> LLMClient:
    cfg = load_config()["llm"]
    provider = provider or cfg["provider"]
    if provider == "mock":
        from .mock import MockLLM

        return MockLLM()
    if provider == "gemini":
        key = gemini_api_key()
        if not key:
            raise LLMError("GEMINI_API_KEY is not set. Add it to .env, or use provider 'mock'.")
        from .gemini import GeminiClient

        model = cfg["judge_model"] if role == "judge" else cfg["generator_model"]
        temperature = cfg["temperature"] if role == "judge" else cfg["generator_temperature"]
        return GeminiClient(
            model=model,
            api_key=key,
            temperature=temperature,
            min_seconds_between_calls=cfg["min_seconds_between_calls"],
            max_retry_wait_seconds=cfg["max_retry_wait_seconds"],
        )
    raise LLMError(f"Unknown LLM provider '{provider}'. Use 'gemini' or 'mock'.")

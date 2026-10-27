"""Pick an LLM provider from config.yaml (or the LLM_PROVIDER environment variable)."""

from __future__ import annotations

from typing import Literal

from ..config import gemini_api_key, load_config
from .base import CallStats, LLMClient, LLMError, RateLimitError, T

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

        if role == "judge":
            models, temperature = [cfg["judge_model"]], cfg["temperature"]
        else:
            models = cfg["generator_model"]
            models = [models] if isinstance(models, str) else list(models)
            temperature = cfg["generator_temperature"]
        clients = [
            GeminiClient(
                model=m,
                api_key=key,
                temperature=temperature,
                min_seconds_between_calls=cfg["min_seconds_between_calls"],
                max_retry_wait_seconds=cfg["max_retry_wait_seconds"],
            )
            for m in models
        ]
        return clients[0] if len(clients) == 1 else FallbackLLM(clients)
    raise LLMError(f"Unknown LLM provider '{provider}'. Use 'gemini' or 'mock'.")


class FallbackLLM:
    """Use the first model until its quota runs out, then move to the next."""

    def __init__(self, clients: list):
        self.clients = clients
        self.index = 0
        self.stats = CallStats()

    @property
    def name(self) -> str:
        return self.clients[self.index].name

    @property
    def model(self) -> str:
        return self.clients[self.index].model

    def generate(self, **kwargs) -> T:
        while True:
            client = self.clients[self.index]
            try:
                result = client.generate(**kwargs)
            except RateLimitError:
                if self.index + 1 >= len(self.clients):
                    raise
                self.index += 1
                continue
            self.stats.record(kwargs.get("task", ""), 0.0)
            return result

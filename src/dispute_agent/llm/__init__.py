"""Pick an LLM provider from config.yaml (or the LLM_PROVIDER environment variable)."""

from __future__ import annotations

from typing import Literal

from ..config import PROVIDERS, gemini_api_key, judge_model, load_config, openai_api_key
from .base import CallStats, LLMClient, LLMError, RateLimitError, T

Role = Literal["judge", "generator"]

__all__ = [
    "CallStats", "LLMClient", "LLMError", "RateLimitError", "PROVIDERS",
    "get_llm", "gemini_available", "openai_available", "local_ollama_available", "available_providers",
]


def gemini_available() -> bool:
    return gemini_api_key() is not None


def openai_available() -> bool:
    return openai_api_key() is not None


def local_ollama_available() -> bool:
    from .ollama import ollama_available

    return ollama_available(load_config()["llm"]["ollama"].get("host", "http://localhost:11434"))


def available_providers() -> list[str]:
    """Providers that can run here: a key is set, or the Ollama server answers."""
    checks = {"gemini": gemini_available, "ollama": local_ollama_available, "openai": openai_available}
    return [p for p in PROVIDERS if p == "mock" or checks[p]()]


def get_llm(role: Role = "judge", provider: str | None = None, model: str | None = None) -> LLMClient:
    """A client for the judge (or the dispute generator). `model` overrides config.yaml."""
    cfg = load_config()["llm"]
    provider = provider or cfg["provider"]
    temperature = cfg["temperature"] if role == "judge" else cfg["generator_temperature"]
    if provider == "mock":
        from .mock import MockLLM

        return MockLLM()
    if provider == "ollama":
        from .ollama import OllamaClient

        o = cfg["ollama"]
        return OllamaClient(
            model=model or judge_model("ollama"), host=o.get("host", "http://localhost:11434"), temperature=temperature,
            num_ctx=o.get("num_ctx", 16384), timeout_seconds=o.get("timeout_seconds", 600),
        )
    if provider == "openai":
        key = openai_api_key()
        if not key:
            raise LLMError("OPENAI_API_KEY is not set. Add it to .env, or use another provider.")
        from .openai_client import OpenAIClient

        return OpenAIClient(model=model or judge_model("openai"), api_key=key, temperature=temperature)
    if provider == "gemini":
        key = gemini_api_key()
        if not key:
            raise LLMError("GEMINI_API_KEY is not set. Add it to .env, or use provider 'mock'.")
        from .gemini import GeminiClient

        if model:
            models = [model]
        elif role == "judge":
            models = [judge_model("gemini")]
        else:
            models = cfg["generator_model"]
            models = [models] if isinstance(models, str) else list(models)
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
    raise LLMError(f"Unknown LLM provider '{provider}'. Use one of: {', '.join(PROVIDERS)}.")


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
            before = (client.stats.tokens_in, client.stats.tokens_out, client.stats.seconds)
            try:
                result = client.generate(**kwargs)
            except RateLimitError:
                if self.index + 1 >= len(self.clients):
                    raise
                self.index += 1
                continue
            self.stats.record(
                kwargs.get("task", ""), client.stats.seconds - before[2],
                tokens_in=client.stats.tokens_in - before[0], tokens_out=client.stats.tokens_out - before[1],
            )
            return result

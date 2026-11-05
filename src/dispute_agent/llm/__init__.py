"""Pick an LLM provider from config.yaml (or the LLM_PROVIDER environment variable)."""

from __future__ import annotations

from typing import Literal

from ..config import PROVIDERS, gemini_api_key, judge_model, load_config, openai_api_key
from .base import CallStats, LLMClient, LLMError, RateLimitError, T

Role = Literal["judge", "generator"]

__all__ = [
    "CallStats", "LLMClient", "LLMError", "RateLimitError", "PROVIDERS", "CloudFallbackLLM", "fallback_provider",
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


def fallback_provider(provider: str) -> str | None:
    """The provider the app falls back to for `provider` (config llm.fallback), if its key is set."""
    fb = (load_config()["llm"].get("fallback") or {}).get(provider)
    if fb == "openai" and openai_available():
        return fb
    if fb == "gemini" and gemini_available():
        return fb
    return None


def get_llm(
    role: Role = "judge", provider: str | None = None, model: str | None = None, for_app: bool = False
) -> LLMClient:
    """A client for the judge (or the dispute generator). `model` overrides config.yaml.

    for_app=True is what the Streamlit app uses (evaluations never do): a failed call goes
    to the fallback provider in config.yaml (Gemini -> OpenAI).
    """
    cfg = load_config()["llm"]
    provider = provider or cfg["provider"]
    if for_app and role == "judge" and fallback_provider(provider):
        primary = get_llm(role, provider, model)
        backup = get_llm(role, fallback_provider(provider))
        return CloudFallbackLLM(primary, backup)
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

        o = cfg.get("openai", {})
        return OpenAIClient(
            model=model or judge_model("openai"), api_key=key, temperature=temperature,
            reasoning_effort=o.get("reasoning_effort"),
        )
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


class CloudFallbackLLM:
    """Try the primary provider; if a call fails, make that call with the backup.

    A daily-quota error switches to the backup for as long as this client lives
    (the app keeps one per browser session; the quota will not come back for
    hours); any other failure falls back for that call only. The backup's own quota
    (OpenAI's free usage tier: about 50 requests a day) is the main limit;
    max_backup_calls is an optional extra cap.
    """

    def __init__(self, primary, backup, max_backup_calls: int | None = None):
        self.primary, self.backup = primary, backup
        self.max_backup_calls = max_backup_calls
        self.backup_calls = 0
        self.primary_exhausted = False
        self.last = primary
        self.stats = CallStats()

    @property
    def name(self) -> str:
        return self.last.name

    @property
    def model(self) -> str:
        return self.last.model

    @property
    def using_backup(self) -> bool:
        return self.last is self.backup

    def _record(self, client, before, task: str) -> None:
        self.stats.record(
            task, client.stats.seconds - before[2],
            tokens_in=client.stats.tokens_in - before[0], tokens_out=client.stats.tokens_out - before[1],
        )

    def generate(self, **kwargs) -> T:
        task = kwargs.get("task", "")
        if not self.primary_exhausted:
            before = (self.primary.stats.tokens_in, self.primary.stats.tokens_out, self.primary.stats.seconds)
            try:
                result = self.primary.generate(**kwargs)
                self.last = self.primary
                self._record(self.primary, before, task)
                return result
            except RateLimitError as e:
                self.primary_exhausted = e.daily
                error: LLMError = e
            except LLMError as e:
                error = e
        else:
            error = LLMError(f"{self.primary.name} quota exhausted earlier in this session")
        if self.max_backup_calls is not None and self.backup_calls >= self.max_backup_calls:
            raise RateLimitError(
                f"{error} The fallback ({self.backup.name}) reached its limit of {self.max_backup_calls} calls for this session.",
                daily=True, model=self.backup.model,
            )
        self.backup_calls += 1
        before = (self.backup.stats.tokens_in, self.backup.stats.tokens_out, self.backup.stats.seconds)
        result = self.backup.generate(**kwargs)
        self.last = self.backup
        self._record(self.backup, before, task)
        return result


class FallbackLLM:
    """Use the first model until its quota runs out, then move to the next (dispute generation)."""

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

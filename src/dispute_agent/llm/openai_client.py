"""OpenAI API provider (paid), using structured outputs.

`chat.completions.parse` turns the pydantic schema into a strict JSON schema
and returns the parsed object. An optional SpendTracker caps what the app can
spend per calendar month.
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import openai

from .base import CallStats, LLMError, RateLimitError, T

# Reasoning models accept only the default temperature.
_NO_TEMPERATURE = ("gpt-5", "o1", "o3", "o4")
_REASONING = ("gpt-5", "o1", "o3", "o4")


def _retry_after(err: Exception, default: float) -> float:
    """Seconds OpenAI asks us to wait (retry-after-ms or retry-after headers), capped at 60."""
    headers = getattr(getattr(err, "response", None), "headers", None) or {}
    for name, scale in (("retry-after-ms", 0.001), ("retry-after", 1.0)):
        try:
            if headers.get(name) is not None:
                return min(60.0, float(headers.get(name)) * scale)
        except (TypeError, ValueError):
            pass
    return min(60.0, default)


class SpendTracker:
    """Running OpenAI spend for the current calendar month, kept in a small JSON file.

    Cost = tokens x the per-million prices in config.yaml (reasoning tokens are billed
    as output). Once the month's spend reaches the budget, calls are refused. The file
    lives in outputs/, so on Streamlit Community Cloud it resets when the app restarts:
    the OpenAI project's own budget is the hard limit.
    """

    def __init__(self, file: Path, budget_sgd: float, usd_to_sgd: float, prices: dict[str, dict[str, float]]):
        self.file = Path(file)
        self.budget_sgd = budget_sgd
        self.usd_to_sgd = usd_to_sgd
        self.prices = prices
        self.lock = threading.Lock()

    def _month(self) -> str:
        return datetime.now().strftime("%Y-%m")

    def _load(self) -> dict:
        try:
            data = json.loads(self.file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        return data if data.get("month") == self._month() else {"month": self._month(), "usd": 0.0, "calls": 0}

    def spent_sgd(self) -> float:
        return round(self._load()["usd"] * self.usd_to_sgd, 4)

    def check(self, model: str) -> None:
        if model not in self.prices:
            raise LLMError(f"No price for {model} in config.yaml llm.openai.prices_usd_per_million; refusing paid calls.")
        if self.spent_sgd() >= self.budget_sgd:
            raise RateLimitError(
                f"OpenAI budget reached: S${self.spent_sgd():.2f} of S${self.budget_sgd:.0f} this month.",
                daily=True, model=model,
            )

    def add(self, model: str, tokens_in: int, tokens_out: int) -> float:
        p = self.prices[model]
        usd = (tokens_in * p["input"] + tokens_out * p["output"]) / 1_000_000
        with self.lock:
            data = self._load()
            data["usd"] = round(data["usd"] + usd, 6)
            data["calls"] = data.get("calls", 0) + 1
            self.file.parent.mkdir(parents=True, exist_ok=True)
            self.file.write_text(json.dumps(data), encoding="utf-8")
        return usd


class OpenAIClient:
    def __init__(
        self,
        model: str,
        api_key: str,
        temperature: float = 0.0,
        timeout_seconds: float = 180,
        reasoning_effort: str | None = None,
        spend: SpendTracker | None = None,
    ):
        self.name = "openai"
        self.model = model
        self.temperature = temperature
        self.reasoning_effort = reasoning_effort
        self.spend = spend
        self.client = openai.OpenAI(api_key=api_key, timeout=timeout_seconds, max_retries=0)
        self.stats = CallStats()

    def generate(
        self,
        *,
        task: str,
        system: str,
        prompt: str,
        schema: type[T],
        hints: dict[str, Any] | None = None,
        temperature: float | None = None,
    ) -> T:
        kwargs: dict[str, Any] = {}
        if not self.model.startswith(_NO_TEMPERATURE):
            kwargs["temperature"] = self.temperature if temperature is None else temperature
        if self.reasoning_effort and self.model.startswith(_REASONING):
            kwargs["reasoning_effort"] = self.reasoning_effort
        if self.spend:
            self.spend.check(self.model)
        failures = 0
        rate_limits = 0
        while True:
            start = time.monotonic()
            try:
                resp = self.client.chat.completions.parse(
                    model=self.model,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                    response_format=schema,
                    **kwargs,
                )
            except openai.RateLimitError as e:
                # insufficient_quota means the account is out of credit: waiting will not help.
                # Otherwise it is a per-minute limit: wait as long as OpenAI asks, then retry.
                daily = "insufficient_quota" in str(e)
                rate_limits += 1
                if daily or rate_limits > 12:
                    raise RateLimitError(f"OpenAI quota exhausted for {self.model}: {e}", daily=daily, model=self.model) from e
                time.sleep(_retry_after(e, default=5.0 * rate_limits) + 1)
                continue
            except (openai.APIConnectionError, openai.InternalServerError) as e:
                failures += 1
                if failures > 3:
                    raise LLMError(f"OpenAI request failed: {e}") from e
                time.sleep(10 * failures)
                continue
            except openai.APIError as e:
                raise LLMError(f"OpenAI rejected the request: {e}") from e
            usage = resp.usage
            tokens_in = getattr(usage, "prompt_tokens", 0) or 0
            tokens_out = getattr(usage, "completion_tokens", 0) or 0
            self.stats.record(task, time.monotonic() - start, tokens_in=tokens_in, tokens_out=tokens_out)
            if self.spend:
                self.spend.add(self.model, tokens_in, tokens_out)
            message = resp.choices[0].message
            if message.parsed is not None:
                return message.parsed
            raise LLMError(f"OpenAI returned no {schema.__name__}: {message.refusal or 'empty reply'}")

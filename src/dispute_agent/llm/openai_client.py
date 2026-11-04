"""OpenAI API provider (paid), using structured outputs.

`chat.completions.parse` turns the pydantic schema into a strict JSON schema
and returns the parsed object.
"""

from __future__ import annotations

import time
from typing import Any

import openai

from .base import CallStats, LLMError, RateLimitError, T

# Reasoning models accept only the default temperature.
_NO_TEMPERATURE = ("gpt-5", "o1", "o3", "o4")


class OpenAIClient:
    def __init__(self, model: str, api_key: str, temperature: float = 0.0, timeout_seconds: float = 120):
        self.name = "openai"
        self.model = model
        self.temperature = temperature
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
        failures = 0
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
                daily = "insufficient_quota" in str(e)
                failures += 1
                if daily or failures > 5:
                    raise RateLimitError(f"OpenAI quota exhausted for {self.model}: {e}", daily=daily, model=self.model) from e
                time.sleep(10 * failures)
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
            self.stats.record(
                task, time.monotonic() - start,
                tokens_in=getattr(usage, "prompt_tokens", 0), tokens_out=getattr(usage, "completion_tokens", 0),
            )
            message = resp.choices[0].message
            if message.parsed is not None:
                return message.parsed
            raise LLMError(f"OpenAI returned no {schema.__name__}: {message.refusal or 'empty reply'}")

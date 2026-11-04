"""Local models served by Ollama (https://ollama.com).

Uses Ollama's own /api/chat endpoint with a JSON schema in `format`, which
constrains the model's output to the schema. The schema also goes in the prompt
so the model sees the field descriptions. Nothing leaves the machine.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

import httpx
from pydantic import ValidationError

from .base import CallStats, LLMError, T


def ollama_available(host: str, timeout: float = 1.5) -> bool:
    try:
        return httpx.get(f"{host.rstrip('/')}/api/tags", timeout=timeout).status_code == 200
    except httpx.HTTPError:
        return False


def installed_models(host: str, timeout: float = 3.0) -> list[str]:
    try:
        resp = httpx.get(f"{host.rstrip('/')}/api/tags", timeout=timeout)
        resp.raise_for_status()
    except httpx.HTTPError:
        return []
    return sorted(m["name"] for m in resp.json().get("models", []))


class OllamaClient:
    def __init__(
        self,
        model: str,
        host: str = "http://localhost:11434",
        temperature: float = 0.0,
        num_ctx: int = 16384,
        timeout_seconds: float = 600,
    ):
        self.name = "ollama"
        self.model = model
        self.host = host.rstrip("/")
        self.temperature = temperature
        self.num_ctx = num_ctx
        self.http = httpx.Client(timeout=timeout_seconds)
        # Thinking models (Qwen 3 and others) are asked not to think: it multiplies
        # the time per case on a consumer GPU. Models without a thinking mode
        # reject the flag, so it is dropped after the first refusal.
        self.send_think_flag = True
        self.stats = CallStats()

    def _chat(self, body: dict) -> dict:
        try:
            resp = self.http.post(f"{self.host}/api/chat", json=body)
        except httpx.ConnectError as e:
            raise LLMError(f"Ollama is not reachable at {self.host}. Start Ollama, or pick another provider.") from e
        except httpx.HTTPError as e:
            raise LLMError(f"Ollama request failed: {e}") from e
        if resp.status_code == 404:
            raise LLMError(f"Ollama has no model '{self.model}'. Run: ollama pull {self.model}")
        if resp.status_code >= 400:
            raise LLMError(f"Ollama error ({resp.status_code}): {resp.text[:300]}")
        return resp.json()

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
        json_schema = schema.model_json_schema()
        body: dict[str, Any] = {
            "model": self.model,
            "stream": False,
            "format": json_schema,
            "options": {
                "temperature": self.temperature if temperature is None else temperature,
                "num_ctx": self.num_ctx,
            },
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": f"{prompt}\n\nReply with only a JSON object matching this JSON Schema:\n{json.dumps(json_schema)}",
                },
            ],
        }
        bad_output = 0
        while True:
            if self.send_think_flag:
                body["think"] = False
            else:
                body.pop("think", None)
            start = time.monotonic()
            try:
                data = self._chat(body)
            except LLMError as e:
                if self.send_think_flag and "think" in str(e).lower():
                    self.send_think_flag = False
                    continue
                raise
            self.stats.record(
                task, time.monotonic() - start,
                tokens_in=data.get("prompt_eval_count", 0), tokens_out=data.get("eval_count", 0),
            )
            # Ollama silently drops the start of a prompt that does not fit the window.
            if (data.get("prompt_eval_count") or 0) + (data.get("eval_count") or 0) >= self.num_ctx:
                raise LLMError(f"Prompt did not fit {self.model}'s {self.num_ctx}-token window; raise llm.ollama.num_ctx")
            text = (data.get("message", {}).get("content") or "").strip()
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
            try:
                return schema.model_validate_json(text)
            except ValidationError as e:
                bad_output += 1
                if bad_output > 1:
                    raise LLMError(f"{self.model} output did not match {schema.__name__}: {e}") from e

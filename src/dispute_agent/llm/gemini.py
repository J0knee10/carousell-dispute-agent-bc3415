"""Google Gemini provider (free tier friendly).

Paces calls, retries short per-minute rate limits in place, and raises
RateLimitError for anything longer (such as the daily quota) so batch jobs can
save progress and resume later.
"""

from __future__ import annotations

import re
import threading
import time
from typing import Any

from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from .base import CallStats, LLMError, RateLimitError, T

_pace_lock = threading.Lock()
_last_call = 0.0


def _pace(min_interval: float) -> None:
    global _last_call
    with _pace_lock:
        wait = _last_call + min_interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()


def parse_rate_limit(err: errors.APIError) -> tuple[float | None, bool]:
    """Read the suggested retry delay and whether a per-day quota was hit."""
    text = str(err.details)
    delay = None
    m = re.search(r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)s", text)
    if m:
        delay = float(m.group(1))
    daily = bool(re.search(r"PerDay", text))
    return delay, daily


class GeminiClient:
    def __init__(
        self,
        model: str,
        api_key: str,
        temperature: float = 0.0,
        min_seconds_between_calls: float = 4.5,
        max_retry_wait_seconds: float = 90,
        timeout_seconds: float = 120,
    ):
        self.name = "gemini"
        self.model = model
        self.temperature = temperature
        self.min_interval = min_seconds_between_calls
        self.max_retry_wait = max_retry_wait_seconds
        # A timeout stops a stalled request hanging a batch run, and turning off the
        # SDK's own retries lets the loop below decide when to wait and when to stop.
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=int(timeout_seconds * 1000), retry_options=types.HttpRetryOptions(attempts=1)
            ),
        )
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
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=self.temperature if temperature is None else temperature,
            response_mime_type="application/json",
            response_schema=schema,
        )
        server_errors = 0
        rate_limits = 0
        bad_output = 0
        while True:
            _pace(self.min_interval)
            start = time.monotonic()
            try:
                resp = self.client.models.generate_content(model=self.model, contents=prompt, config=config)
            except errors.ClientError as e:
                if e.code != 429:
                    raise LLMError(f"Gemini rejected the request ({e.code}): {e.message}") from e
                delay, daily = parse_rate_limit(e)
                rate_limits += 1
                if daily or delay is None or delay > self.max_retry_wait or rate_limits > 5:
                    raise RateLimitError(
                        f"Gemini quota exhausted for {self.model}: {e.message}",
                        retry_after_seconds=delay,
                        daily=daily,
                        model=self.model,
                    ) from e
                time.sleep(delay + 1)
                continue
            except errors.ServerError as e:
                # 503 "high demand" spikes are common on the free tier; back off and retry.
                server_errors += 1
                if server_errors > 4:
                    raise LLMError(f"Gemini server error ({e.code}): {e.message}") from e
                time.sleep(10 * server_errors)
                continue
            except Exception as e:  # network errors and timeouts from the HTTP client
                server_errors += 1
                if server_errors > 4:
                    raise LLMError(f"Gemini request failed: {e}") from e
                time.sleep(10 * server_errors)
                continue

            self.stats.record(task, time.monotonic() - start)
            parsed = resp.parsed
            if isinstance(parsed, schema):
                return parsed
            try:
                return schema.model_validate_json(resp.text or "")
            except ValidationError as e:
                bad_output += 1
                if bad_output > 1:
                    raise LLMError(f"Gemini output did not match {schema.__name__}: {e}") from e

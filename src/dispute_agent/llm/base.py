"""The interface every LLM provider implements.

Agent code only ever calls `generate(task=..., system=..., prompt=..., schema=...)`
and gets back a validated pydantic object, so swapping Gemini for a local model
means writing one new class.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    """The provider failed or returned output that does not fit the schema."""


class RateLimitError(LLMError):
    """Quota exhausted. `daily` means waiting a minute will not help."""

    def __init__(self, message: str, retry_after_seconds: float | None = None, daily: bool = False, model: str = ""):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds
        self.daily = daily
        self.model = model


@dataclass
class CallStats:
    calls: int = 0
    seconds: float = 0.0
    by_task: dict[str, int] = field(default_factory=dict)

    def record(self, task: str, seconds: float) -> None:
        self.calls += 1
        self.seconds += seconds
        self.by_task[task] = self.by_task.get(task, 0) + 1


class LLMClient(Protocol):
    name: str
    model: str
    stats: CallStats

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
        """Return `schema` filled in. `hints` carries raw case data that only the mock uses."""
        ...

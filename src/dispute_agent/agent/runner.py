"""Run the agent on a case: up to the staff pause, then resume with a decision."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Iterator

from langgraph.types import Command

from ..schemas import DisputeCase


@dataclass
class RunResult:
    thread_id: str
    state: dict
    seconds: float
    llm_calls: int
    waiting_for_staff: bool
    trace: list[dict] = field(default_factory=list)


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def new_thread(case_id: str) -> str:
    return f"{case_id}-{uuid.uuid4().hex[:8]}"


def run_to_review(graph, case: DisputeCase, llm=None, thread_id: str | None = None, proposed_rule: str | None = None) -> RunResult:
    """Run every step up to the staff decision and return the state there."""
    thread_id = thread_id or new_thread(case.case_id)
    calls_before = llm.stats.calls if llm else 0
    start = time.monotonic()
    inputs: dict[str, Any] = {"case": case.model_dump(mode="json")}
    if proposed_rule:
        inputs["proposed_rule"] = proposed_rule
    graph.invoke(inputs, _config(thread_id))
    snap = graph.get_state(_config(thread_id))
    return RunResult(
        thread_id=thread_id,
        state=dict(snap.values),
        seconds=round(time.monotonic() - start, 2),
        llm_calls=(llm.stats.calls - calls_before) if llm else 0,
        waiting_for_staff=bool(snap.next),
        trace=list(snap.values.get("trace", [])),
    )


def stream_to_review(graph, case: DisputeCase, thread_id: str) -> Iterator[tuple[str, dict]]:
    """Yield (node, update) as each step finishes; used by the UI to show progress."""
    for chunk in graph.stream({"case": case.model_dump(mode="json")}, _config(thread_id), stream_mode="updates"):
        for node, update in chunk.items():
            if node != "__interrupt__":
                yield node, update or {}


def resume(graph, thread_id: str, decision: dict) -> dict:
    """Give the staff decision ({action, outcome, note, ...}) and finish the run."""
    graph.invoke(Command(resume=decision), _config(thread_id))
    return dict(graph.get_state(_config(thread_id)).values)


def current_state(graph, thread_id: str) -> dict:
    return dict(graph.get_state(_config(thread_id)).values)

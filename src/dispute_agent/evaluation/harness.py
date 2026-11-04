"""Run the agent or the single-prompt baseline over a set of cases.

Each prediction is appended to outputs/runs/<run>/<system>.jsonl as soon as it
is made, so a run stopped by the API quota resumes where it left off.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable

from ..config import path
from ..llm import LLMClient, LLMError, RateLimitError
from ..rag.chunker import load_clauses
from ..rag.store import PolicyStore
from ..schemas import BaselineJudgement, DisputeCase
from ..agent import prompts
from ..agent.graph import build_graph
from ..agent.runner import run_to_review


class QuotaExhausted(RuntimeError):
    def __init__(self, err: RateLimitError, done: int, remaining: int):
        super().__init__(str(err))
        self.err = err
        self.done = done
        self.remaining = remaining


def run_dir(run: str) -> Path:
    d = path("outputs.runs_dir") / run
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_records(run: str, system: str) -> list[dict]:
    file = run_dir(run) / f"{system}.jsonl"
    if not file.exists():
        return []
    with open(file, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_run_info(run: str, info: dict) -> None:
    file = run_dir(run) / "run_info.json"
    old = json.loads(file.read_text(encoding="utf-8")) if file.exists() else {}
    old.update(info)
    file.write_text(json.dumps(old, indent=2), encoding="utf-8")


def predict_agent(graph, llm: LLMClient, case: DisputeCase) -> dict:
    tokens = (llm.stats.tokens_in, llm.stats.tokens_out)
    r = run_to_review(graph, case, llm)
    st = r.state
    rec = st["recommendation"]
    retrieved = {c["clause_id"] for c in st.get("clauses", [])} | {"PROPOSED-1"}
    raw_cites = st.get("adjudication", {}).get("citations", [])
    return {
        "predicted_outcome": rec["outcome"],
        "predicted_eligible": rec["eligible"],
        "eligibility_status": rec["eligibility_status"],
        "confidence": rec["confidence"],
        "escalate": rec["escalate"],
        "escalation_reasons": rec["escalation_reasons"],
        "citations": rec["citations"],
        # What the judge cited before the citation check removed clauses it was never shown.
        "raw_invalid_citations": sorted(set(raw_cites) - retrieved) if rec["decided_by"] == "llm" else [],
        "reasons": rec["reasons"],
        "decided_by": rec["decided_by"],
        "retrieved": [c["clause_id"] for c in st.get("clauses", [])],
        "tool_calls": st.get("tool_calls", []),
        "judge_rounds": st.get("judge_rounds", 0),
        "gaps": [g["gap_type"] for g in st.get("claims", {}).get("gaps", [])],
        "partial_refund_percent": rec.get("partial_refund_percent", 0),
        "seconds": r.seconds,
        "llm_calls": r.llm_calls,
        "tokens_in": llm.stats.tokens_in - tokens[0],
        "tokens_out": llm.stats.tokens_out - tokens[1],
    }


def predict_baseline(llm: LLMClient, case: DisputeCase, threshold: float) -> dict:
    clauses = [c.as_retrieved() for c in load_clauses()]
    valid = {c.clause_id for c in clauses}
    calls = llm.stats.calls
    tokens = (llm.stats.tokens_in, llm.stats.tokens_out)
    start = time.monotonic()
    j = llm.generate(
        task="baseline", system=prompts.BASELINE_SYSTEM, prompt=prompts.baseline_prompt(case, clauses),
        schema=BaselineJudgement, hints={"case": case.model_dump(mode="json")},
    )
    cites = [c for c in j.citations if c in valid]
    return {
        "predicted_outcome": j.outcome if j.eligible else "decline",
        "predicted_eligible": j.eligible,
        "eligibility_status": "eligible" if j.eligible else "not_covered",
        "confidence": j.confidence,
        # The baseline has no review gate; treat low confidence as its escalation.
        "escalate": j.confidence < threshold,
        "escalation_reasons": [],
        "citations": cites,
        "invalid_citations": sorted(set(j.citations) - valid),
        "raw_invalid_citations": sorted(set(j.citations) - valid),
        "reasons": j.reasons,
        "decided_by": "llm",
        "retrieved": [],
        "gaps": [],
        "partial_refund_percent": 0,
        "seconds": round(time.monotonic() - start, 2),
        "llm_calls": llm.stats.calls - calls,
        "tokens_in": llm.stats.tokens_in - tokens[0],
        "tokens_out": llm.stats.tokens_out - tokens[1],
    }


def run_system(
    system: str,
    cases: list[DisputeCase],
    llm: LLMClient,
    store: PolicyStore,
    run: str,
    threshold: float,
    progress: Callable[[str], None] = print,
    use_retrieval: bool = True,
    retry_errors: bool = True,
    retrieval: str = "per_gap",
) -> list[dict]:
    """retry_errors=False keeps a case that failed (e.g. invalid JSON) as a failure instead of re-running it."""
    file = run_dir(run) / f"{system}.jsonl"
    records = load_records(run, system)
    done = {r["case_id"] for r in records if retry_errors is False or not r.get("error")}
    todo = [c for c in cases if c.case_id not in done]
    progress(f"[{system}] {len(done)} done, {len(todo)} to run")
    graph = (
        build_graph(llm, store, draft_messages=False, decision_logger=None, use_retrieval=use_retrieval, retrieval=retrieval)
        if system == "agent" else None
    )
    for i, case in enumerate(todo):
        try:
            pred = predict_agent(graph, llm, case) if system == "agent" else predict_baseline(llm, case, threshold)
        except RateLimitError as e:
            raise QuotaExhausted(e, done=len(done) + i, remaining=len(todo) - i) from e
        except LLMError as e:
            pred = {"error": str(e)[:500]}
        record = {"case_id": case.case_id, "system": system, "provider": llm.name, "model": llm.model, **pred}
        with open(file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        shown = pred.get("predicted_outcome", "ERROR")
        progress(f"[{system}] {case.case_id}: {shown}" + (" (escalated)" if pred.get("escalate") else ""))
    return [r for r in load_records(run, system) if not r.get("error")]

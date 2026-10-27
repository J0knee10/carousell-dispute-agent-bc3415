"""What-if policy test: re-judge past disputes under a proposed rule change.

For each eligible case the claim matching and the current-policy judgement are
cached, so testing another proposed rule costs one LLM call per case.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Callable

from ..agent import prompts
from ..agent.eligibility import check_eligibility
from ..agent.graph import retrieve_for_gaps
from ..config import load_config, path
from ..data.cases import case_ids_for, cases_by_id
from ..llm import LLMClient, RateLimitError, get_llm
from ..rag.store import get_store
from ..schemas import Adjudication, ClaimMatchResult, DisputeCase, RetrievedClause
from .harness import QuotaExhausted


def _cache_file() -> Path:
    d = path("outputs.whatif_dir")
    d.mkdir(parents=True, exist_ok=True)
    return d / "baseline_cache.jsonl"


def _load_cache(model: str) -> dict[str, dict]:
    file = _cache_file()
    if not file.exists():
        return {}
    out = {}
    with open(file, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec["model"] == model:
                out[rec["case_id"]] = rec
    return out


def _judge(llm: LLMClient, case: DisputeCase, claims: dict, clauses: list[RetrievedClause], rule: str | None) -> Adjudication:
    return llm.generate(
        task="whatif_adjudication" if rule else "adjudication",
        system=prompts.JUDGE_SYSTEM,
        prompt=prompts.judge_prompt(case, json.dumps(claims["gaps"], indent=1), clauses, rule),
        schema=Adjudication,
        hints={"case": case.model_dump(mode="json"), "gaps": claims["gaps"], "clauses": [c.model_dump() for c in clauses], "proposed_rule": rule},
    )


def current_policy_result(llm: LLMClient, case: DisputeCase, cache: dict[str, dict]) -> dict:
    """Claims, clauses and outcome under today's policy (cached per case and model)."""
    if case.case_id in cache:
        return cache[case.case_id]
    claims = llm.generate(
        task="claim_matching", system=prompts.CLAIMS_SYSTEM, prompt=prompts.claims_prompt(case),
        schema=ClaimMatchResult, hints={"case": case.model_dump(mode="json")},
    )
    max_clauses = load_config()["rag"]["max_clauses"]
    clauses = retrieve_for_gaps(get_store(), case.dispute.reason, claims, max_clauses)
    adj = _judge(llm, case, claims.model_dump(), clauses, None)
    rec = {
        "case_id": case.case_id,
        "model": llm.model,
        "claims": claims.model_dump(),
        "clauses": [c.model_dump() for c in clauses],
        "outcome": adj.outcome,
        "reasons": adj.reasons,
    }
    with open(_cache_file(), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    cache[case.case_id] = rec
    return rec


def run_whatif(
    change: str,
    split: str = "dev",
    limit: int | None = None,
    provider: str | None = None,
    case_ids: list[str] | None = None,
    llm: LLMClient | None = None,
    progress: Callable[[str], None] = print,
) -> tuple[Path, dict]:
    llm = llm or get_llm(provider=provider)
    by_id = cases_by_id()
    ids = case_ids or case_ids_for(split)
    cases = [by_id[i] for i in ids if check_eligibility(by_id[i]).status == "eligible"]
    if limit:
        cases = cases[:limit]
    cache = _load_cache(llm.model)
    rows = []
    store = get_store()
    for i, case in enumerate(cases):
        try:
            before = current_policy_result(llm, case, cache)
            clauses = [RetrievedClause.model_validate(c) for c in before["clauses"]]
            # Also fetch clauses the proposed rule touches, so the judge sees what it changes.
            known = {c.clause_id for c in clauses}
            clauses += [c for c in store.retrieve(change, k=2) if c.clause_id not in known]
            after = _judge(llm, case, before["claims"], clauses, change)
        except RateLimitError as e:
            raise QuotaExhausted(e, done=i, remaining=len(cases) - i) from e
        flipped = after.outcome != before["outcome"]
        rows.append(
            {
                "case_id": case.case_id,
                "title": case.listing.title,
                "difficulty": case.meta.difficulty,
                "gaps": [g["gap_type"] for g in before["claims"]["gaps"]],
                "before": before["outcome"],
                "after": after.outcome,
                "flipped": flipped,
                "uses_proposed_rule": "PROPOSED-1" in after.citations,
                "reasons_after": after.reasons,
            }
        )
        progress(f"{case.case_id}: {before['outcome']} -> {after.outcome}" + ("  FLIPPED" if flipped else ""))

    n = len(rows)
    flips = [r for r in rows if r["flipped"]]
    refund = lambda key: sum(r[key] != "decline" for r in rows)  # noqa: E731
    summary = {
        "change": change,
        "model": f"{llm.name}/{llm.model}",
        "cases": n,
        "flipped": len(flips),
        "flip_rate": round(len(flips) / n, 3) if n else None,
        "transitions": dict(Counter(f"{r['before']} -> {r['after']}" for r in flips)),
        "buyer_win_rate_before": round(refund("before") / n, 3) if n else None,
        "buyer_win_rate_after": round(refund("after") / n, 3) if n else None,
    }
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = path("outputs.whatif_dir") / f"whatif_{stamp}.json"
    out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2), encoding="utf-8")
    return out, {"summary": summary, "rows": rows}

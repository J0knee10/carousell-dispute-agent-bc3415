"""Evaluation metrics from the project brief, computed from saved predictions."""

from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean, median

from ..schemas import OUTCOMES


def latest_by_case(records: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in records:
        if not r.get("error"):
            out[r["case_id"]] = r
    return out


def _share(n: int, d: int) -> float | None:
    return round(n / d, 3) if d else None


def failed_cases(records: list[dict]) -> dict[str, str]:
    """Cases with an error record and no successful prediction: case_id -> error."""
    ok = {r["case_id"] for r in records if not r.get("error")}
    return {r["case_id"]: r["error"] for r in records if r.get("error") and r["case_id"] not in ok}


def compute_metrics(records: list[dict], labels: dict[str, dict], meta: dict[str, dict]) -> dict:
    """records: predictions; labels: case_id -> {outcome, eligible, source}; meta: case_id -> {difficulty, ...}.

    A case where the model never gave a valid answer (for example invalid JSON
    twice) counts as a wrong decision and as handed to a person, so a model that
    fails often cannot look better by being scored on fewer cases.
    """
    preds = latest_by_case(records)
    rows = []
    for cid in failed_cases(records):
        lab = labels.get(cid)
        if lab and lab.get("outcome"):
            rows.append({
                "case_id": cid, "difficulty": meta[cid]["difficulty"], "label": lab["outcome"],
                "label_eligible": lab["eligible"], "label_source": lab["source"], "pred": None, "pred_eligible": None,
                "correct": False, "escalate": True, "citations": [], "invalid_citations": [],
                "raw_invalid_citations": [], "seconds": None, "llm_calls": None, "decided_by": "failed",
                "tool_calls": [], "tokens_in": None, "tokens_out": None,
            })
    for cid, p in preds.items():
        lab = labels.get(cid)
        if not lab or not lab.get("outcome"):
            continue
        rows.append(
            {
                "case_id": cid,
                "difficulty": meta[cid]["difficulty"],
                "label": lab["outcome"],
                "label_eligible": lab["eligible"],
                "label_source": lab["source"],
                "pred": p["predicted_outcome"],
                "pred_eligible": p["predicted_eligible"],
                "correct": p["predicted_outcome"] == lab["outcome"],
                "escalate": bool(p.get("escalate")),
                "citations": p.get("citations", []),
                "invalid_citations": p.get("invalid_citations", []),
                "raw_invalid_citations": p.get("raw_invalid_citations", p.get("invalid_citations", [])),
                "seconds": p.get("seconds", 0.0),
                "llm_calls": p.get("llm_calls", 0),
                "decided_by": p.get("decided_by", "llm"),
                "tool_calls": p.get("tool_calls", []),
                "tokens_in": p.get("tokens_in"),
                "tokens_out": p.get("tokens_out"),
            }
        )
    n = len(rows)
    if n == 0:
        return {"n": 0}

    def acc(subset: list[dict]) -> float | None:
        return _share(sum(r["correct"] for r in subset), len(subset))

    by_diff = defaultdict(list)
    for r in rows:
        by_diff[r["difficulty"]].append(r)

    buyer_wins = [r for r in rows if r["label"] != "decline"]
    seller_wins = [r for r in rows if r["label"] == "decline"]
    direction = sum((r["pred"] == "decline") == (r["label"] == "decline") for r in rows)

    inel = [r for r in rows if not r["label_eligible"]]
    wrong = [r for r in rows if not r["correct"]]
    right = [r for r in rows if r["correct"]]
    judged = [r for r in rows if r["decided_by"] == "llm"]

    confusion = {lab: {pred: 0 for pred in OUTCOMES} for lab in OUTCOMES}
    for r in rows:
        if r["pred"] in OUTCOMES:
            confusion[r["label"]][r["pred"]] += 1

    answered = [r for r in rows if r["decided_by"] != "failed"]
    secs = [r["seconds"] for r in answered] or [0.0]
    calls = [r["llm_calls"] for r in answered] or [0]
    tok_in = [r["tokens_in"] for r in answered if r["tokens_in"] is not None]
    tok_out = [r["tokens_out"] for r in answered if r["tokens_out"] is not None]
    return {
        "n": n,
        "label_sources": dict(Counter(r["label_source"] for r in rows)),
        "decision_accuracy": acc(rows),
        "accuracy_by_difficulty": {d: {"n": len(v), "accuracy": acc(v)} for d, v in sorted(by_diff.items())},
        "direction_accuracy": _share(direction, n),
        "buyer_win_accuracy": {"n": len(buyer_wins), "accuracy": acc(buyer_wins)},
        "seller_win_accuracy": {"n": len(seller_wins), "accuracy": acc(seller_wins)},
        "eligibility_accuracy": _share(sum(r["pred_eligible"] == r["label_eligible"] for r in rows), n),
        "ineligible_flagged": {"n": len(inel), "share": _share(sum(not r["pred_eligible"] for r in inel), len(inel))},
        "cited_at_least_one_clause": _share(sum(bool(r["citations"]) for r in judged), len(judged)),
        "invented_citation_rate": _share(sum(bool(r["invalid_citations"]) for r in rows), n),
        # Before the agent's citation check: how often the model itself cited a clause it was not shown.
        "raw_invented_citation_rate": _share(sum(bool(r["raw_invalid_citations"]) for r in judged), len(judged)),
        "failed": {"n": n - len(answered), "share": _share(n - len(answered), n)},
        "tool_use": {
            "judged": len(judged),
            "cases_using_search": _share(sum(bool(r["tool_calls"]) for r in judged), len(judged)),
            "searches": sum(len(r["tool_calls"]) for r in judged),
        },
        "tokens_per_case": {
            "input": round(mean(tok_in)) if tok_in else None,
            "output": round(mean(tok_out)) if tok_out else None,
        },
        "escalation": {
            "escalated_share": _share(sum(r["escalate"] for r in rows), n),
            "wrong_decisions_escalated": _share(sum(r["escalate"] for r in wrong), len(wrong)),
            "right_decisions_escalated": _share(sum(r["escalate"] for r in right), len(right)),
            "accuracy_when_not_escalated": acc([r for r in rows if not r["escalate"]]),
        },
        "seconds_per_case": {"mean": round(mean(secs), 2), "median": round(median(secs), 2)},
        "llm_calls_per_case": round(mean(calls), 2),
        "confusion": confusion,
        "wrong_cases": [{"case_id": r["case_id"], "label": r["label"], "pred": r["pred"], "difficulty": r["difficulty"], "escalated": r["escalate"]} for r in wrong],
    }

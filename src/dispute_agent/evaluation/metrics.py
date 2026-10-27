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


def compute_metrics(records: list[dict], labels: dict[str, dict], meta: dict[str, dict]) -> dict:
    """records: predictions; labels: case_id -> {outcome, eligible, source}; meta: case_id -> {difficulty, ...}."""
    preds = latest_by_case(records)
    rows = []
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
                "seconds": p.get("seconds", 0.0),
                "llm_calls": p.get("llm_calls", 0),
                "decided_by": p.get("decided_by", "llm"),
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

    secs = [r["seconds"] for r in rows]
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
        "escalation": {
            "escalated_share": _share(sum(r["escalate"] for r in rows), n),
            "wrong_decisions_escalated": _share(sum(r["escalate"] for r in wrong), len(wrong)),
            "right_decisions_escalated": _share(sum(r["escalate"] for r in right), len(right)),
            "accuracy_when_not_escalated": acc([r for r in rows if not r["escalate"]]),
        },
        "seconds_per_case": {"mean": round(mean(secs), 2), "median": round(median(secs), 2)},
        "llm_calls_per_case": round(mean(r["llm_calls"] for r in rows), 2),
        "confusion": confusion,
        "wrong_cases": [{"case_id": r["case_id"], "label": r["label"], "pred": r["pred"], "difficulty": r["difficulty"], "escalated": r["escalate"]} for r in wrong],
    }

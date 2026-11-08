"""Retrieval accuracy: does search return the clause that answers each test query?

Expected clauses are written as phrases from the policy text rather than clause
IDs, so the test set survives changes to the chunking.
"""

from __future__ import annotations

import json

from ..config import path
from ..rag.chunker import load_clauses
from ..rag.store import get_store


def load_queries() -> list[dict]:
    with open(path("data.retrieval_queries"), encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def expected_ids(phrases: list[str]) -> set[str]:
    out = set()
    for clause in load_clauses():
        text = clause.text.lower()
        if any(p.lower() in text for p in phrases):
            out.add(clause.clause_id)
    return out


def evaluate_retrieval(k: int = 3, modes: tuple[str, ...] = ("dense", "lexical", "hybrid")) -> dict:
    store = get_store()
    queries = load_queries()
    results: dict = {"k": k, "n_queries": len(queries), "modes": {}, "misses": {}}
    for mode in modes:
        hit1 = hitk = rr = 0.0
        misses = []
        for q in queries:
            want = expected_ids(q["expected_phrases"])
            got = [c.clause_id for c in store.retrieve(q["query"], k=k, mode=mode)]
            rank = next((i + 1 for i, cid in enumerate(got) if cid in want), None)
            hit1 += rank == 1
            hitk += rank is not None
            rr += 1 / rank if rank else 0
            if rank is None:
                misses.append({"query": q["query"], "expected": sorted(want), "got": got})
        n = len(queries)
        results["modes"][mode] = {
            "hit@1": round(hit1 / n, 3),
            f"hit@{k}": round(hitk / n, 3),
            "mrr": round(rr / n, 3),
        }
        results["misses"][mode] = misses
    return results


def hybrid_behind(results: dict, depth: int = 8) -> list[dict]:
    """Queries hybrid search misses in its top k although dense or lexical search alone finds the clause.

    Gives each mode's rank of the answer within the top `depth`, to show what rank fusion did.
    """
    hybrid_missed = {m["query"] for m in results["misses"].get("hybrid", [])}
    others_missed = [{m["query"] for m in results["misses"].get(mode, [])} for mode in ("dense", "lexical")]
    behind = [q for q in hybrid_missed if any(q not in missed for missed in others_missed)]
    if not behind:
        return []
    store = get_store()
    out = []
    for q in load_queries():
        if q["query"] not in behind:
            continue
        want = expected_ids(q["expected_phrases"])
        ranks = {}
        for mode in ("dense", "lexical", "hybrid"):
            got = [c.clause_id for c in store.retrieve(q["query"], k=depth, mode=mode)]
            ranks[mode] = next((i + 1 for i, cid in enumerate(got) if cid in want), None)
        out.append({"query": q["query"], "expected": sorted(want), "ranks": ranks})
    return out


def format_hybrid_behind(rows: list[dict], results: dict, depth: int = 8) -> str:
    """Explain why hybrid search can find fewer answers in the top k than one method alone."""
    if not rows:
        return ""
    k, n = results["k"], results["n_queries"]
    missed = {mode: len(results["misses"][mode]) for mode in results["misses"]}
    m = results["modes"]
    rank = lambda r: str(r) if r else f"below {depth}"  # noqa: E731
    lines = [
        f"## Why hybrid search finds fewer answers in the top {k} than keyword search",
        "",
        f"Hybrid search misses {missed['hybrid']} of {n} queries in the top {k}, keyword search alone "
        f"{missed['lexical']} and embeddings alone {missed['dense']}. Hybrid search merges the two rankings by "
        "reciprocal rank fusion, which favours clauses that both methods rank fairly high, so a clause that only "
        f"one method ranks high can be pushed down. That happened on these queries, where one method alone had "
        f"the answer in its top {k}:",
        "",
    ]
    for r in rows:
        ex = ", ".join(r["expected"])
        lines.append(
            f"- {r['query']}: the answer ({ex}) is ranked {rank(r['ranks']['lexical'])} by keyword search, "
            f"{rank(r['ranks']['dense'])} by embeddings and {rank(r['ranks']['hybrid'])} by hybrid search."
        )
    lines += [
        "",
        f"The trade is worth it for the agent: hybrid search puts the right clause first far more often "
        f"(Hit@1 {m['hybrid']['hit@1']:.0%} against {m['lexical']['hit@1']:.0%} and {m['dense']['hit@1']:.0%}) "
        f"and has the best MRR ({m['hybrid']['mrr']:.2f}), so the clause the judge reads first is usually the right one.",
    ]
    return "\n".join(lines)


def format_retrieval_table(by_k: dict[int, dict]) -> str:
    """One table across several k: hit rates at each k, and MRR over the top 3 (what the agent uses)."""
    ks = sorted(by_k)
    first = by_k[ks[0]]
    lines = [
        f"Retrieval accuracy on {first['n_queries']} test queries (`data/eval/retrieval_queries.jsonl`). "
        "Hit@k: the clause that answers the query is in the top k results. MRR: mean of 1 / rank of that clause "
        "within the top 3 (0 if missing). The agent takes the top 3 per query.",
        "",
        "| Mode | " + " | ".join(f"Hit@{k}" for k in ks) + " | MRR (top 3) |",
        "|---|" + "---|" * (len(ks) + 1),
    ]
    mrr_k = 3 if 3 in by_k else ks[-1]
    for mode in first["modes"]:
        cells = [f"{by_k[k]['modes'][mode][f'hit@{k}']:.0%}" for k in ks]
        lines.append(f"| {mode} | " + " | ".join(cells) + f" | {by_k[mrr_k]['modes'][mode]['mrr']:.2f} |")
    return "\n".join(lines)

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


def format_retrieval(results: dict) -> str:
    k = results["k"]
    lines = [
        f"Retrieval accuracy on {results['n_queries']} test queries (data/eval/retrieval_queries.jsonl)",
        "",
        f"| Mode | Hit@1 | Hit@{k} | MRR |",
        "|---|---|---|---|",
    ]
    for mode, m in results["modes"].items():
        lines.append(f"| {mode} | {m['hit@1']:.0%} | {m[f'hit@{k}']:.0%} | {m['mrr']:.2f} |")
    return "\n".join(lines)
